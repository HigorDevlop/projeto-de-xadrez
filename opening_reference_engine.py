"""Small, real local evaluations for the reference lesson header."""
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from threading import Lock
import chess
import chess.engine
import streamlit as st
from stockfish_analysis import find_engine, _ENGINE_LOCK


def _calculate(fen):
    path = find_engine()
    if not path or not _ENGINE_LOCK.acquire(blocking=False):
        return None
    try:
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        with chess.engine.SimpleEngine.popen_uci(path,timeout=3,**kwargs) as engine:
            engine.configure({'Threads':1,'Hash':16})
            score=engine.analyse(chess.Board(fen),chess.engine.Limit(time=.04))['score'].white()
            return f'#{score.mate()}' if score.is_mate() else f'{score.score()/100:+.2f}'
    except (OSError,chess.engine.EngineError,TimeoutError):
        return None
    finally:
        _ENGINE_LOCK.release()


class Evaluations:
    """Bound the engine work; drawing or moving pieces never waits for it."""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='opening-evaluation')
        self.jobs = OrderedDict()
        self.lock = Lock()

    def get(self, fen):
        with self.lock:
            job = self.jobs.get(fen)
            if job is None:
                # Keep the running evaluation and the latest requested board.
                # Older queued positions are obsolete once the learner moves.
                for key, old in list(self.jobs.items()):
                    if not old.done() and old.cancel():
                        del self.jobs[key]
                job = self.executor.submit(_calculate, fen)
                self.jobs[fen] = job
                while len(self.jobs) > 512:
                    self.jobs.popitem(last=False)
            if not job.done():
                return None
            return job.result()


@st.cache_resource(show_spinner=False)
def _evaluations():
    return Evaluations()


def evaluation(fen):
    return _evaluations().get(fen)
