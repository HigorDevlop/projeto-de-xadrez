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
    "brilliant": Category("Brilhante", "Brilliant", "#00CDB5", "#071A20", "!!",
                          "Sacrifício de peça ligado ao lance jogado, confirmado pelo motor, sem perda relevante de chances e sem vitória já garantida pelas alternativas."),
    "best": Category("Melhor", "Best", "#713BD6", "#FFFFFF", "★",
                     "Primeira escolha do motor selecionado, sem perda no indicador de chances."),
    "excellent": Category("Excelente", "Excellent", "#166534", "#FFFFFF", "✓",
                          "Alternativa com perda inferior a 2 pontos percentuais, inclusive empates na avaliação."),
    "good": Category("Bom", "Good", "#B7E355", "#16220B", "•",
                     "Perda de 2 até menos de 5 pontos percentuais."),
    "inaccuracy": Category("Imprecisão", "Inaccuracy", "#FACC15", "#2A2200", "?!",
                           "Perda de 5 até menos de 10 pontos percentuais."),
    "mistake": Category("Erro", "Mistake", "#F97316", "#281201", "?",
                        "Perda de 10 a 20 pontos percentuais, inclusive."),
    "blunder": Category("Capivorada", "Blunder", "#C81E3A", "#FFFFFF", "??",
                        "Perda superior a 20 pontos percentuais."),
}

SPECIAL_CATEGORIES = frozenset({'brilliant'})


def canonical_category(key):
    """Read older analyses using the single current special-move category."""
    return 'brilliant' if key == 'great' else key


def canonical_explanation(text):
    return text.replace('classificado como GENIAL', 'classificado como Brilhante').replace(
        'classificado como Grande Lance', 'classificado como Brilhante')


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
    """Chance-loss bands; brilliance is a conservative application heuristic.

    5% starts inaccuracy, 10% starts mistake; blunder is strictly above 20%.
    Rating does not relax the quality required for a special classification.
    """
    for value in (best_expected, played_expected, second_expected):
        if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError("Pontos esperados devem estar entre 0 e 1.")
    loss = round(max(0, best_expected - played_expected), 8)
    if (sacrifice and not in_book and played_expected >= 0.5 and loss <= 0.005
            and second_expected is not None and second_expected < 0.95):
        return "brilliant"
    if is_best and loss == 0:
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
            raise ValueError("PGN inválido: a sequência contém um lance ilegal ou uma notação não reconhecida.")
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
    """The played piece is captured on the reply and its deficit persists.

    Mate with a retained deficit also qualifies. Balanced exchanges and a piece
    merely hanging without an accepted sacrifice do not qualify.
    """
    if board.legal_moves.count() <= 1 or len(pv) < 3:
        return False
    first = pv[0]
    piece = board.piece_at(first.from_square)
    if first not in board.legal_moves or not piece or piece.piece_type not in VALUES or piece.piece_type == chess.PAWN:
        return False
    color = board.turn
    baseline = material(board, color)
    original_pieces = sum(len(board.pieces(kind, color)) for kind in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))
    probe = board.copy()
    probe.push(first)
    reply = pv[1]
    if (reply not in probe.legal_moves or reply.to_square != first.to_square
            or not probe.is_capture(reply)):
        return False
    probe.push(reply)
    # Includes exchange sacrifices and a minor piece given for a pawn.
    if baseline - material(probe, color) < 150:
        return False
    sustained = 0
    for ply, move in enumerate(pv[2:7], 2):
        if move not in probe.legal_moves:
            return False
        probe.push(move)
        if ply >= 2 and probe.turn != color:
            deficit = baseline - material(probe, color)
            pieces = sum(len(probe.pieces(kind, color)) for kind in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))
            piece_sacrificed = deficit >= 150 and pieces < original_pieces
            if not piece_sacrificed:
                return False
            sustained += 1
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
    engine_name: str = 'Stockfish'
    accuracy_before: float | None = None
    accuracy_after: float | None = None
    best_line: str = ''
    position_fen: str = ''


def player_accuracy(reviews: list[MoveReview], side: str) -> float | None:
    """Local estimate: combine volatility-weighted and harmonic move accuracy.

    Uses the aggregation approach documented at lichess.org/page/accuracy,
    with our paired root evaluations. It is not an official website score.
    """
    from analysis_accuracy import game_accuracy
    current = game_accuracy(reviews, side)
    if current is not None:
        return current
    from statistics import pstdev
    ordered=sorted(reviews,key=lambda review:review.ply)
    window=max(2,min(8,len(ordered)//10))
    chances=[]
    for review in ordered:
        if review.played_expected is not None:
            value=review.played_expected if review.side=='Brancas' else 1-review.played_expected
        elif review.white_mate is not None:
            value=float(review.white_mate>0)
        elif review.white_cp is not None:
            value=1/(1+math.exp(-.00368208*max(-1000,min(1000,review.white_cp))))
        else:value=.5
        chances.append(value*100)
    scores=[]
    for index,review in enumerate(ordered):
        if review.side!=side:continue
        delta=max(0,review.expected_loss)*100
        score=100.0 if delta==0 else max(0,min(100,103.1668*math.exp(-.04354*delta)-3.1669))
        start=max(0,min(index-window+1,len(chances)-window))
        weight=max(.5,min(12,pstdev(chances[start:start+window])))
        scores.append((score,weight))
    if not scores:return None
    weighted=sum(score*weight for score,weight in scores)/sum(weight for _,weight in scores)
    harmonic=0 if any(score==0 for score,_ in scores) else len(scores)/sum(1/score for score,_ in scores)
    return round((weighted+harmonic)/2,1)


def export_review(game: chess.pgn.Game, reviews: list[MoveReview]) -> str:
    copy = chess.pgn.read_game(StringIO(str(game)))
    by_ply = {review.ply: review for review in reviews}
    for ply, node in enumerate(copy.mainline(), 1):
        review = by_ply.get(ply)
        if review is None:
            continue
        from move_evidence import matches
        if not matches(node.board(), review):
            continue
        category = CATEGORIES[canonical_category(review.category)]
        # Preserve existing user comments and annotations.
        annotation = f"{category.label} {category.symbol}. {canonical_explanation(review.explanation)}"
        node.comment = (node.comment + " " + annotation).strip()
        if review.white_cp is not None or review.white_mate is not None:
            score = (chess.engine.Mate(review.white_mate) if review.white_mate is not None
                     else chess.engine.Cp(review.white_cp))
            node.set_eval(chess.engine.PovScore(score, chess.WHITE))
    return copy.accept(chess.pgn.StringExporter(headers=True, variations=True, comments=True))
