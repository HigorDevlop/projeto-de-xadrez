"""Reference-screen opening families, backed by the bundled public ECO data."""
import csv
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import chess

DISPLAY_NAMES = {'london': 'London System', 'e4': "King's Pawn Game", 'queens_gambit': "Queen's Gambit",
    'italian': 'Italian Game', 'caro': 'Caro-Kann Defense', 'sicilian': 'Sicilian Defense',
    'french': 'French Defense', 'e5': "King's Pawn Game", 'kings_indian': "King's Indian Defense",
    'slav': 'Slav Defense', 'nimzo': 'Nimzo-Indian Defense', 'qgd': "Queen's Gambit Declined"}

FAMILIES = (
    ('english', 'English Opening', 'c4'), ('indian', 'Indian Defense', 'd4 Nf6'),
    ('queens_pawn', "Queen's Pawn Game", 'd4 d5'), ('zukertort', 'Zukertort Opening', 'Nf3'),
    ('zukertort_variation', 'Zukertort Variation', 'd4 d5 Nf3'), ('pirc', 'Pirc Defense', 'e4 d6'),
    ('ruy_lopez', 'Ruy Lopez', 'e4 e5 Nf3 Nc6 Bb5'),
    ('symmetrical', 'Symmetrical Variation', 'd4 d5 Nf3 Nf6'),
    ('horwitz', 'Horwitz Defense', 'd4 e6'), ('scandinavian', 'Scandinavian Defense', 'e4 d5'),
    ('scotch', 'Scotch Game', 'e4 e5 Nf3 Nc6 d4'), ('petrov', "Petrov's Defense", 'e4 e5 Nf3 Nf6'),
    ('alekhine', 'Alekhine Defense', 'e4 Nf6'), ('modern', 'Modern Defense', 'e4 g6'),
    ('nimzowitsch', 'Nimzowitsch Defense', 'e4 Nc6'), ('vienna', 'Vienna Game', 'e4 e5 Nc3'),
    ('kings_gambit', "King's Gambit", 'e4 e5 f4'), ('center', 'Center Game', 'e4 e5 d4'),
    ('trompowsky', 'Trompowsky Attack', 'd4 Nf6 Bg5'), ('dutch', 'Dutch Defense', 'd4 f5'),
    ('grunfeld', 'Grünfeld Defense', 'd4 Nf6 c4 g6 Nc3 d5'),
    ('old_indian', 'Old Indian Defense', 'd4 d6 c4'), ('englund', 'Englund Gambit', 'd4 e5'),
    ('nimzo_larsen', 'Nimzo-Larsen Attack', 'b3'), ('hungarian', 'Hungarian Opening', 'g3'),
    ('bird', 'Bird Opening', 'f4'), ('kings_indian_attack', "King's Indian Attack", 'Nf3 d5 g3'),
)


@lru_cache(maxsize=1)
def eco_paths():
    rows = []
    for path in sorted((Path(__file__).parent / 'data/openings').glob('*.tsv')):
        with path.open(encoding='utf-8-sig') as source:
            for row in csv.DictReader(source, delimiter='\t'):
                board, moves = chess.Board(), []
                for token in row['pgn'].split():
                    if token.endswith('.'):
                        continue
                    move = board.parse_san(token)
                    moves.append(move.uci())
                    board.push(move)
                rows.append((tuple(moves), row['name']))
    return rows


def _moves(san):
    board, result = chess.Board(), []
    for token in san.split():
        move = board.parse_san(token)
        result.append(move.uci())
        board.push(move)
    return result


def _course(key, name, preview, paths, side):
    board = chess.Board()
    for move in preview:
        board.push_uci(move)
    notation_board, notation = chess.Board(), []
    for ply, uci in enumerate(preview):
        move = chess.Move.from_uci(uci)
        notation.append((f'{ply//2+1}.' if ply % 2 == 0 else '') + notation_board.san(move))
        notation_board.push(move)
    decisions, lines = {}, []
    for moves, variation in paths:
        moves = list(moves[:14])
        if len(moves) % 2 == (0 if side == 'white' else 1):
            moves = moves[:-1]
        if not moves:
            continue
        board2, additions, consistent = chess.Board(), {}, True
        for uci in moves:
            if board2.turn == (side == 'white'):
                fen = board2.epd()
                if fen in decisions and decisions[fen] != uci:
                    consistent = False
                    break
                additions[fen] = uci
            board2.push_uci(uci)
        if not consistent or any(line['moves'] == moves for line in lines):
            continue
        decisions.update(additions)
        lines.append(dict(id=key+'-'+sha256(' '.join(moves).encode()).hexdigest()[:12], moves=moves,
                          side=side, opening=variation.split(':')[0], variation=variation.partition(': ')[2]))
        if len(lines) == 8:
            break
    group = 'white' if side == 'white' else 'black_e4' if preview[0]=='e2e4' else 'black_d4' if preview[0]=='d2d4' else 'black_other'
    return dict(id=key, title=name, side=side, group=group,
                fen=board.fen(), notation=' '.join(notation), lines=lines)


def extra_courses(base):
    result = []
    rows = eco_paths()
    for key, name, san in FAMILIES:
        preview = _moves(san)
        candidates = [(moves, title) for moves, title in rows
                      if moves[:len(preview)] == tuple(preview) and len(moves) >= max(6, len(preview))]
        candidates.sort(key=lambda row: (abs(len(row[0])-10), row[1]))
        if key == 'english':
            candidates = [(_moves(text), title) for text, title in (
                ('c4 Nf6 d4 e6 Nc3 Bb4 Qc2 O-O e4 d5 e5', 'Nimzo-Indian Defense'),
                ('c4 c6 d4 d5 cxd5 cxd5 Nc3 Nf6 Bf4 e6 Rc1', 'Slav Defense: Exchange Variation'),
                ('c4 e5 Nc3 Nf6 g3 Nc6 Bg2 g6', 'Four Knights System: Nimzowitsch Variation'),
                ('c4 c5 Nc3 Nc6 e3 g6 d4 cxd4 exd4 Bg7 Nf3', 'Symmetrical Variation: Two Knights Variation'),
            )] + candidates
        if not candidates:
            candidates = [(tuple(preview), name)]
        for side in ('white', 'black'):
            course = _course(key if side == 'white' else key+'_black', name, preview, candidates, side)
            if course['lines']:
                result.append(course)
    for course in base:
        side = 'black' if course['side'] == 'white' else 'white'
        # The opposite side uses a consistent response tree, preserving old IDs.
        preview = _moves(' '.join(token.split('.')[-1] for token in course['notation'].split()))
        paths = [(line['moves'], DISPLAY_NAMES.get(course['id'], course['title'])) for line in course['lines']]
        result.append(_course(course['id']+'_'+side, DISPLAY_NAMES.get(course['id'], course['title']), preview, paths, side))
    return result


def display_name(course):
    return DISPLAY_NAMES.get(course['id'], course['title'])
