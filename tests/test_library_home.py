from io import BytesIO
import sys
from pathlib import Path

import chess
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from sample_books import sample_pdf

ROOT = Path(__file__).resolve().parents[1]


def test_pdf_cover_and_original_pages_render_distinctly():
    from book_reader import book_info, pdf_page
    data = sample_pdf()
    assert book_info('Livro.pdf', data)['count'] == 3
    cover = pdf_page(data, 0, 280)
    second = pdf_page(data, 1, 280)
    assert cover != second
    image = Image.open(BytesIO(cover))
    assert image.width == 280
    assert image.height > image.width
    assert image.getpixel((2, 2)) != Image.open(BytesIO(second)).getpixel((2, 2))
    with pytest.raises(ValueError):
        pdf_page(data, 3)


def test_books_are_added_without_duplicates_and_text_keeps_page_breaks():
    from book_reader import merge_books, book_info
    text = 'Primeira página.\fSegunda página.'.encode()
    assert merge_books((('A.txt', text),), [('A.txt', text), ('B.txt', b'B')]) == (('A.txt', text), ('B.txt', b'B'))
    info = book_info('A.txt', text)
    assert info['count'] == 2
    assert 'Segunda' in info['pages'][1]
    assert book_info('A.bin', b'')['count'] == 0


def test_editor_can_rebuild_position_and_rejects_invalid_piece_data():
    from study_workspace import apply_position_edit
    fen = chess.Board(None).fen()
    for square, piece in [('e1', 'K'), ('e8', 'k'), ('a1', 'R')]:
        fen = apply_position_edit(fen, {'to': square, 'piece': piece})
    fen = apply_position_edit(fen, {'from': 'a1', 'to': 'b5'})
    board = chess.Board(fen)
    assert board.is_valid()
    assert board.piece_at(chess.B5) == chess.Piece(chess.ROOK, chess.WHITE)
    assert board.piece_at(chess.A1) is None
    fen = apply_position_edit(fen, {'to': 'b5', 'piece': ''})
    assert chess.Board(fen).piece_at(chess.B5) is None
    for event in [{'to': 'z9', 'piece': 'Q'}, {'to': 'e4', 'piece': 'script'}, {'from': 'a1', 'to': 'a2'}]:
        with pytest.raises(ValueError):
            apply_position_edit(fen, event)


def test_home_orders_latest_eight_and_never_invents_accuracy():
    from recent_games import recent_eight, cards_data, game_id
    items = [{'pgn': f'[White "Demo"]\n[Black "Player{i}"]\n\n1. e4 e5 *',
              'white': {'username': 'demo'}, 'black': {'username': f'Player{i}'},
              'end_time': i, 'url': str(i)} for i in range(10)]
    items[-1]['accuracies'] = {'white': 96.4}
    items[-2]['accuracies'] = {'white': True}
    latest = recent_eight(items + [items[-1]])
    assert [g['end_time'] for g in latest] == list(range(9, 1, -1))
    cards = cards_data(items, 'Demo', {game_id(items[-2]): {'white': 87.5}})
    assert len(cards) == 8
    assert '96,4%' in cards[0]['accuracy'] and 'Chess.com' in cards[0]['accuracy']
    assert '87,5%' in cards[1]['accuracy'] and 'estimada' in cards[1]['accuracy']
    assert 'não publicada' in cards[2]['accuracy']
    assert all(card['empty'] for card in cards_data([], '', {}))


def test_reader_pagination_and_editor_do_not_change_main_game(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_USER_PREFERENCE', str(tmp_path/'user.json'))
    monkeypatch.setenv('ACERVO_APPEARANCE_PREFERENCE', str(tmp_path/'appearance.json'))
    monkeypatch.setenv('STOCKFISH_PATH', str(tmp_path/'absent'))
    for module in ('interactive_board', 'recent_games', 'study_workspace', 'study_entrance', 'profile_avatar',
                   'page_chrome', 'cat_mascot', 'tactics_forge', 'tactic_demo', 'pgn_clipboard'):
        sys.modules.pop(module, None)
    at = AppTest.from_file(str(ROOT/'app.py'))
    at.session_state.study_files = (('Manual.txt', b'Page one\fPage two\fPage three'),)
    at.session_state.main_view = 'Estudo com livros'
    at.run(timeout=25)
    assert not at.exception
    from streamlit.util import calc_hash
    at._page_hash = calc_hash('estudo')
    main_game = at.session_state.game
    next(b for b in at.button if b.label == 'Abrir livro').click().run(timeout=20)
    assert at.session_state.reader_page == 0
    at.button(key='reader_next').click().run(timeout=20)
    assert at.session_state.reader_page == 1
    next(b for b in at.button if b.label == 'Editar posição').click().run(timeout=20)
    next(b for b in at.button if b.label == 'Limpar tabuleiro').click().run(timeout=20)
    next(b for b in at.button if b.label == 'Concluir edição').click().run(timeout=20)
    assert at.session_state.book_editing is True
    assert at.error
    assert at.session_state.reader_page == 1
    next(b for b in at.button if b.label == 'Cancelar edição').click().run(timeout=20)
    assert at.session_state.game == main_game
    assert at.session_state.book_editing is False
    assert not at.exception
