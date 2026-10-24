"""Small vector teaching diagrams, with no downloaded images or bitmap models."""
import chess
import chess.svg
from functools import lru_cache


@lru_cache(maxsize=20)
def theme_symbol(theme):
    """Small golden teaching motifs: pieces and relationships, without a board."""
    motifs={
        'mix':([('N',50,52,48)],[(20,68,80,28),(20,28,80,68)],'↔'),
        'fork':([('N',50,72,42),('K',21,22,30),('Q',79,22,30)],[(47,59,23,35),(56,59,78,35)],''),
        'pin':([('R',50,82,34),('N',50,49,32),('K',50,15,30)],[(50,70,50,24)],''),
        'skewer':([('B',22,81,34),('K',50,49,32),('Q',80,17,30)],[(28,72,80,20)],''),
        'discoveredAttack':([('R',24,81,32),('B',24,48,32),('Q',24,15,28)],[(24,69,24,23),(39,47,77,32)],''),
        'mateIn1':([('R',27,74,38),('K',74,24,34)],[(32,58,71,33)],'1'),
        'mateIn2':([('Q',25,73,38),('K',74,24,34)],[(34,60,61,54),(63,49,72,36)],'2'),
        'backRankMate':([('R',18,76,32),('K',70,17,29),('P',51,44,20),('P',70,44,20),('P',89,44,20)],[(19,63,19,16),(22,16,56,16)],''),
        'hangingPiece':([('N',26,74,38),('B',76,26,34)],[(40,59,64,39)],'○'),
        'deflection':([('Q',20,77,32),('R',53,30,30),('K',84,18,26)],[(30,64,48,42),(42,29,15,23)],''),
        'sacrifice':([('B',25,75,36),('K',75,25,34)],[(39,60,64,36)],'✦'),
        'endgame':([('P',29,71,36),('K',72,38,42)],[(29,55,29,20)],''),
        'attraction':([('Q',22,77,34),('K',77,22,34)],[(35,64,55,46),(69,35,57,46)],''),
        'clearance':([('R',28,83,32),('B',28,48,32)],[(28,68,28,14),(42,48,78,36)],''),
        'interference':([('R',24,18,30),('R',24,83,30),('B',78,51,36)],[(60,51,30,51)],'⊥'),
        'intermezzo':([('N',26,72,38),('K',73,25,34)],[(39,58,64,36)],'!'),
        'promotion':([('P',25,74,34),('Q',76,24,38)],[(39,60,61,39)],''),
        'underPromotion':([('P',25,74,34),('N',76,24,38)],[(39,60,61,39)],''),
        'doubleCheck':([('R',17,78,30),('B',55,77,32),('K',75,19,32)],[(24,66,65,29),(58,62,72,33)],''),
        'smotheredMate':([('N',22,75,34),('K',74,18,29),('P',64,44,21),('P',86,44,21),('R',91,13,19)],[(33,61,61,29)],''),
    }
    pieces,arrows,mark=motifs[theme]
    body=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">']
    for x1,y1,x2,y2 in arrows:
        import math
        angle=math.atan2(y2-y1,x2-x1);size=6
        a=(x2-size*math.cos(angle-.5),y2-size*math.sin(angle-.5));b=(x2-size*math.cos(angle+.5),y2-size*math.sin(angle+.5))
        body.append(f'<path d="M{x1} {y1} L{x2} {y2} M{a[0]:.1f} {a[1]:.1f} L{x2} {y2} L{b[0]:.1f} {b[1]:.1f}" stroke="#cca86b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    for symbol,x,y,size in pieces:
        svg=chess.svg.piece(chess.Piece.from_symbol(symbol))
        inner=svg[svg.index('>')+1:svg.rindex('</svg>')]
        inner=inner.replace('#ffffff','#e7ce9c').replace('#fff','#e7ce9c').replace('#000000','#65502b').replace('#000','#65502b')
        body.append(f'<svg x="{x-size/2}" y="{y-size/2}" width="{size}" height="{size}" viewBox="0 0 45 45">{inner}</svg>')
    if mark:body.append(f'<text x="83" y="84" fill="#d8ba80" text-anchor="middle" font-family="Georgia" font-size="20">{mark}</text>')
    return ''.join(body)+'</svg>'


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
    'attraction': ('5rk1/5ppp/8/8/8/3B4/7Q/6K1 w - - 0 1', [('h2', 'h7'), ('g8', 'h7')]),
    'clearance': ('6k1/8/8/8/3B4/8/3R4/6K1 w - - 0 1', [('d4', 'g7'), ('d2', 'd8')]),
    'interference': ('3r2k1/8/8/8/8/1B6/8/3R2K1 w - - 0 1', [('b3', 'd5')]),
    'intermezzo': ('4r1k1/5ppp/8/8/8/8/4Q3/4R1K1 w - - 0 1', [('e2', 'e8')]),
    'promotion': ('8/3P2k1/8/8/8/8/8/6K1 w - - 0 1', [('d7', 'd8')]),
    'underPromotion': ('8/3P4/4k3/8/8/8/8/6K1 w - - 0 1', [('d7', 'd8'), ('d8', 'e6')]),
    'doubleCheck': ('4k3/8/8/8/4B3/8/4R3/6K1 w - - 0 1', [('e4', 'b5'), ('e2', 'e8')]),
    'smotheredMate': ('6rk/6pp/8/4N3/8/8/8/6K1 w - - 0 1', [('e5', 'f7')]),
}


def theme_art(theme):
    fen, lines = DIAGRAMS[theme]
    arrows = [chess.svg.Arrow(chess.parse_square(a), chess.parse_square(b), color='#be8344') for a, b in lines]
    return chess.svg.board(chess.Board(fen), arrows=arrows, coordinates=False, size=280,
                           colors={'square light': '#f3f7eb', 'square dark': '#629269'})
