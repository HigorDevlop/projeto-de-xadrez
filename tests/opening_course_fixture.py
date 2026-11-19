"""Local fixture for the sidebar Openings page."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
import json
import os
from functools import wraps
import opening_course_ui
from opening_course_state import active_session
from opening_training_state import board_for

# Save protocol traces only in this isolated browser-test fixture.
if not getattr(opening_course_ui, '_fixture_traced', False):
    def trace(handler):
        @wraps(handler)
        def traced(plan, event, *args):
            session = active_session(plan)
            before = dict(revision=session['revision'], phase=session['phase'], fen=board_for(session).fen())
            result = handler(plan, event, *args)
            log = dict(handler=handler.__name__, event=event, before=before,
                       after=dict(revision=session['revision'], phase=session['phase'], feedback=session['feedback']))
            with (Path(os.environ['ACERVO_PREPARATION_DIR']) / 'protocol.jsonl').open('a', encoding='utf8') as output:
                output.write(json.dumps(log) + '\n')
            return result
        return traced
    opening_course_ui.receive_move = trace(opening_course_ui.receive_move)
    opening_course_ui.resync_board = trace(opening_course_ui.resync_board)
    opening_course_ui._fixture_traced = True
from presentation import apply_theme
from opening_practice import render_opening_practice
from datetime import UTC
st.set_page_config(page_title='Aberturas',layout='wide')
dark = st.query_params.get('theme') == 'dark'
apply_theme(dark)
st.session_state.fixture_runs = st.session_state.get('fixture_runs', 0) + 1
st.html(f'<span id="fixture-runs" data-runs="{st.session_state.fixture_runs}" hidden></span>')
showcase = st.query_params.get('showcase')
if showcase and not st.session_state.get('showcase_seeded'):
    from datetime import datetime, timezone
    from opening_course_state import select_course, ensure_course
    from preparation_state import today
    st.session_state.showcase_seeded = True
    plan = select_course(None, 'browser-openings', 'english')
    for progress in ensure_course(plan).values():
        progress['learned'] = True
    st.session_state.update(openings_owner='browser-openings', openings_plan=plan,
                            openings_active=False, openings_overlay=showcase)
    if showcase == 'profile':
        st.session_state.history_games = [dict(
            pgn=f'[White "browser-openings"]\n[Black "Opponent"]\n[Result "1-0"]\n[WhiteElo "{1250+i*30}"]\n[BlackElo "1300"]\n[Opening "Italian Game"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 1-0',
            end_time=int(datetime.now(UTC).timestamp()) - (1-i)*86400,
            url=f'https://example.test/game/{i}') for i in range(2)]
render_opening_practice('browser-openings',dark)
