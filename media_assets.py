"""Recursos dos exercícios, independentes da antiga abertura em vídeo."""
import base64
from pathlib import Path
import streamlit as st


@st.cache_data(max_entries=3, show_spinner=False)
def asset_source(path, modified):
    source = Path(path)
    mime = {'.webm': 'video/webm', '.mp4': 'video/mp4', '.png': 'image/png', '.jpg': 'image/jpeg'}[source.suffix.lower()]
    return f'data:{mime};base64,' + base64.b64encode(source.read_bytes()).decode()
