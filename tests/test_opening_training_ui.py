from datetime import timedelta
from pathlib import Path
import sys
import chess
import pytest
from streamlit.testing.v1 import AppTest

from test_browser_components import browser_page, mount, board_data, drag
from opening_catalog_ui import catalog_cards
from opening_training_state import create_repertoire_plan, session_for
from preparation_state import today
from design_tokens import palette


@pytest.fixture(autouse=True)
def isolated_component_registration():
    modules = ('opening_catalog_ui', 'opening_training_ui', 'interactive_board',
               'preparation_workspace', 'preparation_ui', 'opening_transition', 'opening_preparation_training')
    for name in modules:
        sys.modules.pop(name, None)
    yield
    for name in modules:
        sys.modules.pop(name, None)


def test_catalog_selection_across_tabs_blocks_fifth_and_unlocks(browser_page):
    page = browser_page
    data = dict(courses=catalog_cards(), colors=palette(False), selected=[],
                start=str(today()), end=str(today()+timedelta(days=6)), valid=True)
    mount(page, 'opening_catalog_ui.py', data)
    assert page.locator('.confirm').is_disabled()
    page.locator('[data-id="london"]').click()
    page.locator('[data-id="e4"]').click()
    assert page.get_by_role('tab').count() == 2
    page.get_by_role('tab', name='Pretas', exact=True).click()
    page.locator('[data-id="caro"]').click()
    page.locator('[data-id="slav"]').click()
    assert page.locator('.counter').inner_text() == 'Aberturas Selecionadas: [4/4]'
    assert page.locator('[data-id="nimzo"]').is_disabled()
    assert page.locator('[data-id="nimzo"]').evaluate('(el)=>getComputedStyle(el).pointerEvents') == 'none'
    page.wait_for_timeout(200)
    assert page.locator('[data-id="nimzo"]').evaluate('(el)=>getComputedStyle(el).opacity') == '0.45'
    page.locator('[data-id="slav"]').click()
    assert page.locator('[data-id="nimzo"]').is_enabled()
    page.locator('[data-id="nimzo"]').click()
    page.locator('.confirm').click()
    assert page.evaluate('window.events[0].value.ids') == ['london', 'e4', 'caro', 'nimzo']


def test_catalog_mobile_no_horizontal_overflow_and_keyboard_tabs(browser_page):
    page = browser_page
    page.set_viewport_size({'width': 390, 'height': 844})
    mount(page, 'opening_catalog_ui.py', dict(courses=catalog_cards(), colors=palette(True),
        selected=[], start=str(today()), end=str(today()), valid=True))
    page.get_by_role('tab', name='Brancas', exact=True).focus()
    page.keyboard.press('ArrowRight')
    assert page.get_by_role('tab', name='Pretas', exact=True).get_attribute('aria-selected') == 'true'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    Path(__file__).with_name('artifacts').mkdir(exist_ok=True)
    page.screenshot(path=str(Path(__file__).with_name('artifacts') / 'repertorios-celular.png'), full_page=True)


def test_training_board_click_and_wrong_drag_snap_back(browser_page):
    page = browser_page
    data = board_data()
    data.update(trainingMode=True, trainingExpected='e2e4')
    mount(page, 'interactive_board.py', data)
    page.locator('[data-square=e2]').click()
    page.locator('[data-square=e4]').click()
    assert page.evaluate('window.events[0].value.uci') == 'e2e4'
    # A new revision acknowledges the previous event.
    data['revision'] = 1
    page.evaluate('data=>window.render(data)', data)
    drag(page, 'd2', 'd4')
    assert page.evaluate('window.events[1].value.uci') == 'd2d4'
    assert page.locator('.drag-ghost').count() == 0
    assert 'dragging' not in page.locator('[data-square=d2]').get_attribute('class')
    assert page.locator('[data-square=d2] svg').count() == 1


@pytest.fixture
def repertoire_server(tmp_path):
    import os
    import socket
    import subprocess
    import time
    from urllib.request import urlopen

    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, ACERVO_PREPARATION_DIR=str(tmp_path))
    process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run',
        str(Path(__file__).with_name('repertoire_fixture.py')), '--server.headless=true',
        f'--server.port={port}', '--browser.gatherUsageStats=false'], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        for _ in range(100):
            try:
                with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        yield f'http://127.0.0.1:{port}'
    finally:
        process.terminate()
        process.wait(timeout=15)


def test_preparation_restores_indicators_and_cancels_from_trail(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    app = AppTest.from_string("from preparation_workspace import render_preparation\nrender_preparation([], 'test-ui', '', False)", default_timeout=20).run()
    app.session_state.prep_plan = create_repertoire_plan('test-ui',['caro'],today(),today()+timedelta(days=6))
    app.session_state.prep_repertoire_active = True
    app.run()
    assert not app.exception
    assert [b.label for b in app.button] == ['Voltar à trilha']
    assert app.subheader[0].value.startswith('Caro-Kann')
    assert app.caption and not app.metric
    app.button[0].click().run()
    assert not app.exception
    assert not app.session_state.prep_repertoire_active
    assert [b.label for b in app.button] == ['Cancelar preparo']
    assert not app.subheader and not app.metric and not app.get('progress') and not app.expander
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state.prep_plan is None


def test_instant_catalog_click_starts_selected_course(browser_page):
    page = browser_page
    mount(page,'opening_catalog_ui.py',dict(courses=catalog_cards(),colors=palette(False),
        selected=[],start=str(today()),end=str(today()),valid=True,instant=True))
    assert not page.locator('.confirm').is_visible()
    page.locator('[data-id=italian]').click(timeout=60000)  # 1º carregamento do Streamlit pode levar ~15 s
    assert page.evaluate('window.events[0].value.ids') == ['italian']


@pytest.mark.parametrize('width,height', [(1366,768),(390,844),(844,390)])
def test_preparation_repeats_automatically_without_hints(browser_page,repertoire_server,tmp_path,width,height):
    import json
    from playwright.sync_api import expect
    page = browser_page
    page.set_viewport_size(dict(width=width,height=height))
    page.goto(repertoire_server)
    page.locator('[data-id=italian]').click(timeout=60000)  # 1º carregamento do Streamlit pode levar ~15 s
    expect(page.locator('.board')).to_be_visible()
    expect(page.locator('.board-coordinate')).to_have_count(16)
    expect(page.locator('[data-square=a1] .file')).to_have_text('a')
    expect(page.locator('.training-hint')).to_have_count(0)
    assert page.get_by_role('button', name='Próxima posição', exact=True).count() == 0
    def saved():
        import time
        for _ in range(50):
            try:
                return json.loads(next(tmp_path.glob('*.json')).read_text(encoding='utf8'))['training_days'][str(today())]
            except (PermissionError, FileNotFoundError, StopIteration):
                time.sleep(.01)
        raise AssertionError('Não foi possível ler o progresso salvo')
    previous = None
    for _i in range(8):
        session = saved()
        assert session['current'] != previous
        previous = session['current']
        exercise = session['positions'][previous]['exercise']
        board = chess.Board(exercise['fen'])
        uci = next(m.uci() for m in board.legal_moves if m.uci() != exercise['uci'])
        page.locator('[data-square='+uci[:2]+'].movable').click()
        page.locator('[data-square='+uci[2:4]+']').click()
        expect(page.get_by_text('Jogada incorreta. Essa posição aparecerá novamente.',exact=True)).to_be_visible()
        # Wait for the acknowledged board; every accepted event gets a revision.
        import time
        deadline = time.monotonic()+10
        while saved()['revision'] == session['revision'] and time.monotonic() < deadline:
            page.wait_for_timeout(30)
        assert saved()['revision'] > session['revision']
        expect(page.locator('.training-hint')).to_have_count(0)
        page.wait_for_timeout(150)
    bounds = page.locator('.board').bounding_box()
    assert abs(bounds['width']-bounds['height']) < 2
    if width > 1000:
        assert bounds['width'] >= 500
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    folder = Path(__file__).with_name('artifacts')
    folder.mkdir(exist_ok=True)
    page.screenshot(path=str(folder/f'preparo-repeticao-{width}x{height}.png'),full_page=True)
    before = saved()
    page.get_by_role('button',name='Voltar à trilha').click()
    page.locator('.day.current').click()
    expect(page.locator('.board')).to_be_visible()
    assert saved()['positions'] == before['positions']
    assert saved()['current'] == before['current']
