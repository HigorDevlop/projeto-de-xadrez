from io import BytesIO, StringIO
from pathlib import Path
import sys
import chess
import chess.pgn
import chess.svg
from PIL import Image
import pytest
from streamlit.testing.v1 import AppTest

from book_positions import BookPositionService, PagePositions, scan_page, text_positions
from book_reader import book_id, book_info
from test_browser_components import browser_page


def after(*moves):
    board = chess.Board()
    for move in moves:
        board.push_san(move)
    return board


def test_fen_pages_preserve_exact_turn_castling_and_en_passant():
    board = after('e4', 'c5', 'e5', 'd5')
    fen = board.fen(en_passant='fen')
    positions = text_positions(f'Posição do livro: {fen}')
    assert len(positions) == 1 and positions[0].fen == fen
    assert positions[0].turn_known and positions[0].castling_known
    unknown = text_positions(board.board_fen())[0]
    assert not unknown.castling_known


def test_bare_placement_uses_explicit_turn_and_never_invents_roque():
    positions = text_positions(chess.STARTING_BOARD_FEN + '\nPretas jogam')
    board = chess.Board(positions[0].fen)
    assert board.turn == chess.BLACK and not board.castling_rights
    assert positions[0].turn_known and not positions[0].castling_known
    assert not text_positions('8/8/8/8/8/8/8/8 w - - 0 1')
    assert not text_positions('Um texto sem diagrama ou notação.')


def test_pgn_books_have_complete_games_per_page_including_custom_positions():
    custom = chess.pgn.Game()
    custom.setup(chess.Board('4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'))
    custom.add_variation(chess.Move.from_uci('e2e4'))
    data = ('1. e4 e5 *\n\n' + str(custom)).encode()
    info = book_info('Manual.pgn', data)
    assert info['count'] == 2 and info['pgn']
    second = scan_page(data, info, 1).positions[0]
    assert second.fen == custom.board().fen()
    assert list(chess.pgn.read_game(StringIO(second.pgn)).mainline_moves()) == [chess.Move.from_uci('e2e4')]


def test_service_prepares_next_pages_and_reuses_disk_cache(tmp_path, monkeypatch):
    fens = [after().fen(), after('e4').fen(), after('d4').fen()]
    data = '\f'.join(fens).encode()
    entry = 'Manual.txt', data, book_info('Manual.txt', data)
    service = BookPositionService(tmp_path)
    try:
        identity = service.prepare(entry, 0)
        service.jobs[identity, 1].result(timeout=10)
        service.prepare(entry, 1)
        assert service.result(identity, 1).positions[0].fen == fens[1]
    finally:
        service.executor.shutdown(wait=True)
    monkeypatch.setattr('book_positions.scan_page', lambda *args: pytest.fail('Prepared pages must be read from cache'))
    restored = BookPositionService(tmp_path)
    try:
        restored.prepare(entry, 1, lookahead=0)
        cached = restored.jobs[identity, 1].result(timeout=10)
        assert cached.positions[0].fen == fens[1]
    finally:
        restored.executor.shutdown(wait=True)


def test_retry_uses_higher_resolution_and_keeps_previous_diagrams(tmp_path, monkeypatch):
    from book_positions import BookPosition
    first = BookPosition(after('e4').fen(), 'Diagrama 1', 'diagrama do PDF')
    second = BookPosition(after('d4').fen(), 'Diagrama 2', 'diagrama do PDF')
    flags = []
    def scanner(data, info, index, *, high_resolution=False):
        flags.append(high_resolution)
        return PagePositions((second,) if high_resolution else (first,))
    monkeypatch.setattr('book_positions.scan_page', scanner)
    entry = 'Manual.pdf', b'pdf', {'kind':'pdf','count':1}
    service = BookPositionService(tmp_path)
    try:
        identity = service.prepare(entry, 0)
        service.jobs[identity, 0].result(timeout=10)
        service.retry(entry, 0)
        result = service.jobs[identity, 0].result(timeout=10)
        assert {p.fen for p in result.positions} == {first.fen, second.fen}
        assert flags == [False, True]
    finally:
        service.close()


def _scan_ready(app):
    service = app.session_state._book_position_service
    for future in list(service.jobs.values()):
        future.result(timeout=15)
    app.run(timeout=20)
    assert not app.exception


def test_entire_book_is_preloaded_and_far_pages_reuse_disk_cache(tmp_path, monkeypatch):
    data = ('\f'.join([after('e4').fen()] * 260)).encode()
    entry = 'Livro inteiro.txt', data, book_info('Livro inteiro.txt', data)
    service = BookPositionService(tmp_path)
    try:
        identity = service.preload(entry)
        service.preloads[identity]['future'].result(timeout=20)
        assert service.preload_progress(identity) == (260, 260, 0)
        assert len(service.jobs) <= 128
    finally:
        service.close()
    monkeypatch.setattr('book_positions.scan_page', lambda *args: pytest.fail('Page was already preloaded'))
    restored = BookPositionService(tmp_path)
    try:
        restored.prepare(entry, 259, lookahead=0)
        page = restored.jobs[identity, 259].result(timeout=10)
        assert page.positions[0].fen == after('e4').fen()
    finally:
        restored.close()


def test_printed_lines_are_legal_from_the_diagram_and_not_invented():
    position = after('e4', 'e5')
    result = text_positions(position.fen()+'\n2. Nf3 Nc6 3. Bb5 a6')
    diagram = next(p for p in result if chess.Board(p.fen).board_fen() == position.board_fen())
    game = chess.pgn.read_game(StringIO(diagram.pgn))
    assert [move.uci() for move in game.mainline_moves()] == ['g1f3', 'b8c6', 'f1b5', 'a7a6']
    assert game.board().fullmove_number == 2
    invalid = text_positions(position.fen()+'\n2. Qh8 Rxa1')
    assert not invalid[0].pgn


def test_original_line_can_be_restored_after_exploring_another_move(tmp_path):
    data = b'1. e4 e5 2. Nf3 Nc6 *'
    entry = 'Linha.pgn', data, book_info('Linha.pgn', data)
    service = BookPositionService(tmp_path)
    identity = service.prepare(entry, 0)
    service.jobs[identity, 0].result(timeout=10)
    app = AppTest.from_string('''
import streamlit as st
from book_position_ui import render_page_positions
render_page_positions(st.session_state.entry)
''')
    app.session_state.entry = entry
    app.session_state._book_position_service = service
    app.session_state.reader_book = identity
    app.session_state.reader_page = 0
    app.session_state.book_editing = False
    app.session_state.book_revision = 0
    app.session_state.book_follow_positions = True  # Legacy preference must not auto-load.
    app.session_state.book_game = str(chess.pgn.Game())
    app.session_state.book_ply = 0
    try:
        app.run()
        app.button(key='load_book_page_position').click().run()
        original = app.session_state.book_game
        app.session_state.book_game = '1. d4 d5 *'
        app.session_state.book_ply = 2
        app.run()
        assert 'd4' in app.session_state.book_game
        app.button(key='restore_book_line').click().run()
        assert app.session_state.book_game == original
        assert app.session_state.book_ply == 0
        app.segmented_control[0].set_value('Pretas').run()
        app.button(key='load_book_page_position').click().run()
        assert not list(chess.pgn.read_game(StringIO(app.session_state.book_game)).mainline_moves())
        app.button(key='restore_book_line').click().run()
        assert app.segmented_control[0].value == 'Brancas'
        assert app.session_state.book_game == original
        assert not app.exception
    finally:
        service.close()


def test_reader_loads_each_page_and_preserves_exploration_on_the_same_page(tmp_path):
    # AppTest owns a fresh component registry, independent of modules imported
    # during collection by other analysis/editor tests.
    for name in ('interactive_board', 'study_workspace', 'study_focus', 'book_position_ui'):
        sys.modules.pop(name, None)
    first, second = after(), after('d4', 'd5')
    data = (first.fen()+'\f'+second.fen()).encode()
    app = AppTest.from_string('''
import streamlit as st
from study_workspace import render_study
st.session_state.setdefault('study_upload_revision', 0)
render_study(st.session_state.study_files, True, False)
''')
    app.session_state.study_files = (('Manual.txt', data),)
    app.session_state.reader_book = book_id('Manual.txt', data)
    app.session_state.reader_page = 0
    app.session_state.reader_page_input = 1
    app.session_state.game = 'Partida principal preservada'
    app.session_state.book_follow_positions = True  # Legacy preference must not auto-load.
    app.session_state.book_game = str(chess.pgn.Game())
    app.session_state.book_ply = 0
    app.session_state._book_position_service = BookPositionService(tmp_path)
    try:
        app.run(timeout=20)
        _scan_ready(app)
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == first.fen()
        game = chess.pgn.Game()
        game.add_variation(chess.Move.from_uci('e2e4'))
        app.session_state.book_game = str(game)
        app.session_state.book_ply = 1
        app.run()
        assert app.session_state.book_ply == 1  # No reset on a move/rerun within one page.
        app.button(key='reader_next').click().run()
        assert app.session_state.book_ply == 1
        app.button(key='load_book_page_position').click().run()
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == second.fen()
        app.button(key='reader_previous').click().run()
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == second.fen()
        app.button(key='load_book_page_position').click().run()
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == first.fen()
        next(b for b in app.button if b.label == 'Editar posição').click().run()
        app.button(key='reader_next').click().run()
        assert app.session_state.book_editing
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == first.fen()
        assert app.button(key='load_book_page_position').disabled
        next(b for b in app.button if b.label == 'Cancelar edição').click().run()
        app.button(key='load_book_page_position').click().run()
        assert not app.session_state.book_editing
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == second.fen()
        assert app.session_state.game == 'Partida principal preservada'
        assert not app.exception
    finally:
        app.session_state._book_position_service.executor.shutdown(wait=True)


def test_reader_selects_between_multiple_positions_on_one_page(tmp_path):
    first, second = after('e4'), after('d4')
    data = (first.fen()+'\n\n'+second.fen()).encode()
    entry = 'Diagramas.txt', data, book_info('Diagramas.txt', data)
    service = BookPositionService(tmp_path)
    identity = service.prepare(entry, 0)
    service.jobs[identity, 0].result(timeout=10)
    app = AppTest.from_string('''
import streamlit as st
from book_position_ui import render_page_positions
render_page_positions(st.session_state.entry)
''')
    app.session_state.entry = entry
    app.session_state._book_position_service = service
    app.session_state.reader_book = identity
    app.session_state.reader_page = 0
    app.session_state.book_editing = False
    app.session_state.book_revision = 0
    app.session_state.book_follow_positions = True  # Legacy preference must not auto-load.
    app.session_state.book_game = str(chess.pgn.Game())
    app.session_state.book_ply = 0
    try:
        app.run()
        assert not app.exception
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == chess.STARTING_FEN
        app.button(key='load_book_page_position').click().run()
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == first.fen()
        app.selectbox[0].select(1).run()
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == first.fen()
        app.button(key='load_book_page_position').click().run()
        assert chess.pgn.read_game(StringIO(app.session_state.book_game)).board().fen() == second.fen()
        assert not app.exception
    finally:
        service.executor.shutdown(wait=True)


@pytest.mark.parametrize('kind', ['fen', 'pgn'])
def test_reader_can_override_known_turn_and_restore_book_line(tmp_path, kind):
    board = after('e4')
    game = chess.pgn.Game()
    game.setup(board)
    game.add_variation(chess.Move.from_uci('e7e5'))
    name = 'Vez.pgn' if kind == 'pgn' else 'Vez.txt'
    data = (str(game) if kind == 'pgn' else board.fen(en_passant='fen')).encode()
    entry = name, data, book_info(name, data)
    service = BookPositionService(tmp_path)
    identity = service.prepare(entry, 0)
    service.jobs[identity, 0].result(timeout=10)
    app = AppTest.from_string('''
import streamlit as st
from book_position_ui import render_page_positions
render_page_positions(st.session_state.entry)
''')
    app.session_state.entry = entry
    app.session_state._book_position_service = service
    app.session_state.reader_book = identity
    app.session_state.reader_page = 0
    app.session_state.book_editing = False
    app.session_state.book_revision = 0
    app.session_state.book_follow_positions = True  # Legacy preference must not auto-load.
    app.session_state.book_game = str(chess.pgn.Game())
    app.session_state.book_ply = 0
    try:
        app.run()
        selector = app.segmented_control[0]
        assert selector.label == 'Quem joga nesta posição?'
        assert selector.value == 'Pretas'
        selector.set_value('Brancas').run()
        app.button(key='load_book_page_position').click().run()
        assert not app.exception
        selected = chess.pgn.read_game(StringIO(app.session_state.book_game))
        assert selected.board().turn == chess.WHITE
        assert selected.board().board_fen() == board.board_fen()
        assert selected.board().ep_square is None
        assert chess.Move.from_uci('g1f3') in selected.board().legal_moves
        assert not list(selected.mainline_moves())
        app.segmented_control[0].set_value('Pretas').run()
        app.button(key='load_book_page_position').click().run()
        restored = chess.pgn.read_game(StringIO(app.session_state.book_game))
        assert restored.board().fen() == board.fen()
        if kind == 'pgn':
            assert list(restored.mainline_moves()) == [chess.Move.from_uci('e7e5')]
        assert not app.exception
    finally:
        service.executor.shutdown(wait=True)


def test_scanned_pdf_diagrams_are_recognized_locally_and_multiple_boards_are_ordered(browser_page):
    page = browser_page
    boards = [after('e4', 'e5', 'Nf3'), after('d4', 'd5', 'c4')]
    canvas = Image.new('RGB', (1000, 1400), 'white')
    for board, (x, y) in zip(boards, [(70, 150), (570, 850)]):
        page.set_content('<style>body{margin:0}</style>'+chess.svg.board(board, size=340, coordinates=False,
                         colors={'square light':'#ffffff', 'square dark':'#bbbbbb'}))
        tile = Image.open(BytesIO(page.locator('svg').screenshot())).convert('RGB')
        canvas.paste(tile, (x,y))
    pdf = BytesIO()
    canvas.save(pdf, format='PDF', resolution=100)
    data = pdf.getvalue()
    result = scan_page(data, {'kind':'pdf'}, 0)
    assert not result.notice
    assert len(result.positions) == 2
    assert [chess.Board(p.fen).board_fen() for p in result.positions] == [b.board_fen() for b in boards]
    assert all(not p.turn_known and not p.castling_known for p in result.positions)
    assert all(p.confidence > .96 for p in result.positions)
    # Nearby PDF text establishes the active side without guessing from the image.
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    overlay = writer.add_blank_page(width=720, height=1008)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'),
                             NameObject('/BaseFont'):NameObject('/Helvetica')})
    overlay[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 14 Tf 52 914 Td (Black to move) Tj ET')
    overlay[NameObject('/Contents')] = writer._add_object(stream)
    combined = PdfWriter()
    base = combined.add_page(PdfReader(BytesIO(data)).pages[0])
    base.merge_page(overlay)
    output = BytesIO()
    combined.write(output)
    with_context = scan_page(output.getvalue(), {'kind':'pdf'}, 0)
    assert with_context.positions[0].turn_known
    assert chess.Board(with_context.positions[0].fen).turn == chess.BLACK


def test_uncertain_diagram_is_not_loaded(monkeypatch):
    from types import SimpleNamespace
    from book_positions import diagram_positions
    image = Image.new('RGB', (200,200), 'white')
    monkeypatch.setattr('book_positions._vision', lambda:(None,SimpleNamespace(predict=lambda *a,**k:
                        SimpleNamespace(confidence=.6,squares={}))))
    monkeypatch.setattr('book_positions._detect_diagrams', lambda *a:[SimpleNamespace(box=(0,0,200,200))])
    positions, uncertain = diagram_positions(image, lambda box:'White to move')
    assert not positions and uncertain == 1
