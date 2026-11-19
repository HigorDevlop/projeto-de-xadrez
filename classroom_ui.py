"""Professor access, routine editor and student dashboards."""
from datetime import date, datetime
from io import StringIO
from html import escape
import streamlit as st
import chess.pgn

import classroom as rooms
from preparation_state import today, LOCAL_ZONE


def _clear_workspace():
    """Discard account data and late results before another identity signs in."""
    state = st.session_state
    revision = state.get('board_revision', 0) + 1
    generation = state.get('analysis_generation', 0) + 1
    book_revision = state.get('book_revision', 0) + 1
    puzzle_revision = state.get('puzzle_revision', 0) + 1
    upload_revision = state.get('study_upload_revision', 0) + 1
    for key in ('analysis_cancel', 'accuracy_cancel'):
        if cancel := state.get(key):
            cancel.set()
    for _, future in state.get('jobs', {}).values():
        future.cancel()
    if preparation := state.get('prep_job'):
        preparation['cancel'].set()
        preparation['future'].cancel()
    if cache := state.pop('_reader_page_cache', None):
        cache.executor.shutdown(wait=False, cancel_futures=True)
    if service := state.pop('_book_position_service', None):
        service.cancel_preloads()
        service.preload_executor.shutdown(wait=False, cancel_futures=True)
        service.executor.shutdown(wait=False, cancel_futures=True)
    prefixes = ('analysis_', 'book_', 'reader_', 'study_', 'prep_', 'openings_', 'puzzle_',
                'dashboard_', 'history_', 'forge_', 'tactic_', 'remote_', 'presence_')
    for key in list(state):
        if key.startswith(prefixes):
            state.pop(key, None)
    for key in ('_book_library_owner', '_book_sources_cache', '_analysis_files', '_analysis_library_id', 'books', 'interactive_board', 'quick_answer',
                'import_text', 'import_file', 'move_error', 'last_explanation',
                'quality_save_error', 'chesscom_login_username'):
        state.pop(key, None)
    state.update(game=str(chess.pgn.Game()), ply=0, reviews={}, explanations={},
                 official_accuracies={}, loaded_analysis=None, recent_accuracies={},
                 study_files=(), library_uploads=(), study_open=False, study_upload_revision=upload_revision,
                 tab_history=[], jobs={}, job_errors={}, navigation_ack=0,
                 board_revision=revision, analysis_generation=generation,
                 book_revision=book_revision, puzzle_revision=puzzle_revision,
                 dashboard_history_games=[], dashboard_history_key=None)


def _switch(token=None):
    if previous_room := st.session_state.pop('classroom_room_token',None):
        try:
            from classroom_sessions import leave
            leave(previous_room)
        except PermissionError:pass
        rooms.logout(previous_room)
    st.session_state.classroom_mode=False
    if previous := st.session_state.get('classroom_token'):
        rooms.logout(previous)
    _clear_workspace()
    st.session_state.classroom_token = token
    user = rooms.identity(token)
    st.session_state.update(archive_user=user.get('chesscom','') if user else '',
        history_games=[],history_loaded_user=None,openings_owner=None,openings_plan=None,
        openings_active=False,openings_catalog=True,puzzle=None,puzzle_buffer=[],puzzle_progress=0,
        player_rating=None,rating_user=None,profile_bytes=rooms.load_profile_photo(token) if user else None)
    st.session_state.pop('openings_overlay',None)
    st.session_state.pop('last_professor_invite',None)
    st.session_state.pop('photo_error',None)
    st.session_state.pop('room_notice',None)
    st.session_state.pop('room_opening_request',None)
    st.session_state.pop('prep_workspace_student',None)
    st.session_state.pop('prep_workspace_tabs',None)
    destination = 'Usuários' if user and user['role']=='admin' else 'Preparo' if user and user['role']=='professor' else 'Aberturas'
    st.session_state.requested_page = destination
    st.session_state.active_tab = st.session_state.main_view = destination


def training_token():
    state=st.session_state
    return state.get('classroom_room_token') if state.get('classroom_mode') else state.get('classroom_token')


def _training_context(room_token=None):
    state=st.session_state
    if previous:=state.get('classroom_room_token'):
        if previous!=room_token:
            try:
                from classroom_sessions import leave
                leave(previous)
                rooms.pulse(previous,False)
            except PermissionError:pass
            rooms.logout(previous)
    state.update(classroom_room_token=room_token,classroom_mode=bool(room_token),
        openings_owner=None,openings_plan=None,openings_active=False,openings_catalog=True,
        puzzle=None,puzzle_buffer=[],puzzle_progress=0,requested_page='Preparo' if room_token else 'Aberturas')
    state.pop('openings_overlay',None)
    state.pop('room_opening_request',None)
    if room_token:
        from classroom_sessions import begin
        begin(room_token,new_entry=True)


def access(show_session=True):
    user=rooms.identity(st.session_state.get('classroom_token'))
    if not user:
        return None
    labels={'admin':'Superadministrador','professor':'Professor · Mestre da Sala','student':'Aluno','user':'Usuário'}
    if user['role']=='user':
        token=st.session_state.classroom_token
        link=rooms.membership(token)
        if st.session_state.get('classroom_mode') and not rooms.identity(st.session_state.get('classroom_room_token')):
            try:st.session_state.classroom_room_token=rooms.room_session(token)
            except (ValueError,PermissionError):
                _training_context();st.session_state.room_notice='O acesso à sala foi revogado. Suas abas comuns continuam disponíveis.'
            st.rerun()
        if notice:=st.session_state.pop('room_notice',None):st.warning(notice)
        if link:
            st.caption('Sala do Professor · '+link['professor'])
            if st.session_state.get('classroom_mode'):
                if st.button('Usar abas comuns',width='stretch'):_training_context();st.rerun()
            elif st.button('Abrir sala do Professor',width='stretch'):
                try:_training_context(rooms.room_session(token));st.rerun()
                except (ValueError,PermissionError) as error:st.error(str(error))
        else:
            with st.expander('Tenho uma chave do professor',expanded=True,icon=':material/key:'):
                st.caption('Cole a chave recebida para abrir sua trilha de treino.')
                with st.form('join_professor_room'):
                    code=st.text_input('Código da sala',type='password')
                    if st.form_submit_button('Juntar-se à sala'):
                        try:_training_context(rooms.join_room(token,code));st.rerun()
                        except (ValueError,PermissionError) as error:st.error(str(error))
    if show_session:
        session_settings(user)
    return user


def join_room_panel():
    token=st.session_state.get('classroom_token')
    actor=rooms.identity(token)
    if not actor or actor['role']!='user' or rooms.membership(token):return
    st.html('<style>.st-key-classroom_join_panel{padding:22px!important;border:1px solid #8b7848!important;border-radius:18px!important;background:linear-gradient(125deg,#273a2e,#17251f)!important;box-shadow:0 8px 22px #0003}.st-key-classroom_join_panel [data-testid=stForm]{border:0;background:transparent;padding:0}</style>')
    with st.container(border=True,key='classroom_join_panel'):
        st.subheader('Recebeu uma chave do professor?',anchor=False)
        st.write('Cole a chave abaixo para entrar na sala e receber sua trilha de treino.')
        with st.form('join_professor_room_main'):
            code=st.text_input('Chave de acesso do professor',placeholder='Cole aqui a chave recebida',type='password')
            if st.form_submit_button('Entrar na sala do professor',icon=':material/key:',type='primary',width='stretch'):
                try:
                    _training_context(rooms.join_room(token,code))
                    st.session_state.requested_page='Preparo'
                    st.rerun()
                except (ValueError,PermissionError) as error:st.error(str(error))


def session_settings(user):
    labels={'admin':'Superadministrador','professor':'Professor','student':'Aluno','user':'Jogador'}
    with st.container(border=True,key='session_settings'):
        st.caption('MINHA SESSÃO')
        st.write(labels[user['role']]+' · '+user['name'])
        if st.button('Sair e esquecer este navegador',key='classroom_logout',width='stretch'):
            from auth_ui import logout_current
            logout_current();st.rerun()
        if st.button('Revogar meus acessos automáticos',key='classroom_revoke_devices',width='stretch'):
            rooms.revoke_remembered_access(st.session_state.classroom_token)
            st.success('Acessos automáticos revogados. Seu login atual continua ativo.')


def _metrics(summary):
    task=summary['routine']
    if not task:
        from classroom_design import empty
        empty('Uma trilha começa com um plano','As metas e o progresso do aluno aparecerão aqui quando a rotina for definida.','target');return
    st.write(f"**{summary['status']} · {summary['day']}**")
    columns=st.columns(3)
    columns[0].metric('Linhas concluídas',f"{summary['lines']} / {task['lines']}")
    columns[1].metric('Táticos resolvidos',f"{summary['tactics']} / {task['tactics']}")
    columns[2].metric('Tempo ativo',f"{summary['seconds']/60:.1f} / {task['minutes']} min")
    columns=st.columns(4)
    for column,(key,label) in zip(columns, [('pending','A Fazer'),('wrong','Erro'),('unknown','Não Sei'),('correct','Certo')]):
        column.metric(label,summary['states'][key])
    st.caption(f"Meta de posições concluídas: {summary['states']['correct']} / {task['positions']}")
    for key,label in [('opening','Precisão em aberturas'),('tactics','Precisão em táticos')]:
        value=summary['accuracy'][key]
        st.write(f"{label}: **{value:.1f}%**" if value is not None else f'{label}: sem tentativas registradas.')
    st.progress(min(1,summary['lines']/task['lines']),text='Progresso da trilha')


@st.cache_data(ttl=300,show_spinner=False)
def last_games(username):
    from chesscom import fetch_recent_games
    from opening_reference_catalog import eco_paths
    index={tuple(moves):name for moves,name in eco_paths()}
    games=fetch_recent_games(username,limit=20,max_months=12000)
    rows=[]
    for item in games[:20]:
        game=chess.pgn.read_game(StringIO(item['pgn']))
        name='Abertura não identificada';eco='—'
        if game and not game.errors:
            name=game.headers.get('Opening') or name
            eco=game.headers.get('ECO','—')
            path=[]
            for move in game.mainline_moves():
                path.append(move.uci())
                if tuple(path) in index:
                    name=index[tuple(path)]
        rows.append({'Data':datetime.fromtimestamp(item.get('end_time',0),LOCAL_ZONE).strftime('%d/%m/%Y %H:%M'),
            'Brancas':item.get('white',{}).get('username','—'),
            'Negras':item.get('black',{}).get('username','—'),'Abertura':name,'ECO':eco,'Partida':item.get('url','')})
    return rows


def professor_workspace(token):
    user=rooms.identity(token)
    if not user or user['role'] not in ('professor','admin'):
        st.error('Modo Preparo é exclusivo do Professor. Entre pelo acesso Professor na barra lateral.');return
    _class_style()
    from classroom_design import hero,section,summary as plan_summary
    if user['role']=='admin':rooms.ensure_admin_room(token)
    from classroom_challenges_ui import teacher as teacher_challenges
    teacher_challenges(token)
    roster=rooms.students(token)
    if not roster:
        hero('Modo Preparo')
        st.info('Ainda não há alunos. Emita uma chave de Professor em Usuários para iniciar uma sala.');return
    if training_request:=st.session_state.pop('prep_roster_training_request',None):
        if any(row['id']==training_request and not row['banned'] for row in roster):
            st.session_state.prep_workspace_student=training_request
            st.session_state.prep_workspace_tabs='Treino e provas'
    heading,selector=st.columns([2.2,1],vertical_alignment='center')
    with heading:hero('Modo Preparo','Crie cursos e teste no seu laboratório. Gerencie todas as salas.' if user['role']=='admin' else 'Planeje, acompanhe e converse com sua turma.')
    selected=selector.selectbox('Selecionar aluno',[row['id'] for row in roster],key='prep_workspace_student',
        format_func=lambda identifier:next((row.get('professor','')+' · ' if user['role']=='admin' else '')+row['name']+(' · Banido' if row['banned'] else '') for row in roster if row['id']==identifier))
    student=next(row for row in roster if row['id']==selected)
    profile=rooms.dashboard(token,selected)
    st.html('<div class="prep-profile"><span class="prep-avatar">'+escape(student['name'][:1].upper())+'</span><div><strong>'+escape(student['name'])+'</strong><small>'+('Rotina definida' if profile['routine'] else 'Pronto para uma nova rotina')+'</small></div><span class="prep-profile-tag">'+str(student['warnings'])+'/3 advertências</span></div>')
    keys,editor,materials_tab,dashboard,audit,chat,lessons=st.tabs(['Alunos e acessos','Rotina individual','Treino e provas','Dashboard','Presença e advertências','Conversas','Aulas'],key='prep_workspace_tabs',on_change='rerun')
    with materials_tab:
        if materials_tab.open:
            from classroom_materials_ui import teacher_materials
            teacher_materials(token,selected)
    if not lessons.open and st.session_state.get('live_view_class_'+student['room']):
        from community_ui import release_live_view
        release_live_view(token,student['room'])
    with chat:
        if chat.open:
            from community_ui import conversations
            with st.container(key='prep_chat_room'):
                conversations(token,student['room'],student['id'],teacher=True)
    with lessons:
        if lessons.open:
            from community_ui import lesson_room
            lesson_room(token,student['room'],teacher=True)
    with keys:
        if keys.open:
            from classroom_roster_ui import roster_cards
            roster_cards(token,roster)
    with editor:
        from opening_repertoires import catalog
        from opening_reference_catalog import display_name
        summary=rooms.dashboard(token,selected)
        task=summary['routine'] or {}
        courses={c['id']:c for c in catalog()}
        content,preview=st.columns([1.8,1],gap='large')
        with content,st.container(border=True,key='routine_editor'):
            section('01','Repertório','Escolha as aberturas que guiarão o treino.')
            openings=st.multiselect('Aberturas da rotina (até 4)',list(courses),default=task.get('openings',[]),
                format_func=lambda key:display_name(courses[key])+(' · Brancas' if courses[key]['side']=='white' else ' · Negras'),placeholder='Selecione as aberturas',key='routine_openings_'+selected,max_selections=4)
            section('02','Metas do dia')
            grid=st.columns(2)
            lines=grid[0].number_input('Linhas por dia (total entre as aberturas)',min_value=1,max_value=128,value=task.get('lines',1),key='routine_lines_'+selected)
            positions=grid[1].number_input('Posições concluídas por dia',min_value=1,max_value=1536,value=task.get('positions',1),key='routine_positions_'+selected)
            grid=st.columns(2)
            tactics=grid[0].number_input('Táticos resolvidos por dia',min_value=0,max_value=1000,value=task.get('tactics',5),key='routine_tactics_'+selected)
            minutes=grid[1].number_input('Tempo ativo de treino (minutos por dia)',min_value=1,max_value=480,value=task.get('minutes',30),key='routine_minutes_'+selected)
            section('03','Agenda')
            weekdays=st.pills('Dias de treino',list(range(7)),default=task.get('weekdays',list(range(7))),selection_mode='multi',
                format_func=lambda day:['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][day],key='routine_days_'+selected) or []
            start=st.date_input('Início da rotina',value=date.fromisoformat(task['start']) if task else today(),key='routine_start_'+selected,format='DD/MM/YYYY')

            if st.button('Salvar rotina',disabled=bool(student['banned']) or not openings,type='primary',width='stretch'):
                try:
                    rooms.save_routine(token,selected,openings,int(lines),int(positions),int(tactics),int(minutes),weekdays,start)
                    st.success('Rotina salva. O aluno a recebe na aba Aberturas.');st.rerun()
                except ValueError as error:st.error(str(error))
        with preview:plan_summary(len(openings),lines,tactics,minutes,weekdays)
    with dashboard:
        _student_dashboard(token,student)
    with audit:
        history,actions=st.columns([1.8,1],gap='large')
        with history:
            _private_sessions(token,selected)
            rows=[row for row in rooms.attendance(token,selected) if row['scheduled'] or row['present']]
            with st.expander('Histórico diário'):
                if rows:st.dataframe([{'Dia':r['day'],'Presença':r['status'],'Linhas':r['lines'],'Táticos':r['tactics'],'Minutos':round(r['seconds']/60,1)} for r in rows],hide_index=True,width='stretch')
                else:
                    from classroom_design import empty
                    empty('Nenhum treino agendado','Os dias de treino aparecerão aqui depois que a rotina for salva.','calendar')
        with actions,st.container(border=True,key='prep_warning_card'):
            section('!','Acompanhamento')
            st.metric('Advertências',f"{student['warnings']} / 3")
            if student['banned']:st.error('Aluno banido · acesso revogado.')
            with st.form('warning_'+selected):
                reason=st.text_area('Motivo da advertência',placeholder='Registre o motivo para o aluno…',height=100)
                st.caption('Na terceira advertência, o acesso à sala é revogado.')
                if st.form_submit_button('Aplicar advertência',disabled=bool(student['banned']),width='stretch'):
                    try:rooms.warn(token,selected,reason);st.rerun()
                    except ValueError as error:st.error(str(error))
            for item in rooms.dashboard(token,selected)['warnings']:
                st.caption(datetime.fromtimestamp(item['created'],LOCAL_ZONE).strftime('%d/%m %H:%M')+' · '+item['reason'])


def student_routine(token,on_opening,on_tactics):
    summary=rooms.dashboard(token)
    with st.expander('Minha rotina · metas do Professor',expanded=True):
        _metrics(summary)
        task=summary['routine']
        if task:
            from opening_repertoires import selected_courses
            for course in selected_courses(task['openings']):
                st.button('Treinar '+course['title'],key='assigned_'+course['id'],on_click=on_opening,args=({'id':course['id']},))
            st.button('Treinar táticos da rotina',on_click=on_tactics)


_ACTIVITY=st.components.v2.component('classroom_active_training',html='<span hidden></span>',js='''
export default function({data,parentElement,setStateValue}){
 if(parentElement._classroomClock){parentElement._classroomClock.emit=setStateValue;parentElement._classroomClock.paused=data.paused;return;}
 const doc=parentElement.ownerDocument,clock={last:0,emit:setStateValue,paused:data.paused};
 parentElement._classroomClock=clock;
 const activity=()=>{clock.last=Date.now();};
 doc.addEventListener('pointerdown',activity,true);doc.addEventListener('keydown',activity,true);
 const timer=setInterval(()=>{
   if(!(parentElement.host??parentElement).isConnected){clearInterval(timer);doc.removeEventListener('pointerdown',activity,true);doc.removeEventListener('keydown',activity,true);return;}
   clock.emit('pulse',{nonce:Date.now(),active:!clock.paused&&!doc.hidden&&doc.hasFocus()&&Date.now()-clock.last<60000});
 },10000);
}''')


@st.fragment
def activity(token,paused=False):
    def tick():
        event=st.session_state.classroom_training_clock.pulse
        try:rooms.pulse(token,bool(isinstance(event,dict) and event.get('active') and not paused))
        except PermissionError:
            st.session_state.classroom_revoked=True
    if st.session_state.pop('classroom_revoked',False):
        st.rerun(scope='app')
    _ACTIVITY(key='classroom_training_clock',data={'paused':paused},height=0,on_pulse_change=tick)


def _student_dashboard(token,student):
    selected=student['id']
    date,refresh=st.columns([3,1],vertical_alignment='bottom')
    day=date.date_input('Dia do dashboard',value=today(),max_value=today(),format='DD/MM/YYYY')
    refresh.button('Atualizar dashboard',icon=':material/refresh:',key='classroom_refresh_dashboard',width='stretch')
    summary=rooms.dashboard(token,selected,day)
    _metrics(summary)
    if not summary['routine']:st.button('Criar rotina',on_click=_open_routine,args=(selected,),type='primary')
    sessions,games=st.columns(2,gap='large')
    with sessions:
        _private_sessions(token,selected,view='dashboard')
    with games:
        st.subheader('Aberturas nas últimas 20 partidas')

        if student['chesscom']:
            if st.button('Carregar / atualizar últimas 20 partidas'):
                last_games.clear()
                try:
                    st.session_state['classroom_games_'+selected]=last_games(student['chesscom'])
                except ValueError as error:st.error(str(error))
            rows=st.session_state.get('classroom_games_'+selected)
            if rows is not None:
                st.dataframe(rows,hide_index=True,width='stretch',column_config={'Partida':st.column_config.LinkColumn('Partida')})
                if len(rows)<20:st.caption(f'{len(rows)} partidas disponíveis no histórico consultado; não foram inventadas partidas para completar 20.')
        else:
            from classroom_design import empty
            empty('O próximo capítulo está nas partidas','Vincule o Chess.com do aluno na aba de chaves para acompanhar suas últimas 20 partidas.','chart')


def professor_dashboard(token):
    user=rooms.identity(token)
    if not user or user['role'] not in ('professor','admin'):
        st.error('Desempenho é exclusivo do Professor e do Superadministrador.');return
    st.header('Desempenho dos alunos')
    _class_style()
    roster=rooms.students(token)
    if not roster:
        st.info('Nenhum aluno cadastrado.');return
    selected=st.selectbox('Selecionar aluno',[row['id'] for row in roster],
        format_func=lambda identifier:next(f"{row['slot']} · {row['name']}" for row in roster if row['id']==identifier))
    _student_dashboard(token,next(row for row in roster if row['id']==selected))


def student_workspace(token):
    user=rooms.identity(token)
    if not user or user['role']!='student':
        st.error('Entre na sala do Professor para acessar o Modo Preparo.');return
    _class_style()
    from classroom_design import hero
    hero('Modo Preparo','Seu próximo passo começa aqui.')
    from classroom_challenges_ui import student as student_challenges
    student_challenges(token)
    def opening(event):
        st.session_state.room_opening_request=event
        st.session_state.requested_page='Aberturas'
    routine,materials_tab,chat,lessons=st.tabs(['Minha trilha','Treino e provas','Conversas','Aulas'],key='prep_student_tabs',on_change='rerun')
    with materials_tab:
        if materials_tab.open:
            from classroom_materials_ui import student_materials
            student_materials(token)
    if not lessons.open and st.session_state.get('live_view_class_'+user['room']):
        from community_ui import release_live_view
        release_live_view(token,user['room'])
    with routine:
        if routine.open:student_routine(token,opening,lambda:st.session_state.update(requested_page='Tático'))
    with chat:
        if chat.open:
            from community_ui import conversations
            with st.container(key='prep_chat_room'):
                conversations(token,user['room'],user['id'])
    with lessons:
        if lessons.open:
            from community_ui import lesson_room
            lesson_room(token,user['room'])


def _class_style():
    st.html('<style>[data-testid="stMetric"]{background:linear-gradient(125deg,#1b1b1b,#111);border:1px solid #2b2b2b;border-radius:16px;padding:16px} .st-key-routine_editor{background:linear-gradient(135deg,#181818,#101010);border-radius:20px} .visit-card{padding:16px 20px;border:1px solid #303030;border-left:4px solid var(--visit-color);border-radius:12px;margin:10px 0;background:#141414;display:flex;justify-content:space-between;gap:20px}.visit-card time{color:var(--visit-color);font-size:22px;font-weight:700}.visit-card small{display:block;color:#aaa;margin-top:5px}[data-baseweb=tab-list]{gap:6px;overflow-x:auto;scrollbar-width:thin}[data-baseweb=tab]{border-radius:12px 12px 0 0;padding:10px 14px;white-space:nowrap}div[class*=st-key-seat_]{background:linear-gradient(130deg,#1e2529,#121619);border-radius:18px}div[class*=st-key-seat_] pre{font-size:12px;overflow-wrap:anywhere}@media(max-width:700px){[data-testid=stMetricValue]{font-size:24px!important}.visit-card{padding:12px;gap:10px}.visit-card time{font-size:19px}.stMainBlockContainer{padding-left:14px!important;padding-right:14px!important}[data-baseweb=tab]{font-size:13px;padding:8px 10px}} </style>')

    from classroom_design import apply
    apply()


def _open_routine(student):
    st.session_state.prep_workspace_student=student
    st.session_state.prep_workspace_tabs='Rotina individual'
    st.session_state.requested_page='Preparo'


def _time_label(seconds):
    seconds=int(max(0,seconds))
    return f'{seconds//60:02d}:{seconds%60:02d}'


@st.fragment(run_every='5s')
def _private_sessions(token,student,view='audit'):
    import classroom_sessions
    rows=classroom_sessions.history(token,student)
    st.subheader('Sessões de preparo')
    if not rows:
        from classroom_design import empty
        empty('Tudo pronto para o primeiro treino','A presença e o tempo de cada sessão aparecerão aqui assim que o aluno entrar.','calendar');return
    for row in rows[:20]:
        color={'green':'#39ca87','red':'#f05c71','orange':'#f8ac43'}[row['color']]
        started=datetime.fromtimestamp(row['started'],LOCAL_ZONE).strftime('%d/%m · %H:%M')
        end=' → '+datetime.fromtimestamp(row['ended'],LOCAL_ZONE).strftime('%H:%M') if row['ended'] is not None else ''
        st.html(f'<div class="visit-card" style="--visit-color:{color}"><div><strong>{escape(row["status"])}</strong><small>Presença registrada · {started}{end}</small></div><div><time>{_time_label(row["seconds"])}</time><small>Meta {_time_label(row["target"])}</small></div></div>')


_ROOM_CLOCK=st.components.v2.component('preparation_session_timer',html='<div class="clock"><div><small>SESSÃO DE PREPARO</small><strong class="clock-status"></strong></div><time></time></div>',css=':host{display:block}.clock{display:flex;align-items:center;justify-content:space-between;background:linear-gradient(110deg,#202020,#121212);border:1px solid #333;border-radius:16px;padding:16px 22px;color:#eee;font-family:Arial}.clock small{color:#aaa;font-size:10px;letter-spacing:1.5px}.clock strong{display:block;margin-top:8px;font-size:15px}.clock time{font-size:32px;font-weight:700;color:#ff9700;font-variant-numeric:tabular-nums}',js="""
export default function({data,parentElement,setStateValue}){
 const node=parentElement;
 if(node._clock){node._clock.data=data;node._clock.received=Date.now();node._clock.emit=setStateValue;return;}
 const doc=node.ownerDocument,c={data,received:Date.now(),emit:setStateValue};node._clock=c;
 const tick=()=>{
  const value=c.data,seconds=value.completed?Math.floor(value.seconds):Math.max(0,Math.ceil(value.remaining-(value.running?(Date.now()-c.received)/1000:0)));
  node.querySelector('time').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');
  node.querySelector('time').style.color=value.completed?'#39ca87':'#ff9700';
  node.querySelector('.clock-status').textContent=value.completed?'Trilha concluída':value.running?'Presença registrada · treino em andamento':'Sessão pausada';
 };
 const emit=()=>c.emit('heartbeat',{nonce:Date.now(),active:!doc.hidden});
 const hide=()=>c.emit('heartbeat',{nonce:Date.now(),active:false});
 doc.addEventListener('visibilitychange',emit);doc.defaultView.addEventListener('pagehide',hide);
 let count=0;const timer=setInterval(()=>{
  if(!(node.host??node).isConnected){clearInterval(timer);doc.removeEventListener('visibilitychange',emit);doc.defaultView.removeEventListener('pagehide',hide);return;}
  tick();if(++count%5===0)emit();
 },1000);tick();
}
""")


@st.fragment
def preparation_clock(token):
    import classroom_sessions
    def update():
        event=st.session_state.preparation_room_clock.heartbeat
        try:
            if event and event.get('active'):classroom_sessions.begin(token)
            classroom_sessions.heartbeat(token,bool(event and event.get('active')))
        except PermissionError:st.session_state.classroom_revoked=True
    status=classroom_sessions.current(token)
    if status:_ROOM_CLOCK(key='preparation_room_clock',data=status,height=105,on_heartbeat_change=update)
