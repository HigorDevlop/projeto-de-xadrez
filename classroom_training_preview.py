"""Try the prepared line locally without writing any pupil progress."""
import hashlib
import json
import streamlit as st
import classroom_materials as materials


def render_preview(payload,kind,key,refresh_parent=False,on_complete=None,on_stop=None):
    checked=materials.validate(kind,payload)
    st.caption('Simulação particular: as tentativas não alteram o progresso do aluno.')
    if kind=='tactic' and 'puzzles' in checked:
        from classroom_tactic_block_ui import render_block
        render_block(checked,key+'_block',refresh_parent=refresh_parent,on_complete=on_complete);return
    practice_line(checked,kind,key,on_complete,on_stop)


def practice_line(payload,kind,key,on_complete=None,on_stop=None):
    from classroom_materials_ui import assigned_training
    assigned_training(None,dict(id=key,kind=kind,payload=payload,progress=None),simulation=True,preview_key=key,on_complete=on_complete,on_stop=on_stop)


@st.fragment
def render_step_preview(token,student,step,key,on_stop=None,on_next_step=None):
    from classroom_materials_ui import LABELS,_preview,_video_player
    import classroom_trails as trails
    available=[]
    for item in step['items']:
        if not item['reviewed']:break
        available.append(item)
        if item['kind']=='tactic' and 'puzzles' in item['payload']:
            block_key=key+'_'+item['id']+'_block'
            signature=hashlib.sha256(json.dumps(materials.validate('tactic',item['payload']),sort_keys=True).encode()).hexdigest()
            if st.session_state.get(block_key+'_source')!=signature or not st.session_state.get(block_key+'_state',{}).get('passed'):break
    if not available:
        st.info('Configure e salve uma atividade antes de testar.');return
    choices={item['id']:item for item in available}
    if pending:=st.session_state.pop(key+'_next',None):
        ids=list(choices)
        if pending in ids and ids.index(pending)+1<len(ids):st.session_state[key+'_selected']=ids[ids.index(pending)+1]
    def advance():
        ids=list(choices)
        if ids.index(selected)==len(ids)-1:
            if on_next_step:on_next_step()
            st.session_state[key+'_finished']=True
            st.rerun(scope='fragment')
        st.session_state[key+'_next']=selected
        st.rerun(scope='app')
    if st.session_state.get(key+'_finished'):
        st.success('Você concluiu todas as atividades desta linha.')
        if st.button('Voltar à trilha',key=key+'_finish_back') and on_stop:on_stop()
        return
    selected=st.selectbox('Material da aula',list(choices),format_func=lambda value:LABELS[choices[value]['kind']]+' · '+choices[value]['title'],key=key+'_selected')
    item=choices[selected];payload=item['payload'];kind=item['kind']
    st.subheader(item['title'],anchor=False)
    if payload.get('instructions'):st.write(payload['instructions'])
    if kind in ('line','tactic'):render_preview(payload,kind,key+'_'+selected,refresh_parent=True,on_complete=advance,on_stop=on_stop)
    elif kind=='note':st.write(payload['text'])
    elif kind=='game':_preview(payload,kind,key+'_'+selected)
    elif kind=='video':
        room,_=trails.video_catalog(token,student)
        _video_player(token,payload,key+'_'+selected,room=room)
    elif kind=='exam':
        from classroom_materials_ui import _student_exam
        _student_exam(None,dict(item,result=None),simulation=True,on_complete=advance)

    if kind in ('note','game','video') and st.button('Concluir e continuar',key=key+'_continue_'+selected):advance()
