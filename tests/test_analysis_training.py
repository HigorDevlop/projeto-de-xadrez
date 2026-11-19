from dataclasses import replace
from datetime import date
from io import StringIO

import chess
import chess.pgn
import pytest

import analysis_archive as archive
import analysis_training as training
import classroom as rooms
from chess_review import MoveReview


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    def no_engine(*args, **kwargs):
        raise AssertionError('O treino não pode iniciar o motor.')
    monkeypatch.setattr(chess.engine.SimpleEngine, 'popen_uci', no_engine)
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path / 'training.sqlite3'))
    monkeypatch.setattr(training, 'today', lambda: date(2026, 11, 10))
    return (rooms.bootstrap_owner('owner', 'password-owner-123'),
            rooms.register_user('other', 'password-other-123'))


def save(token, pgn='1. e4 *', **changes):
    game = chess.pgn.read_game(StringIO(pgn))
    board = game.board()
    reports = {}
    for ply, move in enumerate(game.mainline_moves(), 1):
        report = MoveReview(ply, str(board.fullmove_number), 'Brancas' if board.turn else 'Pretas',
            board.san(move), move.uci(), 'mistake', 100, 20, None,
            'd4' if board.fen() == chess.STARTING_FEN else board.san(move), '', [], 'Explicação salva.')
        reports[ply] = replace(report, **changes)
        board.push(move)
    return archive.save(token, str(game), dict(reviews=reports, explanations={}, references={})), str(game)


def test_pre_move_position_dedup_and_legal_recommendation(accounts):
    token, other = accounts
    game, _ = save(token, best_line='1. d4 d5 2. c4')
    key = training.create(token, game, 1)
    assert training.create(token, game, 1) == key
    item, = training.listing(token)
    assert item['fen'] == chess.STARTING_FEN and item['uci'] == 'd2d4'
    assert item['best_line'] == '1. d4 d5 2. c4'
    assert training.listing(other) == []
    with pytest.raises(ValueError): training.create(other, game, 1)
    with pytest.raises(ValueError): training.submit(other, key, 'd2d4', 0)
    with pytest.raises(ValueError): training.create(token, game, 0)
    save(token, best_san='Qh8')
    with pytest.raises(ValueError): training.create(token, game, 1)


def test_transposition_and_old_archive_compatibility(accounts):
    import json
    token, other = accounts
    game, _ = save(token)
    # Simulate an archive written before the optional best_line field existed.
    with rooms.database() as db:
        row = db.execute('SELECT payload FROM saved_analyses WHERE game=?', (game,)).fetchone()
        payload = json.loads(row['payload'])
        payload['reviews']['1'].pop('best_line')
        db.execute('UPDATE saved_analyses SET payload=? WHERE game=?', (json.dumps(payload), game))
    key = training.create(token, game, 1)
    pgn = '[SetUp "1"]\n[FEN "' + chess.STARTING_FEN.replace('0 1', '8 40') + '"]\n\n40. e4 *'
    second, _ = save(token, pgn, best_san='d4')
    assert second != game and training.create(token, second, 1) == key
    assert len(training.listing(token)) == 1
    other_game, _ = save(other)
    assert training.create(other, other_game, 1) == key
    training.submit(other, key, 'd2d4', 0)
    assert training.listing(token)[0]['revision'] == 0


def test_attempt_atomic_schedule_and_relogin(accounts, monkeypatch):
    token, _ = accounts
    game, _ = save(token)
    key = training.create(token, game, 1)
    for invalid in ('e2e5', '0000', 'invalid'):
        with pytest.raises(ValueError): training.submit(token, key, invalid, 0)
    assert training.listing(token)[0]['revision'] == 0
    result = training.submit(token, key, 'e2e4', 0)
    assert not result['matched'] and result['due'] == '2026-11-11'
    assert result['best_line'] == ''  # Never substitute the played line.
    with pytest.raises(ValueError): training.submit(token, key, 'd2d4', 0)
    with pytest.raises(ValueError): training.submit(token, key, 'd2d4', 1)
    training.create(token, game, 1)
    assert training.listing(token)[0]['revision'] == 1
    rooms.logout(token)
    with pytest.raises(PermissionError): training.listing(token)
    token = rooms.login_owner('owner', 'password-owner-123')
    monkeypatch.setattr(training, 'today', lambda: date(2026, 11, 11))
    result = training.submit(token, key, 'd2d4', 1)
    assert result['matched'] and result['due'] == '2026-11-14'
    with rooms.database() as db:
        attempts = list(db.execute('SELECT uci,matched FROM analysis_attempts ORDER BY revision'))
    assert [tuple(row) for row in attempts] == [('e2e4', 0), ('d2d4', 1)]


def test_fen_start_black_turn_promotion_and_invalid_pv(accounts):
    token, _ = accounts
    pgn = '[SetUp "1"]\n[FEN "7k/8/8/8/8/8/p7/7K b - - 0 40"]\n\n40... a1=Q+ *'
    game, _ = save(token, pgn, best_san='a1=R+', best_line='40... a1=R+ 41. Kg2')
    key = training.create(token, game, 1)
    item, = training.listing(token)
    assert chess.Board(item['fen']).turn == chess.BLACK
    assert item['uci'] == 'a2a1r'
    assert training.submit(token, key, 'a2a1r', 0)['matched']
    save(token, pgn, best_san='a1=R+', best_line='40... a1=Q+')
    with pytest.raises(ValueError): training.create(token, game, 1)


def test_ui_create_attempt_feedback_and_account_switch(accounts, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import analysis_training_ui as ui
    token, other = accounts
    _, pgn = save(token, best_line='1. d4 d5')
    monkeypatch.setattr(ui, 'today', lambda: date(2026, 11, 10))
    boards = []
    monkeypatch.setattr(ui, 'interactive_board', lambda board, **kwargs: boards.append(board.fen()))
    app = AppTest.from_string('''
import streamlit as st
from analysis_training_ui import render
render(st.session_state.pgn, ready=True)
''')
    app.session_state.classroom_token = token
    app.session_state.pgn = pgn
    app.run()
    assert not app.exception and not training.listing(token)
    app.button[0].click().run()
    assert not app.exception and boards[-1] == chess.STARTING_FEN
    assert not any('Recomendação:' in item.value for item in app.markdown)
    app.selectbox[-1].select('d2d4').run()
    app.button[-1].click().run()
    assert not app.exception
    assert any('Recomendação: 1. d4 d5' in item.value for item in app.markdown)
    assert training.listing(token)[0]['revision'] == 1
    app.run()
    assert training.listing(token)[0]['revision'] == 1
    app.session_state.classroom_token = other
    app.run()
    assert not app.exception and not app.selectbox
    assert not any('Recomendação:' in item.value for item in app.markdown)


def test_engine_preserves_recommended_line_separately():
    from stockfish_analysis import analyse_with_books, find_engine
    engine = find_engine()
    if not engine:
        pytest.skip('Motor local não instalado.')
    game = chess.pgn.read_game(StringIO('1. f3 *'))
    report = analyse_with_books(game, engine, quality='Rápida')['reviews'][1]
    recommended = chess.pgn.read_game(StringIO(report.best_line + ' *'))
    played = chess.pgn.read_game(StringIO(report.line + ' *'))
    assert not recommended.errors and not played.errors
    assert game.board().san(next(iter(recommended.mainline_moves()))) == report.best_san
    assert next(iter(played.mainline_moves())).uci() == report.uci
