from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import chess
from PIL import Image
import pytest

from profile_photo import normalize_photo
from tactics import fetch_puzzle, fetch_puzzle_range, parse_puzzle, solve_move


def payload():
    return {'game': {'pgn': '1. f3 e5 2. g4 *'},
            'puzzle': {'id': 'test1', 'initialPly': 2, 'rating': 800,
                       'themes': ['mateIn1'], 'solution': ['d8h4']}}


def test_puzzle_setup_move_is_applied_and_solution_legal():
    puzzle = parse_puzzle(payload())
    board = chess.Board(puzzle.fen)
    assert board.turn == chess.BLACK
    assert board.piece_at(chess.G4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert solve_move(puzzle, 0, 'd8h4', puzzle.fen) == (1, 'Tático resolvido!')
    assert solve_move(puzzle, 0, 'b8c6', puzzle.fen)[0] == 0
    with pytest.raises(ValueError, match='posição mudou'):
        solve_move(puzzle, 0, 'd8h4', chess.STARTING_FEN)


def test_puzzle_replies_and_promotion():
    from tactics import Puzzle
    puzzle = Puzzle('promotion', '8/P3k3/8/8/8/8/8/4K3 w - - 0 1',
                    ('a7a8q', 'e7e6', 'a8e8'), 1000, ())
    progress, message = solve_move(puzzle, 0, 'a7a8q', puzzle.fen)
    assert progress == 2 and 'respondeu' in message
    board = chess.Board(puzzle.fen)
    for move in puzzle.solution[:progress]:
        board.push_uci(move)
    assert solve_move(puzzle, progress, 'a8e8', board.fen())[0] == 3


def test_rejects_bad_provider_solution_and_handles_rate_limit():
    data = payload()
    data['puzzle']['solution'] = ['e2e4']
    with pytest.raises(ValueError, match='inválido'):
        parse_puzzle(data)
    with patch('tactics.urlopen', side_effect=HTTPError('url', 429, '', {}, None)):
        with pytest.raises(ValueError, match='limitou'):
            fetch_puzzle()


def test_request_passes_theme_and_difficulty():
    import json
    with patch('tactics.urlopen', return_value=BytesIO(json.dumps(payload()).encode())) as request:
        assert fetch_puzzle('mateIn1', 'easier').id == 'test1'
    assert 'angle=mateIn1&difficulty=easier' in request.call_args.args[0].full_url


@pytest.mark.parametrize('mode,format', [('RGB', 'JPEG'), ('RGBA', 'PNG'), ('P', 'PNG'), ('RGB', 'WEBP')])
def test_normalizes_photo_formats(mode, format):
    data = BytesIO()
    Image.new(mode, (800, 400)).save(data, format=format)
    result = Image.open(BytesIO(normalize_photo(data.getvalue())))
    assert result.format == 'PNG' and result.size == (512, 256)


def test_invalid_photo_returns_readable_error():
    with pytest.raises(ValueError, match='Não foi possível'):
        normalize_photo(b'not an image')
    with pytest.raises(ValueError, match='10 MB'):
        normalize_photo(b'x' * (10 * 1024 * 1024 + 1))


def test_cropped_photo_is_square():
    data = BytesIO()
    Image.new('RGB', (800, 400), 'red').save(data, format='JPEG')
    result = Image.open(BytesIO(normalize_photo(data.getvalue(), square=True)))
    assert result.size == (320, 320) and result.format == 'PNG'


def test_range_search_is_bounded_and_never_returns_wrong_rating():
    puzzle = parse_puzzle(payload())
    with patch('tactics.fetch_puzzle', return_value=puzzle) as fetch:
        assert fetch_puzzle_range('mateIn1', 700, 900) == puzzle
        assert fetch.call_count == 1
    with patch('tactics.fetch_puzzle', return_value=puzzle) as fetch:
        with pytest.raises(ValueError, match='Nenhum tático'):
            fetch_puzzle_range('mateIn1', 1000, 1200)
        assert fetch.call_count == 3
    with patch('tactics.fetch_puzzle') as fetch:
        with pytest.raises(ValueError, match='faixa'):
            fetch_puzzle_range('mateIn1', 900, 700)
        fetch.assert_not_called()


def test_profile_rating_uses_most_recent_public_mode():
    from chesscom import fetch_rating
    with patch('chesscom.get_json', return_value={
        'chess_rapid': {'last': {'rating': 1400, 'date': 20}},
        'chess_blitz': {'last': {'rating': 1550, 'date': 30}},
        'chess_bullet': {'last': {'rating': 1700, 'date': 10}},
    }):
        assert fetch_rating('demo') == (1550, 'Blitz')
    with patch('chesscom.get_json', return_value={}):
        assert fetch_rating('demo') == (None, 'Sem rating publicado')
