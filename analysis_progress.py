"""Thread-safe engine progress and a centered, nonblocking progress panel."""
from dataclasses import dataclass, replace
from threading import Lock

import streamlit as st


@dataclass(frozen=True)
class ProgressSnapshot:
    completed: int = 0
    total: int = 0
    phase: str = 'Preparando a análise'
    engine: str = ''

    @property
    def fraction(self):
        return self.completed / self.total if self.total else 0.0


class AnalysisProgress:
    """Workers publish immutable snapshots; only the UI calls Streamlit."""
    def __init__(self, engine=''):
        self._lock = Lock()
        self._snapshot = ProgressSnapshot(engine=engine)

    def update(self, completed, total, phase, engine=None):
        with self._lock:
            total = max(0, int(total))
            self._snapshot = replace(self._snapshot, total=total,
                                     completed=max(0, min(total, int(completed))),
                                     phase=phase, engine=engine or self._snapshot.engine)

    def snapshot(self):
        with self._lock:
            return self._snapshot


def render_progress(snapshot):
    st.html('''<style>
    .st-key-analysis_progress_overlay{
      position:fixed!important;left:50%!important;top:50%!important;
      transform:translate(-50%,-50%);z-index:1000002;
      width:min(480px,calc(100vw - 32px))!important;max-height:80dvh;overflow:auto;
      padding:24px!important;border:1px solid #48433b!important;border-radius:18px!important;
      background:linear-gradient(145deg,#292722,#171818)!important;
      box-shadow:0 24px 80px #000b,inset 0 1px 0 #ffffff12;
      opacity:1!important;color:#f5f5f5}
    .st-key-analysis_progress_overlay [data-stale="true"]{opacity:1!important}
    .st-key-analysis_progress_overlay h3{font-size:22px!important;margin:0!important}
    .st-key-analysis_progress_overlay [role="progressbar"]{border-radius:8px}
    </style>''')
    with st.container(border=True, key='analysis_progress_overlay', gap='small'):
        st.subheader('Analisando sua partida', anchor=False)
        st.caption(snapshot.engine)
        percent = round(snapshot.fraction * 100)
        st.progress(snapshot.fraction, text=f'{percent}% · {snapshot.phase}')
        if snapshot.total:
            st.caption(f'{snapshot.completed} de {snapshot.total} '
                       + ('lance avaliado' if snapshot.total == 1 else 'lances avaliados'))
        st.caption('Você pode continuar explorando o tabuleiro.')
