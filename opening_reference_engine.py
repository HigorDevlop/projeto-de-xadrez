"""Small, real local evaluations for the reference lesson header."""
import os
import subprocess
import chess
import chess.engine
import streamlit as st
from stockfish_analysis import find_engine, _ENGINE_LOCK


@st.cache_data(show_spinner=False,max_entries=512,ttl=300)
def evaluation(fen):
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
