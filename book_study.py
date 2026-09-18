"""Index uploaded books before evaluating games, without a language model."""
from collections import defaultdict
from dataclasses import dataclass
import re
import unicodedata

import chess

from chess_review import CATEGORIES, position_key
from strategy import describe
from tutor import move_ideas, position_facts


TOPICS = {
    'centro': ('centro', 'central', 'center', 'centre'),
    'desenvolvimento': ('desenvolv', 'develop'),
    'roque': ('roque', 'castl'),
    'segurança do rei': ('seguranca do rei', 'king safety', 'ataque ao rei', 'king attack'),
    'coluna aberta': ('coluna aberta', 'colunas abertas', 'open file'),
    'peão isolado': ('peao isolado', 'peoes isolados', 'isolated pawn'),
    'peões dobrados': ('peoes dobrados', 'doubled pawn'),
    'peão passado': ('peao passado', 'peoes passados', 'passed pawn'),
    'final': ('final', 'endgame', 'oposicao', 'opposition'),
    'captura e troca': ('captur', 'troca', 'exchange', 'recaptur'),
    'xeque': ('xeque', 'check', 'mate'),
}


def folded(text):
    return unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode()


def passage_topics(text):
    text = folded(text)
    return {topic for topic, words in TOPICS.items()
            if any(re.search(r'\b' + re.escape(word), text) for word in words)}


def position_topics(board):
    facts = describe(board)
    topics = set()
    if facts['fase'] == 'final':
        topics.add('final')
    if facts['colunas_abertas']:
        topics.add('coluna aberta')
    for side in facts['lados'].values():
        for key, topic in [('isolados', 'peão isolado'), ('dobrados', 'peões dobrados'), ('passados', 'peão passado')]:
            if side['peoes'][key]:
                topics.add(topic)
        if side['casas_atacadas_perto_do_rei']:
            topics.add('segurança do rei')
    if board.is_check():
        topics.add('xeque')
    if board.move_stack:
        before = board.copy()
        move = before.pop()
        piece = before.piece_at(move.from_square)
        if before.is_castling(move):
            topics.update(('roque', 'segurança do rei'))
        if before.is_capture(move):
            topics.add('captura e troca')
        if piece.piece_type in (chess.KNIGHT, chess.BISHOP) and chess.square_rank(move.from_square) == (0 if piece.color else 7):
            topics.add('desenvolvimento')
        if move.to_square in (chess.D4, chess.E4, chess.D5, chess.E5) or any(
                square in board.attacks(move.to_square) for square in (chess.D4, chess.E4, chess.D5, chess.E5)):
            topics.add('centro')
    elif facts['fase'] == 'abertura':
        topics.update(('centro', 'desenvolvimento'))
    return topics


@dataclass(frozen=True)
class BookReference:
    source: str
    quote: str
    match: str
    topics: tuple[str, ...] = ()


class BookStudy:
    """One reusable inverted index for all uploaded passages, including late pages."""
    def __init__(self, passages=()):
        self.passages = tuple(passages)
        self.passage_topic_sets = tuple(passage_topics(passage.text) for passage in self.passages)
        self.positions = defaultdict(set)
        self.topics = defaultdict(set)
        for i, passage in enumerate(self.passages):
            if passage.position:
                self.positions[passage.position].add(i)
            else:
                for topic in self.passage_topic_sets[i]:
                    self.topics[topic].add(i)

    def references(self, board):
        relevant_topics = position_topics(board)
        exact = self.positions.get(position_key(board), set())
        candidates = set(exact)
        for topic in relevant_topics:
            candidates.update(self.topics.get(topic, ()))
        def score(i):
            return (i in exact, len(relevant_topics & self.passage_topic_sets[i]), -i)
        references = []
        for i in sorted(candidates, key=score, reverse=True)[:2]:
            passage = self.passages[i]
            # Quote a literal sentence from the matching portion, not an invented paraphrase.
            sentences = re.split(r'(?<=[.!?])\s+', passage.text.strip())
            sentence = max(sentences, key=lambda sentence: len(relevant_topics & passage_topics(sentence)))
            quote = sentence if len(sentence) <= 480 else sentence[:477].rsplit(' ', 1)[0] + '…'
            references.append(BookReference(passage.source, quote, 'posição exata' if i in exact else 'tema relacionado',
                                            tuple(sorted(relevant_topics & passage_topics(sentence)))))
        return references


def explain_from_books(board, study, review=None, references=None):
    refs = study.references(board) if references is None else references
    paragraphs = []
    if refs:
        for i, ref in enumerate(refs, 1):
            relation = 'Comentário desta posição' if ref.match == 'posição exata' else 'Princípio relacionado'
            paragraphs.append(f'{relation} [{i}] ({ref.source}): “{ref.quote}”')
    else:
        paragraphs.append('Não foi encontrado trecho correspondente nos livros carregados.' if study.passages
                          else 'Nenhum livro com texto foi carregado; esta explicação usa somente fatos do tabuleiro e o Stockfish.')
    if board.is_game_over():
        paragraphs.extend(position_facts(board))
    elif board.move_stack:
        before = board.copy()
        move = before.pop()
        details = move_ideas(before, move)
        paragraphs.append('Nesta partida: ' + '. '.join(text.rstrip('.') for text in details['facts'][:2]) + '.')
        topics = sorted({topic for ref in refs if ref.match == 'tema relacionado' for topic in ref.topics})
        if topics:
            paragraphs.append('A relação com o material é temática (' + ', '.join(topics) + '); a variante concreta é verificada pelo Stockfish.')
    else:
        paragraphs.extend(position_facts(board)[:2])
    if review:
        paragraphs.append(f'Pela avaliação do Stockfish, {review.san} é classificado como {CATEGORIES[review.category].label}, '
                          f'com perda de {review.expected_loss:.1%} dos pontos esperados.')
        if not board.is_game_over() and review.line:
            paragraphs.append(f'Continuação calculada a partir do lance jogado: {review.line}.')
        if review.uci and review.best_san != review.san:
            paragraphs.append(f'A melhor alternativa calculada antes do lance era {review.best_san}.')
        if review.sources:
            paragraphs.append('Linha catalogada em: ' + '; '.join(review.sources[:2]) + '.')
    return ' '.join(paragraphs), refs
