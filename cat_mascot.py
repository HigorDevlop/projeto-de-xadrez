"""Mascote fotorrealista com quadros locais e movimentos no fundo da página."""
from pathlib import Path
import base64
import streamlit as st


_CAT = st.components.v2.component(
    'chess_cat_3d',
    html='<canvas class="cat" width="480" height="480" role="img" aria-label="Gato espia pela esquerda, aparece pela direita e se deita observando o tabuleiro"></canvas>',
    css='''
    .cat {position:fixed;width:230px;height:230px;z-index:20;pointer-events:none;display:none;
      filter:drop-shadow(0 5px 5px #0003)}
    ''',
    js=(Path(__file__).parent / 'assets/cat-photoreal.js').read_text(encoding='utf-8'),
)


@st.cache_data(max_entries=1, show_spinner=False)
def cat_atlas():
    return 'data:image/png;base64,' + base64.b64encode((Path(__file__).parent / 'assets/cat-photoreal-atlas.png').read_bytes()).decode()


def cat_mascot():
    _CAT(data={'atlas': cat_atlas()}, key='cat_mascot', height=0)
