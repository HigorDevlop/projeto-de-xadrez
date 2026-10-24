"""Guided opening lessons, active recall, whole-line retries and scheduling."""
from datetime import date, timedelta
from uuid import uuid4
import random
import chess

from opening_repertoires import selected_courses
from preparation_state import new_plan, today
from opening_repetition import next_status, reinsert_index, ensure_quiz_states, learner_plies, quiz_state_key

INTERVALS = (1, 3, 7, 14, 30)


def create_repertoire_plan(username, ids, start, end):
    courses = selected_courses(ids)
    plan = new_plan(username, start, end,
                    [{'id': c['id'], 'opening': c['title'], 'side': c['side']} for c in courses])
    plan.update(repertoire_mode=True, repertoire_ids=list(ids), training_days={}, retention={})
    return plan


def lines_for(plan):
    allowed=plan.get('classroom_line_ids')
    if 'personal_lines' in plan:
        return {line['id']: line for line in plan['personal_lines']
                if allowed is None or line['id'] in allowed}
    courses=selected_courses(plan['repertoire_ids'])
    lines=[line for course in courses for line in course['lines']]
    for line in plan.get('course_extensions',[]):
        course=next((course for course in courses if course['id']==line.get('course_id')),None)
        if course and line['moves'][:len(course['family_prefix'])]==course['family_prefix']:
            # A prepared foundation replaces the shorter bundled draft of its branch.
            if line.get('stage')=='foundation':
                lines=[item for item in lines if not (item.get('branch')==line.get('branch') and item.get('stage')=='foundation' and item.get('needs_preparation'))]
            if not any(item['id']==line['id'] for item in lines): lines.append(line)
    if plan.get('course_extensions'):
        lines.sort(key=lambda item:(0 if item.get('stage')=='foundation' else 1,item.get('branch',0),item.get('lesson_moves',0),item['id']))
    return {line['id']:line for line in lines if allowed is None or line['id'] in allowed}


def session_for(plan, day=None):
    day = str(day or today())
    if not plan['start'] <= day <= plan['end']:
        return None
    if day not in plan['training_days']:
        lines = lines_for(plan)
        due = [key for key in lines if plan['retention'].get(key, {}).get('due', day) <= day]
        session = dict(day=day, token=uuid4().hex, revision=0, queue=due, total=len(due),
                       ply=0, history=[], errors=0, line_error=False, failed=[], mastered=[],
                       recovered=[], tested=0, first_correct=0, feedback=None, hint=False,
                       phase='start' if due else 'complete', next_at=0, mode='learn',
                       learned=[], attempted=False)
        plan['training_days'][day] = session
        if due:
            _start_line(plan, session, lines)
    session = plan['training_days'][day]
    # Saved sessions from before guided lessons retain their current position
    # and recall statistics. New, unseen lines still receive an introduction.
    session.setdefault('mode', 'recall')
    session.setdefault('learned', [])
    session.setdefault('attempted', bool(session['errors']))
    session.setdefault('animation', None)
    session.setdefault('marks', {})
    session.setdefault('quiz_queue', [])
    session.setdefault('quiz_retry', [])
    ensure_quiz_states(plan, session)
    return session


def current_line(plan, session):
    if session.get('quiz_bank') and session.get('mode') == 'quiz':
        return session['quiz_bank'][str(session['quiz_key'])]['line']
    return session.get('custom_line') or lines_for(plan).get(session.get('line_id'))


def board_for(session):
    board = chess.Board()
    for uci in session['history']:
        board.push_uci(uci)
    return board


def _start_line(plan, session, lines):
    session.pop('quiz_bank', None)
    session.pop('quiz_key', None)
    session.update(ply=0, history=[], errors=0, line_error=False, feedback=None, hint=False,
                   animation=None, next_at=0, attempted=False, marks={}, display_marks={})
    line = lines[session['queue'][0]]
    context = line.get('context_plies', 0)
    session.update(ply=context, history=list(line['moves'][:context]))
    session['line_id'] = line['id']
    known = line['id'] in plan['retention'] or line['id'] in session['learned']
    session['mode'] = 'recall' if known else 'learn'
    session['phase'] = 'answer' if context or line['side'] == 'white' else 'opponent'
    session['hint'] = session['mode'] == 'learn' and session['phase'] == 'answer'
    session['revision'] += 1


def expected_move(plan, session):
    line = current_line(plan, session)
    return line['moves'][session['ply']] if line and session['ply'] < len(line['moves']) else None


def _record_attempt(session, correct):
    if session.get('mode', 'recall') != 'learn' and not session.get('attempted', bool(session['errors'])):
        session['tested'] += 1
        session['first_correct'] += int(correct)
    session['attempted'] = True


def _mark_for_retry(session):
    if session.get('mode', 'recall') != 'learn':
        session['line_error'] = True
        key = session['line_id']
        if key not in session['failed']:
            session['failed'].append(key)


def request_hint(plan, session):
    """Reveal a move immediately; assisted recall must be repeated unaided."""
    if session['phase'] != 'answer' or not expected_move(plan, session) or session['hint']:
        return False
    _record_attempt(session, False)
    if session.get('practice_intent') != 'explore' and session.get('mode') != 'learn':
        session['requested_hint'] = True
    session['marks'].setdefault(str(session['ply']), 'unknown')
    if session.get('mode') == 'quiz':
        ensure_quiz_states(plan, session)
        key = quiz_state_key(session)
        session.setdefault('quiz_first_answers',{}).setdefault(key,False)
        # A hint never erases an error or counts as an unassisted recovery.
        if session['quiz_states'][key] == 'pending':
            session['quiz_states'][key] = 'unknown'
        session['display_marks'] = dict(session['quiz_states'])
    else:
        session.setdefault('display_marks', {})[str(session['ply'])] = 'unknown'
    _mark_for_retry(session)
    session['hint'] = True
    session['revision'] += 1
    return True


def play_hint(plan, session, now):
    """Play the suggested learner move once, using the normal timed flow."""
    uci = expected_move(plan, session)
    if session['phase'] != 'answer' or not uci:
        return False
    request_hint(plan, session)
    event = {'uci': uci, 'fen': board_for(session).fen(),
             'revision': f"{session['token']}:{session['revision']}"}
    if not submit_move(plan, session, event, now):
        return False
    session['animation'] = uci
    return True


def submit_move(plan, session, event, now, *, restart_on_error=True):
    """Reject stale/duplicate events; wrong moves never enter board or history."""
    if not isinstance(event, dict) or session['phase'] != 'answer' or not expected_move(plan, session):
        return False
    revision = f"{session['token']}:{session['revision']}"
    board = board_for(session)
    if event.get('revision') != revision or event.get('fen') != board.fen():
        return False
    try:
        move = chess.Move.from_uci(event.get('uci', ''))
    except (ValueError, TypeError, AttributeError):
        return False
    if move not in board.legal_moves:
        return False
    correct = move.uci() == expected_move(plan, session)
    if session.get('mode') == 'quiz':
        ensure_quiz_states(plan, session)
        key = quiz_state_key(session)
        session.setdefault('quiz_first_answers',{}).setdefault(key,bool(correct and not session['hint']))
        status = next_status(session['quiz_states'][key], correct, session['hint'])
        session['quiz_reinsert_at'] = reinsert_index(session['token'], session['revision'], int(key),
                                                    len(session['quiz_queue']) - 1)
        session['quiz_states'][key] = status
        session['display_marks'] = dict(session['quiz_states'])
        session['marks'][key] = status
        _record_attempt(session, correct)
        session['feedback'] = {'square': chess.square_name(move.to_square), 'correct': correct,
                               'assisted': session['hint']}
        if not correct:
            session['had_error'] = True
            _mark_for_retry(session)
        if correct:
            session['history'].append(move.uci())
        session.update(phase='feedback', next_at=now, hint=False, animation=None)
        session['revision'] += 1
        return True
    session['marks'].setdefault(str(session['ply']), 'correct' if correct else 'wrong')
    session.setdefault('display_marks', {})[str(session['ply'])] = (
        'unknown' if correct and session.get('requested_hint') and session['hint']
        else 'correct' if correct else 'wrong')
    _record_attempt(session, correct)
    session['feedback'] = {'square': chess.square_name(move.to_square), 'correct': correct,
                           'assisted': session['hint']}
    session['animation'] = None
    session['revision'] += 1
    if not correct:
        session['had_error'] = True
        session['errors'] += 1
        _mark_for_retry(session)
        if session.get('mode') == 'learn' or not restart_on_error:
            session['hint'] = True
        else:
            session.update(hint=False, phase='restart', next_at=now + .45)
        return True
    if session.get('mode') == 'quiz' and session['hint']:
        if session['ply'] not in session['quiz_retry']:
            session['quiz_retry'].append(session['ply'])
    session['history'].append(move.uci())
    session['ply'] += 1
    session.update(errors=0, hint=False, attempted=False, phase='feedback', next_at=now + .22)
    return True


def _restart_recall(plan, session, *, retry=False):
    line = current_line(plan, session)
    session.pop('quiz_bank', None)
    session.pop('quiz_key', None)
    context = line.get('context_plies', 0)
    session.update(mode='recall', ply=context, history=list(line['moves'][:context]), errors=0, line_error=False,
                   feedback=None, animation=None, hint=False, attempted=False,
                   marks={}, display_marks={}, next_at=0, quiz_queue=[], quiz_retry=[])
    session['phase'] = 'answer' if context or line['side'] == 'white' else 'opponent'


def _quiz_position(plan, session):
    if session.get('quiz_bank'):
        session['quiz_key'] = session['quiz_queue'][0]
    line = current_line(plan, session)
    ply = session['quiz_bank'][str(session['quiz_key'])]['ply'] if session.get('quiz_bank') else session['quiz_queue'][0]
    session.update(ply=ply, history=list(line['moves'][:ply]), phase='answer',
                   feedback=None, animation=None, hint=False, attempted=False, next_at=0)


def _start_quiz(plan, session):
    line = session.get('custom_line') or lines_for(plan).get(session['line_id']) or current_line(plan, session)
    session.pop('quiz_bank',None)
    session.pop('quiz_key',None)
    plies = list(learner_plies(line))
    if session.get('course_round') is not None and session.get('practice_intent') in ('learn','practice'):
        from opening_rounds import quiz_target
        level,limit=quiz_target(plan,session)
        # Each line gets its own quiz. Longer rounds revisit its positions;
        # distinct question IDs preserve retries and exact answer counts.
        bank={str(index):dict(line=line,ply=plies[index%len(plies)]) for index in range(limit)}
        session.update(quiz_bank=bank,quiz_limit=limit,quiz_level=level,quiz_policy=2,
                       quiz_scope=[line['id']],quiz_pool_size=len(plies))
        plies=list(range(limit))
    elif line.get('stage') and session.get('practice_intent') != 'explore':
        from opening_achievements import quiz_limit,position_key
        learned=plan.get('practice_progress',{})
        selected=[item for item in lines_for(plan).values() if item['id']==session['line_id'] or learned.get(item['id'],{}).get('learned')]
        session['quiz_scope']=sorted(item['id'] for item in selected)
        level=max(item.get('lesson_moves',5) for item in selected)
        limit=quiz_limit(level)
        if len(selected)>1:
            bank, seen = {}, set()
            for item in selected:
                board=chess.Board()
                for ply,uci in enumerate(item['moves']):
                    position=(item['side'],board.epd())
                    if ply in learner_plies(item) and position not in seen:
                        bank[str(len(bank))]=dict(line=item,ply=ply)
                        seen.add(position)
                    board.push_uci(uci)
            session['quiz_pool_size']=len(bank)
            rng=random.Random(session['token']+':selection:'+str(session['revision']))
            seen_counts=plan.get('quiz_seen',{})
            order=list(bank)
            rng.shuffle(order)
            order.sort(key=lambda key:seen_counts.get(position_key(bank[key]['line'],bank[key]['ply']),0))
            fresh=[key for key in order if bank[key]['line']['id']==session['line_id']] if not learned.get(session['line_id'],{}).get('learned') else []
            chosen=(fresh[:limit]+[key for key in order if key not in fresh[:limit]])[:limit]
            bank={key:bank[key] for key in chosen}
            session['quiz_bank']=bank
            plies=[int(key) for key in bank]
        else:
            plies=plies[:limit]
        session.update(quiz_limit=limit,quiz_level=level,quiz_policy=2)
    random.Random(f"{session['token']}:{line['id']}").shuffle(plies)
    states = {str(ply): 'pending' for ply in plies}
    session.update(mode='quiz', quiz_schema=2, quiz_states=states, quiz_queue=plies,
                   quiz_retry=[], marks={}, display_marks=dict(states),quiz_size=len(plies),quiz_first_answers={})
    _quiz_position(plan, session)


def advance(plan, session, now, *, auto_continue=True):
    """Advance automatically; pause only while waiting for a learner move."""
    if session['phase'] == 'complete' or now < session['next_at']:
        return False
    line = current_line(plan, session)
    if session['phase'] == 'line_end':
        return continue_line(plan, session) if auto_continue else False
    if session['phase'] == 'restart':
        if session.get('mode') == 'quiz':
            _quiz_position(plan, session)
        else:
            _restart_recall(plan, session, retry=True)
    elif session.get('mode') == 'quiz' and session['phase'] == 'feedback':
        answered = session['quiz_queue'].pop(0)
        if session['quiz_states'][str(answered)] != 'correct':
            session['quiz_queue'].insert(session.pop('quiz_reinsert_at', len(session['quiz_queue'])), answered)
        if session['quiz_queue']:
            _quiz_position(plan, session)
        else:
            _finish_line(plan, session, line)
            session.update(phase='line_end', feedback=None, animation=None, hint=False, next_at=now + .5)
    elif session['ply'] >= len(line['moves']):
        session.update(phase='line_end', feedback=None, animation=None, hint=False, next_at=now + .5)
    elif session['phase'] == 'answer':
        return False
    elif session['phase'] in ('feedback', 'opponent'):
        uci = line['moves'][session['ply']]
        session['history'].append(uci)
        session['ply'] += 1
        session.update(feedback=None, animation=uci, phase='settling', next_at=now + .28)
    elif session['phase'] == 'settling':
        session.update(animation=None, phase='answer', hint=session.get('mode') == 'learn')
    session['revision'] += 1
    return True


def continue_line(plan, session):
    """Teaching leads to recall, flawless recall to quiz, then the next line."""
    if session['phase'] != 'line_end':
        return False
    line = current_line(plan, session)
    if not session['queue']:
        session.update(phase='complete', animation=None, feedback=None, next_at=0)
        session['revision'] += 1
        return True
    if session.get('mode') == 'learn':
        if line['id'] not in session['learned']:
            session['learned'].append(line['id'])
        _restart_recall(plan, session)
    elif session.get('mode') == 'recall':
        if session['line_error']:
            _restart_recall(plan, session, retry=True)
        else:
            _start_quiz(plan, session)
    elif session['queue']:
        _start_line(plan, session, lines_for(plan))
    else:
        session.update(phase='complete', animation=None, feedback=None, next_at=0)
    session['revision'] += 1
    return True


def _finish_line(plan, session, line):
    key = session['queue'].pop(0)
    target = 'recovered' if key in session['failed'] else 'mastered'
    if key not in session[target]:
        session[target].append(key)
    previous = plan['retention'].get(key, {})
    level = 0 if key in session['failed'] else min(previous.get('level', -1) + 1, len(INTERVALS)-1)
    plan['retention'][key] = {'level': level,
        'due': str(date.fromisoformat(session['day']) + timedelta(days=INTERVALS[level]))}


def metrics(session):
    return {'accuracy': 100 * session['first_correct'] / session['tested'] if session['tested'] else None,
            'mastered': len(session['mastered']), 'recovered': len(session['recovered']),
            'tested': session['tested'], 'first_correct': session['first_correct']}
