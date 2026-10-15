"""Closed, curated opening courses. No history, engine or network required.

SAN is validated when the catalogue is loaded. Each course chooses one response
per player position; only the opponent branches. Counts describe the bundled
paths, not exhaustive coverage of chess theory.
"""
from functools import lru_cache
from hashlib import sha256
import chess


# id, title, segment, characteristic position, complete training paths
_COURSES = (
    ('london', 'Sistema Londres', 'white', 'd4 d5 Nf3 Nf6 Bf4', (
        'd4 d5 Nf3 Nf6 Bf4 e6 e3 c5 c3 Nc6 Nbd2',
        'd4 d5 Nf3 Nf6 Bf4 c5 e3 Nc6 c3 Qb6 Qb3',
        'd4 Nf6 Nf3 g6 Bf4 Bg7 e3 d6 h3 O-O Be2',
        'd4 d5 Nf3 Nc6 Bf4 Bf5 e3 e6 Bd3',
        'd4 f5 Nf3 Nf6 Bf4 e6 e3 Be7 Bd3',
    )),
    ('e4', 'Repertório 1.e4', 'white', 'e4', (
        'e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3',
        'e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 d4',
        'e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3',
        'e4 e6 d4 d5 exd5 exd5 Bd3 Nf6 Nf3',
        'e4 c6 d4 d5 exd5 cxd5 Bd3 Nc6 c3',
        'e4 d5 exd5 Qxd5 Nc3 Qa5 d4 Nf6 Nf3',
        'e4 d6 d4 Nf6 Nc3 g6 Nf3 Bg7 Be2',
    )),
    ('queens_gambit', 'Gambito da Dama', 'white', 'd4 d5 c4', (
        'd4 d5 c4 e6 Nc3 Nf6 Nf3 Be7 Bg5',
        'd4 d5 c4 dxc4 Nf3 Nf6 e3 e6 Bxc4',
        'd4 d5 c4 c6 Nf3 Nf6 Nc3 e6 e3',
        'd4 d5 c4 e5 dxe5 d4 Nf3 Nc6 a3',
        'd4 Nf6 c4 e6 Nf3 d5 Nc3 Be7 Bg5',
        'd4 Nf6 c4 g6 Nf3 Bg7 Nc3 O-O e4',
    )),
    ('italian', 'Italiana', 'white', 'e4 e5 Nf3 Nc6 Bc4', (
        'e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O',
        'e4 e5 Nf3 Nc6 Bc4 Nf6 d3 Bc5 c3 d6 O-O',
        'e4 e5 Nf3 Nc6 Bc4 Nd4 Nxd4 exd4 O-O',
        'e4 e5 Nf3 d6 d4 exd4 Nxd4 Nf6 Nc3',
        'e4 c5 Nf3 d6 d4 cxd4 Nxd4',
        'e4 e6 d4 d5 exd5 exd5 Bd3',
        'e4 c6 d4 d5 exd5 cxd5 Bd3',
    )),
    ('caro', 'Caro-Kann', 'black_e4', 'e4 c6', (
        'e4 c6 d4 d5 e5 Bf5 Nf3 e6 Be2 c5',
        'e4 c6 d4 d5 exd5 cxd5 Bd3 Nc6 c3 Nf6',
        'e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5 Ng3 Bg6',
        'e4 c6 d4 d5 Nd2 dxe4 Nxe4 Bf5',
        'e4 c6 Nc3 d5 Nf3 Bg4 h3 Bxf3 Qxf3 e6',
        'e4 c6 d4 d5 exd5 cxd5 c4 Nf6 Nc3 e6',
    )),
    ('sicilian', 'Siciliana', 'black_e4', 'e4 c5', (
        'e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6',
        'e4 c5 Nf3 d6 Bb5+ Bd7 Bxd7+ Qxd7',
        'e4 c5 c3 d5 exd5 Qxd5 d4 Nf6',
        'e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7',
        'e4 c5 d4 cxd4 c3 d3 Bxd3 Nc6',
        'e4 c5 Bc4 e6 Nf3 d5 exd5 exd5',
    )),
    ('french', 'Francesa', 'black_e4', 'e4 e6', (
        'e4 e6 d4 d5 e5 c5 c3 Nc6 Nf3 Qb6',
        'e4 e6 d4 d5 exd5 exd5 Nf3 Nf6 Bd3 Bd6',
        'e4 e6 d4 d5 Nc3 Nf6 e5 Nfd7 f4 c5',
        'e4 e6 d4 d5 Nd2 c5 exd5 exd5',
        'e4 e6 d3 d5 Nd2 Nf6 Ngf3 c5',
    )),
    ('e5', '1...e5 sólido', 'black_e4', 'e4 e5', (
        'e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6',
        'e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7',
        'e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Bc5',
        'e4 e5 f4 exf4 Nf3 d5 exd5 Nf6',
        'e4 e5 Nc3 Nf6 f4 d5 fxe5 Nxe4',
        'e4 e5 Qh5 Nc6 Bc4 g6 Qf3 Nf6',
    )),
    ('kings_indian', 'Indiana do Rei', 'black_d4', 'd4 Nf6 c4 g6 Nc3 Bg7', (
        'd4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O',
        'd4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O',
        'd4 Nf6 Nf3 g6 Bf4 Bg7 e3 d6',
        'c4 Nf6 Nc3 g6 e4 d6 d4 Bg7',
        'Nf3 Nf6 g3 g6 Bg2 Bg7 O-O O-O',
    )),
    ('slav', 'Eslava', 'black_d4', 'd4 d5 c4 c6', (
        'd4 d5 c4 c6 Nf3 Nf6 Nc3 dxc4 a4 Bf5',
        'd4 d5 c4 c6 cxd5 cxd5 Nc3 Nf6 Nf3 Nc6',
        'd4 d5 c4 c6 Nf3 Nf6 e3 Bf5 Nc3 e6',
        'd4 d5 Nf3 Nf6 Bf4 c6 e3 Bf5',
        'c4 c6 Nf3 d5 d4 Nf6',
        'Nf3 d5 d4 Nf6 c4 c6',
    )),
    ('nimzo', 'Nimzoíndia', 'black_d4', 'd4 Nf6 c4 e6 Nc3 Bb4', (
        'd4 Nf6 c4 e6 Nc3 Bb4 e3 O-O Bd3 d5',
        'd4 Nf6 c4 e6 Nc3 Bb4 Qc2 O-O a3 Bxc3+',
        'd4 Nf6 c4 e6 Nc3 Bb4 a3 Bxc3+ bxc3 O-O',
        'd4 Nf6 c4 e6 Nf3 d5 Nc3 Be7',
        'd4 Nf6 Bf4 d5 e3 e6 Nf3 Bd6',
        'c4 Nf6 Nc3 e6 d4 Bb4',
        'Nf3 Nf6 c4 e6 d4 d5',
    )),
    ('qgd', 'Gambito da Dama Recusado', 'black_d4', 'd4 d5 c4 e6', (
        'd4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O',
        'd4 d5 c4 e6 Nc3 Nf6 cxd5 exd5 Bg5 Be7',
        'd4 d5 c4 e6 Nf3 Nf6 e3 Be7 Bd3 O-O',
        'd4 d5 Bf4 Nf6 e3 e6 Nf3 Bd6',
        'c4 e6 Nc3 d5 d4 Nf6',
        'Nf3 d5 d4 Nf6 c4 e6',
    )),
)


@lru_cache(maxsize=1)
def catalog():
    result = []
    for key, title, group, preview, paths in _COURSES:
        side = 'white' if group == 'white' else 'black'
        lines, choices = [], {}
        for text in paths:
            board, moves = chess.Board(), []
            for san in text.split():
                move = board.parse_san(san)
                if board.turn == (side == 'white'):
                    position = board.epd()
                    if choices.setdefault(position, move.uci()) != move.uci():
                        raise ValueError(f'Repertório contraditório: {key}: {text}')
                moves.append(move.uci())
                board.push(move)
            # End at the learner's last decision, never on an untested reply.
            if board.turn == (side == 'white'):
                moves.pop()
            line_id = key + '-' + sha256(' '.join(moves).encode()).hexdigest()[:12]
            lines.append({'id': line_id, 'moves': moves, 'side': side, 'opening': title})
        board = chess.Board()
        for san in preview.split():
            board.push_san(san)
        result.append({'id': key, 'title': title, 'group': group, 'side': side,
                       'fen': board.fen(), 'notation': _notation(preview), 'lines': lines})
    from opening_reference_catalog import extra_courses
    return tuple(result + extra_courses(result))


def _notation(text):
    return ' '.join(f'{i//2+1}.{san}' if i % 2 == 0 else san
                    for i, san in enumerate(text.split()))


def selected_courses(ids):
    if not isinstance(ids, list) or not 1 <= len(ids) <= 4 or any(not isinstance(x, str) for x in ids):
        raise ValueError('Selecione de 1 a 4 aberturas.')
    lookup = {item['id']: item for item in catalog()}
    if len(set(ids)) != len(ids) or any(key not in lookup for key in ids):
        raise ValueError('Seleção de aberturas inválida.')
    return [lookup[key] for key in ids]
