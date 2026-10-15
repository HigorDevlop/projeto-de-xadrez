"""Questionário e treino de preparo com material local e interação real no tabuleiro."""
from datetime import timedelta
from io import StringIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import chess
import chess.pgn
import pytest
from streamlit.testing.v1 import AppTest

from preparation_fixture import fixture_history, fixture_material
from preparation_state import today
from test_browser_components import drag


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests' / 'preparation_fixture.py'


@pytest.fixture
def preparation_app(tmp_path, monkeypatch):
    import preparation_data

    original_builder = preparation_data.build_training_material
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    monkeypatch.delenv('ACERVO_PREP_FIXTURE_SEEDED', raising=False)
    for module in ('preparation_workspace', 'interactive_board', 'opening_catalog_ui', 'opening_training_ui', 'opening_transition', 'preparation_ui'):
        sys.modules.pop(module, None)
    app = AppTest.from_file(str(FIXTURE), default_timeout=20)
    yield app
    preparation_data.build_training_material = original_builder
    for module in ('preparation_workspace', 'interactive_board', 'opening_catalog_ui', 'opening_training_ui', 'opening_transition', 'preparation_ui'):
        sys.modules.pop(module, None)


def click(app, label):
    next(button for button in app.button if button.label == label and not button.disabled).click().run()
    assert not app.exception


def wait_for_plan(app):
    for _ in range(30):
        assert not app.exception
        plan = app.session_state.prep_plan
        if plan and plan.get('material', {}).get('opening_lines'):
            return plan
        time.sleep(.03)
        app.run()
    pytest.fail('O preparo local não terminou de montar o material.')


def test_fixture_lessons_are_legal_and_error_is_from_the_source_game():
    material = fixture_material()
    assert len(fixture_history()) == 2
    assert len(material['opening_lines']) == 2
    for lesson in material['opening_lines']:
        assert len(lesson['steps']) == 5
        for index, step in enumerate(lesson['steps']):
            board = chess.Board(step['fen'])
            move = chess.Move.from_uci(step['uci'])
            assert move in board.legal_moves
            assert board.san(move) == step['san']
            board.push(move)
            if step.get('reply'):
                board.push_uci(step['reply'])
                assert board.fen() == lesson['steps'][index + 1]['fen']
    exercise = material['tactics'][0]
    source = chess.pgn.read_game(StringIO(exercise['source_pgn']))
    node = list(source.mainline())[exercise['source_ply'] - 1]
    assert node.parent.board().fen() == exercise['fen']
    assert node.move.uci() == 'a2a3'
    assert exercise['uci'] == 'f3h4'
    assert node.parent.board().piece_at(chess.H4).piece_type == chess.QUEEN


def test_preparation_opens_catalog_without_extra_start_button(preparation_app):
    app = preparation_app.run()
    assert not app.exception
    assert len(app.date_input) == 2
    assert not app.session_state.prep_plan
    assert not any(button.label in ('Criar meu preparo','Escolher aberturas para um novo preparo') for button in app.button)


def test_preparation_rejects_invalid_period(preparation_app):
    app = preparation_app.run()
    app.date_input(key='prep_start').set_value(today()+timedelta(days=3))
    app.date_input(key='prep_end').set_value(today()).run()
    assert not app.exception
    assert any('período válido' in error.value for error in app.error)
    assert not app.session_state.prep_plan


@pytest.fixture
def preparation_server(tmp_path):
    pytest.importorskip('playwright.sync_api')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = dict(os.environ, ACERVO_PREPARATION_DIR=str(tmp_path / 'plans'),
               ACERVO_PREP_FIXTURE_SEEDED='1')
    log_path = tmp_path / 'preparation-server.log'
    with log_path.open('w', encoding='utf-8') as log:
        server = subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', str(FIXTURE),
             '--server.port', str(port), '--server.headless', 'true'],
            cwd=ROOT, env=env, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    pytest.fail(log_path.read_text(encoding='utf-8'))
                try:
                    with urlopen(url + '/_stcore/health', timeout=.5):
                        break
                except OSError:
                    time.sleep(.15)
            else:
                pytest.fail('O servidor local do preparo não respondeu.')
            yield url, tmp_path / 'plans'
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def saved_plan(folder):
    return json.loads(next(folder.glob('*.json')).read_text(encoding='utf-8'))


def wait_for_course(page, folder, condition):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        course = saved_plan(folder)['course']
        if all(course[key] == value for key, value in condition.items()):
            return course
        page.wait_for_timeout(50)
    pytest.fail(f'Estado esperado {condition}; recebido {saved_plan(folder)["course"]}')


def test_automatic_repetition_resume_and_daily_map_progression(preparation_server):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel='msedge',headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1100})
        url, folder = preparation_server
        try:
            page.goto(url)
            page.locator('.day.current').click()
            expect(page.locator('.board')).to_be_visible()
            def session():
                return saved_plan(folder)['position_sessions']['opening']
            # Initialization is persisted on the first answer or periodic save.
            deadline = time.monotonic()+15
            while 'position_sessions' not in saved_plan(folder) and time.monotonic()<deadline:
                page.wait_for_timeout(100)
            initial = session()
            ex = initial['positions'][initial['current']]['exercise']
            wrong = next(m.uci() for m in chess.Board(ex['fen']).legal_moves if m.uci()!=ex['uci'])
            drag(page,wrong[:2],wrong[2:4])
            expect(page.get_by_text('Jogada incorreta. Essa posição aparecerá novamente.',exact=True)).to_be_visible()
            assert session()['positions'][initial['current']]['status']=='error'
            assert session()['current'] != initial['current']
            expect(page.locator('.training-hint')).to_have_count(0)
            before = session()
            page.reload()
            page.locator('.day.current').click()
            expect(page.locator('.board')).to_be_visible()
            assert session()['positions']==before['positions']
            assert session()['current']==before['current']
            for stage in ('opening','middlegame','tactics'):
                if stage != 'opening':
                    page.locator('.day.current').click()
                    expect(page.locator('.board')).to_be_visible()
                deadline = time.monotonic()+15
                while stage not in saved_plan(folder).get('position_sessions',{}) and time.monotonic()<deadline:
                    page.wait_for_timeout(100)
                for _ in range(50):
                    s = saved_plan(folder)['position_sessions'][stage]
                    if s['phase']=='complete':
                        break
                    exercise = s['positions'][s['current']]['exercise']
                    uci = exercise['uci']
                    page.locator('[data-square='+uci[:2]+'].movable').wait_for()
                    drag(page,uci[:2],uci[2:4])
                    deadline = time.monotonic()+10
                    while saved_plan(folder)['position_sessions'][stage]['revision']==s['revision'] and time.monotonic()<deadline:
                        page.wait_for_timeout(30)
                    assert saved_plan(folder)['position_sessions'][stage]['revision']>s['revision']
                    page.wait_for_timeout(120)
                else:
                    pytest.fail('A fase não concluiu após os acertos necessários')
                expect(page.locator('.trail')).to_be_visible()
                assert saved_plan(folder)['days'][str(today())][stage]['done']
            page.get_by_role('button',name='Encerrar Preparo',exact=True).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            expect(page.get_by_text('Posições dominadas',exact=True)).to_be_visible()
        finally:
            browser.close()


def test_mobile_focus_clock_and_finish_dialog(preparation_server):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':390, 'height':844})
        url, folder = preparation_server
        try:
            page.goto(url)
            expect(page.locator('.day.current')).to_be_visible(timeout=30000)
            expect(page.locator('.st-key-prep_day_card img')).to_be_visible()
            artifacts = ROOT / 'tests' / 'artifacts'
            artifacts.mkdir(exist_ok=True)
            page.screenshot(path=str(artifacts/'preparo-trilha-celular.png'), full_page=True)
            page.locator('.day.current').click()
            expect(page.locator('.board')).to_be_visible()
            expect(page.locator('[data-testid="stSidebar"]')).to_be_hidden()
            expect(page.locator('[role="timer"]')).to_be_visible()
            assert page.locator('.st-key-prep_clock').bounding_box()['y'] == 0
            assert page.locator('.st-key-prep_clock').bounding_box()['width'] <= 390
            assert page.locator('.board').bounding_box()['width'] <= 390
            page.screenshot(path=str(artifacts/'preparo-foco-celular.png'), full_page=True)
            page.get_by_role('button', name='Concluir Treino', exact=True).click()
            dialog = page.get_by_role('dialog')
            expect(dialog).to_be_visible()
            expect(dialog.get_by_text('Nenhuma tentativa registrada.', exact=True)).to_be_visible()
            expect(page.locator('[data-testid="stAppViewContainer"]')).to_have_css('filter', 'blur(8px)')
            assert dialog.get_by_role('button').count() == 1
            assert saved_plan(folder)['finished']
            assert saved_plan(folder)['active'] is None
            page.screenshot(path=str(artifacts/'preparo-resultado-celular.png'), full_page=True)
            page.get_by_role('button', name='Iniciar Novo Preparo', exact=True).click()
            page.get_by_text('Período do preparo',exact=True).click()
            expect(page.get_by_label('Data de início', exact=True)).to_be_visible()
        finally:
            browser.close()
