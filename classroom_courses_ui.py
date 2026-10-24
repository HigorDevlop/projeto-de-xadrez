import streamlit as st
import classroom as rooms
import classroom_courses as courses


def courses_workspace(token,student,roster):
    actor=rooms.identity(token)
    st.subheader('Cursos reutilizáveis',anchor=False)
    st.caption('Prepare linhas, táticos, partidas e provas em Treino e provas. Salve o conjunto como curso para atribuir a outras vagas. As respostas dos alunos não são copiadas.')
    with st.form('prep_course_save'):
        title=st.text_input('Nome do curso')
        if st.form_submit_button('Salvar materiais desta vaga como curso',type='primary'):
            try:courses.save_course(token,student,title);st.success('Curso salvo na biblioteca.')
            except (ValueError,PermissionError) as error:st.error(str(error))
    library=courses.list_courses(token)
    if library:
        lookup={c['id']:c for c in library}
        selected=st.selectbox('Biblioteca de cursos',list(lookup),format_func=lambda k:lookup[k]['title'],key='prep_course_selected')
        st.caption(f"{len(lookup[selected]['payload'])} materiais no curso")
        target=st.selectbox('Atribuir curso à vaga',list(r['id'] for r in roster),format_func=lambda k:next(r['name'] for r in roster if r['id']==k),key='prep_course_target')
        if st.button('Atribuir curso',icon=':material/school:',key='prep_course_assign'):
            try:
                ids=courses.assign_course(token,selected,target)
                st.success(f'Curso atribuído: {len(ids)} materiais. O progresso de outras vagas foi preservado.')
            except (ValueError,PermissionError) as error:st.error(str(error))
        with st.popover('Excluir modelo de curso',icon=':material/delete:'):
            st.caption('Remove apenas o modelo da biblioteca. Materiais já atribuídos e resultados dos alunos são preservados.')
            if st.checkbox('Confirmo a exclusão deste modelo',key='prep_course_confirm_'+selected):
                if st.button('Excluir modelo',key='prep_course_delete_'+selected):courses.delete_course(token,selected);st.rerun()
    else:st.info('Sua biblioteca está pronta para receber o primeiro curso.')
    if actor['role']=='admin':
        st.divider();st.subheader('Laboratório e manutenção',anchor=False)
        seat=next(r for r in roster if r['id']==student)
        st.caption('O administrador pode preparar conteúdos sem chave de Professor. As prévias são feitas nas suas vagas de laboratório, separadas dos alunos reais.')
        rotate,reactivate=st.columns(2)
        if rotate.button('Renovar chave da vaga',key='prep_admin_rotate'):
            rooms.admin_maintain_student(token,student);st.success('Chave renovada; acessos da vaga foram encerrados.')
        if reactivate.button('Reativar vaga',key='prep_admin_reactivate',disabled=not seat['banned']):
            rooms.admin_maintain_student(token,student,reactivate=True);st.rerun()
        if seat['room']==actor['id'] and not seat['banned']:
            with st.expander('Prévia como aluno · laboratório'):
                key='prep_admin_preview_'+student
                if not rooms.identity(st.session_state.get(key)):
                    st.session_state[key]=rooms.admin_preview_session(token,student)
                from classroom_materials_ui import student_materials
                student_materials(st.session_state[key])
