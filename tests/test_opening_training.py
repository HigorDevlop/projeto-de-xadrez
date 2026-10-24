from copy import deepcopy
from datetime import timedelta
import json
import chess
import pytest
from opening_repertoires import catalog, selected_courses
from opening_training_state import (create_repertoire_plan, session_for, current_line,
    board_for, expected_move, submit_move, advance, metrics, continue_line, request_hint, play_hint)
from preparation_state import today, save_plan, load_plan


def plan_for(ids=None):
    return create_repertoire_plan('repertoire-test', ids or ['london'], today(), today()+timedelta(days=60))


def event(session, uci):
    return dict(uci=uci, fen=board_for(session).fen(), revision=f"{session['token']}:{session['revision']}")


def settle(plan, session):
    for _ in range(12):
        if session['phase'] in ('answer', 'complete'):
            return
        assert advance(plan, session, session['next_at'] + 1)
    pytest.fail('Transition did not settle')


def play_until(plan, session, condition):
    for _ in range(2000):
        settle(plan, session)
        if condition():
            return
        assert session['phase'] == 'answer'
        assert submit_move(plan, session, event(session, expected_move(plan, session)), 1)
    pytest.fail('Training did not reach expected phase')


def test_catalog_has_closed_consistent_legal_paths_and_exact_counts():
    courses = catalog()
    assert len(courses) == 78
    assert {c['group'] for c in courses} == {'white', 'black_e4', 'black_d4', 'black_other'}
    for course in courses:
        choices = {}
        assert len({x['id'] for x in course['lines']}) == len(course['lines'])
        for line in course['lines']:
            board = chess.Board()
            for uci in line['moves']:
                move = chess.Move.from_uci(uci)
                assert move in board.legal_moves
                if board.turn == (course['side'] == 'white'):
                    assert choices.setdefault(board.epd(), uci) == uci
                board.push(move)
            assert board.turn != (course['side'] == 'white')


def test_retry_clears_previous_red_marks_without_forgetting_error():
    from opening_training_state import _restart_recall
    plan = plan_for()
    session = session_for(plan)
    key = session['line_id']
    session.update(display_marks={'0':'correct','2':'wrong'}, marks={'2':'wrong'},
                   feedback={'square':'d4','correct':False}, failed=[key], had_error=True)
    _restart_recall(plan, session, retry=True)
    assert session['display_marks'] == {}
    assert session['marks'] == {}
    assert session['feedback'] is None
    assert session['failed'] == [key] and session['had_error']


@pytest.mark.parametrize('ids', [[], ['london']*2, ['bad'], [x['id'] for x in catalog()][:5], None])
def test_selection_is_validated_on_server(ids):
    with pytest.raises(ValueError):
        selected_courses(ids)


@pytest.mark.parametrize('side,length', [('white', 3), ('white', 4), ('black', 3), ('black', 4)])
def test_teach_recall_quiz_then_complete_automatically(monkeypatch, side, length):
    line = dict(id='test', side=side, moves=['e2e4','e7e5','g1f3','b8c6'][:length])
    monkeypatch.setattr('opening_training_state.lines_for', lambda plan: {'test': line})
    plan = plan_for()
    session = session_for(plan)
    settle(plan, session)
    assert session['mode'] == 'learn' and session['hint']
    play_until(plan, session, lambda: session['mode'] == 'recall')
    assert not session['hint'] and session['learned'] == ['test']
    assert session['tested'] == 0 and plan['retention'] == {}
    play_until(plan, session, lambda: session['mode'] == 'quiz')
    assert not session['hint'] and session['mastered'] == []
    assert sorted(session['quiz_queue']) == list(range(0 if side == 'white' else 1,length,2))
    play_until(plan, session, lambda: session['phase'] == 'complete')
    assert session['mastered'] == ['test'] and metrics(session)['accuracy'] == 100
    before = deepcopy(session)
    assert not advance(plan, session, 999)
    assert session == before


def test_error_restarts_same_line_immediately_without_arrows_and_rejects_stale_events():
    plan = plan_for()
    session = session_for(plan)
    play_until(plan, session, lambda: session['mode'] == 'recall')
    assert submit_move(plan, session, event(session, expected_move(plan, session)), 1)
    settle(plan, session)
    key = session['line_id']
    board = board_for(session)
    wrong = next(m.uci() for m in board.legal_moves if m.uci() != expected_move(plan, session))
    stale = event(session, wrong)
    assert submit_move(plan, session, stale, 1)
    assert session['phase'] == 'restart' and not session['hint']
    assert not submit_move(plan, session, stale, 1)
    assert not advance(plan, session, session['next_at'] - .01)
    settle(plan, session)
    assert session['line_id'] == key and session['ply'] == 0 and session['history'] == []
    assert not session['hint'] and session['mode'] == 'recall'
    for _ in range(2):
        assert submit_move(plan, session, event(session, 'a2a3'), 1)
        settle(plan, session)
        assert session['mode'] == 'recall' and session['ply'] == 0
    play_until(plan, session, lambda: session['mode'] == 'quiz')
    assert session['line_id'] == key and session['mastered'] == []


def test_quiz_error_requeues_question_and_all_questions_must_be_correct():
    plan = plan_for()
    session = session_for(plan)
    play_until(plan, session, lambda: session['mode'] == 'quiz')
    pending = list(session['quiz_queue'])
    board = board_for(session)
    wrong = next(m.uci() for m in board.legal_moves if m.uci() != expected_move(plan, session))
    assert submit_move(plan, session, event(session, wrong), 1)
    settle(plan, session)
    assert session['mode'] == 'quiz' and session['quiz_queue'][0] == pending[1] and not session['hint']
    assert sorted(session['quiz_queue']) == sorted(pending)
    assert session['quiz_states'][str(pending[0])] == 'wrong'
    key = session['line_id']
    play_until(plan, session, lambda: session['line_id'] != key)
    assert key in session['recovered'] and plan['retention'][key]['level'] == 0


def test_all_courses_finish_and_schedule_review():
    for course in catalog():
        plan = plan_for([course['id']])
        session = session_for(plan)
        play_until(plan, session, lambda: session['phase'] == 'complete')
        assert metrics(session)['accuracy'] == 100
        assert len(session['mastered']) == len(course['lines'])
        assert {v['due'] for v in plan['retention'].values()} == {str(today()+timedelta(days=1))}


def test_resume_preserves_retry_and_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan = plan_for()
    session = session_for(plan)
    play_until(plan, session, lambda: session['mode'] == 'recall')
    assert submit_move(plan, session, event(session, 'a2a3'), 1)
    save_plan(plan)
    restored = load_plan(plan['username'])
    assert session_for(restored) == session
    settle(restored, session_for(restored))
    assert session_for(restored)['history'] == []
    assert not session_for(restored)['hint']


def test_black_starts_with_opponent_and_invalid_events_do_not_mutate():
    plan = plan_for(['caro'])
    session = session_for(plan)
    before = deepcopy(session)
    assert not submit_move(plan, session, event(session,'e2e4'),1)
    assert session == before
    assert advance(plan,session,1)
    assert session['animation'] == 'e2e4'
    settle(plan,session)
    assert board_for(session).turn == chess.BLACK
    for uci in ('bad','e7e4',None):
        assert not submit_move(plan,session,event(session,uci),1)


def test_guided_preparation_waits_for_repeat_and_preserves_requested_hint(monkeypatch):
    line = dict(id='test', side='white', moves=['e2e4'])
    monkeypatch.setattr('opening_training_state.lines_for', lambda plan: {'test': line})
    plan = plan_for()
    session = session_for(plan)
    assert play_hint(plan, session, 1)
    assert advance(plan, session, 2, auto_continue=False)
    assert session['phase'] == 'line_end' and session['mode'] == 'learn'
    before = deepcopy(session)
    assert not advance(plan, session, 999, auto_continue=False)
    assert session == before
    assert continue_line(plan, session)
    assert session['mode'] == 'recall' and not session['hint']
    assert request_hint(plan, session)
    assert session_for(plan)['hint']
    assert session['marks'] == {'0': 'unknown'}
    assert play_hint(plan, session, 1000)
    assert advance(plan, session, 1001, auto_continue=False)
    assert continue_line(plan, session)
    # Assisted recall repeats before the quiz; a hint does not master a line.
    assert session['mode'] == 'recall' and not session['hint']
    assert plan['retention'] == {}


def test_guided_wrong_move_retains_position_and_error_mark():
    plan = plan_for()
    session = session_for(plan)
    play_until(plan, session, lambda: session['mode'] == 'recall')
    history = list(session['history'])
    assert submit_move(plan, session, event(session, 'a2a3'), 1, restart_on_error=False)
    assert session['phase'] == 'answer' and session['history'] == history
    assert session_for(plan)['hint']
    assert session['marks'] == {'0': 'wrong'}
    assert play_hint(plan, session, 2)
    assert session['marks'] == {'0': 'wrong'}
    assert session['line_error']


def test_guided_quiz_retests_an_assisted_answer_before_mastery(monkeypatch):
    line = dict(id='test', side='white', moves=['e2e4'])
    monkeypatch.setattr('opening_training_state.lines_for', lambda plan: {'test': line})
    plan = plan_for()
    session = session_for(plan)
    play_until(plan, session, lambda: session['mode'] == 'quiz')
    assert request_hint(plan, session)
    assert play_hint(plan, session, 1)
    assert advance(plan, session, 2, auto_continue=False)
    assert session['phase'] == 'answer' and not session['hint']
    assert session['quiz_queue'] == [0] and plan['retention'] == {}
    assert submit_move(plan, session, event(session, 'e2e4'), 3, restart_on_error=False)
    assert advance(plan, session, 4, auto_continue=False)
    assert session['phase'] == 'line_end' and session['recovered'] == ['test']
    assert continue_line(plan, session)
    assert session['phase'] == 'complete'
