"""Respostas locais, limitadas aos fatos verificáveis da posição recebida."""
import re
import unicodedata

import chess

from tutor import PIECES, basic_lesson, position_facts


def answer_question(question, board):
    question = question.strip()[:1000]
    if not question:
        return "Digite uma pergunta sobre a posição atual."
    if not board.is_valid():
        return "A posição atual é inválida. Carregue uma partida ou uma posição FEN válida."
    if board.is_game_over():
        return " ".join(position_facts(board))
    normalized = unicodedata.normalize('NFKD', question.lower()).encode('ascii', 'ignore').decode()
    side = 'brancas' if board.turn else 'pretas'
    if board.move_stack and any(word in normalized for word in ('por que', 'porque', 'ultimo lance')):
        before = board.copy()
        previous = before.pop()
        if before.san(previous).lower() in question.lower() or 'ultimo lance' in normalized:
            return basic_lesson(board)
    # An explicit move takes precedence over generic words such as 'capturar'.
    candidate = re.search(r'\b[a-h][1-8][a-h][1-8][qrbn]?\b|\b(?:[KQRBNBRDC]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|O-O(?:-O)?)\b', question)
    if candidate and (len(candidate.group()) > 2 or any(word in normalized for word in ('jogar', 'lance', 'posso'))):
        token = candidate.group()
        try:
            move = board.parse_uci(token) if len(token) in (4, 5) and token[0].islower() and token[1].isdigit() else board.parse_san(token)
        except ValueError:
            return f"{token} não é um lance legal nesta posição para as {side}. Confira a casa de origem, o caminho da peça e a segurança do rei."
        after = board.copy()
        san = board.san(move)
        after.push(move)
        return f"{san} é legal para as {side}. " + basic_lesson(after)
    if any(word in normalized for word in ('material', 'vantagem', 'ganhando', 'ganha')):
        values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
        scores = {color: sum(len(board.pieces(piece, color))*value for piece, value in values.items()) for color in chess.COLORS}
        delta = scores[chess.WHITE] - scores[chess.BLACK]
        result = 'O material está equilibrado.' if not delta else f"As {'brancas' if delta > 0 else 'pretas'} têm {abs(delta)} ponto(s) de vantagem material."
        return result + ' Essa contagem não determina quem está melhor: confira as ameaças e a segurança dos reis.'
    if any(word in normalized for word in ('ameaca', 'captur', 'pendur', 'defes', 'atacad', 'xeque')):
        captures = [board.san(move) for move in board.legal_moves if board.is_capture(move)]
        return ' '.join(position_facts(board)[:3]) + (' Capturas legais: ' + ', '.join(captures[:12]) + '.' if captures else ' Não há captura legal para o lado a jogar.')
    if any(word in normalized for word in ('roque', 'rocar')):
        castles = [board.san(move) for move in board.legal_moves if board.is_castling(move)]
        return ('Roques legais nesta posição: ' + ', '.join(castles) + '.') if castles else 'Não há roque legal nesta posição. O rei precisa ter o direito de rocar, o caminho livre e não pode estar, passar ou terminar em xeque.'
    square = re.search(r'\b[a-h][1-8]\b', question.lower())
    if square:
        name = square.group()
        index = chess.parse_square(name)
        piece = board.piece_at(index)
        occupant = f"um {PIECES[piece.piece_type]} das {'brancas' if piece.color else 'pretas'}" if piece else 'nenhuma peça'
        attackers = [chess.square_name(s) for s in board.attackers(not board.turn, index)]
        return f"Em {name} há {occupant}. " + ('O adversário ataca essa casa a partir de ' + ', '.join(attackers) + '.' if attackers else 'O adversário não ataca essa casa na posição atual.')
    if any(word in normalized for word in ('por que', 'porque', 'explic', 'ultimo', 'ideia')) and board.move_stack:
        return basic_lesson(board)
    if any(word in normalized for word in ('plano', 'melhor', 'jogar', 'fazer', 'sugest')):
        return ' '.join(position_facts(board)) + ' Para comparar a melhor continuação com cálculo, use Analisar Partida.'
    return 'Posso verificar lances, material, ameaças, roque e casas específicas. ' + ' '.join(position_facts(board)[:2])
