from copy import deepcopy
from datetime import timedelta

import pytest

from opening_course_state import begin_line, course_lines, record_completion, select_course, settle
from opening_ranking_state import (RANKS, apply_decay, award_completion, decay_library,
                                   rank_summary, ranking_state)
from opening_training_state import board_for, expected_move, request_hint, submit_move
from preparation_state import today, load_plan, save_plan
from test_opening_course import solve


@pytest.mark.parametrize('error,hint,points', [(False, False, 2), (True, False, 1),
                                            (False, True, .5), (True, True, .5)])
def test_completion_points_are_once_per_run_and_hint_takes_priority(error, hint, points):
    plan = select_course(None, 'points-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    session.update(had_error=error, requested_hint=hint)
    solve(plan, session)
    assert rank_summary(plan)['points'] == points
    record_completion(plan, session)
    assert rank_summary(plan)['points'] == points
    assert award_completion(plan, session) == 0
    # Same-day repeat is a new completed run and may earn points.
    review = begin_line(plan, session['line_id'], 'master')
    solve(plan, review)
    assert rank_summary(plan)['points'] == points + 2


@pytest.mark.parametrize('points,rank,level', [(0, 0, 1), (99.5, 0, 1), (100, 0, 2),
    (200, 0, 3), (300, 0, 4), (400, 0, 5), (499.5, 0, 5), (500, 1, 1),
    (1000, 2, 1), (5500, 11, 1), (5999.5, 11, 5), (6000, 11, 5)])
def test_rank_and_level_boundaries(points, rank, level):
    plan = {}
    ranking_state(plan)['units'] = int(points * 2)
    summary = rank_summary(plan)
    assert summary['rank'] == RANKS[rank]
    assert summary['level'] == level
    assert summary['rank_points'] == points - rank * 500
    assert summary['level_points'] == points - rank * 500 - (level - 1) * 100


def test_decay_is_idempotent_protects_rank_floor_and_resets_on_completion():
    plan = {}
    score = ranking_state(plan)
    score.update(units=1012, floor=1000)
    day = today()
    apply_decay(plan, day + timedelta(days=7))
    assert rank_summary(plan)['points'] == 506
    apply_decay(plan, day + timedelta(days=10))
    assert rank_summary(plan)['points'] == 503
    snapshot = deepcopy(plan)
    assert not apply_decay(plan, day + timedelta(days=10))
    assert plan == snapshot
    apply_decay(plan, day + timedelta(days=100))
    assert rank_summary(plan)['points'] == 500
    assert rank_summary(plan)['rank'] == 'Prata'


def test_new_rank_and_score_survive_switch_and_reload(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    plan = select_course(None, 'points-test', 'italian')
    ranking_state(plan)['units'] = 998
    solve(plan, begin_line(plan, course_lines(plan)[0]['id']))
    assert rank_summary(plan)['rank'] == 'Prata'
    other = select_course(plan, 'points-test', 'caro')
    save_plan(other, namespace='openings')
    restored = select_course(load_plan('points-test', namespace='openings'), 'points-test', 'italian')
    assert rank_summary(restored)['points'] == 501
    assert ranking_state(restored)['floor'] == 1000
    assert rank_summary(other)['points'] == 0


def test_threshold_migration_preserves_points_and_recalculates_floor():
    plan = {'practice_ranking': dict(units=212, floor=200,
            last_active=str(today()), last_decay=str(today()), completed=53)}
    summary = rank_summary(plan)
    assert summary['points'] == 106
    assert summary['rank'] == 'Bronze' and summary['level'] == 2
    assert ranking_state(plan)['floor'] == 0
    assert ranking_state(plan)['completed'] == 53


def test_errors_repeat_whole_line_until_clean_and_keep_scoring_history():
    plan = select_course(None, 'points-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    session.update(mode='recall', hint=False)
    for _ in range(4):
        board = board_for(session)
        wrong = next(move.uci() for move in board.legal_moves if move.uci() != expected_move(plan, session))
        event = dict(uci=wrong, fen=board.fen(), revision=f"{session['token']}:{session['revision']}")
        assert submit_move(plan, session, event, 100)
        assert session['phase'] == 'restart'
        assert settle(plan, session, 101)
        assert session['phase'] == 'answer' and session['history'] == []
    solve(plan, session)
    assert session['phase'] == 'complete'
    assert rank_summary(plan)['points'] == 1


def test_requested_hint_is_not_confused_with_automatic_demo():
    plan = select_course(None, 'points-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    session.update(mode='recall', hint=False)
    assert request_hint(plan, session)
    solve(plan, session)
    assert rank_summary(plan)['points'] == .5


def test_guided_errors_allow_unlimited_retries_and_reduce_completion_points():
    plan = select_course(None, 'points-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    for _ in range(20):
        revision = session['revision']
        event = dict(uci='a2a3', fen=board_for(session).fen(),
                     revision=f"{session['token']}:{revision}")
        assert submit_move(plan, session, event, 1)
        assert session['phase'] == 'answer' and session['history'] == []
        assert session['revision'] == revision + 1
        assert session['display_marks']['0'] == 'wrong'
    solve(plan, session)
    assert rank_summary(plan)['points'] == 1


def test_library_decay_updates_inactive_openings_without_inventing_old_points():
    plan = select_course(None, 'points-test', 'italian')
    assert rank_summary(plan)['points'] == 0
    score = ranking_state(plan)
    score.update(units=20, last_active=str(today()-timedelta(days=10)),
                 last_decay=str(today()-timedelta(days=10)))
    other = select_course(plan, 'points-test', 'caro')
    decay_library(other)
    assert rank_summary(other['practice_library']['italian'])['points'] == 7
