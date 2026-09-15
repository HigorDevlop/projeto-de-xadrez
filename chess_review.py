"""Leitura de partidas, acervo e classificação independente da interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
import os
import shutil
import struct
from typing import Callable

import chess
import chess.engine
import chess.pgn
import chess.polyglot


@dataclass(frozen=True)
class Category:
    label: str
    english: str
    color: str
    ink: str
    symbol: str
    description: str


CATEGORIES = {
    "book": Category("Lance de Livro", "Book", "#722F37", "#FFFFFF", "L",
                     "Jogada catalogada no acervo carregado."),
    "brilliant": Category("Genial", "Brilliant", "#FFFFFF", "#15151D", "!!!",
                          "Sacrifício correto que mantém ou amplia vantagem decisiva."),
    "best": Category("Excelente", "Best", "#8B5CF6", "#FFFFFF", "★",
                     "Melhor lance sugerido pela engine."),
    "great": Category("Ótimo", "Great", "#1E40AF", "#FFFFFF", "!",
                      "Precisão equivalente à linha principal."),
    "good": Category("Bom", "Good", "#7DD3FC", "#102A43", "✓",
                     "Mantém o equilíbrio ou a vantagem sem grandes concessões."),
    "mistake": Category("Ruim", "Mistake", "#FACC15", "#332A00", "?",
                        "Perda relevante de centipeões ou concessão posicional."),
    "blunder": Category("Péssimo", "Blunder", "#DC2626", "#FFFFFF", "??",
                        "Perda tática grave ou revés decisivo na avaliação."),
}


@dataclass(frozen=True)
class Thresholds:
    great: int = 20
    mistake: int = 80
    blunder: int = 200
    decisive: int = 300

    def __post_init__(self):
        if not 0 <= self.great < self.mistake < self.blunder:
            raise ValueError("Os limites devem seguir: Ótimo < Ruim < Péssimo.")
        if self.decisive <= 0:
            raise ValueError("A vantagem decisiva deve ser positiva.")


def classify(*, in_book: bool, is_best: bool, sacrifice: bool,
             best_cp: int, played_cp: int, best_mate: int | None = None,
             played_mate: int | None = None, thresholds: Thresholds = Thresholds()) -> str:
    """Pontuações sempre do ponto de vista de quem jogou; 100 cp = 1 peão."""
    loss = max(0, best_cp - played_cp)
    if in_book:
        return "book"
    if (sacrifice and played_cp >= thresholds.decisive
            and loss <= thresholds.great and (played_mate is None or played_mate > 0)):
        return "brilliant"
    if is_best:
        return "best"
    enters_mate = played_mate is not None and played_mate <= 0 and (best_mate is None or best_mate > 0)
    reversal = best_cp >= 150 and played_cp <= -150
    if loss >= thresholds.blunder or enters_mate or reversal:
        return "blunder"
    if loss >= thresholds.mistake:
        return "mistake"
    if loss <= thresholds.great:
        return "great"
    return "good"


def decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def read_games(text: str) -> list[chess.pgn.Game]:
    stream = StringIO(text.lstrip("\ufeff"))
    games = []
    while (game := chess.pgn.read_game(stream)) is not None:
        if game.errors:
            raise ValueError(f"PGN inválido: {game.errors[0]}")
        if game.headers.get("Variant", "Standard") not in ("Standard", "Chess", "Normal"):
            raise ValueError("Esta versão aceita apenas xadrez clássico.")
        if not game.board().is_valid():
            raise ValueError("A posição inicial do PGN é inválida.")
        pending = [(game, game.board())]
        count = 0
        while pending:
            node, board = pending.pop()
            for child in node.variations:
                if child.move not in board.legal_moves:
                    raise ValueError("O PGN contém um lance ilegal ou nulo.")
                next_board = board.copy()
                next_board.push(child.move)
                pending.append((child, next_board))
                count += 1
                if count > 20000:
                    raise ValueError("Limite de 20.000 lances por partida excedido.")
        if game.variations:
            games.append(game)
        if len(games) > 2000:
            raise ValueError("Carregue até 2.000 partidas por arquivo.")
    if not games:
        raise ValueError("Nenhuma partida com lances encontrada no PGN.")
    return games


def position_key(board: chess.Board) -> str:
    return " ".join(board.fen(en_passant="legal").split()[:4])


@dataclass
class BookIndex:
    positions: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    polyglot: dict[tuple[int, int], set[str]] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.positions) + len(self.polyglot)

    def add_pgn(self, text: str, source: str, max_plies: int = 40) -> None:
        games = read_games(text)  # Validate the whole file before mutating the index.
        for game in games:
            pending = [(game, game.board(), 0)]
            while pending:
                node, board, ply = pending.pop()
                if ply >= max_plies:
                    continue
                for child in node.variations:
                    self.positions.setdefault((position_key(board), child.move.uci()), set()).add(source)
                    after = board.copy()
                    after.push(child.move)
                    pending.append((child, after, ply + 1))

    def add_polyglot(self, data: bytes, source: str) -> None:
        if not data or len(data) % 16:
            raise ValueError("Livro Polyglot inválido: registros devem ter 16 bytes.")
        for key, raw_move, weight, _ in struct.iter_unpack(">QHHI", data):
            if weight:
                self.polyglot.setdefault((key, raw_move), set()).add(source)

    def sources(self, board: chess.Board, move: chess.Move) -> list[str]:
        if move not in board.legal_moves:
            return []
        target = move.to_square
        if board.is_castling(move):
            target = chess.square(7 if board.is_kingside_castling(move) else 0,
                                  chess.square_rank(move.from_square))
        raw = target | (move.from_square << 6) | (((move.promotion or 1) - 1) << 12)
        sources = self.positions.get((position_key(board), move.uci()), set())
        binary_sources = self.polyglot.get((chess.polyglot.zobrist_hash(board), raw), set())
        return sorted(sources | binary_sources)


def find_engine() -> str:
    configured = os.environ.get("STOCKFISH_PATH")
    if configured and Path(configured).is_file():
        return configured
    located = shutil.which("stockfish")
    if located:
        return located
    root = Path(__file__).resolve().parent
    for folder in (root / "engines", root.parent.parent / "stockfish-windows-x86-64-avx2"):
        if folder.is_dir():
            for candidate in folder.rglob("stockfish*.exe"):
                return str(candidate)
    return ""


VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
          chess.ROOK: 500, chess.QUEEN: 900}


def material(board: chess.Board, color: chess.Color) -> int:
    return sum(value * (len(board.pieces(piece, color)) - len(board.pieces(piece, not color)))
               for piece, value in VALUES.items())


def sacrifice_in_line(board: chess.Board, pv: list[chess.Move]) -> bool:
    """Conservative heuristic: deficit persists across two opportunities to recapture.

    Mate with a retained deficit also qualifies. Balanced exchanges and a piece
    merely hanging without an accepted sacrifice do not qualify.
    """
    if board.legal_moves.count() <= 1 or len(pv) < 3:
        return False
    color = board.turn
    baseline = material(board, color)
    probe = board.copy()
    sustained = 0
    for ply, move in enumerate(pv[:12]):
        if move not in probe.legal_moves:
            return False
        probe.push(move)
        if ply >= 2 and probe.turn != color:
            deficit = baseline - material(probe, color)
            sustained = sustained + 1 if deficit >= 100 else 0
            if sustained >= 2 or (deficit >= 100 and probe.is_checkmate()):
                return True
    return False


@dataclass
class MoveReview:
    ply: int
    number: str
    side: str
    san: str
    uci: str
    category: str
    loss: int
    white_cp: int
    white_mate: int | None
    best_san: str
    line: str
    sources: list[str]
    explanation: str


def analyse_game(game: chess.pgn.Game, engine_path: str, book: BookIndex | None = None,
                 depth: int = 16, seconds: float = 0.3,
                 thresholds: Thresholds = Thresholds(),
                 progress: Callable[[int, int], None] | None = None) -> list[MoveReview]:
    if not Path(engine_path).is_file():
        raise ValueError("Selecione um executável Stockfish válido.")
    book = book or BookIndex()
    board = game.board()
    moves = list(game.mainline_moves())
    reviews = []
    with chess.engine.SimpleEngine.popen_uci(engine_path, timeout=30) as engine:
        engine.configure({"Threads": 1, "Hash": 128})
        limit = chess.engine.Limit(depth=depth, time=seconds)
        for index, move in enumerate(moves, 1):
            if board.is_game_over():
                raise ValueError("O PGN contém lances após o fim da partida.")
            color = board.turn
            best = engine.analyse(board, limit)
            best_move = best["pv"][0]
            played = best if best_move == move else engine.analyse(board, limit, root_moves=[move])
            best_score = best["score"].pov(color)
            played_score = played["score"].pov(color)
            best_cp = best_score.score(mate_score=100000)
            played_cp = played_score.score(mate_score=100000)
            sources = book.sources(board, move)
            pv = played.get("pv", [move])
            sacrifice = sacrifice_in_line(board, pv)
            category = classify(in_book=bool(sources), is_best=best_move == move,
                                sacrifice=sacrifice, best_cp=best_cp, played_cp=played_cp,
                                best_mate=best_score.mate(), played_mate=played_score.mate(),
                                thresholds=thresholds)
            loss = max(0, best_cp - played_cp)
            explanation = CATEGORIES[category].description
            if sources:
                explanation += " Fonte: " + ", ".join(sources) + "."
            elif category == "brilliant":
                explanation += " Déficit material detectado na continuação da engine (heurística)."
            else:
                explanation += f" Perda estimada: {loss} cp; melhor alternativa: {board.san(best_move)}."
            white_score = played["score"].white()
            reviews.append(MoveReview(
                index, f"{board.fullmove_number}{'.' if color else '...'}",
                "Brancas" if color else "Pretas", board.san(move), move.uci(), category, loss,
                white_score.score(mate_score=100000), white_score.mate(), board.san(best_move),
                board.variation_san(pv[:10]), sources, explanation))
            board.push(move)
            if progress:
                progress(index, len(moves))
    return reviews


def export_review(game: chess.pgn.Game, reviews: list[MoveReview]) -> str:
    copy = chess.pgn.read_game(StringIO(str(game)))
    for node, review in zip(copy.mainline(), reviews):
        category = CATEGORIES[review.category]
        # Preserve existing user comments and annotations.
        annotation = f"{category.label} {category.symbol}. {review.explanation}"
        node.comment = (node.comment + " " + annotation).strip()
        score = (chess.engine.Mate(review.white_mate) if review.white_mate is not None
                 else chess.engine.Cp(review.white_cp))
        node.set_eval(chess.engine.PovScore(score, chess.WHITE))
    return copy.accept(chess.pgn.StringExporter(headers=True, variations=True, comments=True))
