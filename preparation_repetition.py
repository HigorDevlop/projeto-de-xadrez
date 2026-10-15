"""Per-position recall for preparation only; no engine or PGN analysis."""
from datetime import date, timedelta
from copy import deepcopy
import random
from uuid import uuid4

import chess


def create_session(exercises, *, mastered=()):
    positions = {}
    for exercise in exercises:
        key = exercise['id']
        positions[key] = dict(exercise=exercise, position_id=key,
            status='correct' if key in mastered else None, attempts=0,
            correct_attempts=0, wrong_attempts=0, last_seen=None)
    session = dict(positions=positions, queue=[], current=None, phase='answer',
                   token=uuid4().hex, revision=0, feedback=None)
    select_next(session)
    return session


def select_next(session, rng=None):
    """Random rounds ensure every pending position returns, without starvation."""
    rng = rng or random
    previous = session['current']
    pending = [key for key, item in session['positions'].items() if item['status'] != 'correct']
    queue = [key for key in session['queue'] if key in pending]
    if not queue:
        queue = list(pending)
        rng.shuffle(queue)
    previous_fen = session['positions'].get(previous, {}).get('exercise', {}).get('fen')
    different = [key for key in pending if session['positions'][key]['exercise']['fen'] != previous_fen]
    eligible = different or [key for key in pending if key != previous]
    if queue and eligible and queue[0] not in eligible:
        alternatives = [key for key in queue if key in eligible]
        if alternatives:
            other = rng.choice(alternatives)
            queue.remove(other)
        else:
            other = rng.choice(eligible)
        queue.insert(0, other)
    session['current'] = queue.pop(0) if queue else None
    session['queue'] = queue
    session['phase'] = 'answer' if session['current'] is not None else 'complete'
    session['revision'] += 1


def current_exercise(session):
    item = session['positions'].get(session['current'])
    return item['exercise'] if item else None


def revision(session):
    return f"{session['token']}:{session['revision']}"


def submit(session, event, now, rng=None):
    exercise = current_exercise(session)
    if (not isinstance(event, dict) or session['phase'] != 'answer' or not exercise
            or event.get('revision') != revision(session) or event.get('fen') != exercise['fen']):
        return False
    board = chess.Board(exercise['fen'])
    try:
        move = chess.Move.from_uci(event.get('uci', ''))
    except (ValueError, TypeError, AttributeError):
        return False
    if move not in board.legal_moves:
        return False
    item = session['positions'][session['current']]
    correct = move.uci() == exercise['uci']
    item['status'] = ('correct' if item['status'] == 'learning' else 'learning') if correct else 'error'
    item['attempts'] += 1
    item['correct_attempts'] += int(correct)
    item['wrong_attempts'] += int(not correct)
    item['last_seen'] = now
    session['feedback'] = dict(position_id=item['position_id'], correct=correct, status=item['status'])
    # A fresh revision acknowledges even a wrong answer and unlocks the board.
    select_next(session, rng)
    return True


def counts(session):
    result = dict(error=0, learning=0, correct=0, unanswered=0, total=len(session['positions']))
    for item in session['positions'].values():
        result[item['status'] or 'unanswered'] += 1
    return result


def repertoire_session(plan, day=None):
    from opening_training_state import session_for, lines_for
    session = session_for(plan, day)
    if session is None or 'positions' in session:
        return session
    lines = lines_for(plan)
    completed = set(session['mastered'] + session['recovered'])
    line_ids = list(dict.fromkeys(list(completed) + session['queue']))
    exercises, mastered = [], []
    for key in line_ids:
        line = lines[key]
        board = chess.Board()
        for ply, uci in enumerate(line['moves']):
            if board.turn == (line['side'] == 'white'):
                identifier = f'{key}:{ply}'
                exercises.append(dict(id=identifier, line_id=key, ply=ply, fen=board.fen(),
                    uci=uci, side=line['side'], opening=line['opening']))
                if key in completed:
                    mastered.append(identifier)
            board.push_uci(uci)
    recall = create_session(exercises, mastered=mastered)
    # Carry unfinished learning across days. Completed positions enter a new
    # review only when their line is due; their previous mastery is not erased.
    previous_days = sorted((key for key in plan['training_days'] if key < session['day']), reverse=True)
    if previous_days:
        previous = plan['training_days'][previous_days[0]].get('positions', {})
        unfinished = {item['exercise']['line_id'] for item in previous.values()
                      if item['status'] != 'correct'}
        for key, item in previous.items():
            if key in recall['positions'] and item['exercise']['line_id'] in unfinished:
                recall['positions'][key] = deepcopy(item)
        # Copied mastered positions must be removed from the initial queue too.
        if recall['current'] and recall['positions'][recall['current']]['status'] == 'correct':
            select_next(recall)
    # Old marks represent single attempts, not mastery. Preserve their evidence.
    for ply, mark in session.get('marks', {}).items():
        item = recall['positions'].get(f"{session.get('line_id')}:{ply}")
        if item and item['status'] != 'correct':
            item['status'] = 'error' if mark == 'wrong' else 'learning'
    session.update(recall)
    session['repetition_lines'] = line_ids
    return session


def submit_repertoire(plan, session, event, now):
    if not submit(session, event, now):
        return False
    for line_id in session['repetition_lines']:
        items = [p for p in session['positions'].values() if p['exercise']['line_id'] == line_id]
        if (items and all(p['status'] == 'correct' for p in items)
                and line_id not in session['mastered'] + session['recovered']):
            recovered = any(p['wrong_attempts'] for p in items)
            session['recovered' if recovered else 'mastered'].append(line_id)
            plan['retention'][line_id] = dict(level=0,
                due=str(date.fromisoformat(session['day']) + timedelta(days=1)))
    return True
