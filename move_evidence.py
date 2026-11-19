"""Deterministic evidence presentation; no searches, network or generated prose."""
import chess
from chess_review import CATEGORIES, canonical_category, position_key
from tutor import PIECES, position_facts


def matches(board, review):
    if review.position_fen and review.position_fen != board.fen():
        return False
    return bool(board.move_stack and board.peek().uci() == review.uci
                and len(board.move_stack) == review.ply)


def facts(board):
    if not board.is_valid():
        return ['Posição inválida; não é possível afirmar fatos de jogo legal.']
    result = []
    if board.move_stack:
        before = board.copy()
        move = before.pop()
        if move in before.legal_moves:
            piece = before.piece_at(move.from_square)
            result.append(f'{before.san(move)}: {PIECES[piece.piece_type]} de '
                          f'{chess.square_name(move.from_square)} para {chess.square_name(move.to_square)}.')
            if before.is_castling(move):
                result.append('O lance é um roque legal nesta posição.')
            if before.is_capture(move):
                victim = chess.Piece(chess.PAWN, not piece.color) if before.is_en_passant(move) else before.piece_at(move.to_square)
                result.append(f'Captura de {PIECES[victim.piece_type]}' +
                              (' en passant.' if before.is_en_passant(move) else '.'))
            if move.promotion:
                result.append('Promoção a ' + PIECES[move.promotion] + '.')
    result.extend(position_facts(board))
    return result


def build(board, review=None, references=(), *, has_books=None, position=None):
    engine, books, notices, accepted = [], [], [], []
    if review and matches(board, review):
        engine.append('Fonte: ' + review.engine_name + '. O motor avalia posições; não lê os livros do usuário.')
        if review.white_mate is not None:
            engine.append(f'Mate calculado: {review.white_mate:+d}, na perspectiva das brancas.')
        elif review.white_cp is not None:
            engine.append(f'Avaliação após o lance: {review.white_cp/100:+.2f} peões, na perspectiva das brancas.')
        else:
            engine.append('Avaliação numérica não disponível nesta análise.')
        category = CATEGORIES.get(canonical_category(review.category))
        if category:
            engine.append(f'Classificação do Coach Chess a partir da análise: {category.label}.')
        if review.best_expected is not None and review.played_expected is not None:
            engine.append(f'Perda no indicador de chances: {review.expected_loss*100:.1f} pontos percentuais '
                          '(estimativa do método de análise, não certeza de resultado).')
        if review.best_san:
            engine.append('Melhor lance calculado antes da jogada: ' + review.best_san + '.')
        if review.best_line:
            engine.append('Continuação recomendada antes da jogada: ' + review.best_line + '.')
        if review.line:
            engine.append('Continuação a partir do lance jogado: ' + review.line + '.')
        engine.append('As continuações são calculadas, não respostas obrigatórias do adversário.')
        if not review.position_fen:
            notices.append('Análise antiga: vínculo pelo lance e índice; não há FEN de evidência salvo.')
        if review.sources:
            books.append('Linha catalogada (não é citação textual): ' + '; '.join(review.sources) + '.')
    elif position and position.get('fen') == board.fen():
        if position.get('result'):
            engine.append('Sem avaliação numérica do motor: posição encerrada pelas regras, resultado ' + position['result'] + '.')
        else:
            engine.append('Fonte: ' + position['engine_name'] + '; avaliação da posição, sem leitura dos livros.')
            if position.get('mate') is not None:
                engine.append(f"Mate calculado: {position['mate']:+d}, na perspectiva das brancas.")
            elif position.get('cp') is not None:
                engine.append(f"Avaliação: {position['cp']/100:+.2f} peões, na perspectiva das brancas.")
        if position.get('line'):
            engine.append('Continuação calculada, não obrigatória: ' + position['line'] + '.')
    else:
        engine.append('Avaliação do motor não disponível para esta posição.')
        if review or position:
            notices.append('A evidência do motor não pôde ser vinculada à posição atual; consulte o texto anterior, se houver.')
    for ref in references or ():
        if ref.position and ref.position != position_key(board):
            notices.append('Referência de outra posição omitida: ' + ref.source + '.')
            continue
        accepted.append(ref)
        number = len(accepted)
        topics = ', '.join(ref.topics) or 'a posição registrada'
        books.append(f'Referência [{number}] ({ref.source}): '
                     f'{ref.match}. Resumo temático do índice: {topics}; não é citação nem tradução.')
        if ref.match == 'tema relacionado':
            books.append('A correspondência é temática; não demonstra que o autor analisou este lance.')
        if not ref.position:
            notices.append('Referência antiga sem posição de vínculo salva: ' + ref.source + '.')
    if not accepted:
        books.append('Nenhum livro com texto foi carregado; nenhuma referência textual disponível.' if has_books is False
                     else 'Não foi encontrado trecho correspondente nos livros carregados.' if has_books
                     else 'Nenhuma referência textual disponível nesta análise; não há registro de trecho correspondente.')
    return dict(fen=board.fen(), engine=engine, facts=facts(board), books=books, references=accepted, notices=notices)


def text(evidence):
    return '\n\n'.join(label + ': ' + ' '.join(evidence[key]) for label, key in
                       [('Avaliação do motor', 'engine'), ('Fatos verificáveis no tabuleiro', 'facts'),
                        ('Referências dos livros', 'books')]) + (
                            '\n\nLimites da evidência: ' + ' '.join(evidence['notices']) if evidence['notices'] else '')


def render(board, review=None, references=(), *, position=None, legacy_text=''):
    import streamlit as st
    evidence = build(board, review, references, position=position)
    with st.expander('Explicação do lance · evidências'):
        for title, key in [('Avaliação do motor', 'engine'), ('Fatos verificáveis no tabuleiro', 'facts'),
                           ('Referências dos livros', 'books')]:
            st.markdown('**' + title + '**')
            for paragraph in evidence[key]:
                st.write(paragraph)
        for i, ref in enumerate(evidence['references'], 1):
            with st.expander(f'Trecho original [{i}] · {ref.source}'):
                st.caption('Citação no idioma original, sem tradução automática. Reticências podem indicar corte.')
                st.text(ref.quote or 'Esta referência não contém trecho textual.')
        st.caption('Fatos calculados localmente pelas regras do tabuleiro. Casas atacadas indicam ataques geométricos; '
                   'não provam ganho de material ou intenção do jogador.')
        for notice in evidence['notices']:
            st.caption(notice)
        if legacy_text and (not review or not review.position_fen):
            with st.expander('Texto anterior preservado · sem nova verificação de autoria'):
                st.text(legacy_text)
