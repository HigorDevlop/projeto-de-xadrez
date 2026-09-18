"""Book extraction and deterministic position descriptions; no language model."""
from dataclasses import dataclass
from io import BytesIO
import re
import unicodedata

import chess

from chess_review import CATEGORIES, decode_text, position_key, read_games
from strategy import strategic_context


@dataclass(frozen=True)
class Passage:
    source: str
    text: str
    position: str = ""


def load_passages(files: tuple[tuple[str, bytes], ...]) -> tuple[list[Passage], list[str]]:
    passages, errors = [], []
    for name, data in files:
        try:
            if name.lower().endswith(".bin"):
                continue  # Polyglot has moves and weights, no explanatory prose.
            if name.lower().endswith(".pdf"):
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(data))
                if reader.is_encrypted:
                    raise ValueError("PDF protegido por senha; carregue uma cópia desbloqueada.")
                if len(reader.pages) > 1000:
                    raise ValueError("Use PDFs com até 1.000 páginas.")
                pages = [(f"{name}, p. {i + 1}", page.extract_text() or "")
                         for i, page in enumerate(reader.pages)]
            elif name.lower().endswith(".pgn"):
                for game in read_games(decode_text(data)):
                    title = f"{name} · {game.headers.get('White', '?')} × {game.headers.get('Black', '?')}"
                    pending = [game]
                    while pending:
                        node = pending.pop()
                        if node.comment:
                            passages.append(Passage(title, node.comment[:1600], position_key(node.board())))
                        pending.extend(node.variations)
                continue
            else:
                pages = [(name, decode_text(data))]
            found = 0
            for source, text in pages:
                text = re.sub(r"\s+", " ", text).strip()
                for offset in range(0, min(len(text), 2_000_000), 1100):
                    chunk = text[offset:offset + 1400]
                    if len(chunk) > 30:
                        passages.append(Passage(source, chunk))
                        found += 1
            if not found:
                errors.append(f"{name}: nenhum texto extraído. PDFs digitalizados precisam de OCR.")
        except ImportError:
            errors.append(f"{name}: instale as dependências para habilitar a leitura de PDF.")
        except Exception as error:
            errors.append(f"{name}: não foi possível ler o livro ({error}).")
    return passages, errors


def tokens(text):
    return set(re.findall(r"[a-z0-9]{3,}", unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()))


def retrieve(passages, board, question="", previous_fen=None):
    query = tokens(question + " " + " ".join(position_facts(board)))
    positions = {position_key(board)}
    if previous_fen:
        positions.add(position_key(chess.Board(previous_fen)))
    ranked = []
    for passage in passages:
        if passage.position:
            score = 100 if passage.position in positions else 0
        else:
            score = len(query & tokens(passage.text))
        if score >= (1 if passage.position else 2):
            ranked.append((score, passage))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [passage for _, passage in ranked[:3]]


PIECES = {chess.PAWN: "peão", chess.KNIGHT: "cavalo", chess.BISHOP: "bispo",
          chess.ROOK: "torre", chess.QUEEN: "dama", chess.KING: "rei"}


def position_facts(board: chess.Board) -> list[str]:
    side = "brancas" if board.turn else "pretas"
    if board.is_checkmate():
        return [f"Xeque-mate: as {side} não têm defesa legal."]
    if board.is_stalemate():
        return ["Empate por afogamento: não há lance legal, mas o rei não está em xeque."]
    if board.is_game_over():
        return [f"Partida encerrada: {board.result()}."]
    facts = [f"É a vez das {side}."]
    if board.is_check():
        facts.append("O rei está em xeque: a prioridade é sair do ataque.")
    loose = []
    for square, piece in board.piece_map().items():
        if piece.color == board.turn and piece.piece_type != chess.KING:
            if board.is_attacked_by(not piece.color, square) and not board.is_attacked_by(piece.color, square):
                loose.append(f"{PIECES[piece.piece_type]} em {chess.square_name(square)}")
    if loose:
        facts.append("Peças atacadas sem defesa direta: " + ", ".join(loose[:4]) + ". Confira se a captura é legal.")
    center = [chess.square_name(s) for s in (chess.D4, chess.E4, chess.D5, chess.E5)
              if board.is_attacked_by(board.turn, s)]
    facts.append("Casas centrais controladas pelo lado a jogar: " + (", ".join(center) or "nenhuma") + ".")
    return facts


def move_ideas(before: chess.Board, move: chess.Move) -> dict:
    """Observable changes, not an inferred claim about the player's intent."""
    after = before.copy()
    piece = before.piece_at(move.from_square)
    color = piece.color
    san = before.san(move)
    origin, target = chess.square_name(move.from_square), chess.square_name(move.to_square)
    capture = before.piece_at(move.to_square)
    if before.is_en_passant(move):
        capture = chess.Piece(chess.PAWN, not color)
    after.push(move)
    ideas = []
    if before.is_castling(move):
        ideas.append(f"Com {san}, o rei sai do centro e a torre entra em jogo; o foco é preparar a coordenação das peças sem deixar o rei exposto")
    elif capture:
        ideas.append(f"Com {san}, o {PIECES[piece.piece_type]} de {origin} captura um {PIECES[capture.piece_type]} e ocupa {target}, alterando o material e a ocupação dessa casa")
    else:
        ideas.append(f"Com {san}, o {PIECES[piece.piece_type]} sai de {origin} e ocupa {target}")
    if move.promotion:
        ideas.append(f"O peão é promovido a {PIECES[move.promotion]}, mudando as possibilidades de ataque e defesa")
    center = [chess.square_name(s) for s in (chess.D4, chess.E4, chess.D5, chess.E5)
              if s in after.attacks(move.to_square)]
    if center:
        ideas.append(f"Dessa casa, a peça controla {', '.join(center)}; essa influência central ajuda a disputar espaço")
    elif piece.piece_type in (chess.KNIGHT, chess.BISHOP) and chess.square_rank(move.from_square) == (0 if color else 7):
        ideas.append("A peça deixa a primeira fileira e passa a participar da disputa por casas, dando sequência ao desenvolvimento")
    if piece.piece_type == chess.PAWN:
        opened = []
        for square, other in before.piece_map().items():
            if other.color == color and other.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN):
                gained = (after.attacks(square) - before.attacks(square))
                if len(gained) >= 2:
                    opened.append(f"{PIECES[other.piece_type]} de {chess.square_name(square)}")
        if opened:
            ideas.append("O avanço também abre linhas para " + " e ".join(opened[:2]))
    targets = [f"{PIECES[p.piece_type]} em {chess.square_name(s)}"
               for s, p in after.piece_map().items()
               if p.color != color and p.piece_type != chess.KING and s in after.attacks(move.to_square)]
    if targets:
        ideas.append("A peça passa a pressionar " + " e ".join(targets[:2]) + "; isso cria um ponto concreto para o adversário defender")
    if after.is_checkmate():
        ideas.append("É xeque-mate: o rei adversário está atacado e não existe resposta legal")
    elif after.is_check():
        ideas.append("O lance dá xeque, portanto o adversário precisa responder ao ataque ao rei antes de executar outro plano")
    risk = []
    for square, own in after.piece_map().items():
        if own.color == color and own.piece_type != chess.KING:
            if after.is_attacked_by(not color, square) and not after.is_attacked_by(color, square):
                risk.append(f"{PIECES[own.piece_type]} em {chess.square_name(square)}")
    if risk and not after.is_game_over():
        improvement = "Antes de repetir essa ideia, confira a segurança do " + " e do ".join(risk[:2]) + ", que está sob ataque sem defesa direta; verifique se a captura adversária é legal"
    elif capture:
        improvement = f"Para avaliar melhor uma troca como essa, conte as recapturas legais em {target} e compare quais peças continuam ativas depois dela"
    elif piece.piece_type == chess.PAWN:
        improvement = f"Para melhorar a decisão, compare o espaço ganho em {target} com as casas que o peão deixou de proteger ao sair de {origin}, pois ele não poderá recuar"
    else:
        improvement = f"Para melhorar essa escolha, confira se o {PIECES[piece.piece_type]} em {target} pode ser expulso por um peão ou se terá de perder outro tempo para se defender"
    return {"san": san, "facts": ideas, "improvement": improvement,
            "before_fen": before.fen(), "after_fen": after.fen()}


def basic_lesson(board, review=None, snapshot=None):
    if not board.move_stack:
        return "Escolha um lance no tabuleiro para examinarmos sua ideia. Nesta posição, podemos comparar o espaço no centro, a atividade das peças e a segurança dos reis antes de decidir o que jogar."
    before = board.copy()
    move = before.pop()
    details = move_ideas(before, move)
    sentences = details["facts"][:4]
    if review and review.category in {"inaccuracy", "mistake", "blunder", "miss"}:
        sentences.append(f"A análise aponta {review.best_san} como alternativa mais precisa a {details['san']}; compare o que muda na defesa e nas ameaças antes de escolher")
    if snapshot and snapshot["line"] and not board.is_game_over():
        sentences.append(f"O adversário pode responder com {snapshot['steps'][0].split(':')[0]}; uma continuação possível é {snapshot['line']}, sem que essa sequência seja obrigatória")
    if not board.is_game_over():
        sentences.append(details["improvement"])
    return ". ".join(s.rstrip(".") for s in sentences) + "."


def single_paragraph(text: str) -> str:
    text = re.sub(r"(?m)^\s*(?:#{1,6}\s+|[-*>]\s+|\d+\.\s+)", "", text)
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def tutor_mood(category=None, thinking=False):
    expressions = {
        None: ("pensativo", "Antes de escolher seu plano, descubra o que o adversário ameaça."),
        "book": ("serio", "Conhecer a abertura ajuda; entender a ideia por trás dela é o que ensina."),
        "brilliant": ("pensativo", "Uma ideia incomum apareceu; vamos entender por que ela funciona."),
        "best": ("serio", "O lance encontrou a continuação mais precisa desta posição."),
        "great": ("pensativo", "Esta escolha é estreita; observe o detalhe que a torna especial."),
        "excellent": ("serio", "O lance preserva a posição com segurança e propósito."),
        "good": ("serio", "A posição continua saudável; veja como o plano pode avançar."),
        "inaccuracy": ("pensativo", "Há um pequeno detalhe a investigar antes de repetir este lance."),
        "mistake": ("raiva", "Esse lance deixou uma chance escapar. Vamos descobrir o que passou despercebido."),
        "miss": ("raiva", "Uma oportunidade ficou para trás; vamos localizar o momento decisivo."),
        "blunder": ("raiva", "Este erro muda a posição de forma grave; vamos encontrar a defesa necessária."),
    }
    _, message = expressions.get(category, expressions[None])
    return category if category in CATEGORIES else "book", message


def move_lesson(board, review=None, snapshot=None, category=None, question="", variation=0):
    """Position-dependent evidence derived from legal board state."""
    context = strategic_context(board, snapshot)
    if board.is_game_over() or not board.move_stack:
        return ' '.join(context['prioridades'])
    before = board.copy()
    move = before.pop()
    details = move_ideas(before, move)
    sentences = [details['facts'][0].rstrip('.') + '.']
    priorities = context['prioridades']
    if variation and len(priorities) > 1:
        priorities = priorities[1:] + priorities[:1]
    sentences.extend(priorities[:2])
    sentences.extend(context['mudancas'][:1])
    if review and review.category in {'inaccuracy', 'mistake', 'blunder', 'miss'} and review.best_san:
        sentences.append(f'A alternativa calculada é {review.best_san}; compare essa escolha com a ameaça imediata indicada na posição.')
    if snapshot and snapshot.get('line'):
        sentences.append(f'Uma continuação calculada é {snapshot["line"]}; observe como a resposta adversária condiciona seu próximo passo.')
    return ' '.join(sentences)


