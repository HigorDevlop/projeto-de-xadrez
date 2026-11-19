from dataclasses import replace
from io import StringIO

import chess
import chess.engine
import chess.pgn
import pytest

from book_study import BookStudy, explain_from_books
from chess_review import MoveReview, export_review
from move_evidence import build, facts, text
from tutor import Passage, load_passages


def position():
    board = chess.Board()
    board.push_san('e4')
    review = MoveReview(1, '1.', 'Brancas', 'e4', 'e2e4', 'good', 25, -35, None,
                        'd4', '1. e4 e5', [], '', .03, .55, .52,
                        engine_name='Stockfish local', best_line='1. d4 d5', position_fen=board.fen())
    return board, review


def test_three_sources_and_original_language_are_not_conflated(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Explicações não podem iniciar motor nem rede.')
    import requests
    monkeypatch.setattr(chess.engine.SimpleEngine, 'popen_uci', forbidden)
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    board, review = position()
    study = BookStudy([Passage('Meu livro, p. 7', 'Control the center and develop your pieces.')])
    explanation, refs = explain_from_books(board, study, review)
    assert all(label in explanation for label in ('Avaliação do motor:', 'Fatos verificáveis no tabuleiro:', 'Referências dos livros:'))
    assert 'Classificação do Coach Chess' in explanation and '-0.35' in explanation
    assert 'perspectiva das brancas' in explanation and '3.0 pontos percentuais' in explanation
    assert 'tema relacionado' in explanation and 'não é citação nem tradução' in explanation
    assert refs[0].quote == 'Control the center and develop your pieces.'
    assert refs[0].quote not in explanation and 'Meu livro, p. 7' in explanation
    assert 'não lê os livros' in explanation
    evidence = build(board, review, refs)
    assert all('Stockfish' not in line for line in evidence['facts'])
    assert any('peão de e2 para e4' in line for line in evidence['facts'])


def test_absent_books_irrelevant_books_and_no_engine():
    board, _ = position()
    empty, refs = explain_from_books(board, BookStudy())
    assert not refs and 'Nenhum livro com texto' in empty
    assert 'Avaliação do motor não disponível' in empty
    irrelevant, refs = explain_from_books(board, BookStudy([Passage('História', 'Uma cidade foi fundada.')]))
    assert not refs and 'Não foi encontrado trecho correspondente' in irrelevant
    assert 'Referência [1]' not in irrelevant


def test_exact_pgn_reference_and_wrong_position_rejected():
    passages, errors = load_passages((('aula.pgn', b'1. e4 {Control the center.} e5 {Challenge e4.} *'),))
    assert not errors
    board, review = position()
    refs = BookStudy(passages).references(board)
    assert refs[0].match == 'posição exata'
    assert 'posição exata' in text(build(board, review, refs))
    board.push_san('e5')
    evidence = build(board, review, refs)
    assert evidence['references'] == []
    assert 'não disponível' in ' '.join(evidence['engine'])
    assert 'outra posição omitida' in ' '.join(evidence['notices'])
    # Same move and ply are insufficient when the saved FEN differs.
    original, review = position()
    wrong = replace(review, position_fen=board.fen())
    assert 'não disponível' in ' '.join(build(original, wrong)['engine'])


@pytest.mark.parametrize('fen,uci,expected', [
    ('4k3/8/8/8/8/8/8/4K2R w K - 0 1', 'e1g1', 'roque legal'),
    ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6', 'en passant'),
    ('6k1/4P3/4K3/8/8/8/8/8 w - - 0 1', 'e7e8q', 'Promoção a dama'),
])
def test_observable_move_facts(fen, uci, expected):
    board = chess.Board(fen)
    assert chess.Move.from_uci(uci) in board.legal_moves
    board.push_uci(uci)
    result = ' '.join(facts(board))
    assert expected in result
    assert 'intenção' not in result and 'o foco' not in result


def test_terminal_and_mate_perspective():
    board = chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')
    assert board.is_stalemate()
    assert any('afogamento' in line for line in facts(board))
    board, review = position()
    result = build(board, replace(review, white_mate=-3))
    assert any('Mate calculado: -3' in line for line in result['engine'])
    result = build(board, position=dict(fen=board.fen(), engine_name='Local', cp=15, mate=None))
    assert '+0.15' in ' '.join(result['engine'])


def test_pgn_keeps_user_comments_eval_and_evidence_and_rejects_stale_review():
    game = chess.pgn.read_game(StringIO('1. e4 {Minha anotação.} (1. d4) *'))
    board, review = position()
    review.explanation, _ = explain_from_books(board, BookStudy(), review)
    exported = chess.pgn.read_game(StringIO(export_review(game, [review])))
    node = next(iter(exported.mainline()))
    assert 'Minha anotação.' in node.comment and len(exported.variations) == 2
    assert all(label in node.comment for label in ('Avaliação do motor:', 'Fatos verificáveis', 'Referências dos livros:'))
    assert node.eval().white().score() == -35
    stale = replace(review, position_fen=chess.STARTING_FEN)
    node = next(iter(chess.pgn.read_game(StringIO(export_review(game, [stale]))).mainline()))
    assert node.comment == 'Minha anotação.' and node.eval() is None


def test_ui_quotes_original_text_and_preserves_legacy_explanation():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string('''
import chess
from book_study import BookStudy
from tutor import Passage
from move_evidence import render
board = chess.Board(); board.push_san('e4')
refs = BookStudy([Passage('Livro em inglês, p. 2', 'Control the center.')]).references(board)
render(board, references=refs, legacy_text='Explicação antiga preservada.')
''').run()
    assert not app.exception
    assert any(item.value == 'Control the center.' for item in app.text)
    assert any('sem tradução automática' in item.value for item in app.caption)
    assert any(item.value == 'Explicação antiga preservada.' for item in app.text)
    assert any('Avaliação do motor não disponível' in item.value for item in app.markdown)


def test_archive_roundtrip_and_legacy_fields(tmp_path, monkeypatch):
    import json
    import classroom as rooms
    import analysis_archive as archive
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'evidence.sqlite3'))
    token = rooms.register_user('reader', 'reader-password-123')
    board, review = position()
    study = BookStudy([Passage('Livro, p. 3', 'Control the center.')])
    review.explanation, refs = explain_from_books(board, study, review)
    key = archive.save(token, '1. e4 *', dict(reviews={1: review}, explanations={1: review.explanation},
                                            references={1: refs}))
    saved = archive.load(token, key)
    assert saved['reviews'][1].position_fen == board.fen()
    assert saved['references'][1] == refs
    with rooms.database() as db:
        payload = json.loads(db.execute('SELECT payload FROM saved_analyses WHERE game=?', (key,)).fetchone()[0])
        payload['reviews']['1'].pop('position_fen')
        payload['references']['1'][0].pop('position')
        db.execute('UPDATE saved_analyses SET payload=? WHERE game=?', (json.dumps(payload), key))
    saved = archive.load(token, key)
    assert saved['reviews'][1].position_fen == ''
    assert saved['references'][1][0].position == ''
    evidence = build(board, saved['reviews'][1], saved['references'][1])
    assert evidence['references'] and any('Análise antiga' in note for note in evidence['notices'])
