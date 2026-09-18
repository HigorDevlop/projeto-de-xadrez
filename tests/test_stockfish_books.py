from hashlib import sha256
from io import BytesIO, StringIO
import json
import sys
from pathlib import Path
from unittest.mock import patch

import chess
import chess.pgn
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from chess_review import BookIndex, classify, export_review, player_accuracy, sacrifice_in_line
from stockfish_analysis import analyse_with_books, find_engine, expected_points
from book_study import BookStudy, explain_from_books
from tutor import Passage


def test_books_are_indexed_beyond_first_thirty_passages():
    passages = [Passage(f'outro{i}.txt', 'Uma frase sem tema enxadrístico reconhecido.') for i in range(45)]
    passages.append(Passage('Livro de abertura, p. 46', 'Develop your pieces and control the center.'))
    study = BookStudy(passages)
    board = chess.Board()
    board.push_san('e4')
    text, refs = explain_from_books(board, study)
    assert refs[0].source == 'Livro de abertura, p. 46'
    assert refs[0].quote == 'Develop your pieces and control the center.'
    assert refs[0].quote in text and refs[0].source in text
    assert 'e4' in text


def test_pgn_comments_require_exact_position_and_take_priority():
    from tutor import load_passages
    passages, errors = load_passages((('livro.pgn', b'1. e4 {Control the center.} e5 {Challenge e4.} *'),))
    assert not errors
    study = BookStudy([Passage('geral.txt', 'Central control and development.')]+passages)
    board = chess.Board()
    board.push_san('e4')
    refs = study.references(board)
    assert refs[0].match == 'posição exata' and refs[0].quote == 'Control the center.'
    assert all(ref.quote != 'Challenge e4.' for ref in refs)
    board.push_san('e5')
    assert study.references(board)[0].quote == 'Challenge e4.'


def test_unrelated_book_does_not_produce_a_fabricated_citation():
    study = BookStudy([Passage('irrelevante.txt', 'Esta passagem descreve a história de uma cidade.')])
    board = chess.Board()
    board.push_san('e4')
    text, refs = explain_from_books(board, study)
    assert not refs and '[1]' not in text
    assert 'Não foi encontrado trecho correspondente' in text
    assert 'Nenhum livro com texto' in explain_from_books(board, BookStudy())[0]


def test_wdl_is_from_movers_perspective_and_mate_is_exact():
    import chess.engine
    info = {'score': chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE),
            'wdl': chess.engine.PovWdl(chess.engine.Wdl(600, 300, 100), chess.WHITE)}
    assert expected_points(info, chess.WHITE, 10) == .75
    assert expected_points(info, chess.BLACK, 10) == .25
    mate = {'score': chess.engine.PovScore(chess.engine.Mate(3), chess.BLACK)}
    assert expected_points(mate, chess.BLACK, 10) == 1
    assert expected_points(mate, chess.WHITE, 10) == 0


def test_cancelled_job_does_not_launch_engine():
    from concurrent.futures import CancelledError
    from threading import Event
    cancel = Event()
    cancel.set()
    game, _ = example()
    with patch('stockfish_analysis.Path.is_file', return_value=True), patch('chess.engine.SimpleEngine.popen_uci') as launch:
        with pytest.raises(CancelledError):
            analyse_with_books(game, 'stockfish', cancel=cancel)
        launch.assert_not_called()


def test_engine_starts_only_after_all_book_positions_are_prepared():
    import chess.engine
    game, _ = example()
    study = BookStudy([Passage('aula.txt', 'Desenvolvimento e controle do centro.')])
    original = study.references
    with patch.object(study, 'references', wraps=original) as lookup:
        def launch(*args, **kwargs):
            assert lookup.call_count == 4
            raise chess.engine.EngineError('expected failure')
        with patch('stockfish_analysis.Path.is_file', return_value=True), patch('chess.engine.SimpleEngine.popen_uci', side_effect=launch):
            with pytest.raises(ValueError, match='executar o Stockfish'):
                analyse_with_books(game, 'stockfish', study=study)


@pytest.mark.skipif(not find_engine(), reason='Stockfish not installed')
def test_real_stockfish_preloads_book_citations_and_exports_evaluations():
    from tutor import load_passages
    game, _ = example()
    passages, _ = load_passages((('livro.pgn', b'1. e4 {Control the center.} e5 2. Nf3 {Develop the knight.} *'),))
    result = analyse_with_books(game, find_engine(), study=BookStudy(passages), quality='Rápida')
    assert set(result['explanations']) == {0, 1, 2, 3}
    assert result['references'][1][0].quote == 'Control the center.'
    assert result['references'][3][0].quote == 'Develop the knight.'
    assert 'Develop the knight.' in result['explanations'][3]
    assert all(0 <= review.played_expected <= review.best_expected <= 1 for review in result['reviews'].values())
    exported = chess.pgn.read_game(StringIO(export_review(game, list(result['reviews'].values()))))
    assert list(exported.mainline())[2].eval() is not None
    assert 'livro.pgn' in list(exported.mainline())[2].comment

ROOT = Path(__file__).resolve().parents[1]


def example(pgn='1. e4 e5 2. Nf3 *'):
    game = chess.pgn.read_game(StringIO(pgn))
    return game, {'reviews': {}, 'explanations': {0: 'Posição inicial.',
        1: 'Texto do livro para e4.', 2: 'Texto do livro para e5.', 3: 'Texto do livro para Nf3.'},
        'references': {}}


def test_rating_adjusts_only_productive_sacrifice_tolerance():
    args = dict(in_book=False, is_best=False, sacrifice=True, best_expected=.7,
                played_expected=.685, second_expected=.65)
    assert classify(**args, rating=800) == 'brilliant'
    assert classify(**args, rating=2400) == 'excellent'
    assert classify(**{**args, 'sacrifice': False}, rating=800) == 'excellent'
    assert classify(**{**args, 'played_expected': .3}, rating=800) == 'blunder'
    assert classify(**{**args, 'sacrifice': False, 'played_expected': .7, 'second_expected': .5}) == 'great'


def test_pawn_offer_is_not_a_brilliant_piece_sacrifice():
    board = chess.Board()
    pv = []
    for san in ['e4', 'd5', 'Nf3', 'dxe4', 'Nc3', 'Nf6', 'Bc4']:
        pv.append(board.parse_san(san))
        board.push(pv[-1])
    assert not sacrifice_in_line(chess.Board(), pv)


def test_piece_sacrifice_requires_sustained_material_loss():
    board = chess.Board('6k1/8/7p/8/4N3/8/8/R3K3 w - - 0 1')
    pv = [chess.Move.from_uci(uci) for uci in ['e4g5', 'h6g5', 'a1a2', 'g5g4', 'a2a3']]
    assert not sacrifice_in_line(board, pv[:3])
    assert sacrifice_in_line(board, pv)


@pytest.fixture
def app_environment(tmp_path, monkeypatch):
    st.cache_resource.clear()
    monkeypatch.setenv('ACERVO_USER_PREFERENCE', str(tmp_path / 'user.json'))
    monkeypatch.setattr('stockfish_analysis.find_engine', lambda: 'stockfish-test')
    for module in ('interactive_board', 'profile_avatar'):
        sys.modules.pop(module, None)


def drain(at):
    for _, future in list(at.session_state.jobs.values()):
        future.result(timeout=5)
    at.run(timeout=30)
    assert not at.exception


def test_clicking_pgn_moves_uses_single_preloaded_batch(app_environment):
    game, payload = example()
    with patch('stockfish_analysis.analyse_with_books', return_value=payload) as request:
        at = AppTest.from_file(str(ROOT / 'app.py'))
        at.session_state.game = str(game)
        at.run(timeout=30)
        drain(at)
        for ply in [3, 1, 2, 3, 1]:
            at.button(key=f'panel_{ply}').click().run(timeout=30)
            assert not at.exception
            assert at.session_state.ply == ply
            assert payload['explanations'][ply] in at.session_state.last_explanation
        assert request.call_count == 1


def test_changing_uploaded_books_rebuilds_explanations(app_environment):
    game, payload = example()
    def analyse(*args):
        study = args[4]
        board = game.board()
        board.push_san('e4')
        text, refs = explain_from_books(board, study)
        return {'reviews': {}, 'explanations': {0: 'Inicial.', 1: text}, 'references': {1: refs}}
    with patch('stockfish_analysis.analyse_with_books', side_effect=analyse) as evaluate:
        at = AppTest.from_file(str(ROOT / 'app.py'))
        at.session_state.game = str(game)
        at.session_state.study_files = (('primeiro.txt', b'Control the center and develop your pieces.'),)
        at.run(timeout=30)
        drain(at)
        at.button(key='panel_1').click().run(timeout=30)
        assert 'primeiro.txt' in at.session_state.last_explanation
        at.session_state.study_files = (('segundo.txt', b'Central control gives your pieces room to develop.'),)
        at.run(timeout=30)
        drain(at)
        assert 'segundo.txt' in at.session_state.last_explanation
        assert 'primeiro.txt' not in at.session_state.last_explanation
        assert evaluate.call_count == 2


def test_late_response_cannot_replace_another_game(app_environment):
    from concurrent.futures import Future
    game, payload = example()
    at = AppTest.from_file(str(ROOT / 'app.py'))
    at.session_state.game = str(game)
    original = Future()
    replacement = Future()
    class Pool:
        def __init__(self):
            self.calls = 0
        def submit(self, *args):
            self.calls += 1
            return original if self.calls == 1 else replacement
    with patch('concurrent.futures.ThreadPoolExecutor', return_value=Pool()):
        at.run(timeout=30)
        old_key = at.session_state.jobs['full'][0]
        assert at.session_state.jobs['full'][1] is original
        original.set_running_or_notify_cancel()
        at.button(key='panel_1').click().run(timeout=30)
        next(b for b in at.button if b.label == 'Nova partida · jogar livremente').click().run(timeout=30)
        original.set_result(payload)
        at.run(timeout=30)
        assert not at.exception
        assert at.session_state.explanations == {}
        assert at.session_state.jobs['full'][0] != old_key


def test_tactics_load_automatically_and_restart_without_network(app_environment, monkeypatch):
    from tactics import parse_puzzle
    monkeypatch.setattr('stockfish_analysis.find_engine', lambda: '')
    puzzle = parse_puzzle({'game': {'pgn': '1. f3 e5 2. g4 *'},
                          'puzzle': {'id': 'test1', 'initialPly': 2, 'rating': 800,
                                     'themes': ['mateIn1'], 'solution': ['d8h4']}})
    with patch('tactics.fetch_puzzle_range', return_value=puzzle) as fetch:
        at = AppTest.from_file(str(ROOT / 'app.py'))
        at.session_state.main_view = 'Tático'
        at.run(timeout=30)
        assert not at.exception
        # AppTest cannot switch to callable Pages by path; persist their registered hash.
        from streamlit.util import calc_hash
        at._page_hash = calc_hash('tatico')
        assert len([button for button in at.button if button.key.startswith('theme_')]) == 12
        at.button(key='theme_mateIn1').click().run(timeout=30)
        assert not at.get('select_slider')
        at.selectbox(key='rating_min').set_value(700).run(timeout=30)
        assert not fetch.called
        at.selectbox(key='rating_max').set_value(900).run(timeout=30)
        drain(at)
        assert at.session_state.puzzle.id == puzzle.id
        original_game = at.session_state.game
        for _ in range(3):
            at.session_state.puzzle_progress = 1
            at.session_state.puzzle_message = 'Tático resolvido!'
            revision = at.session_state.puzzle_revision
            next(b for b in at.button if b.label == 'Recomeçar tático').click().run(timeout=30)
            assert not at.exception
            assert at.session_state.puzzle_progress == 0
            assert at.session_state.puzzle_message == ''
            assert at.session_state.puzzle_revision > revision
        assert fetch.call_count == 1
        assert at.session_state.game == original_game
