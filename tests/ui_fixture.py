"""Deterministic browser fixtures; never used by the normal app launcher."""
from hashlib import sha256
from pathlib import Path
import runpy
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chess_review import MoveReview
from tactics import parse_puzzle

fixture = st.query_params.get('fixture')
if fixture and st.session_state.get('_fixture') != fixture:
    st.session_state._fixture = fixture
    st.session_state.engine_path = ''
    st.session_state.auto_classify = False
    if fixture == 'brilliant':
        st.session_state.game = '1. e4 *'
        st.session_state.ply = 1
        st.session_state.analysis_signature = (sha256(repr(()).encode()).hexdigest(), 40, '', 'Equilibrada')
        st.session_state.reviews = {1: MoveReview(1, '1.', 'Brancas', 'e4', 'e2e4', 'brilliant',
                                                0, 10, None, 'e4', '', [], 'Fixture')}
    elif fixture == 'tactic':
        st.session_state.main_view = st.session_state.active_tab = 'Tático'
        st.session_state.puzzle = parse_puzzle({'game': {'pgn': '1. f3 e5 2. g4 *'},
            'puzzle': {'id': 'fixture', 'initialPly': 2, 'rating': 800,
                       'themes': ['mateIn1'], 'solution': ['d8h4']}})

runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
