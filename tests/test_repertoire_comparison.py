import chess
import chess.engine
import chess.pgn
import pytest

import classroom as rooms
import repertoire_comparison as comparison
import analysis_training as training
from personal_openings import remember_history, storage_key
from preparation_state import save_plan


def game(sans, white='alice', black='bob', fen=None):
    result = chess.pgn.Game()
    if fen:
        result.setup(chess.Board(fen))
    result.headers.update(White=white, Black=black)
    board, node = result.board(), result
    for san in sans.split():
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)
    return dict(pgn=str(result), white={'username': white}, black={'username': black})


def line(sans='d4 d5 Nf3 Nf6 c4 e6', context=4, **kwargs):
    board, moves = chess.Board(), []
    for san in sans.split():
        move = board.parse_san(san)
        moves.append(move.uci())
        board.push(move)
    return dict(id=sans, moves=moves, side='white', context_plies=context, **kwargs)


def test_transposition_and_later_reentry():
    item = game('Nf3 d5 d4 Nf6 c4 e6')
    result = comparison.compare([item], 'ALICE', [line()])['games'][0]
    assert result['status'] == 'matched' and result['covered'] == 1
    finding = comparison.compare([item], 'alice', [line(context=0)])['games'][0]['findings'][0]
    assert finding['status'] == 'reentry' and finding['reentry'] == 3
    assert finding['fen'] == chess.STARTING_FEN and finding['played'] == 'Nf3'


def test_no_match_and_multiple_repertoires():
    assert comparison.compare([game('e4 e5 Nf3 Nc6')], 'alice', [line()])['games'][0]['status'] == 'no_match'
    first = line('e4 e5 Nf3 Nc6', context=2, source='A')
    second = line('e4 e5 Bc4 Nc6', context=2, source='B')
    assert comparison.compare([game('e4 e5 Bc4 Nc6')], 'alice', [first, second])['games'][0]['status'] == 'matched'
    finding = comparison.compare([game('e4 e5 d3 Nc6')], 'alice', [first, second])['games'][0]['findings'][0]
    assert {o['expected_san'] for o in finding['options']} == {'Nf3', 'Bc4'}
    assert finding['status'] == 'divergence' and finding['ply'] == 3
    board = chess.Board(finding['fen'])
    assert all(chess.Move.from_uci(o['expected']) in board.legal_moves for o in finding['options'])


def test_castling_rights_and_invalid_sources():
    board = chess.Board()
    board.push_san('e4'); board.push_san('e5')
    board.castling_rights = chess.BB_EMPTY
    result = comparison.compare([game('Nf3', fen=board.fen()), game('e4', white='foreign')], 'alice',
                                [line('e4 e5 Nf3', context=2), dict(line(), moves=['e2e5'])])
    assert result['games'][0]['status'] == 'no_match'
    assert result['skipped_lines'] == 1 and result['skipped_games'] == 1


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('Comparison must remain local and engine-free')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(chess.engine.SimpleEngine, 'popen_uci', forbidden)
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path / 'accounts.sqlite3'))
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path / 'plans'))
    rooms.bootstrap_owner('owner', 'password-owner-123')
    tokens = [rooms.register_user(name, 'password-test-123') for name in ('one', 'two')]
    for token in tokens:
        rooms.save_chesscom_user(token, 'alice')
    token = tokens[0]
    owner = 'user:' + rooms.identity(token)['id']
    save_plan(dict(version=1, username=storage_key(owner, 'alice'), personal_lines=[line()]), namespace='openings')
    remember_history(owner, 'alice', [game('d4 d5 Nf3 Nf6 e3 e6')])
    return tokens


def test_account_isolation_navigation_dedup_attempt_and_review(accounts):
    token, other = accounts
    result = comparison.report(token)
    assert result['lines'] == 1 and len(result['games']) == 1
    assert comparison.report(other)['games'] == [] and comparison.report(other)['lines'] == 0
    finding = result['games'][0]['findings'][0]
    state = dict(classroom_token=token)
    comparison.open_position(token, state, finding['id'])
    assert state['requested_page'] == 'Análise' and state['dashboard_review_request']['ply'] == 4
    with pytest.raises(PermissionError):
        comparison.open_position(token, dict(classroom_token=other), finding['id'])
    with pytest.raises(ValueError):
        comparison.open_position(other, dict(classroom_token=other), finding['id'])
    for _ in range(2):
        comparison.open_position(token, state, finding['id'], line=finding['options'][0]['line'], exercise=True)
    item, = training.listing(token)
    assert item['source'] == 'repertoire' and item['fen'] == finding['fen']
    assert training.listing(other) == []
    with pytest.raises(ValueError):
        training.submit(token, item['id'], 'e2e5', 0)
    attempt = training.submit(token, item['id'], item['uci'], 0)
    assert attempt['matched'] and training.listing(token)[0]['revision'] == 1
    assert attempt['due'] > item['due']
    comparison.open_position(token, state, finding['id'], line=finding['options'][0]['line'], exercise=True)
    assert training.listing(token)[0]['revision'] == 1
    rooms.logout(token)
    with pytest.raises(PermissionError):
        comparison.report(token)


def test_course_filter_and_library(accounts, monkeypatch):
    import opening_training_state
    token, _ = accounts
    owner = 'user:' + rooms.identity(token)['id']
    a, b = line(source='unused'), line('e4 e5 Nf3', context=2)
    monkeypatch.setattr(opening_training_state, 'lines_for', lambda plan: {a['id']: a, b['id']: b})
    root = dict(version=1, username=owner, repertoire_ids=['current'],
                practice_progress={a['id']: {'learned': True}},
                practice_library={'previous': dict(practice_progress={b['id']: {'learned': True}})})
    save_plan(root, namespace='openings')
    lines = comparison.load_sources(token)['lines']
    assert len(lines) == 3
    assert {l['source'] for l in lines} == {'Repertório pessoal', 'Curso estudado: current', 'Curso estudado: previous'}
    assert all(l['studied'] for l in lines if l['source'].startswith('Curso'))


def test_archived_games_are_account_scoped(accounts):
    import analysis_archive
    from chess_review import MoveReview
    from io import StringIO
    token, other = accounts
    archived = game('e4 e5 Nf3 Nc6')['pgn']
    parsed = chess.pgn.read_game(StringIO(archived))
    board, reviews = parsed.board(), {}
    for ply, move in enumerate(parsed.mainline_moves(), 1):
        reviews[ply] = MoveReview(ply, str(board.fullmove_number), 'Brancas' if board.turn else 'Pretas',
            board.san(move), move.uci(), 'good', 0, 0, None, board.san(move), '', [], '')
        board.push(move)
    result = dict(reviews=reviews, explanations={}, references={})
    analysis_archive.save(other, archived, result)
    assert len(comparison.report(token)['games']) == 1
    assert comparison.report(other)['games'][0]['pgn'] == archived
    analysis_archive.save(token, archived, result)
    assert len(comparison.report(token)['games']) == 2


def test_black_side_and_missing_identity():
    reference = line('e4 e5 Nf3 Nc6', context=1)
    reference['side'] = 'black'
    item = game('e4 c5', white='bob', black='alice')
    finding = comparison.compare([item], 'alice', [reference])['games'][0]['findings'][0]
    assert finding['ply'] == 2 and finding['played'] == 'c5'
    assert finding['options'][0]['expected_san'] == 'e5'
    assert not chess.Board(finding['fen']).turn
    assert not comparison.compare([item], '', [reference])['games']


def test_ui_navigation_and_lazy_loading(accounts, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import repertoire_comparison_ui as ui
    token, other = accounts
    boards = []
    monkeypatch.setattr(ui, 'interactive_board', lambda board, **kwargs: boards.append(board.fen()))
    app = AppTest.from_string('''
import streamlit as st
from repertoire_comparison_ui import render
render(st.session_state.classroom_token)
''', default_timeout=20)
    app.session_state.classroom_token = token
    app.run()
    assert not app.exception and not boards
    app.toggle[0].set_value(True).run()
    assert not app.exception and boards
    owner = rooms.identity(token)['id']
    app.button(key='dashboard_repertoire_' + owner + '_study').click().run()
    assert not app.exception and app.session_state.dashboard_review_request['ply'] == 4
    app.button(key='dashboard_repertoire_' + owner + '_train').click().run()
    assert not app.exception and len(training.listing(token)) == 1
    app.session_state.classroom_token = other
    app.run()
    assert not app.exception and not app.selectbox
