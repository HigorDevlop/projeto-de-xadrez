import time
import json

import pytest

from test_browser_components import browser_page, drag
from test_opening_course_ui import course_server, current, saved, wait_phase, ROOT
from opening_training_state import board_for, expected_move


def wait_answer(page, folder, mode=None):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        assert page.locator('[data-testid="stException"]').count() == 0, page.locator('body').inner_text()
        session = current(folder)
        if session['phase'] == 'answer' and (mode is None or session['mode'] == mode):
            if page.locator('.board').get_attribute('data-revision') == f"{session['token']}:{session['revision']}":
                return session
        page.wait_for_timeout(50)
    page.screenshot(path=str(folder/'answer-failure.png'), full_page=True)
    status = page.locator('.board').evaluate('board=>({revision:board.dataset.revision,status:board.getRootNode()._acervoState?.status()})') if page.locator('.board').count() else page.locator('body').inner_text()
    pytest.fail('O treino não ficou jogável: ' + str(current(folder)) + '\n' + json.dumps(status))


def play(page, folder, session, uci, *, by_drag=False):
    live = wait_answer(page, folder, session['mode'])
    assert live['ply'] == session['ply'] and live['history'] == session['history']
    session = live
    page.locator('[data-square='+uci[:2]+'].movable').wait_for(state='visible')
    if by_drag:
        page.locator('.board').scroll_into_view_if_needed()
        drag(page, uci[:2], uci[2:4])
    else:
        page.locator('[data-square='+uci[:2]+']').click()
        if 'selected' not in (page.locator('[data-square='+uci[:2]+']').get_attribute('class') or ''):
            status = page.locator('.board').evaluate('board=>board.getRootNode()._acervoState?.status()')
            pytest.fail('Origem não selecionou: ' + json.dumps(status))
        page.locator('[data-square='+uci[2:4]+']').click()
    deadline = time.monotonic()+10
    while current(folder)['revision'] == session['revision'] and time.monotonic() < deadline:
        assert page.locator('[data-testid="stException"]').count() == 0, page.locator('body').inner_text()
        page.wait_for_timeout(50)
    if current(folder)['revision'] == session['revision']:
        page.screenshot(path=str(folder/'input-failure.png'), full_page=True)
        if page.locator('.board').count() == 0:
            pytest.fail('Tabuleiro saiu: ' + page.locator('body').inner_text())
        diagnostic = page.locator('.board').evaluate('''board => ({
        revision: board.dataset.revision,
        selected: [...board.querySelectorAll('.selected')].map(e=>e.dataset.square),
        animations: board.getAnimations({subtree:true}).map(e=>e.playState),
        signature: board.getRootNode()._acervoState?.signature,
        status: board.getRootNode()._acervoState?.status(),
        handlers: [...board.querySelectorAll('.movable')].map(e=>({square:e.dataset.square,click:!!e.onclick,down:!!e.onpointerdown}))
        })''')
        (folder/'board-debug.json').write_text(json.dumps(diagnostic), encoding='utf8')
        pytest.fail(json.dumps(diagnostic['status']))


@pytest.mark.parametrize('width,course', [(1366, 'italian'), (390, 'caro')])
def test_repeated_errors_restart_and_allow_completion(browser_page, course_server, width, course):
    from playwright.sync_api import expect
    page = browser_page
    page.set_default_timeout(15000)
    url, folder = course_server
    page.set_viewport_size(dict(width=width, height=1000))
    page.goto(url)
    expect(page.get_by_role('heading', name='Como subir no ranking de aberturas')).to_be_visible()
    expect(page.get_by_text('Inatividade:', exact=False)).to_be_visible()
    page.locator(f'[data-id={course}]').click()
    page.get_by_role('button', name='Treinar', exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    session = wait_answer(page, folder, 'learn')
    initial_history = list(session['history'])
    page.wait_for_timeout(2500)
    assert current(folder)['history'] == initial_history  # Never auto-play the learner's turn.
    expect(page.locator('.training-hint')).to_have_count(1)
    for attempt in range(6):
        session = wait_answer(page, folder, 'learn')
        board = board_for(session)
        wrong = next(move.uci() for move in board.legal_moves if move.uci() != expected_move(saved(folder), session))
        play(page, folder, session, wrong, by_drag=attempt % 2 == 0)
        expect(page.locator('.opening-mark.wrong')).to_have_count(1)
        assert current(folder)['history'] == initial_history
    page.screenshot(path=str(ROOT / f'tests/artifacts/aberturas-erros-{width}.png'), full_page=True)
    # Complete the guided phase by making every learner move.
    guided_deadline = time.monotonic() + 60
    while current(folder)['mode'] == 'learn':
        assert time.monotonic() < guided_deadline, 'A fase guiada não terminou'
        session = current(folder)
        if session['phase'] == 'answer':
            play(page, folder, session, expected_move(saved(folder), session))
        else:
            page.wait_for_timeout(100)
    for attempt in range(6):
        session = wait_answer(page, folder, 'recall')
        assert session['history'] == initial_history
        # Errors after making progress must reset the full line as well.
        if attempt % 2:
            play(page, folder, session, expected_move(saved(folder), session))
            session = wait_answer(page, folder, 'recall')
        board = board_for(session)
        wrong = next(move.uci() for move in board.legal_moves if move.uci() != expected_move(saved(folder), session))
        play(page, folder, session, wrong, by_drag=attempt % 2 == 0)
        # The next repetition is a fresh playable position, never a pending lock.
        repeated = wait_answer(page, folder, 'recall')
        assert repeated['history'] == initial_history and repeated['had_error'], (folder/'protocol.jsonl').read_text(encoding='utf8')[-4000:]
        assert page.get_by_text('posições resolvidas', exact=False).count() == 1
    toolbar = page.locator('.st-key-opening_lesson_toolbar').bounding_box()
    board_box = page.locator('.board').bounding_box()
    assert toolbar['y'] + toolbar['height'] <= board_box['y']
    assert page.get_by_text('Demonstração automática → memorize os lances → quiz → próxima linha. Pause quando quiser.').count() == 0
    deadline = time.monotonic() + 90
    quiz_errors = 0
    while time.monotonic() < deadline:
        assert page.locator('[data-testid="stException"]').count() == 0, page.locator('body').inner_text()
        if saved(folder).get('practice_ranking', {}).get('units') == 2:
            break
        session = current(folder)
        if session['phase'] == 'answer':
            if session['mode'] == 'quiz' and quiz_errors < 3:
                board = board_for(session)
                wrong = next(move.uci() for move in board.legal_moves if move.uci() != expected_move(saved(folder), session))
                play(page, folder, session, wrong, by_drag=True)
                quiz_errors += 1
                repeated = wait_answer(page, folder, 'quiz')
                assert repeated['quiz_queue'] == session['quiz_queue']
            else:
                play(page, folder, session, expected_move(saved(folder), session))
        else:
            page.wait_for_timeout(200)
    else:
        page.screenshot(path=str(folder/'retry-failure.png'), full_page=True)
        pytest.fail('Não concluiu a linha após repetir os erros: '+str(current(folder))+'\n'+page.locator('body').inner_text())
    assert saved(folder)['practice_ranking']['units'] == 2  # Exactly one point.
    assert quiz_errors == 3
