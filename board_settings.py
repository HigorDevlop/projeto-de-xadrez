"""Local board preferences shared by every interactive board."""
import streamlit as st

SPEEDS = {'Sem animação': 0, 'Rápida': 110, 'Normal': 200, 'Suave': 350, 'Lenta': 550}
COLORS = {
    'Original': None,
    'Verde clássico': ('#F2EEDF', '#72977E', '#344D3D'),
    'Madeira': ('#EFDCBA', '#AF8B68', '#654A34'),
    'Azul': ('#E7EEF3', '#64839C', '#30495E'),
    'Grafite': ('#DADCDD', '#747B80', '#343A3F'),
    'Vinho': ('#F0E5DD', '#98646B', '#573B42'),
}
STYLES = ('Clássico', 'Plano', 'Relevo', 'Madeira')


def normalize(values):
    return {key: values.get(key) if values.get(key) in options else default
            for key, options, default in (
                ('board_speed', SPEEDS, 'Normal'),
                ('board_color', COLORS, 'Original'),
                ('board_style', STYLES, 'Clássico'))}


def current():
    choices = normalize(st.session_state)
    return {'duration': SPEEDS[choices['board_speed']],
            'colors': COLORS[choices['board_color']], 'style': choices['board_style']}


def render(saved, save):
    for key, value in normalize(saved).items():
        st.session_state.setdefault(key, value)

    def changed(key):
        st.session_state[key] = st.session_state['_setting_' + key]
        try:
            save(**{key: st.session_state[key]})
        except OSError:
            st.session_state.theme_save_error = 'Ajuste aplicado; não foi possível salvá-lo neste computador.'

    with st.popover('Aparência e movimento', icon=':material/palette:', width='stretch'):
        st.caption('Vale para os tabuleiros de jogo e treino.')
        for key, label, options in (
                ('board_speed', 'Velocidade das peças', SPEEDS),
                ('board_color', 'Cor do tabuleiro', COLORS),
                ('board_style', 'Acabamento do tabuleiro', STYLES)):
            widget = '_setting_' + key
            st.session_state[widget] = st.session_state[key]
            st.selectbox(label, list(options), key=widget, on_change=changed, args=(key,))
        st.caption('Sem animação move imediatamente. A velocidade não altera a análise nem o tempo do treino.')
