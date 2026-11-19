import json
from streamlit.testing.v1 import AppTest
from board_settings import normalize


def test_board_settings_save_and_restore(tmp_path):
    storage = tmp_path / 'appearance.json'
    storage.write_text(json.dumps({'show_table': False}), encoding='utf-8')
    script = f'''
import json
from pathlib import Path
from board_settings import render, current
import streamlit as st
path=Path({str(storage)!r})
saved=json.loads(path.read_text())
def save(**changes):
    value=json.loads(path.read_text());value.update(changes)
    path.write_text(json.dumps(value))
render(saved,save)
st.json(current())
'''
    app = AppTest.from_string(script).run()
    for label, value in [('Velocidade das peças', 'Sem animação'), ('Cor do tabuleiro', 'Azul'), ('Acabamento do tabuleiro', 'Relevo')]:
        next(widget for widget in app.selectbox if widget.label == label).select(value).run()
    assert not app.exception
    value=json.loads(storage.read_text())
    assert value == {'show_table':False,'board_speed':'Sem animação','board_color':'Azul','board_style':'Relevo'}
    restored=AppTest.from_string(script).run()
    assert [widget.value for widget in restored.selectbox] == ['Sem animação','Azul','Relevo']
    assert normalize({'board_speed':'broken'})['board_speed']=='Normal'
