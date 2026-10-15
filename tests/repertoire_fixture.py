"""Local-only fixture for browser verification of closed repertoire training."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from presentation import apply_theme
from preparation_workspace import render_preparation

st.set_page_config(page_title='Repertórios', layout='wide')
dark = st.query_params.get('theme') == 'dark'
apply_theme(dark)
render_preparation([], 'browser-repertoire', '', dark)
