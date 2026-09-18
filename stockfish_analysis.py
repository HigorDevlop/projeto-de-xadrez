"""Stockfish-only batch analysis; books are indexed before starting the engine."""
from concurrent.futures import CancelledError
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


def analyse_with_books(game, engine_path, rating=1500, book=None, study=None,
                       quality='Equilibrada', cancel=None):
    if not engine_path or not Path(engine_path).is_file():
        raise ValueError('Stockfish não encontrado. Configure STOCKFISH_PATH ou instale em engines/.')
    moves = list(game.mainline_moves())
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
    reviews, explanations = {}, {0: initial_text}
    while not _ENGINE_LOCK.acquire(timeout=.1):
        check_cancelled(cancel)
    try:
        check_cancelled(cancel)
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        with chess.engine.SimpleEngine.popen_uci(engine_path, timeout=15, **kwargs) as engine:
            if 'Stockfish' not in engine.id.get('name', ''):
                raise ValueError('O executável configurado deve ser o Stockfish.')
            engine.configure({'Threads': 1, 'Hash': 64})
            if 'UCI_ShowWDL' in engine.options:
                engine.configure({'UCI_ShowWDL': True})
            board = game.board()
            if not moves and not board.is_game_over():
                info = engine.analyse(board, limit)
                explanations[0] += (f" Stockfish: {expected_points(info, board.turn, board.ply()):.1%} de pontos esperados "
                                    f"para as {'brancas' if board.turn else 'pretas'}.")
                pv = info.get('pv', [])
                if pv:
                    explanations[0] += ' Continuação calculada: ' + board.variation_san(pv[:6]) + '.'
            for ply, move in enumerate(moves, 1):
                check_cancelled(cancel)
                color = board.turn
                candidates = engine.analyse(board, limit, multipv=min(2, board.legal_moves.count()))
                best = candidates[0]
                best_move = best['pv'][0]
                check_cancelled(cancel)
                played = best if best_move == move else engine.analyse(board, limit, root_moves=[move])
                best_expected = expected_points(best, color, board.ply())
                played_expected = expected_points(played, color, board.ply())
                # Searches have bounded time and may disagree slightly. Never report a negative loss.
                best_expected = max(best_expected, played_expected)
                second = expected_points(candidates[1], color, board.ply()) if len(candidates) > 1 else None
                sources = book.sources(board, move)
                pv = played.get('pv', [move])
                category = classify(in_book=bool(sources), is_best=best_move == move,
                                    sacrifice=sacrifice_in_line(board, pv), rating=rating,
                                    best_expected=best_expected, played_expected=played_expected,
                                    second_expected=second)
                white = played['score'].white()
                review = MoveReview(ply, f"{board.fullmove_number}{'.' if color else '...'}",
                                    'Brancas' if color else 'Pretas', board.san(move), move.uci(), category,
                                    max(0, best['score'].pov(color).score(mate_score=100000)
                                        - played['score'].pov(color).score(mate_score=100000)),
                                    white.score(mate_score=100000), white.mate(), board.san(best_move),
                                    board.variation_san(pv[:6]), sources, '',
                                    max(0, best_expected - played_expected), best_expected, played_expected)
                board.push(move)
                explanation, refs = explain_from_books(board, study, review, references[ply])
                review.explanation = explanation
                reviews[ply], explanations[ply], references[ply] = review, explanation, refs
            check_cancelled(cancel)
    except (chess.engine.EngineError, OSError, TimeoutError) as error:
        raise ValueError('Não foi possível executar o Stockfish. Confira o executável e tente novamente.') from error
    finally:
        _ENGINE_LOCK.release()
    return {'reviews': reviews, 'explanations': explanations, 'references': references}
