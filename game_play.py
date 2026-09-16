"""Legal board edits, shared by mouse, keyboard and tests."""
from io import StringIO

import chess
import chess.pgn


def play_move(pgn: str, ply: int, uci: str, expected_fen: str) -> tuple[str, int]:
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None:
        raise ValueError("Partida inválida.")
    node = game
    for _ in range(ply):
        if not node.variations:
            raise ValueError("Posição fora da partida.")
        node = node.variations[0]
    board = node.board()
    if board.fen() != expected_fen:
        raise ValueError("A posição mudou. Tente o lance novamente.")
    move = chess.Move.from_uci(uci)
    if board.is_game_over() or move not in board.legal_moves:
        raise ValueError("Lance ilegal nesta posição.")
    # Follow an existing mainline without discarding its result or annotations.
    if node.variations and node.variations[0].move == move:
        return pgn, ply + 1
    # Keep the original continuation as a PGN variation for export/recovery.
    node.add_main_variation(move)
    board.push(move)
    game.headers["Result"] = board.result()
    return str(game), ply + 1
