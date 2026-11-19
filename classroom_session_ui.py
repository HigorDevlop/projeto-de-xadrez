"""Teacher session controls and live progress for the selected pupil."""
from datetime import datetime
import streamlit as st
import classroom_training_sessions as sessions
from preparation_state import LOCAL_ZONE


def _changed(student,notice):
    for key in list(st.session_state):
        if key.startswith(('prep_trail_composer_'+student,'prep_line_editor_'+student)):
            st.session_state.pop(key,None)
    st.session_state.prep_material_notice=notice
    st.rerun()


def _manage(token,student,draft):
    st.caption('Salve modelos para reutilizar e prepare a próxima sessão. O aluno recebe a nova montagem quando você clicar em Disponibilizar trilha ao aluno.')
    with st.form('prep_session_save_'+student):
        title=st.text_input('Nome para salvar na biblioteca',value=draft['title'],key='prep_session_save_title_'+student)
        save,new=st.columns(2)
        only=save.form_submit_button('Salvar trilha na biblioteca',icon=':material/save:',disabled=not draft['steps'],width='stretch')
        save_new=new.form_submit_button('Salvar e criar nova trilha',icon=':material/create_new_folder:',disabled=not draft['steps'],width='stretch')
        if only or save_new:
            try:
                if save_new:
                    sessions.new_draft(token,student,draft['revision'],save_title=title)
                    _changed(student,'Trilha salva na biblioteca. A nova montagem começa vazia.')
                sessions.save_template(token,student,draft['revision'],title)
                st.success('Trilha salva. Ela já pode ser reutilizada em outra sessão ou aluno.')
            except (ValueError,PermissionError) as error:st.error(str(error))
    library=sessions.library(token)
    if library:
        lookup={row['id']:row for row in library}
        selected=st.selectbox('Trilhas salvas',list(lookup),format_func=lambda key:lookup[key]['title']+' · '+datetime.fromtimestamp(lookup[key]['created'],LOCAL_ZONE).strftime('%d/%m %H:%M'),key='prep_session_model_'+student)
        model=lookup[selected]
        total=sum(len(step['items']) for step in model['payload']['steps'])
        st.caption(f"{len(model['payload']['steps'])} linhas · {total} atividades · as respostas dos alunos não são copiadas.")
        keep=st.checkbox('Salvar a montagem atual antes de carregar',value=True,key='prep_session_keep_'+student)
        if st.button('Preparar nova sessão com esta trilha',key='prep_session_load_'+student,icon=':material/library_add:'):
            try:
                sessions.new_draft(token,student,draft['revision'],title=model['title'],template=selected,
                                   save_title=draft['title'] if keep and draft['steps'] else None)
                _changed(student,'Modelo carregado na montagem. Revise e disponibilize quando quiser.')
            except (ValueError,PermissionError) as error:st.error(str(error))
    else:st.info('As trilhas salvas ficarão aqui, prontas para as próximas sessões.')
    st.divider()
    st.markdown('**Reiniciar do zero**')
    st.caption('Limpa a trilha e os resultados atuais deste aluno. A biblioteca e um histórico da sessão são preservados.')
    confirm=st.checkbox('Confirmo reiniciar a trilha e o progresso atual deste aluno',key='prep_session_confirm_reset_'+student+'_'+str(draft['revision']))
    if st.button('Reiniciar trilha do zero',disabled=not confirm,key='prep_session_reset_'+student,icon=':material/restart_alt:'):
        try:
            sessions.reset(token,student,draft['revision'])
            _changed(student,'Trilha reiniciada. Adicione as atividades da nova sessão.')
        except (ValueError,PermissionError) as error:st.error(str(error))


def controls(token,student,draft):
    with st.empty().container():
        _controls(token,student,draft)


def _controls(token,student,draft):
    with st.expander('Sessões de treino e biblioteca',icon=':material/folder_special:',key='prep_session_manager_'+student,on_change='rerun') as manager:
        if manager.open:_manage(token,student,draft)
    with st.expander('Histórico de sessões anteriores',icon=':material/history:',key='prep_session_history_'+student,on_change='rerun') as history_panel:
        history=sessions.history(token,student) if history_panel.open else None
        if history==[]:st.caption('As sessões anteriores aparecerão aqui ao publicar uma nova sessão ou reiniciar.')
        for entry in history or []:
            import json
            completed=len({row['material'] for row in entry['payload']['training'] if row['completed']}|
                          {row['material'] for row in entry['payload']['results']}|
                          {row['material'] for row in entry['payload']['tactics'] if json.loads(row['payload'])['passed']})
            st.markdown('**'+entry['title']+'**')
            st.caption(datetime.fromtimestamp(entry['created'],LOCAL_ZONE).strftime('%d/%m/%Y %H:%M')+f" · {completed}/{len(entry['payload']['items'])} atividades concluídas")


@st.fragment(run_every='5s')
def student_progress(token,student):
    rows=sessions.progress(token,student)
    st.markdown('**Trilha atual e progresso do aluno**')
    if not rows:
        st.info('Ainda não há trilha disponibilizada para este aluno. Prepare os conteúdos em Treino e provas.');return
    done=sum(row['completed'] for row in rows)
    st.progress(done/len(rows),text=f'{done} de {len(rows)} atividades concluídas')
    current=next((row for row in rows if not row['completed']),rows[-1])
    st.caption('Etapa atual: '+current['step']+' · '+current['title'])
    st.dataframe([{'Linha':row['step'],'Atividade':row['title'],
        'Situação':'Concluída' if row['completed'] else 'Bloqueada' if row['blocked'] else 'Em treino' if row['updated'] else 'A iniciar',
        'Lances / posições':row['progress'],'Erros':row['errors'],
        'Acerto nos táticos':f"{row['accuracy']:.0f}%" if row['accuracy'] is not None else '—',
        'Nota':f"{row['score']:g}/{row['maximum']:g}" if row['score'] is not None else '—'} for row in rows],
        hide_index=True,width='stretch')
