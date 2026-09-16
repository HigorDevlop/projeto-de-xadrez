"""Position-specific strategic evidence for the local tutor (no speculative engine scores)."""
import chess

NAMES = {chess.PAWN: 'peão', chess.KNIGHT: 'cavalo', chess.BISHOP: 'bispo',
         chess.ROOK: 'torre', chess.QUEEN: 'dama', chess.KING: 'rei'}
VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def pawn_structure(board, color):
    own, enemy = board.pieces(chess.PAWN, color), board.pieces(chess.PAWN, not color)
    isolated, doubled, passed = [], [], []
    for square in own:
        file, rank = chess.square_file(square), chess.square_rank(square)
        if not any(abs(chess.square_file(other)-file) == 1 for other in own):
            isolated.append(chess.square_name(square))
        if sum(chess.square_file(other) == file for other in own) > 1:
            doubled.append(chess.square_name(square))
        if not any(abs(chess.square_file(other)-file) <= 1 and
                   (chess.square_rank(other) > rank if color else chess.square_rank(other) < rank) for other in enemy):
            passed.append(chess.square_name(square))
    return {'isolados': isolated, 'dobrados': doubled, 'passados': passed}


def phase(board):
    material = sum(VALUES.get(p.piece_type, 0) for p in board.piece_map().values() if p.piece_type != chess.PAWN)
    if material <= 20:
        return 'final'
    undeveloped = sum(board.piece_at(s) == chess.Piece(piece, color)
                      for color, rank in [(chess.WHITE, 0), (chess.BLACK, 7)]
                      for file, piece in [(1, chess.KNIGHT), (2, chess.BISHOP), (5, chess.BISHOP), (6, chess.KNIGHT)]
                      for s in [chess.square(file, rank)])
    return 'abertura' if board.fullmove_number <= 12 and undeveloped >= 4 else 'meio-jogo'


def describe(board):
    result = {'fase': phase(board), 'lados': {}}
    all_pawns = board.pieces(chess.PAWN, chess.WHITE) | board.pieces(chess.PAWN, chess.BLACK)
    result['colunas_abertas'] = [chess.FILE_NAMES[f] for f in range(8)
                                if not any(chess.square_file(s) == f for s in all_pawns)]
    for color, label in [(chess.WHITE, 'brancas'), (chess.BLACK, 'pretas')]:
        pieces = {NAMES[p]: [chess.square_name(s) for s in board.pieces(p, color)] for p in NAMES}
        king = board.king(color)
        zone = chess.SquareSet(chess.BB_KING_ATTACKS[king]) if king is not None else []
        pressure = [chess.square_name(s) for s in zone if board.is_attacked_by(not color, s)]
        result['lados'][label] = {'pecas': pieces, 'peoes': pawn_structure(board, color),
                                'casas_atacadas_perto_do_rei': pressure}
    return result


def strategic_context(board, snapshot=None):
    before = board.copy()
    move = before.pop() if before.move_stack else None
    after_facts = describe(board)
    context = {'antes': describe(before), 'depois': after_facts, 'mudancas': [], 'prioridades': [], 'historico': []}
    history = board.copy()
    for _ in range(min(8, len(history.move_stack))):
        previous_move = history.pop()
        context['historico'].append(history.san(previous_move))
    context['historico'].reverse()
    if board.is_game_over():
        context['prioridades'] = ['É xeque-mate; não há defesa legal.' if board.is_checkmate()
                                  else f'A partida terminou com resultado {board.result()}.']
        return context
    if not move:
        context['prioridades'] = [f'A posição está no {after_facts["fase"]}; compare a estrutura de peões e a atividade das peças dos dois lados.']
        return context
    mover = not board.turn
    own = 'brancas' if mover else 'pretas'
    piece = before.piece_at(move.from_square)
    target, origin = chess.square_name(move.to_square), chess.square_name(move.from_square)
    changes, priorities = context['mudancas'], context['prioridades']
    if board.is_check():
        priorities.append(f'{before.san(move)} dá xeque: o adversário precisa resolver o ataque ao rei antes de prosseguir com seu plano.')
    legal_captures = [m for m in board.legal_moves if board.is_capture(m)]
    hanging = []
    for capture in legal_captures:
        victim = board.piece_at(capture.to_square)
        if victim and victim.color == mover and not board.is_attacked_by(mover, capture.to_square):
            name = f'{NAMES[victim.piece_type]} em {chess.square_name(capture.to_square)}'
            if name not in hanging:
                hanging.append(name)
    if hanging:
        priorities.append('A resposta adversária pode capturar ' + ', '.join(hanging[:2]) +
                          ', sem defesa direta; é preciso verificar a compensação antes de manter o plano.')
    new_attacks = board.attacks(move.to_square) - before.attacks(move.from_square)
    targets = [f'{NAMES[p.piece_type]} de {chess.square_name(s)}' for s,p in board.piece_map().items()
               if p.color != mover and p.piece_type != chess.KING and s in new_attacks]
    if targets:
        priorities.append(f'A peça em {target} cria uma nova pressão sobre ' + ' e '.join(targets[:2]) +
                          '; essa é uma mudança concreta que o adversário deve considerar.')
    old_pawns = context['antes']['lados'][own]['peoes']
    new_pawns = after_facts['lados'][own]['peoes']
    for kind, label in [('isolados', 'isolados'), ('dobrados', 'dobrados')]:
        added = set(new_pawns[kind]) - set(old_pawns[kind])
        if added:
            changes.append(f'Os peões em {", ".join(sorted(added))} ficam {label}; a defesa com peças passa a merecer atenção.')
    if piece.piece_type == chess.PAWN and target in new_pawns['passados']:
        distance = 7-chess.square_rank(move.to_square) if mover else chess.square_rank(move.to_square)
        priorities.append(f'O peão passado em {target} está a {distance} casas da promoção; o plano passa por apoiar seu avanço e impedir o bloqueio.')
    new_files = set(after_facts['colunas_abertas']) - set(context['antes']['colunas_abertas'])
    if new_files:
        priorities.append(f'O lance abre a coluna {", ".join(sorted(new_files))}; compare quais torres conseguem ocupá-la e encontrar casas de entrada.')
    if piece.piece_type == chess.ROOK and chess.FILE_NAMES[chess.square_file(move.to_square)] in after_facts['colunas_abertas']:
        priorities.append(f'A torre em {target} ocupa uma coluna aberta, sem peões bloqueando a linha; procure uma casa de entrada que possa ser sustentada.')
    if context['antes']['fase'] != after_facts['fase']:
        priorities.append(f'A posição passa de {context["antes"]["fase"]} para {after_facts["fase"]}; as trocas mudam quais peças e peões devem orientar o plano.')
    if piece.piece_type == chess.KING and after_facts['fase'] == 'final' and not before.is_castling(move):
        priorities.append(f'No final, o rei em {target} participa da luta pelos peões; compare sua distância dos peões passados e das casas de bloqueio.')
    if before.is_castling(move):
        priorities.append(f'O roque reposiciona o rei em {target} e ativa a torre; a segurança depende agora das linhas e casas atacadas nesse setor.')
    if piece.piece_type == chess.PAWN and chess.square_file(move.to_square) in (3,4):
        blocked = board.piece_at(move.to_square + (8 if mover else -8)) if 0 <= move.to_square + (8 if mover else -8) < 64 else None
        priorities.append(f'O avanço para {target} muda a estrutura central: ' +
                          ('há um peão adversário bloqueando o avanço direto, então rupturas laterais ganham importância.'
                           if blocked and blocked.piece_type == chess.PAWN and blocked.color != mover else
                           'compare as trocas de peões disponíveis e as diagonais que elas podem abrir.'))
    if after_facts['fase'] == 'abertura' and piece.piece_type in (chess.KNIGHT,chess.BISHOP) and chess.square_rank(move.from_square) == (0 if mover else 7):
        priorities.append(f'O {NAMES[piece.piece_type]} deixa {origin} e entra no jogo em {target}; coordene as peças ainda na primeira fileira antes de iniciar operações mais longas.')
    if not priorities:
        priorities.append(f'A mudança central deste lance é a atividade do {NAMES[piece.piece_type]} em {target}; compare suas novas casas de ataque com a função defensiva que exercia em {origin}.')
    context['respostas_legais_de_captura'] = [board.san(m) for m in legal_captures[:8]]
    context['continuação_verificada'] = snapshot.get('steps', []) if snapshot else []
    return context
