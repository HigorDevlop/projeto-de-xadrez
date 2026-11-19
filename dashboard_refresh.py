"""Refresh dashboard reports only after a saved result actually changes."""
import streamlit as st


def fingerprint(records):
    from performance_dashboard import quality_key,_quality_path
    from dashboard_auto_analysis import _path as quality_path
    from game_phase_diagnostics import _path as diagnostic_path
    values=[]
    for record in records:
        key=quality_key(record['game']);side=record['side']
        for path in (_quality_path(key),quality_path(key,side),diagnostic_path(key,side)):
            try:stat=path.stat();values.append((str(path),stat.st_mtime_ns,stat.st_size))
            except OSError:values.append((str(path),None,None))
    return tuple(values)


def watch_reports(history,username,days,auto):
    from preparation_state import today
    from dashboard_auto_analysis import ensure,records_for
    records=records_for(history,username,today(),days)
    baseline=fingerprint(records)
    @st.fragment(run_every='5s')
    def check():
        if auto:ensure(history,username,days)
        if fingerprint(records)!=baseline:st.rerun(scope='app')
    check()


def render_queue(records):
    """The timer updates a single placeholder, never the surrounding charts."""
    from dashboard_auto_analysis import queue
    slot=st.empty();previous=[None]
    @st.fragment(run_every='2s')
    def check():
        status=queue().status(records)
        if status==previous[0]:return
        previous[0]=status
        current=status['current']
        if not current and not status['queued'] and not status['errors']:
            slot.empty();return
        with slot.container():
            if current:
                st.caption(f'Stockfish · {current["done"]}/{current["total"]} lances · {status["queued"]} partidas na fila')
                st.progress(current['done']/max(1,current['total']))
            elif status['queued']:st.caption(f'{status["queued"]} partidas aguardando análise automática.')
            if status['errors']:st.caption('Uma análise será tentada novamente automaticamente. Os resultados salvos foram preservados.')
    check()
