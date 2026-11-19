"""Reference-screen milestones and daily activity, derived from real completions."""
from datetime import timedelta
import chess
from opening_course_state import course_lines
from preparation_state import today


def position_progress(plan):
    known, all_positions = set(), set()
    for line in course_lines(plan):
        board = chess.Board()
        for ply, uci in enumerate(line['moves']):
            if ply >= line.get('context_plies',0) and board.turn == (line['side'] == 'white'):
                all_positions.add(board.epd())
                if line['learned']:
                    known.add(board.epd())
            board.push_uci(uci)
    return len(known), len(all_positions)


def activity_days(plan):
    days = set()
    library = list((plan or {}).get('practice_library', {}).values())
    if plan:
        library.append(plan)
    for saved in library:
        for item in saved.get('practice_progress', {}).values():
            if item.get('last_review'):
                days.add(item['last_review'])
        days.update(saved.get('reference_activity', []))
    return days


def streak(plan, day=None):
    day = day or today()
    days = activity_days(plan)
    cursor = day if str(day) in days else day - timedelta(days=1)
    count = 0
    while str(cursor) in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def record_activity(plan, session):
    if session.get('practice_intent') == 'explore':
        return
    dates = set(plan.get('reference_activity', []))
    dates.add(str(today()))
    plan['reference_activity'] = sorted(dates)


def continue_checkpoint(plan, session):
    checkpoint = session.pop('ui_checkpoint', None)
    if checkpoint and checkpoint['kind'] == 'stage':
        session['reference_continue'] = True
    session['revision'] += 1

