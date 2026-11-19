"""Authenticated browser fixture; storage is provided in a temporary directory."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
import classroom as rooms
from opening_practice import render_opening_practice

st.set_page_config(layout='wide')
if not st.session_state.get('classroom_token'):
    st.session_state.classroom_token = rooms.login_user('endgame-browser', 'endgame-browser-password')
render_opening_practice('endgame-browser', True)
