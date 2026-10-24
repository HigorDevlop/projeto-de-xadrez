from io import StringIO
from types import SimpleNamespace
import chess
import chess.pgn
import analysis_editor
from game_play import play_move


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def test_repeated_branching_preserves_alternatives():
    pgn = str(chess.pgn.Game())
    for uci in ['e2e4', 'd2d4', 'c2c4', 'g1f3']:
        pgn, ply = play_move(pgn, 0, uci, chess.STARTING_FEN)
        assert ply == 1
        game = chess.pgn.read_game(StringIO(pgn))
        assert game.variations[0].move.uci() == uci
    assert len(game.variations) == 4
    board = game.end().board()
    pgn, ply = play_move(pgn, 1, 'd7d5', board.fen())
    assert ply == 2


def test_editor_rejects_invalid_then_saves_playable_position(monkeypatch):
    state = State(board_revision=0)
    monkeypatch.setattr(analysis_editor, 'st', SimpleNamespace(session_state=state))
    saved = []
    analysis_editor.begin(chess.Board())
    analysis_editor.reset(empty=True)
    analysis_editor.save(saved.append)
    assert not saved and state.analysis_editing and state.analysis_edit_error
    state.analysis_draft = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'
    state.analysis_edit_castling = []
    analysis_editor.save(saved.append)
    assert not state.analysis_editing and len(saved) == 1
    pgn, ply = play_move(str(saved[0]), 0, 'e2e4', saved[0].board().fen())
    assert ply == 1
    assert chess.pgn.read_game(StringIO(pgn)).end().board().piece_at(chess.E4) == chess.Piece(chess.PAWN, True)


def test_editor_cancel_keeps_original_game(monkeypatch):
    state = State(board_revision=0, game=str(chess.pgn.Game()))
    monkeypatch.setattr(analysis_editor, 'st', SimpleNamespace(session_state=state))
    original = state.game
    analysis_editor.begin(chess.Board())
    analysis_editor.reset(empty=True)
    analysis_editor.cancel()
    assert state.game == original and not state.analysis_editing


def test_kings_can_be_repositioned_freely_and_roque_is_updated(monkeypatch):
    state = State(board_revision=0)
    monkeypatch.setattr(analysis_editor, 'st', SimpleNamespace(session_state=state))
    analysis_editor.begin(chess.Board())
    for source, target in [('e1', 'd4'), ('e8', 'd5'), ('d4', 'c3'), ('d5', 'f6')]:
        analysis_editor.changed({'from': source, 'to': target,
                                 'revision': state.board_revision, 'fen': state.analysis_draft})
        assert not state.get('analysis_edit_error')
        assert chess.Board(state.analysis_draft).piece_at(chess.parse_square(target)).piece_type == chess.KING
    assert state.analysis_edit_castling == []
    saved = []
    analysis_editor.save(saved.append)
    assert len(saved) == 1 and not state.analysis_editing
