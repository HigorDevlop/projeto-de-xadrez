"""Offline puzzle selection and legal solution validation; optional online tools."""
from dataclasses import dataclass
from io import StringIO
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import chess
import chess.pgn

THEMES = {"Aleatório": "mix", "Garfo / ataque duplo": "fork", "Cravada": "pin",
          "Espeto": "skewer", "Ataque descoberto": "discoveredAttack",
          "Mate em 1": "mateIn1", "Mate em 2": "mateIn2", "Mate na última fileira": "backRankMate",
          "Peça indefesa": "hangingPiece", "Desvio": "deflection", "Sacrifício": "sacrifice",
          "Final": "endgame", "Atração": "attraction", "Liberação de espaço": "clearance",
          "Interferência": "interference", "Lance intermediário": "intermezzo",
          "Promoção": "promotion", "Subpromoção": "underPromotion",
          "Xeque duplo": "doubleCheck", "Mate abafado": "smotheredMate"}


@dataclass(frozen=True)
class Puzzle:
    id: str
    fen: str
    solution: tuple[str, ...]
    rating: int
    themes: tuple[str, ...]
    last_move: str | None = None


def parse_database_row(row):
    """The database starts before the opponent's setup move, unlike the API."""
    try:
        board=chess.Board(row['FEN']);moves=row['Moves'].split()
        if len(moves)<2 or not board.is_valid():raise ValueError('Posição inválida')
        for index,uci in enumerate(moves):
            move=chess.Move.from_uci(uci)
            if move not in board.legal_moves:raise ValueError('Solução ilegal')
            board.push(move)
            if index==0:fen=board.fen()
        return Puzzle(row['PuzzleId'],fen,tuple(moves[1:]),int(row['Rating']),tuple(row['Themes'].split()),moves[0])
    except (KeyError,ValueError,TypeError) as error:
        raise ValueError('Registro inválido no banco de táticos.') from error


def parse_puzzle(data: dict) -> Puzzle:
    try:
        item = data["puzzle"]
        if not re.fullmatch(r"[A-Za-z0-9]+", item["id"]):
            raise ValueError("Identificador inválido")
        game = chess.pgn.read_game(StringIO(data["game"]["pgn"]))
        if not game or game.errors:
            raise ValueError("Partida inválida")
        moves = list(game.mainline_moves())
        initial = item["initialPly"]
        if not isinstance(initial, int) or not 0 <= initial < len(moves):
            raise ValueError("Posição inicial inválida")
        ply = initial + 1  # Lichess uses a zero-based index for the setup move.
        board = game.board()
        for move in moves[:ply]:
            board.push(move)
        if not board.is_valid():
            raise ValueError("Posição inválida")
        fen = board.fen()
        solution = tuple(item["solution"])
        if not solution:
            raise ValueError("Solução vazia")
        for uci in solution:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise ValueError("Solução ilegal")
            board.push(move)
        last = moves[ply-1].uci() if ply else None
        return Puzzle(item["id"], fen, solution, int(item["rating"]), tuple(item["themes"]), last)
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ValueError("O serviço retornou um tático inválido. Tente carregar outro.") from error


def fetch_puzzle(theme="mix", difficulty="normal") -> Puzzle:
    if theme not in THEMES.values() or difficulty not in {"easiest", "easier", "normal", "harder", "hardest"}:
        raise ValueError("Tema ou dificuldade inválidos.")
    request = Request("https://lichess.org/api/puzzle/next?" + urlencode({"angle": theme, "difficulty": difficulty}),
                      headers={"Accept": "application/json", "User-Agent": "AcervoChess/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            return parse_puzzle(json.load(response))
    except HTTPError as error:
        if error.code == 429:
            raise ValueError("O Lichess limitou as consultas. Aguarde um minuto antes de tentar novamente.") from error
        raise ValueError("Não foi possível carregar o tático do Lichess. Tente novamente.") from error
    except (URLError, OSError, json.JSONDecodeError) as error:
        raise ValueError("Sem conexão com os táticos do Lichess. Tente novamente.") from error


def solve_move(puzzle: Puzzle, progress: int, uci: str, fen: str):
    if not isinstance(progress, int) or not 0 <= progress <= len(puzzle.solution):
        raise ValueError("Progresso inválido. Recomece o tático.")
    board = chess.Board(puzzle.fen)
    for move in puzzle.solution[:progress]:
        board.push_uci(move)
    if fen != board.fen() or progress >= len(puzzle.solution):
        raise ValueError("A posição mudou. Tente novamente no tabuleiro atual.")
    if uci != puzzle.solution[progress]:
        if progress+1==len(puzzle.solution):
            try:move=chess.Move.from_uci(uci)
            except ValueError:move=None
            if move in board.legal_moves:
                board.push(move)
                if board.is_checkmate():return progress+1,'Tático resolvido!'
        return progress, "Ainda não é a continuação da solução. Procure outra ideia."
    progress += 1
    if progress < len(puzzle.solution):
        progress += 1  # automatic opponent reply
    return progress, "Tático resolvido!" if progress == len(puzzle.solution) else "Correto! O adversário respondeu; continue."


def fetch_online_puzzle_range(theme, minimum, maximum, exclude_id=None):
    """Bounded sampling, never present an out-of-range exercise as a match.

    Lichess only supports relative difficulty (anonymous reference: 1500).
    Three sequential attempts are a small interactive search, not a DB download.
    """
    if (type(minimum) is not int or type(maximum) is not int
            or not 0 <= minimum <= maximum <= 4000):
        raise ValueError("Selecione uma faixa de rating válida, com início menor ou igual ao final.")
    average = 1500 if (minimum, maximum) == (0, 4000) else (minimum + maximum) / 2
    difficulty = ('easiest' if average < 1000 else 'easier' if average < 1300
                  else 'normal' if average < 1700 else 'harder' if average < 2000 else 'hardest')
    excluded = {exclude_id} if isinstance(exclude_id, str) else set(exclude_id or ())
    for _ in range(3):
        puzzle = fetch_puzzle(theme, difficulty)
        if (minimum <= puzzle.rating <= maximum and puzzle.id not in excluded
                and (theme == 'mix' or theme in puzzle.themes)):
            return puzzle
    raise ValueError("Nenhum tático dessa faixa foi encontrado nesta busca. Amplie a faixa ou tente novamente.")


def fetch_puzzle_range(theme, minimum, maximum, exclude_id=None):
    from offline_tactics import select_puzzle
    return select_puzzle(theme,minimum,maximum,exclude_id)


def fetch_puzzle_pair(theme, minimum, maximum):
    """Prepare the current exercise and its successor before starting a session."""
    first = fetch_puzzle_range(theme, minimum, maximum)
    return [first, fetch_puzzle_range(theme, minimum, maximum, {first.id})]
