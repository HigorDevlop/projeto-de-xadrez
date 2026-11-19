"""Focused line editor: organize first, open one activity at a time."""
import streamlit as st
import classroom_trails as trails


def show_step_editor(token,student,identifier,selected_key,labels):
    def close():
        st.session_state.pop(selected_key,None)
        st.session_state.pop('prep_line_editor_'+student+'_'+identifier+'_view',None)
    @st.dialog('Linha da trilha',width='large',on_dismiss=close)
    def editor():
        draft=trails.load_draft(token,student)
        step=next((step for step in draft['steps'] if step['id']==identifier),None)
        if step is None:close();st.rerun()
        root='prep_line_editor_'+student+'_'+identifier
        current_key=root+'_event';view_key=root+'_view'
        for entry in step['items']:
            prefix=root+'_'+entry['id']
            for suffix in ('title','instructions','source','course','line','side_line','side_game','pgn_line','pgn_game',
                           'move_count','tactic_source','fen','uci','theme','puzzle_search','chosen_puzzles','note','video_id','question_count'):
                field=prefix+'_'+suffix
                if field in st.session_state:st.session_state[field]=st.session_state[field]
            for field in list(st.session_state):
                if field.startswith(prefix+'_q_'):st.session_state[field]=st.session_state[field]
        st.html('''<style>
        div[role="dialog"]{background:linear-gradient(150deg,#1a201d,#111613)!important;border:1px solid #8c9a7540!important;border-radius:20px!important}
        div[role="dialog"] [data-testid="stButton"] button{border-radius:10px;min-height:40px;box-shadow:inset 0 1px #ffffff0c,0 3px 8px #0003}
        div[role="dialog"] [data-testid="stVerticalBlock"]{gap:.8rem}
        div[role="dialog"] [data-testid="stExpander"] details{box-shadow:none!important;background:#101511!important}
        div[role="dialog"] [data-testid="stCaptionContainer"] p{font-size:12px}
        </style>''')
        def change(event):
            trails.edit_draft(token,student,draft['revision'],dict(event,step=identifier))
            st.rerun(scope='app')
        if view_key not in st.session_state:
            pending=next((item for item in step['items'] if not item['reviewed']),None)
            st.session_state[current_key]=pending['id'] if pending else None
            st.session_state[view_key]='content' if pending else 'list'
        if st.session_state.get(current_key) not in [item['id'] for item in step['items']]:
            st.session_state[current_key]=None
            if st.session_state[view_key]=='content':st.session_state[view_key]='list'
        with st.container(horizontal=True,vertical_alignment='center'):
            st.markdown('**'+step['title'].replace('*','')+'**')
            if st.button('Nome e notas',icon=':material/edit_note:',key=root+'_details_open'):
                st.session_state[view_key]='details';st.rerun(scope='app')
            if not st.session_state.get(root+'_schedule_open'):
                with st.popover('Opções',icon=':material/more_horiz:'):
                    if st.button('Desbloquear avanço' if step['locked'] else 'Bloquear avanço',icon=':material/lock:',key=root+'_lock',width='stretch'):
                        if step['locked']:change(dict(action='lock',locked=False))
                        st.session_state[root+'_schedule_open']=True;st.rerun(scope='app')
                    with st.expander('Excluir esta linha'):
                        st.caption('A linha sai da montagem. Respostas já registradas são preservadas.')
                        if st.button('Excluir linha da trilha',key=root+'_delete',width='stretch'):
                            trails.edit_draft(token,student,draft['revision'],dict(action='remove',step=identifier));close();st.rerun(scope='app')
        if step.get('release_at') and step['locked']:
            from classroom_schedule import display_time
            st.caption('Liberação programada: '+display_time(step['release_at'])+' · Brasília')
        if st.session_state.get(root+'_schedule_open'):
            from datetime import datetime,timedelta
            from zoneinfo import ZoneInfo
            with st.container(border=True):
                st.markdown('**Bloqueio da linha**')
                scheduled=st.radio('Liberar a linha',['Manualmente pelo professor','Em data e hora'],key=root+'_schedule_mode')=='Em data e hora'
                timestamp=None
                if scheduled:
                    default=datetime.now(ZoneInfo('America/Sao_Paulo'))+timedelta(days=1)
                    day_col,time_col=st.columns(2)
                    day=day_col.date_input('Data de liberação',value=default.date(),key=root+'_release_day')
                    hour=time_col.time_input('Hora de liberação',value=default.time().replace(second=0,microsecond=0),key=root+'_release_hour')
                    st.caption('Horário de Brasília · a linha e as seguintes ficam bloqueadas até a liberação.')
                    timestamp=datetime.combine(day,hour,tzinfo=ZoneInfo('America/Sao_Paulo')).timestamp()
                if st.button('Confirmar bloqueio',type='primary',key=root+'_schedule_save'):
                    try:
                        trails.edit_draft(token,student,draft['revision'],dict(action='lock',step=identifier,locked=True,release_at=timestamp))
                        st.session_state[root+'_schedule_open']=False;st.rerun(scope='app')
                    except ValueError as error:st.error(str(error))
                if st.button('Cancelar bloqueio',key=root+'_schedule_cancel'):
                    st.session_state[root+'_schedule_open']=False;st.rerun(scope='app')
        def stop_preview():
            close();st.rerun(scope='app')
        def next_preview():
            index=next(i for i,value in enumerate(draft['steps']) if value['id']==identifier)
            following=next((value for value in draft['steps'][index+1:] if any(item['reviewed'] for item in value['items'])),None)
            if following:
                st.session_state[selected_key]=following['id']
                st.session_state['prep_line_editor_'+student+'_'+following['id']+'_view']='stage_preview'
                st.rerun(scope='app')
            st.session_state[root+'_student_test_finished']=True
            st.rerun(scope='app')
        view=st.session_state[view_key]
        if st.session_state.pop(root+'_saved',False):st.success('Atividade salva.')
        with st.container(horizontal=True):
            if st.button('Testar linha',icon=':material/play_arrow:',type='primary' if view=='home' else 'secondary',key=root+'_test_stage',disabled=not any(item['reviewed'] for item in step['items'])):
                st.session_state[view_key]='stage_preview';st.rerun(scope='app')
            if st.button('Configurar linha',icon=':material/tune:',key=root+'_configure'):
                st.session_state[view_key]='list';st.rerun(scope='app')
        if view=='home':
            st.caption(str(len(step['items']))+' atividades · '+str(sum(not item['reviewed'] for item in step['items']))+' para configurar')
            for index,item in enumerate(step['items'],1):st.write(str(index)+' · '+item['title'])
        elif view=='stage_preview':
            from classroom_training_preview import render_step_preview
            render_step_preview(token,student,step,root+'_student_test',on_stop=stop_preview,on_next_step=next_preview)
        if view not in ('home','list','stage_preview') and st.button('Voltar às atividades',icon=':material/arrow_back:',key=root+'_back'):
            st.session_state[view_key]='list';st.rerun(scope='app')
        if view in ('home','stage_preview'):pass
        elif view=='details':
            with st.form(root+'_details'):
                name=st.text_input('Nome da linha',value=step['title'])
                notes=st.text_area('Anotações gerais',value=step.get('notes',''),height=120,placeholder='O que o aluno deve observar nesta etapa?')
                if st.form_submit_button('Salvar nome e anotações',type='primary'):
                    try:
                        trails.edit_draft(token,student,draft['revision'],dict(action='update_step',step=identifier,title=name,notes=notes))
                        st.session_state[view_key]='list';st.rerun(scope='app')
                    except (ValueError,PermissionError) as error:st.error(error)
        elif view=='list':
            st.caption('Atividades na ordem do aluno. Clique no nome para configurar.')
            for index,item in enumerate(step['items']):
                with st.container(border=True):
                    label,test,remove,order_slot=st.columns([7,2,2,1],gap='small',vertical_alignment='center',wrap=False)
                    title=item['title'] if item['title']!=labels[item['kind']] else labels[item['kind']]
                    text=str(index+1)+' · '+title
                    if label.button(text,key=root+'_select_'+item['id'],width='stretch',icon=':material/'+dict(line='route',tactic='psychology',video='play_circle',exam='quiz',game='grid_on',note='edit_note')[item['kind']]+':'):
                        st.session_state[current_key]=item['id'];st.session_state[view_key]='content';st.rerun(scope='app')
                    if test.button('Testar',key=root+'_try_'+item['id'],disabled=not item['reviewed'],icon=':material/play_arrow:',width='stretch'):
                        st.session_state[current_key]=item['id'];st.session_state[view_key]='preview';st.rerun(scope='app')
                    if remove.button('Remover',key=root+'_remove_'+item['id'],icon=':material/delete:',width='stretch'):
                        change(dict(action='remove_item',item=item['id']))
                    with order_slot.popover('⋯',help='Mudar a ordem'):
                        for offset,text in ((-1,'Mover para cima'),(1,'Mover para baixo')):
                            if st.button(text,key=root+item['id']+str(offset),disabled=not 0<=index+offset<len(step['items'])):
                                order=[entry['id'] for entry in step['items']];j=index+offset;order[index],order[j]=order[j],order[index]
                                change(dict(action='item_order',order=order))
                    if not item['reviewed']:st.caption('Configuração pendente')
            if not step['items']:st.info('Adicione a primeira atividade desta linha.')
            with st.popover('Adicionar atividade',icon=':material/add:'):
                for kind in ('line','tactic','video','exam','game','note'):
                    if st.button(labels[kind],key=root+'_add_'+kind,width='stretch'):
                        updated=trails.edit_draft(token,student,draft['revision'],dict(action='add_event',step=identifier,kind=kind))
                        target=next(s for s in updated['steps'] if s['id']==identifier)
                        st.session_state[current_key]=target['items'][-1]['id'];st.session_state[view_key]='content';st.rerun(scope='app')
        elif view=='preview':
            item=next((item for item in step['items'] if item['id']==st.session_state.get(current_key)),None)
            if item:
                from classroom_training_preview import render_step_preview
                render_step_preview(token,student,dict(step,items=[item]),root+'_'+item['id']+'_try',on_stop=stop_preview,on_next_step=next_preview)
        else:
            item=next((item for item in step['items'] if item['id']==st.session_state.get(current_key)),None)
            if item:
                st.markdown('**'+labels[item['kind']]+'**')
                prefix=root+'_'+item['id'];_seed(prefix,item)
                title=st.text_input('Nome da atividade',key=prefix+'_title')
                with st.expander('Orientações para o aluno'):
                    instructions=st.text_area('Orientações para o aluno',key=prefix+'_instructions',height=90)
                from classroom_trail_inputs import content_inputs
                from classroom_line_segments import previous_line
                before=previous_line(draft,identifier,item['id'])
                payload=content_inputs(token,student,prefix,item['kind'],instructions,previous=before,position_notes=item.get('payload',{}).get('position_notes',[]),saved_tactics=item.get('payload',{}).get('puzzles') or ([item['payload']] if item.get('payload',{}).get('fen') else []))
                if st.button('Salvar atividade',type='primary',icon=':material/check:',key=prefix+'_save',disabled=payload is None):
                    try:
                        updated=trails.edit_draft(token,student,draft['revision'],dict(action='save_item',step=identifier,item=item['id'],title=title,payload=payload,reviewed=True))
                        target=next(s for s in updated['steps'] if s['id']==identifier)
                        st.session_state[current_key]=target['items'][step['items'].index(item)]['id']
                        st.session_state[root+'_saved']=True
                        st.session_state[view_key]='list'
                        st.rerun(scope='app')
                    except (ValueError,PermissionError) as error:st.error(error)
        if st.button('Fechar edição',key=root+'_close',width='stretch'):close();st.rerun(scope='app')
    editor()

def _seed(prefix,item):
    if prefix+'_title' in st.session_state:return
    payload=item.get('payload') or {}
    values=dict(title=item['title'],instructions=payload.get('instructions',''),source='Continuar linha anterior' if payload.get('continuation') else 'PGN personalizado' if payload.get('pgn') else 'Catálogo de aberturas',
        pgn_line=payload.get('source_pgn',payload.get('pgn','')),continuation_source=payload.get('source_pgn',payload.get('pgn','')),move_count=payload.get('move_count',5),pgn_game=payload.get('pgn',''),side_line=payload.get('side','white'),side_game=payload.get('side','white'),
        tactic_source='Criar uma posição' if payload.get('fen') else 'Escolher no banco offline',fen=payload.get('fen',''),uci=' '.join(payload.get('solution',[])),
        note=payload.get('text',''),question_count=len(payload.get('questions',[])) or 1)
    if payload.get('video_id'):values['video_id']=payload['video_id']
    for key,value in values.items():
        if key=='continuation_source' and not value:continue
        st.session_state[prefix+'_'+key]=value
    for index,q in enumerate(payload.get('questions',[])):
        key=prefix+'_q_'+str(index)
        for field,value in dict(kind='Fechada' if q['kind']=='closed' else 'Aberta',prompt=q['prompt'],weight=q['weight'],options='\n'.join(q.get('options',[])),correct=q.get('answer') if q['kind']=='closed' else None,answer=q.get('answer','') if q['kind']=='open' else '').items():st.session_state[key+'_'+field]=value
