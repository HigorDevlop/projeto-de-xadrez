from copy import deepcopy
from collections import Counter
import pytest
import chess

from opening_repetition import STATES, next_status, reinsert_index
from opening_course_state import select_course, begin_line, course_lines, receive_move, active_session
from opening_training_state import board_for, expected_move, request_hint, current_line
from preparation_state import save_plan, load_plan
from test_opening_quiz import event
from test_browser_components import browser_page, mount


@pytest.mark.parametrize('before,correct,after', [
    ('pending',True,'correct'), ('pending',False,'wrong'),
    ('wrong',True,'unknown'), ('wrong',False,'wrong'),
    ('unknown',True,'correct'), ('unknown',False,'wrong'),
])
def test_transition_table(before, correct, after):
    assert next_status(before, correct) == after


def practice():
    plan = select_course(None, 'four-states-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'], 'practice')
    session['reference_mode'] = True
    return plan, session


def answer(plan, session, correct=True):
    move = expected_move(plan, session) if correct else next(
        m.uci() for m in board_for(session).legal_moves if m.uci() != expected_move(plan, session))
    receive_move(plan, event(plan, session, move), 100)


def reach(plan, session, target):
    for _ in range(100):
        if session['ply'] == target:
            return
        answer(plan, session)
    raise AssertionError('A posição não retornou')


def test_error_recovery_fallback_persistence_and_conservation(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    plan, session = practice()
    initial = list(session['quiz_queue'])
    target = initial[0]
    assert Counter(session['quiz_states'].values()) == {'pending': len(initial)}
    stale = event(plan, session)
    answer(plan, session, False)
    assert session['ply'] == initial[1]  # Advance immediately, without Next.
    assert session['quiz_states'][str(target)] == 'wrong'
    assert not session.get('ui_checkpoint')
    snapshot = deepcopy(session)
    receive_move(plan, stale, 100)
    assert session == snapshot
    reach(plan, session, target)
    answer(plan, session)
    assert session['quiz_states'][str(target)] == 'unknown'
    save_plan(plan, namespace='openings')
    plan = load_plan('four-states-test', namespace='openings')
    session = active_session(plan)
    assert session['quiz_states'][str(target)] == 'unknown'
    reach(plan, session, target)
    answer(plan, session, False)
    assert session['quiz_states'][str(target)] == 'wrong'
    reach(plan, session, target)
    answer(plan, session)
    assert session['quiz_states'][str(target)] == 'unknown'
    reach(plan, session, target)
    answer(plan, session)
    assert session['quiz_states'][str(target)] == 'correct'
    for _ in range(100):
        statuses = session['quiz_states']
        assert len(statuses) == len(initial)
        assert set(statuses.values()).issubset(STATES)
        assert len(session['quiz_queue']) == len(set(session['quiz_queue']))
        assert set(session['quiz_queue']) == {int(k) for k,v in statuses.items() if v != 'correct'}
        if session['phase'] == 'complete':
            break
        answer(plan, session)
    assert session['phase'] == 'complete'
    assert set(session['quiz_states'].values()) == {'correct'}


def test_hint_does_not_skip_error_recovery():
    plan, session = practice()
    target = session['ply']
    answer(plan, session, False)
    reach(plan, session, target)
    assert request_hint(plan, session)
    answer(plan, session)
    assert session['quiz_states'][str(target)] == 'wrong'
    reach(plan, session, target)
    answer(plan, session)
    assert session['quiz_states'][str(target)] == 'unknown'


def test_random_reinsertion_is_not_always_last_and_single_position_terminates():
    assert {reinsert_index(str(i), i, 0, 5) for i in range(100)} == {1,2,3,4,5}
    assert reinsert_index('one', 1, 0, 0) == 0
    plan, session = practice()
    target = session['ply']
    session['quiz_queue'] = [target]
    session['quiz_states'] = {str(target): 'wrong'}
    answer(plan, session)
    assert session['quiz_queue'] == [target] and session['quiz_states'][str(target)] == 'unknown'
    answer(plan, session)
    assert session['phase'] == 'complete'


def test_browser_and_server_reconcile_random_error_queue(browser_page):
    from opening_quiz import quiz_data
    from interactive_board import position_data, piece_images
    plan, session = practice()
    data = dict(position_data(board_for(session)), revision=f"{session['token']}:{session['revision']}",
                epoch=session['token'], ply=0,total=0,navigation=False,trainingMode=True,
                trainingExpected=expected_move(plan,session),quiz=quiz_data(current_line(plan,session),session),
                syncRecovery=True,instant=True,pieces=piece_images(),disabled=False)
    page=browser_page
    mount(page,'interactive_board.py',data)
    # Mix errors and successes without a server render between attempts.
    for index in range(12):
        uci = expected_move(plan,session)
        if index % 3 == 0:
            uci=next(m.uci() for m in board_for(session).legal_moves if m.uci()!=uci)
        page.locator('[data-square='+uci[:2]+']').click()
        page.locator('[data-square='+uci[2:]+']').click()
        attempts=page.evaluate("window.events.filter(e=>e.key==='move').at(-1).value")
        receive_move(plan,attempts,100)
        client=page.evaluate("document.querySelector('main')._quizLocal")
        if not session['quiz_queue']:
            break  # The final answer waits for the server's completion acknowledgement.
        assert client['quiz']['queue']==session['quiz_queue']
        assert client['quiz']['states']==session['quiz_states']
        assert client['revision']==f"{session['token']}:{session['revision']}"
