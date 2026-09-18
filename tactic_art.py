"""Small vector teaching diagrams, with no downloaded images or bitmap models."""
import chess
import chess.svg


DIAGRAMS = {
    'mix': ('4k3/8/3q4/8/4N3/8/8/4K3 w - - 0 1', [('e4', 'd6'), ('e4', 'f6')]),
    'fork': ('8/3k1q2/8/4N3/8/8/8/4K3 w - - 0 1', [('e5', 'd7'), ('e5', 'f7')]),
    'pin': ('4k3/4n3/8/8/8/8/4R3/4K3 w - - 0 1', [('e2', 'e8')]),
    'skewer': ('4q3/8/4k3/8/8/8/4R3/4K3 w - - 0 1', [('e2', 'e8')]),
    'discoveredAttack': ('4q1k1/8/8/8/4B3/8/4R3/4K3 w - - 0 1', [('e4', 'c6'), ('e2', 'e8')]),
    'mateIn1': ('6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1', [('a1', 'a8')]),
    'mateIn2': ('7k/6pp/8/6Q1/8/8/8/5RK1 w - - 0 1', [('f1', 'f8')]),
    'backRankMate': ('6k1/5ppp/8/8/8/8/4R3/6K1 w - - 0 1', [('e2', 'e8')]),
    'hangingPiece': ('6k1/8/3n4/8/4N3/8/8/6K1 w - - 0 1', [('e4', 'd6')]),
    'deflection': ('3qr1k1/5ppp/8/8/8/8/3Q4/4R1K1 w - - 0 1', [('d2', 'd8'), ('e8', 'd8')]),
    'sacrifice': ('5rk1/5ppp/8/7Q/8/3B4/8/6K1 w - - 0 1', [('d3', 'h7')]),
    'endgame': ('8/5k2/8/4PK2/8/8/8/8 w - - 0 1', [('e5', 'e6')]),
}


def theme_art(theme):
    fen, lines = DIAGRAMS[theme]
    arrows = [chess.svg.Arrow(chess.parse_square(a), chess.parse_square(b), color='#be8344') for a, b in lines]
    return chess.svg.board(chess.Board(fen), arrows=arrows, coordinates=False, size=170)
