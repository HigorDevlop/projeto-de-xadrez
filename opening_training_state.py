"""Guided opening lessons, active recall, whole-line retries and scheduling."""
from datetime import date, timedelta
from uuid import uuid4
import random
import chess

from opening_repertoires import selected_courses
from preparation_state import new_plan, today

INTERVALS = (1, 3, 7, 14, 30)


def create_repertoire_plan(username, ids, start, end):
    courses = selected_courses(ids)
    plan = new_plan(username, start, end,
                    [{'id': c['id'], 'opening': c['title'], 'side': c['side']} for c in courses])
    plan.update(repertoire_mode=True, repertoire_ids=list(ids), training_days={}, retention={})
    return plan


def lines_for(plan):
    return {line['id']: line for c in selected_courses(plan['repertoire_ids']) for line in c['lines']}


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
    return session


def current_line(plan, session):
    return session.get('custom_line') or lines_for(plan).get(session.get('line_id'))


def board_for(session):
    board = chess.Board()
    for uci in session['history']:
        board.push_uci(uci)
    return board


def _start_line(plan, session, lines):
    session.update(ply=0, history=[], errors=0, line_error=False, feedback=None, hint=False,
                   animation=None, next_at=0, attempted=False, marks={}, display_marks={})
    line = lines[session['queue'][0]]
    session['line_id'] = line['id']
    known = line['id'] in plan['retention'] or line['id'] in session['learned']
    session['mode'] = 'recall' if known else 'learn'
    session['phase'] = 'answer' if line['side'] == 'white' else 'opponent'
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
    display = {ply: mark for ply, mark in session.get('display_marks', {}).items()
               if mark == 'wrong'} if retry else {}
    session.update(mode='recall', ply=0, history=[], errors=0, line_error=False,
                   feedback=None, animation=None, hint=False, attempted=False,
                   marks={}, display_marks=display, next_at=0, quiz_queue=[], quiz_retry=[])
    session['phase'] = 'answer' if line['side'] == 'white' else 'opponent'


def _quiz_position(plan, session):
    line = current_line(plan, session)
    ply = session['quiz_queue'][0]
    session.update(ply=ply, history=list(line['moves'][:ply]), phase='answer',
                   feedback=None, animation=None, hint=False, attempted=False, next_at=0)


def _start_quiz(plan, session):
    line = current_line(plan, session)
    plies = list(range(0 if line['side'] == 'white' else 1, len(line['moves']), 2))
    random.Random(f"{session['token']}:{line['id']}").shuffle(plies)
    session.update(mode='quiz', quiz_queue=plies, quiz_retry=[], marks={}, display_marks={})
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
        session['quiz_queue'].pop(0)
        if not session['quiz_queue'] and session['quiz_retry']:
            session['quiz_queue'] = list(session['quiz_retry'])
            session['quiz_retry'] = []
            for ply in session['quiz_queue']:
                session['marks'].pop(str(ply), None)
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
