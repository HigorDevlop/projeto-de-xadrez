"""Leitura de partidas, acervo e classificação independente da interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
import struct
import csv
import math

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
    "book": Category("Livro", "Book", "#9B7955", "#FFFFFF", "📖",
                     "Jogada catalogada no acervo carregado."),
    "brilliant": Category("Brilhante", "Brilliant", "#26BDB0", "#102A43", "!!",
                          "Sacrifício produtivo de peça, com tolerância ajustada ao rating."),
    "best": Category("Melhor", "Best", "#8B5CF6", "#FFFFFF", "★",
                     "Melhor lance sugerido pela engine."),
    "great": Category("Grande Lance", "Great", "#1E40AF", "#FFFFFF", "!",
                      "Única continuação boa identificada na busca (estimativa local)."),
    "excellent": Category("Excelente", "Excellent", "#80A765", "#102A43", "✓✓",
                          "Preserva quase todos os pontos esperados da posição."),
    "good": Category("Bom", "Good", "#7DD3FC", "#102A43", "✓",
                     "Mantém o equilíbrio ou a vantagem sem grandes concessões."),
    "inaccuracy": Category("Imprecisão", "Inaccuracy", "#FACC15", "#332A00", "?!",
                           "Reduz um pouco as chances de um bom resultado."),
    "mistake": Category("Erro", "Mistake", "#F29A38", "#332A00", "?",
                        "Reduz de forma relevante as chances de um bom resultado."),
    "miss": Category("Oportunidade perdida", "Miss", "#D68C66", "#332A00", "×",
                     "Deixa escapar uma oportunidade após um erro adversário (estimativa local)."),
    "blunder": Category("Capivorada", "Blunder", "#DC2626", "#FFFFFF", "??",
                        "Perda tática grave ou revés decisivo na avaliação."),
}


@dataclass(frozen=True)
class Thresholds:
    excellent: float = 0.02
    good: float = 0.05
    inaccuracy: float = 0.10
    mistake: float = 0.20

    def __post_init__(self):
        if not 0 < self.excellent < self.good < self.inaccuracy < self.mistake <= 1:
            raise ValueError("Limites inválidos de perda de pontos esperados.")


def classify(*, in_book: bool, is_best: bool, sacrifice: bool,
             best_expected: float, played_expected: float,
             second_expected: float | None = None, missed_opportunity: bool = False,
             thresholds: Thresholds = Thresholds(), rating: int = 1500) -> str:
    """Expected-points bands; special categories are documented approximations.

    5% starts inaccuracy, 10% starts mistake; blunder is strictly above 20%.
    Rating adjusts only the tolerance for a verified productive piece sacrifice.
    """
    for value in (best_expected, played_expected, second_expected):
        if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError("Pontos esperados devem estar entre 0 e 1.")
    loss = round(max(0, best_expected - played_expected), 8)
    tolerance = max(0.005, min(0.02, 0.02 - (rating - 800) / 120000))
    if (sacrifice and played_expected >= 0.5 and loss <= tolerance
            and second_expected is not None and second_expected < 0.95):
        return "brilliant"
    if (loss == 0 and second_expected is not None and best_expected >= 0.5
            and best_expected - second_expected >= 0.1):
        return "great"
    if loss == 0:
        return "best"
    if loss < thresholds.excellent:
        return "excellent"
    if loss < thresholds.good:
        return "good"
    if loss < thresholds.inaccuracy:
        return "inaccuracy"
    if loss <= thresholds.mistake:
        return "mistake"
    return "blunder"


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

    def add_opening_catalog(self, folder: Path) -> None:
        for path in sorted(folder.glob("*.tsv")):
            with path.open(encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream, delimiter="\t"):
                    self.add_pgn(row["pgn"], f"ECO {row['eco']} · {row['name']}", max_plies=160)

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
    original_pieces = sum(len(board.pieces(kind, color)) for kind in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))
    probe = board.copy()
    sustained = 0
    for ply, move in enumerate(pv[:12]):
        if move not in probe.legal_moves:
            return False
        probe.push(move)
        if ply >= 2 and probe.turn != color:
            deficit = baseline - material(probe, color)
            pieces = sum(len(probe.pieces(kind, color)) for kind in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))
            piece_sacrificed = deficit >= 300 and pieces < original_pieces
            sustained = sustained + 1 if piece_sacrificed else 0
            if sustained >= 2 or (piece_sacrificed and probe.is_checkmate()):
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
    white_cp: int | None
    white_mate: int | None
    best_san: str
    line: str
    sources: list[str]
    explanation: str
    expected_loss: float = 0.0
    best_expected: float | None = None
    played_expected: float | None = None


def player_accuracy(reviews: list[MoveReview], side: str) -> float | None:
    """Mean of an exponential accuracy estimate using expected-point losses.

    This is not Chess.com's CAPS2 or Lichess's weighted game accuracy.
    """
    scores = []
    for review in reviews:
        if review.side != side:
            continue
        delta = max(0, review.expected_loss) * 100
        score = 100.0 if delta == 0 else max(0, min(100, 103.1668 * math.exp(-0.04354 * delta) - 3.1669))
        scores.append(score)
    return round(sum(scores) / len(scores), 1) if scores else None


def export_review(game: chess.pgn.Game, reviews: list[MoveReview]) -> str:
    copy = chess.pgn.read_game(StringIO(str(game)))
    by_ply = {review.ply: review for review in reviews}
    for ply, node in enumerate(copy.mainline(), 1):
        review = by_ply.get(ply)
        if review is None:
            continue
        category = CATEGORIES[review.category]
        # Preserve existing user comments and annotations.
        annotation = f"{category.label} {category.symbol}. {review.explanation}"
        node.comment = (node.comment + " " + annotation).strip()
        if review.white_cp is not None or review.white_mate is not None:
            score = (chess.engine.Mate(review.white_mate) if review.white_mate is not None
                     else chess.engine.Cp(review.white_cp))
            node.set_eval(chess.engine.PovScore(score, chess.WHITE))
    return copy.accept(chess.pgn.StringExporter(headers=True, variations=True, comments=True))
