from time import perf_counter

import chess
import pytest

from quick_question import answer_question


@pytest.mark.parametrize('question,expected', [
    ('Posso jogar e4?', 'e4 é legal'),
    ('Posso jogar e5?', 'não é um lance legal'),
    ('Posso jogar Nf3?', 'Nf3 é legal'),
    ('Qual é o material?', 'material está equilibrado'),
    ('Posso rocar?', 'Não há roque legal'),
    ('O que há em e2?', 'peão das brancas'),
    ('Quais são as ameaças?', 'Não há captura legal'),
])
def test_position_specific_answers_finish_within_five_seconds(question, expected):
    board = chess.Board()
    fen = board.fen()
    started = perf_counter()
    assert expected in answer_question(question, board)
    assert perf_counter() - started < 5
    assert board.fen() == fen


def test_mate_invalid_position_and_side_to_move():
    assert 'inválida' in answer_question('O que jogar?', chess.Board(None))
    board = chess.Board()
    board.push_san('e4')
    assert 'Com e4' in answer_question('Por que e4?', board)
    assert 'e5 é legal para as pretas' in answer_question('Posso jogar e5?', board)
    assert 'não é um lance legal' in answer_question('Posso jogar Nf3?', board)
    board = chess.Board()
    for move in ['f3', 'e5', 'g4', 'Qh4#']:
        board.push_san(move)
    assert 'Xeque-mate' in answer_question('Qual o melhor lance?', board)
