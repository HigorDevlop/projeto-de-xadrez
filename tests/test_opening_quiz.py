from copy import deepcopy

import chess

from opening_course_state import select_course, course_lines, begin_line, receive_move
from opening_training_state import _start_quiz, board_for, expected_move, request_hint, current_line
from opening_quiz import quiz_data


def quiz():
    plan = select_course(None, 'quiz-test', 'italian')
    session = begin_line(plan, course_lines(plan)[0]['id'])
    _start_quiz(plan, session)
    return plan, session


def event(plan, session, uci=None):
    return dict(uci=uci or expected_move(plan, session), fen=board_for(session).fen(),
                revision=f"{session['token']}:{session['revision']}")


def test_preloaded_frames_match_every_legal_question():
    plan, session = quiz()
    data = quiz_data(current_line(plan, session), session)
    assert len(data['positions']) == len(session['quiz_queue'])
    for ply, frame in data['positions'].items():
        board = chess.Board()
        for uci in current_line(plan, session)['moves'][:int(ply)]:
            board.push_uci(uci)
        assert frame['fen'] == board.fen()
        assert frame['trainingExpected'] in frame['legal']


def test_fast_batch_replays_once_and_finishes_without_clock():
    plan, session = quiz()
    simulated = deepcopy(plan)
    live = simulated['practice_sessions'][simulated['practice_current']]
    attempts = []
    while live['phase'] != 'complete':
        attempts.append(event(simulated, live))
        assert receive_move(simulated, attempts[-1], 100)
        assert live['phase'] in ('answer', 'complete')
    assert receive_move(plan, {'attempts': attempts}, 100)
    assert session == live
    completed = deepcopy(plan)
    assert not receive_move(plan, {'attempts': attempts}, 100)
    assert plan == completed


def test_wrong_answer_and_hint_preserve_retry_rules():
    plan, session = quiz()
    original = list(session['quiz_queue'])
    wrong = next(m.uci() for m in board_for(session).legal_moves
                 if m.uci() != expected_move(plan, session))
    revision = session['revision']
    assert receive_move(plan, event(plan, session, wrong), 100)
    assert session['revision'] == revision + 2
    assert session['phase'] == 'answer' and session['quiz_queue'] == original
    assert session['line_id'] in session['failed']
    assert request_hint(plan, session)
    assert receive_move(plan, event(plan, session), 100)
    assert original[0] in session['quiz_retry']


from test_browser_components import browser_page, mount


def test_preloaded_quiz_playable_before_server_ack_keeps_squares(browser_page):
    from interactive_board import position_data, piece_images
    page = browser_page
    plan, session = quiz()
    frames = quiz_data(current_line(plan, session), session)
    data = dict(position_data(board_for(session)), revision=f"{session['token']}:{session['revision']}",
                epoch=session['token'], ply=0, total=0, navigation=False, trainingMode=True,
                trainingExpected=expected_move(plan, session), quiz=frames, syncRecovery=True,
                pieces=piece_images(), disabled=False)
    mount(page, 'interactive_board.py', data)
    page.evaluate("window.originalBoard=document.querySelector('.board');window.originalSquares=[...document.querySelectorAll('.square')]")
    for index in range(2):
        frame = frames['positions'][str(frames['queue'][index])]
        uci = frame['trainingExpected']
        page.locator('[data-square='+uci[:2]+']').click()
        page.locator('[data-square='+uci[2:]+']').click()
        page.wait_for_function("expected=>document.querySelector('.board').dataset.revision===expected",
                               arg=f"{session['token']}:{session['revision']+2*(index+1)}")
    # No Python render/ack has occurred: the second answer must still be accepted.
    events = page.evaluate("window.events.filter(e=>e.key==='move')")
    assert len(events) == 2
    assert len(events[-1]['value']['attempts']) == 2
    # A late first-frame render must neither roll back nor remount the board.
    page.evaluate('(data)=>window.render(data)', data)
    assert page.locator('.board').get_attribute('data-revision') == f"{session['token']}:{session['revision']+4}"
    assert page.evaluate("window.originalBoard===document.querySelector('.board') && window.originalSquares.every((node,i)=>node===document.querySelectorAll('.square')[i])")
    assert receive_move(plan, events[-1]['value'], 100)
    assert session['revision'] == int(page.locator('.board').get_attribute('data-revision').split(':')[-1])
    acknowledged = dict(data, **position_data(board_for(session)),
                        revision=f"{session['token']}:{session['revision']}",
                        quiz=quiz_data(current_line(plan, session), session),
                        trainingExpected=expected_move(plan, session))
    page.evaluate('(data)=>window.render(data)', acknowledged)
    assert page.evaluate('document.querySelector("main")._quizAttempts.length') == 0
    assert page.evaluate('document.querySelector("main")._acervoState.status().pending') is False


import pytest


@pytest.mark.parametrize('identifier', ['italian', 'caro'])
def test_learner_and_opponent_move_in_same_browser_event(browser_page, identifier):
    from opening_quiz import line_data
    from opening_course_state import settle_immediate
    from interactive_board import position_data, piece_images
    page = browser_page
    plan = select_course(None, 'instant-test', identifier)
    session = begin_line(plan, course_lines(plan)[0]['id'])
    settle_immediate(plan, session)
    line = current_line(plan, session)
    frames = line_data(line, session)
    data = dict(position_data(board_for(session), line['side'] == 'black'),
                revision=f"{session['token']}:{session['revision']}", epoch=session['token'],
                ply=0, total=0, navigation=False, trainingMode=True, instant=True,
                trainingExpected=expected_move(plan, session), trainingLine=frames,
                syncRecovery=True, pieces=piece_images(), disabled=False)
    mount(page, 'interactive_board.py', data)
    for index in range(2):
        ply = frames['current'] + index * 2
        frame = frames['positions'][str(ply)]
        result = page.evaluate("""uci=>{
            const root=document.querySelector('main'), squares=[...document.querySelectorAll('.square')];
            document.querySelector('[data-square='+uci.slice(0,2)+']').click();
            document.querySelector('[data-square='+uci.slice(2,4)+']').click();
            return {revision:root._acervoState.status().revision,pending:root._acervoState.status().pending,
              same:squares.every((node,i)=>node===document.querySelectorAll('.square')[i]),
              expected:root._acervoState.status().legal};
        }""", frame['trainingExpected'])
        assert result['revision'] == f"{session['token']}:{session['revision'] + 3*(index+1)}"
        assert not result['pending'] and result['same']
        assert result['expected'] == frames['positions'][str(ply+2)]['legal']
    attempts = page.evaluate("window.events.filter(e=>e.key==='move').at(-1).value")
    assert receive_move(plan, attempts, 100)
    assert session['phase'] == 'answer' and session['animation'] is None
    assert session['ply'] == frames['current'] + 4
