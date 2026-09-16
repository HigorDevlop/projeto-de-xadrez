from io import BytesIO, StringIO
import json
import sys
from pathlib import Path
from unittest.mock import patch

import chess
import chess.pgn
import pytest
from streamlit.testing.v1 import AppTest

from chess_review import BookIndex, analyse_game, classify, export_review, find_engine, read_games, player_accuracy
from chesscom import fetch_archives, fetch_games, fetch_recent_games, get_json, normalize_username
from game_play import play_move
from tutor import (Passage, analyse_position, explain_with_ai, load_passages,
                   position_facts, retrieve, tutor_mood, basic_lesson, single_paragraph)

ROOT = Path(__file__).resolve().parents[1]


def parse(pgn):
    return chess.pgn.read_game(StringIO(pgn))


def test_moves_preserve_mainline_and_branch():
    pgn = '1. e4 e5 2. Nf3 Nc6 *'
    unchanged, ply = play_move(pgn, 0, 'e2e4', chess.Board().fen())
    assert unchanged == pgn and ply == 1
    changed, ply = play_move(pgn, 0, 'd2d4', chess.Board().fen())
    game = parse(changed)
    assert list(game.mainline_moves()) == [chess.Move.from_uci('d2d4')]
    assert game.variations[1].move.uci() == 'e2e4'
    assert len(list(game.variations[1].mainline_moves())) == 3


@pytest.mark.parametrize('uci,fen', [('e2e5', chess.STARTING_FEN), ('e7e5', chess.STARTING_FEN),
                                    ('e2e4', 'stale position')])
def test_invalid_or_stale_move_rejected(uci, fen):
    with pytest.raises(ValueError):
        play_move(str(chess.pgn.Game()), 0, uci, fen)


@pytest.mark.parametrize('fen,uci,expected_square,expected_piece', [
    ('4k3/8/8/8/8/8/8/4K2R w K - 0 1', 'e1g1', chess.F1, chess.ROOK),
    ('4k3/P7/8/8/8/8/8/4K3 w - - 0 1', 'a7a8n', chess.A8, chess.KNIGHT),
    ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2', 'e5d6', chess.D6, chess.PAWN),
])
def test_special_moves(fen, uci, expected_square, expected_piece):
    game = chess.pgn.Game()
    game.setup(chess.Board(fen))
    pgn, ply = play_move(str(game), 0, uci, fen)
    result = parse(pgn).end().board()
    assert ply == 1
    assert result.piece_type_at(expected_square) == expected_piece
    if uci == 'e5d6':
        assert result.piece_at(chess.D5) is None


def test_book_comments_and_retrieval():
    pgn = b'1. e4 {Control the center with a pawn.} e5 *'
    passages, errors = load_passages((('lesson.pgn', pgn),))
    board = chess.Board()
    board.push_san('e4')
    assert not errors
    assert retrieve(passages, board)[0].source.startswith('lesson.pgn')
    assert retrieve(passages, chess.Board()) == []
    assert load_passages((('empty.txt', b''),))[1]


def test_pdf_extracts_page_references():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(400, 400)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    content = DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 40 300 Td (Control the center and develop your pieces before attacking.) Tj ET')
    page[NameObject('/Contents')] = content
    data = BytesIO()
    writer.write(data)
    passages, errors = load_passages((('book.pdf', data.getvalue()),))
    assert not errors and passages[0].source == 'book.pdf, p. 1'
    assert 'center' in passages[0].text


def test_archives_validate_urls_and_games_filter_variants():
    with patch('chesscom.get_json', return_value={'archives': [
        'https://api.chess.com/pub/player/demo/games/2026/08',
        'https://api.chess.com/pub/player/demo/games/2026/09', 'https://other.invalid/2026/10']}):
        assert fetch_archives(' Demo ') == ['2026/09', '2026/08']
    with patch('chesscom.get_json', return_value={'games': [
        {'rules': 'chess960', 'pgn': 'x', 'end_time': 4},
        {'rules': 'chess', 'pgn': '1. e4 *', 'end_time': 2},
        {'rules': 'chess', 'pgn': '1. d4 *', 'end_time': 3}]}):
        assert [g['end_time'] for g in fetch_games('demo', '2026/09')] == [3, 2]
    with pytest.raises(ValueError):
        normalize_username('../other')


def test_api_errors_are_readable():
    from urllib.error import HTTPError
    with patch('chesscom.urlopen', side_effect=HTTPError('url', 429, 'rate limited', {}, None)):
        with pytest.raises(ValueError, match='limitou'):
            get_json('https://api.chess.com/pub/player/demo')


def test_recent_history_automatically_fills_from_older_months():
    recent = {'pgn': '1. e4 *', 'end_time': 3, 'url': 'game1'}
    old = {'pgn': '1. d4 *', 'end_time': 2, 'url': 'game2'}
    with patch('chesscom.fetch_archives', return_value=['2026/09', '2026/08', '2026/07']), \
         patch('chesscom.fetch_games', side_effect=[[recent], [recent, old]]) as fetch:
        assert fetch_recent_games('demo', limit=2) == [recent, old]
        assert fetch.call_count == 2


def test_explanation_changes_with_the_move_and_has_one_paragraph():
    board=chess.Board()
    board.push_san('e4')
    pawn_text=basic_lesson(board)
    assert 'e4' in pawn_text and 'peão' in pawn_text and 'linhas' in pawn_text
    board.push_san('e5')
    board.push_san('Nf3')
    knight_text=basic_lesson(board)
    assert 'Nf3' in knight_text and 'cavalo' in knight_text and 'e5' in knight_text
    assert knight_text != pawn_text
    assert '\n' not in pawn_text + knight_text
    assert '**' not in pawn_text + knight_text
    assert single_paragraph('### Plano\n\n**Jogue** com atenção.\n- Confira a defesa.') == 'Plano Jogue com atenção. Confira a defesa.'


def test_mate_explanation_does_not_advise_future_moves():
    board=chess.Board()
    for san in ['f3', 'e5', 'g4', 'Qh4#']:
        board.push_san(san)
    text=basic_lesson(board)
    assert 'xeque-mate' in text and 'não existe resposta legal' in text
    assert 'Para melhorar' not in text


@pytest.mark.parametrize('loss,category', [(0, 'excellent'), (0.0199, 'excellent'),
    (0.02, 'good'), (0.0499, 'good'), (0.05, 'inaccuracy'), (0.0999, 'inaccuracy'),
    (0.10, 'mistake'), (0.1999, 'mistake'), (0.20, 'blunder'), (0.50, 'blunder')])
def test_public_expected_points_bands(loss, category):
    assert classify(in_book=False, is_best=False, sacrifice=False,
                    best_expected=0.75, played_expected=0.75-loss) == category


def test_book_priority_and_automatic_opening_catalog():
    assert classify(in_book=True, is_best=True, sacrifice=True,
                    best_expected=1.0, played_expected=0.0) == 'book'
    index=BookIndex()
    index.add_opening_catalog(ROOT / 'data/openings')
    board=chess.Board()
    for san in ['e4', 'c5', 'Nf3', 'd6']:
        move=board.parse_san(san)
        assert index.sources(board,move)
        board.push(move)
    assert not index.sources(board, chess.Move.from_uci('a1a8'))


def test_tutor_expressions():
    assert tutor_mood('book')[0] == 'serio'
    assert tutor_mood('best', thinking=True)[0] == 'pensativo'
    assert tutor_mood('mistake')[0] == 'raiva'
    assert tutor_mood('blunder', thinking=True)[0] == 'raiva'


def test_ai_receives_real_context_and_book_sources():
    response = BytesIO(json.dumps({'message': {'content': 'Controle o centro [1].'}}).encode())
    with patch('tutor.urlopen', return_value=response) as request:
        answer = explain_with_ai('test-model', chess.Board(), None, None,
                                 [Passage('book.txt', 'Controle o centro.')], 'Qual plano?')
    payload = json.loads(request.call_args.args[0].data)
    assert payload['stream'] is False
    context = json.loads(payload['messages'][1]['content'])
    assert context['fen'] == chess.STARTING_FEN
    assert context['livros'][0]['referencia'] == '[1] book.txt'
    assert answer == 'Controle o centro [1].'


@pytest.mark.skipif(not find_engine(), reason='Stockfish unavailable')
def test_engine_line_and_sparse_review_export():
    snapshot = analyse_position(chess.STARTING_FEN, find_engine(), 10, 0.1)
    line_game = read_games(snapshot['line'])[0]
    assert 1 <= len(list(line_game.mainline_moves())) <= 6
    game = read_games('1. e4 e5 2. Nf3 *')[0]
    reviews = analyse_game(game, find_engine(), BookIndex(), 8, 0.05)
    assert 0 <= player_accuracy(reviews, 'Brancas') <= 100
    assert player_accuracy([], 'Brancas') is None
    exported = parse(export_review(game, [reviews[2]]))
    nodes = list(exported.mainline())
    assert nodes[0].eval() is None and nodes[1].eval() is None
    assert nodes[2].eval() is not None


def click(at, label):
    next(b for b in at.button if b.label == label).click().run(timeout=20)
    assert not at.exception


def test_ui_free_play_and_navigation():
    at = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=20)
    assert not at.exception
    assert not any(s.value == 'Leitura do lance' for s in at.subheader)
    click(at, 'Nova partida · jogar livremente')
    at.toggle[0].set_value(False).run()
    next(s for s in at.selectbox if s.label == 'Lance legal (SAN)').set_value('e2e4').run()
    click(at, 'Jogar lance')
    assert at.session_state.ply == 1
    assert list(parse(at.session_state.game).mainline_moves())[0].uci() == 'e2e4'
    at.slider(key='position_slider').set_value(0).run()
    assert at.session_state.ply == 0 and not at.exception
    click(at, 'Final')
    assert at.session_state.ply == 1
    if find_engine():
        click(at, 'Analisar partida')
        assert 1 in at.session_state.reviews
        click(at, 'Reexplicar lance')
        assert at.session_state.snapshot[1]['line']
    click(at, 'Nova partida · jogar livremente')
    assert at.session_state.ply == 0
    assert len(at.dataframe) == 1
    assert list(at.dataframe[0].value.columns) == ['Classificação', 'Brancas', 'Pretas']
    assert len(at.metric) == 2
    assert all(metric.value == '—' for metric in at.metric)
    assert not any(s.value == 'Resumo do lance' for s in at.subheader)
    previous_game=at.session_state.game
    at.session_state.workspace_tab='Estudo com livros'
    at.run(timeout=20)
    assert not at.exception
    assert not at.dataframe
    assert any(h.value == 'Carregar livro' for h in at.subheader)
    assert at.session_state.game == previous_game


def test_ui_history_import():
    # AppTest creates a new runtime registry; reload the inline component for it.
    sys.modules.pop('interactive_board', None)
    game = {'rules': 'chess', 'pgn': '[White "Demo"]\n[Black "Test"]\n\n1. d4 d5 *',
            'white': {'username': 'Demo'}, 'black': {'username': 'Test'}, 'end_time': 1,
            'accuracies': {'white': 98.2, 'black': 91.3}}
    with patch('chesscom.fetch_archives', new=lambda user: ['2026/09']), patch('chesscom.fetch_games', new=lambda user, month: [game]):
        at = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=20)
        next(t for t in at.text_input if t.label == 'Usuário do Chess.com').set_value('demo')
        click(at, 'Buscar histórico')
        assert not any(s.label == 'Mês das partidas' for s in at.selectbox)
        assert not any(b.label == 'Abrir no tabuleiro para analisar' for b in at.button)
        at.selectbox(key='history_choice').set_value(0).run(timeout=20)
        assert not at.exception
        assert parse(at.session_state.game).headers['White'] == 'Demo'
        assert at.session_state.ply == 0
        assert [m.value for m in at.metric] == ['98.2%', '91.3%']
        # An alternative invalidates the imported game's accuracy.
        next(s for s in at.selectbox if s.label == 'Lance legal (SAN)').set_value('e2e4').run()
        click(at, 'Jogar lance')
        assert not at.session_state.official_accuracies
