"""Original, locally authored micro-lessons; no downloaded/book-derived content.

Position arrangements and explanatory text were created for Coach Chess.
The contribution is distributed under the project's terms. No third-party
PGN, image, text, tablebase or engine output is embedded.
"""
import chess

LESSONS = (
    dict(id='direct-opposition', title='Oposição direta',
         objective='Jogue com as brancas e coloque o rei em oposição direta ao rei preto.',
         fen='8/8/4k3/8/8/4K3/4P3/8 w - - 0 1', uci='e3e4',
         hints=('Observe os dois reis: queremos alinhá-los com uma casa vazia entre eles.',
                'O rei preto está em e6. A casa e5 deve permanecer vazia.',
                'Mova o rei branco de e3 para e4.'),
         line=('e3e4', 'e6d6', 'e4f5'),
         explanation='Após Ke4, os reis ficam em e4 e e6, separados pela casa e5, e as pretas jogam. '
                     'Nenhum rei pode entrar na casa controlada pelo adversário. Se as pretas escolherem Kd6, '
                     'Kf5 ilustra a passagem pelo outro lado. Esta é uma continuação ilustrativa, não uma prova de vitória.',
         target='e4'),
    dict(id='king-before-pawn', title='O rei à frente do peão',
         objective='Antes de avançar o peão de e4, leve o rei branco à casa e6.',
         fen='4k3/8/8/4K3/4P3/8/8/8 w - - 0 1', uci='e5e6',
         hints=('O rei pode preparar o caminho enquanto o peão espera.',
                'A casa pedida fica duas fileiras à frente do peão e não é atacada pelo rei preto.',
                'Mova o rei de e5 para e6; ainda não mova o peão.'),
         line=('e5e6', 'e8d8', 'e4e5'),
         explanation='Ke6 deixa o rei duas fileiras à frente do peão de e4 e cria oposição com o rei em e8. '
                     'Na resposta ilustrativa Kd8, e5 avança o peão: a casa e5 é protegida pelo rei de e6. '
                     'O exercício pede essa preparação específica; não classifica outras escolhas legais como derrotas.',
         target='e6'),
    dict(id='promotion-check', title='Promoção com xeque',
         objective='Promova o peão de e7 a dama e dê xeque. Não é um exercício de mate.',
         fen='6k1/4P3/4K3/8/8/8/8/8 w - - 0 1', uci='e7e8q',
         hints=('O peão está a um passo da última fileira.',
                'Escolha a dama na promoção: ela atacará o rei preto pela oitava fileira.',
                'Jogue e7–e8 e escolha a dama.'),
         line=('e7e8q', 'g8h7'),
         explanation='e8=Q+ cria uma dama em e8 que ataca o rei de g8. É xeque, não mate: Kh7 é uma resposta legal. '
                     'Também não é afogamento, pois o rei está em xeque e pode se mover. '
                     'Promover a outra peça pode ser legal, mas esta lição pede explicitamente a dama.',
         target='e8'),
)


def lesson(identifier):
    return next(item for item in LESSONS if item['id'] == identifier)


def validate():
    for item in LESSONS:
        board = chess.Board(item['fen'])
        if not board.is_valid() or board.is_game_over() or item['line'][0] != item['uci']:
            raise ValueError('Posição didática inválida: ' + item['id'])
        for uci in item['line']:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                raise ValueError('Continuação ilegal: ' + item['id'])
            board.push(move)


validate()
