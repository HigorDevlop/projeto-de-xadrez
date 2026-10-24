"""Tiny, local board transitions prepared before the player answers."""
from functools import lru_cache
import chess


@lru_cache(maxsize=128)
def answer_preview(fen,solution,progress):
    if not 0<=progress<len(solution): return None
    board=chess.Board(fen)
    for uci in solution[:progress]: board.push_uci(uci)
    source=board.fen()
    for uci in solution[progress:progress+2]: board.push_uci(uci)
    last=board.peek()
    return dict(sourceFen=source,expected=solution[progress],position=dict(fen=board.fen(),legal=[],
        last=[chess.square_name(last.from_square),chess.square_name(last.to_square)]))
