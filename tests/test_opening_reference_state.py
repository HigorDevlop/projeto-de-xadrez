from copy import deepcopy
from datetime import date

import chess
import pytest

from opening_course_state import select_course, begin_line, course_lines, receive_move, settle_immediate
from opening_training_state import board_for, expected_move
from opening_reference_progress import continue_checkpoint, position_progress, streak, record_activity
from endgame_lessons import LESSONS


def event(session, move):
    return dict(uci=move, fen=board_for(session).fen(), revision=f"{session['token']}:{session['revision']}")


def test_error_waits_for_next_and_duplicate_does_not_count_twice():
    plan = select_course(None, 'reference-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    session['reference_mode'] = True
    attempt = event(session, 'd2d4')
    receive_move(plan, attempt, 0)
    snapshot = deepcopy(session)
    receive_move(plan, attempt, 0)
    assert session == snapshot
    assert session['ui_checkpoint']['kind'] == 'error'
    assert session['history'] == []
    assert not settle_immediate(plan, session)
    continue_checkpoint(plan, session)
    receive_move(plan, event(session, expected_move(plan, session)), 1)
    assert session['history'] == ['e2e4', 'e7e5']


def test_stage_waits_for_continue_and_count_uses_unique_positions():
    plan = select_course(None, 'reference-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    session['reference_mode'] = True
    for _ in range(30):
        if session.get('ui_checkpoint'):
            break
        receive_move(plan, event(session, expected_move(plan, session)), 1)
    assert session['mode'] == 'learn'
    assert session['ui_checkpoint']['kind'] == 'stage'
    assert position_progress(plan)[0] == 0
    continue_checkpoint(plan, session)
    settle_immediate(plan, session)
    assert session['mode'] == 'recall'
    assert session['history'] == []
    for row in plan['practice_progress'].values():
        row['learned'] = True
    known, total = position_progress(plan)
    assert known == total
    assert total < sum((len(row['moves'])+1)//2 for row in course_lines(plan))


def test_streak_combines_courses_and_keeps_yesterday_before_todays_training():
    plan = {'reference_activity': ['2026-10-14'], 'practice_library': {
        'other': {'reference_activity': ['2026-10-12', '2026-10-13']}}}
    assert streak(plan, date(2026, 10, 15)) == 3
    assert streak(plan, date(2026, 10, 16)) == 0
    assert streak(None, date(2026, 10, 15)) == 0
    record_activity(plan, {'practice_intent': 'explore'})
    assert plan['reference_activity'] == ['2026-10-14']


@pytest.mark.parametrize('lesson', LESSONS)
def test_endgame_exercises_and_demonstrations_are_legal(lesson):
    board = chess.Board(lesson['fen'])
    assert board.is_valid()
    assert not board.is_game_over()
    for uci in lesson['line']:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)
