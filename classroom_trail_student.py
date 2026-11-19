"""Published step navigation; no draft data or answer keys reach the learner."""
import streamlit as st
from classroom_trails import student_trail


def select_step(token,items):
    steps=student_trail(token)
    if not steps:return items,False
    linked={identifier for step in steps for identifier in step['materials']}
    legacy=[item for item in items if item['id'] not in linked]
    key='prep_student_selected_step'
    available=[step for step in steps if not step['blocked']]
    selected=st.session_state.get(key)
    if selected not in [step['id'] for step in available] and not (selected=='legacy' and legacy):
        st.session_state[key]=available[0]['id'] if available else 'legacy' if legacy else None
    st.subheader('Trilha da aula',anchor=False)
    with st.container(horizontal=True):
        for index,step in enumerate(steps):
            if st.button(str(index+1),icon=':material/lock:' if step['blocked'] else ':material/checklist:',
                         disabled=step['blocked'],key='prep_step_'+step['id'],help=step['title'],
                         type='primary' if st.session_state.get(key)==step['id'] else 'secondary'):
                st.session_state[key]=step['id'];st.rerun()
        if legacy and st.button('Outros materiais',key='prep_step_legacy'):
            st.session_state[key]='legacy';st.rerun()
    from classroom_schedule import display_time
    for step in steps:
        if step['locked'] and step.get('release_at'):
            st.caption(step['title']+' · liberação em '+display_time(step['release_at'])+' (Brasília)')
    if any(step.get('reason')=='teacher' for step in steps):st.caption('As etapas com cadeado serão liberadas pelo Professor.')
    if any(step.get('reason')=='tactics' for step in steps):st.caption('Para avançar, conclua o bloco de táticos com pelo menos 90% de acertos.')
    if st.session_state.get(key)=='legacy':return legacy,False
    current=next((step for step in available if step['id']==st.session_state.get(key)),None)
    if not current:
        st.info('Aguarde o Professor liberar a próxima etapa.');return [],True
    st.markdown('**'+current['title']+'**')
    if current.get('notes'):st.write(current['notes'])
    selected_items={identifier:index for index,identifier in enumerate(current['materials'])}
    return sorted((item for item in items if item['id'] in selected_items),key=lambda item:selected_items[item['id']]),False
