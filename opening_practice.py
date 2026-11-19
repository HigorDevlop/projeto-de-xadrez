"""Opening courses with independent, persistent progress for each repertoire."""
from html import escape
import chess
import streamlit as st

from opening_home_ui import opening_home
from opening_repertoires import selected_courses
from opening_course_state import (select_course, ensure_course, course_lines,
    begin_line)
from opening_course_ui import STYLE, render_trail, rank_card, render_lesson, scroll_course_top
from preparation_state import today, load_plan, save_plan
from opening_reference_progress import position_progress
from opening_reference_catalog import display_name, eco_paths
from opening_reference_pages import celebrate, profile
from opening_reference_style import title_html


def render_opening_practice(username, dark=False):
    dark = True
    username = username or ''
    chesscom_account = username
    state = st.session_state
    import classroom
    from classroom_ui import training_token
    classroom_token=training_token()
    actor=classroom.identity(classroom_token)
    if classroom_token and not actor:
        st.error('Acesso à sala revogado. Procure o Professor.');return
    task=classroom.routine(classroom_token) if actor and actor['role']=='student' else None
    if actor and actor['role']=='student':
        username='classroom:'+actor['id']
    elif actor and actor['role']=='user':
        username='user:'+actor['id']
    if state.get('openings_owner') != username:
        state.openings_owner = username
        state.openings_plan = load_plan(username, namespace='openings')
        state.openings_active = False
        state.openings_catalog = True
        state.pop('openings_save_error', None)

    def save(plan):
        state.openings_plan = plan
        try:
            save_plan(plan, namespace='openings')
            state.pop('openings_save_error', None)
        except OSError:
            state.openings_save_error = 'Seu treino está nesta sessão, mas não foi possível salvá-lo neste computador.'

    def back():
        state.openings_active = False
        state.openings_scroll_top = True

    def catalog():
        back()
        state.openings_catalog = True

    def start_opening(event=None):
        if event is None:
            event = state.openings_home.select
        if isinstance(event, dict) and event.get('action') in ('profile','streak'):
            state.openings_overlay=event['action']
            return
        if not isinstance(event, dict) or not isinstance(event.get('id'), str):
            return
        if actor and actor['role']=='student' and (not task or event['id'] not in task['openings']):
            return
        try:
            plan = select_course(state.get('openings_plan'), username, event['id'])
        except (ValueError, TypeError):
            return
        ensure_course(plan)
        if task:
            plan['classroom_line_ids']=task['line_ids']
            ensure_course(plan)
        state.openings_plan = plan
        state.openings_catalog = False
        state.openings_active = False
        state.openings_scroll_top = True
        state.openings_course_tab = 'Curso'
        intent = event.get('intent')
        if intent in ('learn', 'master'):
            lines = course_lines(plan)
            candidates = ([line for line in lines if line['learned']] if intent == 'master'
                          else [line for line in lines if line['unlocked'] and not line['learned']])
            if intent == 'learn' and not candidates:
                intent = 'master'
                candidates = [line for line in lines if line['learned']]
            if intent == 'master':
                candidates.sort(key=lambda line: (line['due'] or '', line['mastery']))
            if candidates and begin_line(plan, candidates[0]['id'], intent):
                state.openings_active = True
        save(plan)

    if request:=state.pop('room_opening_request',None):
        start_opening(request)
    plan = state.get('openings_plan')
    if actor and actor['role']=='student':
        if not task:
            st.info('Seu Professor ainda não definiu a rotina.');return
        if plan:
            plan['classroom_line_ids']=task['line_ids']
            if any(key not in task['openings'] for key in plan['repertoire_ids']):
                state.openings_plan=None;plan=None
                state.openings_active=False;state.openings_catalog=True
            elif state.get('openings_active'):
                from opening_course_state import active_session
                live=active_session(plan)
                if live and live.get('line_id') not in task['line_ids']:
                    state.openings_active=False
        if not state.get('openings_active'):
            from classroom_ui import student_routine
            student_routine(classroom_token,start_opening,lambda:state.update(requested_page='Tático'))
    # Keep compatibility with saved free-practice sessions across dates.
    if plan and plan['start'] != str(today()):
        previous = plan['training_days'].get(plan['start'])
        plan['start'] = plan['end'] = str(today())
        plan['training_days'] = {str(today()): previous} if previous else {}
        if previous:
            previous['day'] = str(today())
        save(plan)
    st.html('<span class="opening-course-mode" hidden></span><style>' + STYLE + '</style>')
    def close_overlay():
        overlay=state.pop('openings_overlay',None)
        if overlay in ('award','streak_reward'):
            if overlay=='award' and plan.get('reference_streak_seen')!=str(today()):
                plan['reference_streak_seen']=str(today());save(plan)
                state.openings_overlay='streak_reward'
                return
            identifier=state.pop('reference_next_line',None)
            if identifier:
                session=begin_line(plan,identifier,'train')
                if session:
                    session['reference_mode']=True
                    state.openings_active=True;save(plan)

    overlay=state.get('openings_overlay')
    if overlay:
        st.button('Fechar',icon=':material/close:',type='tertiary',on_click=close_overlay)
        if overlay=='profile':
            profile(state.get('history_games',[]),chesscom_account)
        else:
            celebrate(plan,overlay,close_overlay)
    elif state.get('openings_endgames'):
        from opening_reference_endgames import render_endgames
        render_endgames()
    elif not plan or state.get('openings_catalog') or ('personal_lines' in plan and not state.get('openings_active')):
        opening_home(plan,start_opening,allowed_ids=task['openings'] if task else None)
    elif state.get('openings_active'):
        render_lesson(plan,save,back,dark)
        if state.pop('openings_scroll_top',False): scroll_course_top()
    else:
        ensure_course(plan)
        courses=selected_courses(plan['repertoire_ids'])
        title=' · '.join(display_name(course) for course in courses)

        def start(identifier,intent):
            from opening_training_state import lines_for
            line=lines_for(plan).get(identifier)
            from opening_rounds import cycle,next_lesson,target
            if cycle(plan) is not None and intent=='train':
                available,source=next_lesson(plan,list(lines_for(plan).values()))
                if not source: return
                if not available:
                    from opening_levels_ui import request_level
                    request_level(plan,source,target(plan)[0],auto_start=True)
                    return
                identifier=available['id'];line=available
            if line and line.get('needs_preparation'):
                from opening_levels_ui import request_level
                request_level(plan,line,5,auto_start=True)
                return
            session=begin_line(plan,identifier,intent)
            if session:
                session['reference_mode']=True
                state.openings_active=True
                state.openings_scroll_top=True
                save(plan)

        def select_line():
            event=state.openings_trail.select
            from opening_rounds import cycle,phase_number
            if (isinstance(event,dict) and event.get('token')==plan['created'] and
                    (cycle(plan) is None or event.get('phase')==phase_number(plan))):
                start(event.get('id'),'train')

        with st.container(key='opening_course'):
            with st.container(horizontal=True):
                st.button('Todas as aberturas',on_click=catalog,type='tertiary',icon=':material/chevron_left:')
                st.button('Sequência diária',on_click=lambda:state.update(openings_overlay='streak'),type='tertiary',icon=':material/local_fire_department:')
                st.button('Perfil',on_click=lambda:state.update(openings_overlay='profile'),type='tertiary',icon=':material/person:')
                from opening_achievements_ui import render_achievements
                render_achievements(plan,compact=True)
            st.html(title_html(title,medal=False))
            rank_card(plan)
            from opening_levels_ui import render_levels
            if not task:
                render_levels(plan,save,start)
            if state.get('openings_course_tab') not in ('Curso','Armadilhas','Variações'):
                state.openings_course_tab='Curso'
            tab=st.segmented_control('Etapa do curso',['Curso','Armadilhas','Variações'],default='Curso',
                key='openings_course_tab',label_visibility='collapsed',width='stretch') or 'Curso'
            lines=course_lines(plan)
            if not lines:
                st.info('Não há linhas válidas nesta seleção. Atualize as linhas da rotina para esta abertura.')
                return
            if tab=='Curso':
                known,total=position_progress(plan)
                target=min(25,total)
                foundations=sum(line.get('stage')=='foundation' for line in lines)
                if not foundations:
                    st.html(f'<div class="reference-banner"><small>SUA TRILHA</small><h3>Aprenda e revise as posições do curso.</h3></div>')
                render_trail(plan,select_line)
                from opening_rounds import cycle,next_lesson
                available,source=next_lesson(plan,lines)
                candidates=[available or source] if cycle(plan) is not None and source else [line for line in lines if line['unlocked'] and not line['learned']] if cycle(plan) is None else []
                if candidates:
                    st.button('Treinar',type='primary',width='stretch',on_click=start,args=(candidates[0]['id'],'train'))
                learned=[line for line in lines if line['learned']]
                if learned:
                    st.button('Revisar posições aprendidas',width='stretch',on_click=start,args=(min(learned,key=lambda line:line['mastery'])['id'],'practice'))
            elif tab=='Variações':
                for line in lines:
                    with st.expander(line.get('variation') or f"Linha {line['number']} · {title}"):
                        board,notation=chess.Board(),[]
                        for ply,uci in enumerate(line['moves']):
                            move=chess.Move.from_uci(uci)
                            notation.append((f'{ply//2+1}. ' if ply%2==0 else '')+board.san(move));board.push(move)
                        st.write(' '.join(notation))
                        st.button('Explorar no tabuleiro',key='explore_'+line['id'],on_click=start,args=(line['id'],'explore'),width='stretch')
            else:
                prefix=tuple(lines[0].get('family_prefix',lines[0]['moves'][:2]))
                traps=[(moves,name) for moves,name in eco_paths() if 'trap' in name.lower() and moves[:2]==prefix]
                if not traps:
                    st.info('Não há armadilhas cadastradas para esta abertura. As linhas do curso estão em Variações.')
                for number,(moves,name) in enumerate(traps[:12]):
                    with st.expander(name):
                        board,notation=chess.Board(),[]
                        for uci in moves:
                            move=chess.Move.from_uci(uci);notation.append(board.san(move));board.push(move)
                        st.write(' '.join(notation))
                        if st.button('Estudar armadilha',key=f'trap_{number}',width='stretch'):
                            identifier=lines[0]['id']
                            plan['practice_sessions'].pop(identifier+':explore',None)
                            session=begin_line(plan,identifier,'explore')
                            path=list(moves)
                            if len(path)%2==(0 if lines[0]['side']=='white' else 1): path.pop()
                            session['custom_line']=dict(id=identifier,moves=path,side=lines[0]['side'],opening=name)
                            session.update(reference_mode=True,mode='learn',ply=0,history=[],hint=lines[0]['side']=='white',phase='answer' if lines[0]['side']=='white' else 'opponent')
                            state.openings_active=True;save(plan);st.rerun()
        if state.pop('openings_scroll_top',False): scroll_course_top()

    def navigate(destination):
        if destination=='Aberturas':
            state.openings_endgames=False
            state.pop('openings_overlay',None);catalog()
        elif destination=='Finais':
            state.openings_endgames=True
            state.pop('openings_overlay',None)
        else:
            state.openings_endgames=False
            state.requested_page=destination

    if not state.get('openings_active') and not state.get('openings_overlay'):
        with st.container(key='reference_footer',horizontal=True,horizontal_alignment='distribute'):
            for label,destination in [('Finais','Finais'),('Aberturas','Aberturas'),('Partidas','Partida'),('Puzzles','Tático')]:
                st.button(label,icon=':material/'+{'Finais':'emoji_events','Aberturas':'school','Partida':'grid_on','Tático':'extension'}[destination]+':',key='reference_nav_'+destination,type='primary' if destination=='Aberturas' and not state.get('openings_endgames') else 'tertiary',on_click=navigate,args=(destination,))
    if state.get('openings_save_error'): st.warning(state.openings_save_error)
