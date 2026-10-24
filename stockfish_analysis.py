"""UCI batch analysis; books are indexed before starting the selected engine."""
from concurrent.futures import CancelledError
import math
import os
from pathlib import Path
import shutil
import subprocess
from threading import Event, Lock

import chess
import chess.engine

from book_study import BookStudy, explain_from_books
from chess_review import BookIndex, MoveReview, classify, sacrifice_in_line


_ENGINE_LOCK = Lock()  # One engine process across sessions, to bound CPU/memory.
QUALITY = {'Rápida': (12, .08), 'Equilibrada': (18, .25), 'Profunda': (22, .7)}
ANALYSIS_VERSION = 4


def find_engine():
    configured = os.environ.get('STOCKFISH_PATH')
    if configured is not None:
        return configured if Path(configured).is_file() else ''
    folder = Path(__file__).resolve().parent / 'engines'
    for name in (('stockfish.exe',) if os.name == 'nt' else ('stockfish', 'stockfish-linux', 'stockfish-mac')):
        if (folder / name).is_file():
            return str(folder / name)
    return shutil.which('stockfish') or ''


def expected_points(info, color, ply):
    score = info['score'].pov(color)
    if score.is_mate():
        return 1.0 if score.score(mate_score=100000) > 0 else 0.0
    if 'wdl' in info:
        return info['wdl'].pov(color).expectation()
    return score.wdl(model='sf', ply=ply).expectation()


def check_cancelled(cancel):
    if cancel.is_set():
        raise CancelledError()


def review_chances(info, color):
    """Lichess's published CP-to-chances curve, not engine self-play WDL.

    https://lichess.org/page/accuracy ; deliberately separate from expected_points.
    This proxy is not a calibrated probability for a particular human rating.
    """
    score = info['score'].pov(color)
    if score.is_mate():
        return float(score.score(mate_score=100000) > 0)
    cp = max(-1000, min(1000, score.score()))
    return 1 / (1 + math.exp(-0.00368208 * cp))


def score_after_move(info, color):
    """Root scores count the winning mover's current move in mate distance."""
    score = info['score'].pov(color)
    mate = score.mate()
    if mate is not None and mate > 0:
        score = chess.engine.MateGiven if mate == 1 else chess.engine.Mate(mate - 1)
    return chess.engine.PovScore(score, color)


def compare_move(engine, board, move, limit, cancel):
    """Compare both roots in one MultiPV search; verify consequential losses."""
    def search(budget, roots=None):
        check_cancelled(cancel)
        options = {'root_moves': roots} if roots else {}
        return engine.analyse(board, budget, multipv=min(2, len(roots) if roots else board.legal_moves.count()), **options)

    candidates = search(limit)
    global_candidates = True
    best = candidates[0]
    played = next((info for info in candidates if info['pv'][0] == move), None)
    if played is None:
        candidates = search(limit, [best['pv'][0], move])
        global_candidates = False
        best = candidates[0]
        played = next(info for info in candidates if info['pv'][0] == move)
    loss = review_chances(best, board.turn) - review_chances(played, board.turn)
    sacrifice = sacrifice_in_line(board, played.get('pv', []))
    if loss >= .05 or sacrifice:
        # Both roots share the same depth/time budget. A full search is needed
        # for sacrifices so the alternative really is the second global choice.
        verification = chess.engine.Limit(depth=limit.depth + 2, time=max(.25, limit.time * 2))
        roots = None if sacrifice else list(dict.fromkeys([best['pv'][0], move]))
        candidates = search(verification, roots)
        global_candidates = roots is None
        best = candidates[0]
        played = next((info for info in candidates if info['pv'][0] == move), None)
        if played is None:
            candidates = search(verification, [best['pv'][0], move])
            global_candidates = False
            best = candidates[0]
            played = next(info for info in candidates if info['pv'][0] == move)
    second = review_chances(candidates[1], board.turn) if global_candidates and len(candidates) > 1 else None
    return best, played, second


def analyse_with_books(game, engine_path, rating=1500, book=None, study=None,
                       quality='Equilibrada', cancel=None, *, progress=None):
    if not engine_path or not Path(engine_path).is_file():
        raise ValueError('Motor de avaliação não encontrado. Selecione um motor instalado nas opções de análise.')
    moves = list(game.mainline_moves())
    report = progress or (lambda *args: None)
    total = max(1, len(moves))
    report(0, total, 'Preparando as posições')
    if len(moves) > 1000:
        raise ValueError('Analise até 1.000 meios-lances por partida.')
    book = book or BookIndex()
    study = study if isinstance(study, BookStudy) else BookStudy(study or ())
    cancel = cancel or Event()
    board = game.board()
    # Resolve source material for every position before any engine computation.
    initial_text, initial_refs = explain_from_books(board, study)
    references = {0: initial_refs}
    for ply, move in enumerate(moves, 1):
        check_cancelled(cancel)
        if move not in board.legal_moves or board.is_game_over():
            raise ValueError('A partida contém um lance ilegal ou após seu encerramento.')
        board.push(move)
        references[ply] = study.references(board)
    depth, seconds = QUALITY[quality]
    limit = chess.engine.Limit(depth=depth, time=seconds)
    reviews, explanations, position = {}, {0: initial_text}, None
    report(0, total, 'Aguardando o motor')
    while not _ENGINE_LOCK.acquire(timeout=.1):
        check_cancelled(cancel)
    try:
        check_cancelled(cancel)
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        with chess.engine.SimpleEngine.popen_uci(engine_path, timeout=15, **kwargs) as engine:
            engine_name = engine.id.get('name', 'Motor UCI')
            report(0, total, 'Iniciando a avaliação', engine_name)
            if 'MultiPV' not in engine.options:
                raise ValueError('O motor selecionado não oferece MultiPV, necessário para comparar os lances.')
            engine.configure({key: value for key, value in {'Threads': 1, 'Hash': 64}.items()
                              if key in engine.options})
            if 'UCI_ShowWDL' in engine.options:
                engine.configure({'UCI_ShowWDL': True})
            board = game.board()
            if not moves and board.is_game_over():
                position = {'engine_name': engine_name, 'cp': 0, 'mate': None,
                            'line': '', 'result': board.result()}
            if not moves and not board.is_game_over():
                info = engine.analyse(board, limit)
                explanations[0] += (f" {engine_name}: {review_chances(info, board.turn):.1%} no indicador de chances "
                                    f"para as {'brancas' if board.turn else 'pretas'}.")
                pv = info.get('pv', [])
                if pv:
                    explanations[0] += ' Continuação calculada: ' + board.variation_san(pv[:6]) + '.'
                white = info['score'].white()
                position = {'engine_name': engine_name, 'cp': white.score(), 'mate': white.mate(),
                            'line': board.variation_san(pv[:6]) if pv else ''}
            for ply, move in enumerate(moves, 1):
                check_cancelled(cancel)
                report(ply - 1, total, f'Avaliando o lance {ply} de {total}', engine_name)
                color = board.turn
                best, played, second = compare_move(engine, board, move, limit, cancel)
                best_move = best['pv'][0]
                check_cancelled(cancel)
                best_expected = review_chances(best, color)
                played_expected = review_chances(played, color)
                # Searches have bounded time and may disagree slightly. Never report a negative loss.
                best_expected = max(best_expected, played_expected)
                sources = book.sources(board, move)
                pv = played.get('pv', [move])
                category = classify(in_book=bool(sources), is_best=best_move == move,
                                    sacrifice=sacrifice_in_line(board, pv), rating=rating,
                                    best_expected=best_expected, played_expected=played_expected,
                                    second_expected=second)
                white = score_after_move(played, color).white()
                review = MoveReview(ply, f"{board.fullmove_number}{'.' if color else '...'}",
                                    'Brancas' if color else 'Pretas', board.san(move), move.uci(), category,
                                    max(0, best['score'].pov(color).score(mate_score=100000)
                                        - played['score'].pov(color).score(mate_score=100000)),
                                    white.score(mate_score=100000), white.mate(), board.san(best_move),
                                    board.variation_san(pv[:6]), sources, '',
                                    max(0, best_expected - played_expected), best_expected, played_expected,
                                    engine_name=engine_name)
                board.push(move)
                explanation, refs = explain_from_books(board, study, review, references[ply])
                review.explanation = explanation
                reviews[ply], explanations[ply], references[ply] = review, explanation, refs
                report(ply, total, 'Avaliando os lances', engine_name)
            check_cancelled(cancel)
            report(total, total, 'Análise concluída', engine_name)
    except (chess.engine.EngineError, OSError, TimeoutError) as error:
        raise ValueError('Não foi possível executar o motor selecionado. Confira o executável e tente novamente.') from error
    finally:
        _ENGINE_LOCK.release()
    return {'reviews': reviews, 'explanations': explanations, 'references': references,
            'engine_name': engine_name, 'position': position}
