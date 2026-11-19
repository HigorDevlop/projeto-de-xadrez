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
    if plan and 'personal_lines' not in plan:
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
    valid = lines_for(plan)
    for key in list(sessions):
        lesson=valid.get(sessions[key].get('line_id'))
        custom=sessions[key].get('custom_line')
        prefix=lesson.get('family_prefix',[]) if lesson else []
        if not lesson or (custom and prefix and custom['moves'][:len(prefix)]!=prefix):
            del sessions[key]
    for key in valid:
        old = plan['retention'].get(key)
        progress.setdefault(key, dict(learned=bool(old), mastery=min(10, old.get('level', 0)+1) if old else 0,
                                     due=old.get('due') if old else None, last_review=None))
    # Preserve a pre-existing free-practice lesson, including its current board.
    if not plan.get('practice_migrated'):
        old = next(iter(plan.get('training_days', {}).values()), None)
        if old and old.get('line_id') in valid and old['phase'] != 'complete':
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
    lessons=list(lines_for(plan).values())
    foundations=[line for line in lessons if line.get('stage')=='foundation']
    bases_ready=all(progress[line['id']]['learned'] for line in foundations)
    branch_ready={}
    for index, line in enumerate(lessons):
        item = progress[line['id']]
        unlocked=previous_learned or item['learned']
        if 'personal_lines' in plan: unlocked=True
        if line.get('stage')=='depth':
            unlocked=item['learned'] or (bases_ready and branch_ready.get(line['branch'],True))
            branch_ready[line['branch']]=bool(item['learned'])
        result.append(dict(line, number=index+1, **item, unlocked=unlocked))
        previous_learned = item['learned']
    from opening_rounds import cycle,next_lesson,target
    if cycle(plan) is not None:
        upcoming,source=next_lesson(plan,result)
        selected=upcoming or source
        level,_=target(plan)
        for item in result:
            item['unlocked']=bool(item['learned'] or selected and item['id']==selected['id'])
            if item.get('lesson_moves',5)>level: item['unlocked']=False
    return result


def begin_line(plan, identifier, intent='learn'):
    from opening_rounds import cycle
    round_state=cycle(plan)
    if intent == 'train':
        # New material must be taught before its memory quiz; learned lines
        # remain directly available for the four-state review.
        progress = ensure_course(plan).get(identifier)
        intent = 'learn' if round_state is not None else 'practice' if progress and progress['learned'] else 'learn'
    if intent not in ('learn', 'master', 'explore', 'practice'):
        return None
    line = next((item for item in course_lines(plan) if item['id'] == identifier), None)
    if not line or line.get('needs_preparation') or (intent in ('learn', 'practice') and not line['unlocked']) or (intent == 'master' and not line['learned']):
        return None
    sessions = plan['practice_sessions']
    session_key = identifier + ':' + intent
    saved = sessions.get(session_key)
    if saved and round_state is not None and saved.get('course_round')!=round_state['round']:
        if saved.get('course_round') is None and saved['phase']!='complete':
            saved['course_round']=round_state['round']
        else: saved=None
    if saved and saved['phase'] != 'complete' and saved.get('practice_intent') == intent:
        if saved.get('mode')=='quiz' and line.get('stage') and saved.get('course_round') is None:
            scope=sorted(item['id'] for item in course_lines(plan) if item['id']==identifier or item['learned'])
            if saved.get('quiz_scope') != scope or saved.get('quiz_policy')!=2:
                from opening_training_state import _start_quiz
                _start_quiz(plan,saved)
                saved['revision']+=1
        plan['practice_current'] = session_key
        return saved
    scratch = dict(plan, start=str(today()), end=str(today()), training_days={}, retention={})
    session = session_for(scratch, today())
    session.update(queue=[identifier], total=1, learned=[], mastered=[], recovered=[], failed=[])
    _start_line(scratch, session, lines_for(plan))
    session['practice_intent'] = intent
    if round_state is not None:
        from opening_rounds import phase_number
        session.update(course_round=round_state['round'],course_phase=phase_number(plan))
    if intent == 'master':
        session.update(mode='recall', hint=False)
    elif intent == 'practice':
        from opening_training_state import _start_quiz
        _start_quiz(plan, session)
    sessions[session_key] = session
    plan['practice_current'] = session_key
    return session


def active_session(plan):
    ensure_course(plan)
    session = plan['practice_sessions'].get(plan.get('practice_current'))
    if session:
        from opening_rounds import ensure_phase_session
        ensure_phase_session(plan,session)
        lesson=lines_for(plan).get(session['line_id'])
        if lesson and lesson.get('needs_preparation'):
            return None
        if lesson and lesson.get('stage') and session.get('mode')=='quiz' and session.get('quiz_policy') not in (2,3):
            from opening_training_state import _start_quiz
            _start_quiz(plan,session)
            session['revision']+=1
        from opening_repetition import ensure_quiz_states
        ensure_quiz_states(plan, session)
        from opening_error_review import migrate
        migrate(plan, session)
    return session


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


def receive_move(plan, event, now, classroom_token=None):
    """Every browser attempt receives an authoritative revision, even if rejected."""
    from opening_training_state import submit_move
    session = active_session(plan)
    if not session:
        return False
    if classroom_token:
        import classroom
        actor=classroom.identity(classroom_token)
        if not actor:
            raise PermissionError('Acesso à sala revogado. Procure o Professor.')
    if isinstance(event, dict) and isinstance(event.get('attempts'), list):
        # The browser may already be several positions ahead. Replay in order;
        # duplicate acknowledgements never count twice or alter the current FEN.
        changed = False
        for attempt in event['attempts'][:256]:
            if not isinstance(attempt, dict):
                continue
            if attempt.get('revision') != f"{session['token']}:{session['revision']}":
                continue
            changed = receive_move(plan, attempt, now, classroom_token) or changed
        return changed
    revision = f"{session['token']}:{session['revision']}"
    accepted = not session.get('paused') and not session.get('ui_checkpoint') and submit_move(plan, session, event, now)
    if accepted and classroom_token and actor['role']=='student' and session['mode']!='learn' and session.get('practice_intent')!='explore':
        classroom.record(classroom_token,'opening:'+event['revision'],'opening',
            correct=session['feedback']['correct'],line=session['line_id'],states=session.get('quiz_states',{}))
    if accepted and session.get('reference_mode') and session['mode'] != 'quiz' and not session['feedback']['correct']:
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


def resync_board(plan, event, classroom_token=None):
    """Recover an undelivered move once; an already accepted revision is ignored."""
    from opening_training_state import submit_move
    session = active_session(plan)
    if not session or not isinstance(event, dict):
        return False
    if isinstance(event.get('attempts'), list):
        return receive_move(plan, event, time.time(), classroom_token)
    if event.get('revision') != f"{session['token']}:{session['revision']}":
        return False
    return receive_move(plan, event, time.time(), classroom_token)


def next_phase(plan, session):
    return continue_line(plan, session)


def record_completion(plan, session):
    if session.get('practice_recorded'):
        return
    if (session.get('mode')!='quiz' or session.get('quiz_queue') or not session.get('quiz_states')
            or any(value!='correct' for value in session['quiz_states'].values())):
        return
    if session.get('course_phase') and session['course_phase']%5==0 and len(session['quiz_states'])<50:
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
    from opening_achievements import record_achievements
    line=lines_for(plan)[session['line_id']]
    record_achievements(plan,session,line)
    from opening_rounds import complete
    complete(plan,session,line)
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
