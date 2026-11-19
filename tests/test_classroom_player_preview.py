import hashlib
import json
import streamlit as st
from streamlit.testing.v1 import AppTest
import classroom_materials as materials
from test_classroom_tactic_blocks import pack


def test_catalog_filters_courses_and_recovers_stale_choice_when_side_changes():
    script='''
from classroom_trail_inputs import content_inputs
import streamlit as st
payload=content_inputs(None,None,'side_test','line','')
st.json(payload)
'''
    white=AppTest.from_string(script)
    white.session_state['side_test_side_line']='white'
    white.run(timeout=20)
    assert not white.exception
    black=AppTest.from_string(script)
    black.session_state['side_test_side_line']='black'
    black.run(timeout=20)
    assert not black.exception
    first=json.loads(white.json[0].value);second=json.loads(black.json[0].value)
    assert first['side']=='white' and second['side']=='black'
    from opening_repertoires import catalog
    assert white.selectbox[0].options==[course['title'] for course in catalog() if course['side']=='white']
    assert black.selectbox[0].options==[course['title'] for course in catalog() if course['side']=='black']
    assert black.session_state['side_test_course']=='caro'
    black=AppTest.from_string(script)
    black.session_state['side_test_side_line']='black'
    black.session_state['side_test_course']='italian'
    black.run(timeout=20)
    assert not black.exception
    assert black.session_state['side_test_course']=='italian_black'
    assert json.loads(black.json[0].value)['side']=='black'


def test_private_stage_preview_requires_approved_tactics_before_next_activity():
    payload=materials.validate('tactic',pack(2))
    step=dict(items=[dict(id='pack',title='Exercícios',kind='tactic',payload=payload,reviewed=True),
                     dict(id='note',title='Próxima aula',kind='note',payload=dict(text='Liberado'),reviewed=True)])
    script='''
import streamlit as st
from classroom_training_preview import render_step_preview
render_step_preview(None,None,st.session_state['stage'],'preview_test')
'''
    app=AppTest.from_string(script)
    app.session_state['stage']=step
    app.run(timeout=20)
    assert not app.exception
    assert len(app.selectbox[0].options)==1
    from classroom_tactic_blocks import initial
    app.session_state['preview_test_pack_block_state']=initial(passed=True)
    app.run(timeout=20)
    assert len(app.selectbox[0].options)==2
    # Changing the pack invalidates an old private approval.
    app.session_state['preview_test_pack_block_source']='old-payload'
    app.run(timeout=20)
    assert len(app.selectbox[0].options)==1


def test_closed_question_uses_separate_fields_and_preserves_saved_answer():
    app=AppTest.from_string("""
import streamlit as st
from classroom_trail_inputs import content_inputs
from classroom_trail_editor import _seed
_seed('exam',dict(title='Prova',payload=dict(questions=[dict(kind='closed',prompt='Quem joga em L?',options=['Bispo','Cavalo'],answer=1,weight=1)])))
st.json(content_inputs(None,None,'exam','exam',''))
""")
    app.run(timeout=20)
    assert not app.exception
    assert [w.label for w in app.text_input]==['Alternativa A','Alternativa B']
    app.text_input[0].set_value('Torre').run()
    payload=json.loads(app.json[0].value)
    assert payload['questions'][0]['options']==['Torre','Cavalo']
    assert payload['questions'][0]['answer']==1
    materials.validate('exam',payload)


def test_line_repeats_then_quizzes_and_waits_for_continue(monkeypatch):
    import interactive_board
    from types import SimpleNamespace
    def board(board,**kwargs):
        st.session_state['shown_hint']=kwargs.get('hint_move')
        st.session_state['shown_fen']=board.fen()
        event=st.session_state.pop('test_move',None)
        return SimpleNamespace(move=dict(uci=event,fen=board.fen(),revision=kwargs['revision']) if event else None,sync=None)
    monkeypatch.setattr(interactive_board,'interactive_board',board)
    # AppTest executes full runs; production events rerun their fragment.
    real_rerun=st.rerun
    monkeypatch.setattr(st,'rerun',lambda **kwargs:real_rerun())
    app=AppTest.from_string("""
import streamlit as st
from classroom_training_preview import render_step_preview
render_step_preview(None,None,dict(items=[
 dict(id='line',title='Linha',kind='line',reviewed=True,payload=dict(pgn='1. e4 e5 2. Nf3 Nc6 *',side='white')),
 dict(id='note',title='Próxima',kind='note',reviewed=True,payload=dict(text='Fim da aula'))]),'flow')
""")
    app.run(timeout=20)
    assert not app.exception
    assert app.session_state['shown_hint']=='e2e4'
    assert any('Acertos e erros da linha' in element.value for element in app.get('html'))
    def play(move):
        app.session_state['test_move']=move
        app.run(timeout=20)
        assert not app.exception
    play('e2e4');play('g1f3')
    assert app.session_state['flow_line_phase']=='recall'
    assert app.session_state['shown_hint'] is None
    play('d2d4')
    assert app.session_state['flow_line_marks']['0']=='wrong'
    play('e2e4');play('g1f3')
    assert app.session_state['flow_line_phase']=='recall'
    play('e2e4');play('g1f3')
    assert app.session_state['flow_line_phase']=='quiz'
    assert app.session_state['flow_line_ply']==2
    assert any('A fazer, erro, não sei e certo' in element.value for element in app.get('html'))
    play('d2d4')
    assert app.session_state['flow_line_ply']==0
    play('e2e4');play('g1f3')
    assert app.session_state['flow_line_phase']=='quiz'
    assert app.session_state['flow_line_quiz_states']['2']=='unknown'
    play('g1f3')
    assert app.session_state['flow_line_phase']=='done'
    assert app.selectbox[0].value=='line'
    assert any(button.label=='Parar por aqui' for button in app.button)
    next(button for button in app.button if button.label=='Continuar para a próxima linha').click().run()
    assert not app.exception
    assert app.selectbox[0].value=='note'
