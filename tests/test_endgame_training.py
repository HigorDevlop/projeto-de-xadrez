from copy import deepcopy
from datetime import date, timedelta
from types import SimpleNamespace

import chess
import chess.engine
import pytest

import classroom as rooms
import endgame_training as training
from endgame_lessons import LESSONS
import preparation_repetition as recall

DAY = date(2026, 11, 10)


@pytest.fixture
def endgame_server(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    import socket
    import subprocess
    import sys
    import time
    from urllib.request import urlopen
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'accounts.sqlite3'))
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path/'plans'))
    rooms.register_user('endgame-browser', 'endgame-browser-password')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(root/'tests/endgame_fixture.py'),
        '--server.headless=true', f'--server.port={port}', '--browser.gatherUsageStats=false'],
        cwd=root, env=dict(os.environ), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:
                with urlopen(url+'/_stcore/health', timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        yield url
    finally:
        process.terminate()
        process.wait(timeout=15)


@pytest.fixture
def users(tmp_path, monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'users.sqlite3'))
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path/'plans'))
    monkeypatch.setattr(training, 'today', lambda: DAY)
    def forbidden(*args, **kwargs):
        raise AssertionError('Treino de finais deve funcionar sem rede nem motor.')
    import socket
    import requests
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    monkeypatch.setattr(chess.engine.SimpleEngine, 'popen_uci', forbidden)
    return (rooms.register_user('learner', 'learner-password-123'),
            rooms.register_user('other', 'other-password-123'))


def event(token, item, uci=None):
    session = training.load(token)['practice_sessions'][item['id']]
    return dict(fen=item['fen'], revision=recall.revision(session), uci=uci or item['uci'])


def answer(token, item, uci=None):
    return training.act(token, item['id'], 'move', event(token, item, uci))


def complete(token, item):
    training.act(token, item['id'], 'begin')
    answer(token, item)
    training.act(token, item['id'], 'continue')
    plan, changed = answer(token, item)
    assert changed and plan['practice_sessions'][item['id']]['phase'] == 'complete'
    return plan


def test_objectives_match_real_positions():
    first, second, third = LESSONS
    for item in (first, second):
        board = chess.Board(item['fen'])
        board.push_uci(item['uci'])
        white, black = board.king(chess.WHITE), board.king(chess.BLACK)
        assert chess.square_file(white) == chess.square_file(black)
        assert chess.square_distance(white, black) == 2 and board.turn == chess.BLACK
    board = chess.Board(second['fen'])
    board.push_uci(second['uci'])
    assert board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board.king(chess.WHITE) == chess.E6
    board = chess.Board(third['fen'])
    board.push_uci(third['uci'])
    assert board.piece_at(chess.E8) == chess.Piece(chess.QUEEN, chess.WHITE)
    assert board.is_check() and not board.is_checkmate() and not board.is_stalemate()


def test_full_trail_completion_offline_and_unlocking(users):
    token, _ = users
    with pytest.raises(ValueError): training.act(token, LESSONS[1]['id'], 'begin')
    for item in LESSONS:
        plan = complete(token, item)
        assert plan['practice_progress'][item['id']]['learned']
        assert plan['retention'][item['id']] == dict(level=0, due='2026-11-11')
    assert len(plan['practice_progress']) == 3


def test_legal_wrong_illegal_stale_and_duplicate_attempts(users):
    token, _ = users
    item = LESSONS[0]
    plan, _ = training.act(token, item['id'], 'begin')
    for uci in ('e3e6', 'e3e5', '0000', 'invalid'):
        current, changed = answer(token, item, uci)
        assert not changed and current == plan
    attempt = event(token, item, 'e3d3')
    current, changed = training.act(token, item['id'], 'move', dict(attempt, fen=chess.STARTING_FEN))
    assert not changed
    current, changed = training.act(token, item['id'], 'move', attempt)
    assert changed and current['practice_progress'][item['id']]['attempts'] == 1
    session = current['practice_sessions'][item['id']]
    assert chess.Board(session['result_fen']).king(chess.WHITE) == chess.D3
    assert 'Lance legal' in training.feedback(item, session)
    assert training.act(token, item['id'], 'move', attempt)[1] is False
    training.act(token, item['id'], 'continue')
    assert training.act(token, item['id'], 'move', attempt)[1] is False


def test_gradual_hints_solution_and_assistance_do_not_complete(users):
    token, _ = users
    item = LESSONS[0]
    training.act(token, item['id'], 'begin')
    answer(token, item)
    training.act(token, item['id'], 'continue')
    old = event(token, item)
    for level in range(1, 4):
        plan, _ = training.act(token, item['id'], 'hint')
        assert plan['practice_sessions'][item['id']]['hint_level'] == level
    assert not training.act(token, item['id'], 'move', old)[1]
    training.act(token, item['id'], 'solution')
    plan, _ = answer(token, item)
    session = plan['practice_sessions'][item['id']]
    assert session['phase'] != 'complete' and session['solution']
    assert not plan['practice_progress'][item['id']]['learned']
    training.act(token, item['id'], 'continue')
    plan, _ = answer(token, item)
    assert plan['practice_progress'][item['id']]['learned']
    assert plan['retention'][item['id']]['level'] == 0


def test_resume_relogin_isolation_and_review(users, monkeypatch):
    token, other = users
    item = LESSONS[0]
    training.act(token, item['id'], 'begin')
    training.act(token, item['id'], 'hint')
    answer(token, item)
    before = training.load(token)
    rooms.logout(token)
    with pytest.raises(PermissionError): training.load(token)
    token = rooms.login_user('learner', 'learner-password-123')
    assert training.load(token) == before
    assert training.load(other)['practice_sessions'] == {}
    training.act(token, item['id'], 'continue')
    plan, _ = answer(token, item)
    old_session = deepcopy(plan['practice_sessions'][item['id']])
    plan, _ = training.act(token, item['id'], 'begin')
    assert plan['practice_sessions'][item['id']] == old_session
    monkeypatch.setattr(training, 'today', lambda: DAY+timedelta(days=1))
    plan = complete(token, item)
    assert plan['retention'][item['id']] == dict(level=1, due='2026-11-14')
    assert plan['practice_sessions'][item['id']]['token'] != old_session['token']


def test_ui_feedback_board_solution_and_account_switch(users, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import opening_reference_endgames as ui
    token, other = users
    pending, shown = [], []
    def board(position, **kwargs):
        shown.append(position.fen())
        return SimpleNamespace(move=pending.pop(0) if pending and not kwargs['disabled'] else None)
    monkeypatch.setattr(ui, 'interactive_board', board)
    app = AppTest.from_string('from opening_reference_endgames import render_endgames\nrender_endgames()')
    app.session_state.classroom_token = token
    app.run()
    assert not app.exception and app.button[1].disabled
    app.button[0].click().run()
    assert shown[-1] == LESSONS[0]['fen']
    pending.append(event(token, LESSONS[0], 'e3d3'))
    app.run()
    assert not app.exception and chess.Board(shown[-1]).king(chess.WHITE) == chess.D3
    app.button(key='endgame_solution').click().run()
    assert app.select_slider and not app.exception
    assert any('continuação ilustrativa' in m.value.lower() for m in app.markdown)
    app.session_state.classroom_token = other
    app.run()
    assert not app.exception and not app.select_slider
    assert training.load(other)['practice_current'] is None
