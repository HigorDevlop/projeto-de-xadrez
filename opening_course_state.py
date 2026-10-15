"""Persistent opening courses, guided lessons and spaced mastery reviews."""
from copy import deepcopy
from datetime import date, timedelta
import time

from opening_repertoires import selected_courses
from opening_training_state import (create_repertoire_plan, session_for, lines_for,
    _start_line, advance, continue_line, INTERVALS)
from preparation_state import today
from opening_ranking_state import rank_summary, award_completion


def select_course(plan, username, identifier):
    selected_courses([identifier])  # Validate before changing or saving anything.
    library = dict((plan or {}).get('practice_library', {}))
    if plan:
        old_key = '+'.join(plan['repertoire_ids'])
        library[old_key] = deepcopy({k: v for k, v in plan.items() if k != 'practice_library'})
    selected = deepcopy(library.get(identifier))
    if selected is None:
        selected = create_repertoire_plan(username, [identifier], today(), today())
    selected['practice_library'] = library
    return selected


def ensure_course(plan):
    progress = plan.setdefault('practice_progress', {})
    sessions = plan.setdefault('practice_sessions', {})
    for key in lines_for(plan):
        old = plan['retention'].get(key)
        progress.setdefault(key, dict(learned=bool(old), mastery=min(10, old.get('level', 0)+1) if old else 0,
                                     due=old.get('due') if old else None, last_review=None))
    # Preserve a pre-existing free-practice lesson, including its current board.
    if not plan.get('practice_migrated'):
        old = next(iter(plan.get('training_days', {}).values()), None)
        if old and old.get('line_id') and old['phase'] != 'complete':
            saved = deepcopy(old)
            saved.setdefault('mode', 'recall')
            saved.setdefault('learned', [])
            saved.setdefault('attempted', bool(saved.get('errors', 0)))
            saved.setdefault('animation', None)
            saved.setdefault('marks', {})
            saved.setdefault('quiz_queue', [])
            saved.setdefault('quiz_retry', [])
            saved['queue'] = [saved['line_id']] if old['queue'] else []
            saved['total'] = 1
            saved['practice_intent'] = 'learn'
            sessions[saved['line_id'] + ':learn'] = saved
        plan['practice_migrated'] = True
    return progress


def course_lines(plan):
    progress = ensure_course(plan)
    result = []
    previous_learned = True
    for index, line in enumerate(lines_for(plan).values()):
        item = progress[line['id']]
        result.append(dict(line, number=index+1, **item, unlocked=previous_learned or item['learned']))
        previous_learned = item['learned']
    return result


def begin_line(plan, identifier, intent='learn'):
    if intent not in ('learn', 'master', 'explore'):
        return None
    line = next((item for item in course_lines(plan) if item['id'] == identifier), None)
    if not line or (intent == 'learn' and not line['unlocked']) or (intent == 'master' and not line['learned']):
        return None
    sessions = plan['practice_sessions']
    session_key = identifier + ':' + intent
    saved = sessions.get(session_key)
    if saved and saved['phase'] != 'complete' and saved.get('practice_intent') == intent:
        plan['practice_current'] = session_key
        return saved
    scratch = dict(plan, start=str(today()), end=str(today()), training_days={}, retention={})
    session = session_for(scratch, today())
    session.update(queue=[identifier], total=1, learned=[], mastered=[], recovered=[], failed=[])
    _start_line(scratch, session, lines_for(plan))
    session['practice_intent'] = intent
    if intent == 'master':
        session.update(mode='recall', hint=False)
    sessions[session_key] = session
    plan['practice_current'] = session_key
    return session


def active_session(plan):
    ensure_course(plan)
    return plan['practice_sessions'].get(plan.get('practice_current'))


def settle(plan, session, now):
    if session.get('paused') or session.get('ui_checkpoint') or session['phase'] == 'complete':
        return False
    # Teaching waits for the learner, including sessions saved during the old demo.
    session.pop('demo_at', None)
    changed = advance(plan, session, now, auto_continue=False)
    if session['phase'] == 'line_end':
        if session.get('practice_intent') == 'explore':
            session['phase'] = 'complete'
            changed = True
        elif session['mode'] == 'quiz' and not session['queue']:
            record_completion(plan, session)
            session['phase'] = 'complete'
            changed = True
        elif now >= session['next_at']:
            if session.get('reference_mode') and not session.pop('reference_continue', False):
                session['ui_checkpoint'] = {'kind': 'stage', 'mode': session['mode']}
                return True
            changed = continue_line(plan, session) or changed
    return changed


def receive_move(plan, event, now):
    """Every browser attempt receives an authoritative revision, even if rejected."""
    from opening_training_state import submit_move
    session = active_session(plan)
    if not session:
        return False
    if isinstance(event, dict) and isinstance(event.get('attempts'), list):
        # The browser may already be several positions ahead. Replay in order;
        # duplicate acknowledgements never count twice or alter the current FEN.
        changed = False
        for attempt in event['attempts'][:256]:
            if not isinstance(attempt, dict):
                continue
            if attempt.get('revision') != f"{session['token']}:{session['revision']}":
                continue
            changed = receive_move(plan, attempt, now) or changed
        return changed
    revision = f"{session['token']}:{session['revision']}"
    accepted = not session.get('paused') and not session.get('ui_checkpoint') and submit_move(plan, session, event, now)
    if accepted and session.get('reference_mode') and not session['feedback']['correct']:
        from opening_training_state import expected_move
        session['ui_checkpoint'] = {'kind': 'error', 'wrong': event['uci'],
                                    'expected': expected_move(plan, session)}
        return True
    if accepted and session['mode'] == 'quiz' and session['phase'] in ('feedback', 'restart'):
        # Feedback is painted immediately by the browser. No server timer/second
        # network round trip is needed to make the next preloaded question playable.
        settle(plan, session, session['next_at'])
    elif accepted:
        settle_immediate(plan, session)
    if not accepted and (not isinstance(event, dict) or event.get('revision') == revision):
        session['revision'] += 1
    return True


def settle_immediate(plan, session):
    """Resolve the reply and stage transitions in one update, without timers."""
    changed = False
    for _ in range(8):
        if session.get('paused') or session.get('ui_checkpoint') or session['phase'] in ('answer', 'complete'):
            break
        changed = settle(plan, session, session['next_at']) or changed
    session['animation'] = None
    return changed


def resync_board(plan, event):
    """Recover an undelivered move once; an already accepted revision is ignored."""
    from opening_training_state import submit_move
    session = active_session(plan)
    if not session or not isinstance(event, dict):
        return False
    if isinstance(event.get('attempts'), list):
        return receive_move(plan, event, time.time())
    if event.get('revision') != f"{session['token']}:{session['revision']}":
        return False
    return receive_move(plan, event, time.time())


def next_phase(plan, session):
    return continue_line(plan, session)


def record_completion(plan, session):
    if session.get('practice_recorded'):
        return
    item = ensure_course(plan)[session['line_id']]
    item['learned'] = True
    day = str(today())
    clean = session['line_id'] not in session['failed']
    if item['last_review'] != day:
        item['mastery'] = min(10, item['mastery'] + 1) if clean else max(1, item['mastery'] - 1)
    item['last_review'] = day
    interval = INTERVALS[min(max(0, item['mastery']-1), len(INTERVALS)-1)] if clean else 1
    item['due'] = str(date.fromisoformat(day) + timedelta(days=interval))
    award_completion(plan, session)
    from opening_reference_progress import record_activity
    record_activity(plan, session)
    session['practice_recorded'] = True


def course_summary(plan):
    lines = course_lines(plan)
    return dict(learned=sum(item['learned'] for item in lines), total=len(lines),
                **rank_summary(plan),
                due=sum(item['learned'] and (item['due'] or str(today())) <= str(today()) for item in lines))


def opening_rankings(plan):
    """Personal ranking; the active course overrides its older library snapshot."""
    from opening_repertoires import catalog
    library = dict((plan or {}).get('practice_library', {}))
    if plan:
        library['+'.join(plan['repertoire_ids'])] = plan
    rows = []
    for course in catalog():
        saved = library.get(course['id'])
        summary = course_summary(deepcopy(saved)) if saved else dict(
            learned=0, total=len(course['lines']), due=0, **rank_summary())
        rows.append(dict(id=course['id'], title=course['title'], side=course['side'], **summary))
    rows.sort(key=lambda row: (-row['points'], row['title']))
    previous, position = None, 0
    for index, row in enumerate(rows):
        score = row['points']
        if score != previous:
            position = index + 1
        row['position'] = position
        previous = score
    return rows
