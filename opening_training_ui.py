"""Catalogue, daily trail and automatic opening practice for closed courses."""
from datetime import date, timedelta
import time
import streamlit as st

from interactive_board import interactive_board
from opening_catalog_ui import repertoire_catalog
from opening_training_state import (create_repertoire_plan, session_for, current_line,
    board_for, expected_move, submit_move, advance)
from preparation_ui import roadmap
from preparation_state import today
from preparation_repetition import repertoire_session, counts
from opening_transition import transition


STYLE = '''
.stApp:has(.repertoire-focus) [data-testid="stSidebar"],
.stApp:has(.repertoire-focus) [data-testid="stHeader"],
.stApp:has(.repertoire-focus) [data-testid="stSidebarCollapsedControl"],
.stApp:has(.repertoire-focus) .st-key-question_launcher,
.stApp:has(.repertoire-focus) .st-key-navigation_back,
.stApp:has(.repertoire-focus) .st-key-workspace_identity,
.stApp:has(.repertoire-focus) .st-key-page_heading{display:none!important}
.stApp:has(.repertoire-focus){background:#081219!important;--chess-ink:#f5f5f5;--chess-muted:#9ba4a9}
.stApp:has(.repertoire-focus) .stMainBlockContainer{max-width:100%;padding:12px 12px 0!important}
.st-key-repertoire_focus{width:min(100%,calc(100dvh - 100px),900px)!important;margin-inline:auto;gap:8px!important}
.st-key-repertoire_focus button{color:#f5f5f5!important}
.st-key-repertoire_focus [data-testid="stElementContainer"]{margin:0!important}
.st-key-repertoire_cancel{display:flex;justify-content:center}
.st-key-repertoire_cancel button{min-height:38px;background:#232c32!important;border:1px solid #39454b!important}
.stApp:has(.repertoire-trail){background:#081219!important;--chess-ink:#f5f5f5;--chess-muted:#9ba4a9;--chess-border:#252e34;--chess-surface:#232c32;--chess-accent:#ff8500}
'''



def render_repertoire_preparation(username, save, reset, dark=False):
    state = st.session_state
    st.html('<style>' + STYLE + '</style>')

    def confirm():
        event = state.prep_catalog.confirm
        if not isinstance(event, dict):
            return
        try:
            plan = create_repertoire_plan(username, event.get('ids'), event.get('start'), event.get('end'))
        except (ValueError, TypeError):
            state.prep_catalog_error = 'Confira as datas e selecione de 1 a 4 aberturas.'
            return
        state.prep_plan = plan
        state.prep_selected_openings = list(plan['repertoire_ids'])
        state.prep_repertoire_active = True
        state.pop('prep_catalog_error', None)
        save(plan)

    plan = state.get('prep_plan')
    if not plan:
        repertoire_catalog_dates(confirm, dark)
        if state.get('prep_catalog_error'):
            st.error(state.prep_catalog_error)
        return
    current = today()
    session = repertoire_session(plan, current)
    if session:
        save(plan)

    def back_to_trail():
        state.prep_repertoire_active = False

    if session and state.get('prep_repertoire_active'):
        st.html('<span class="repertoire-focus" hidden></span>')
        if session['phase'] == 'complete':
            with st.container(key='repertoire_focus', gap='xsmall'):
                st.subheader('Preparo do dia concluído')
                if current_line(plan, session):
                    interactive_board(board_for(session), key='prep_repertoire_finished', on_move=lambda: None,
                        disabled=True, flip=current_line(plan, session)['side'] == 'black', dark=dark)
            _result(session, reset, back_to_trail)
        else:
            _training(plan, save, reset, back_to_trail, dark)
    else:
        st.html('<span class="repertoire-trail" hidden></span>')
        start, end = date.fromisoformat(plan['start']), date.fromisoformat(plan['end'])

        def open_day():
            event = state.prep_roadmap.select
            if (isinstance(event, dict) and event.get('plan') == plan['created']
                    and event.get('day') == str(today())):
                live = session_for(plan)
                if live and live['phase'] != 'complete':
                    state.prep_repertoire_active = True

        roadmap(plan, open_day, dark)
        if current < start:
            st.caption(f'Seu treino começa em {start:%d/%m}.')
        elif current > end:
            st.success('Trilha encerrada.')
        if st.button('Cancelar preparo', key='repertoire_cancel_plan'):
            if reset():
                st.rerun()
    if state.get('prep_save_error'):
        st.warning(state.prep_save_error)


def repertoire_catalog_dates(on_confirm, dark):
    # Date changes preserve the component's local card selection.
    with st.expander('Período do preparo', expanded=False):
        left, right = st.columns(2)
        start = left.date_input('Data de início', value=today(), key='prep_start', persist_state='session')
        end = right.date_input('Data de término', value=today()+timedelta(days=6), key='prep_end', persist_state='session')
        if end < start or (end-start).days > 365:
            st.error('Escolha um período válido de até um ano.')
    repertoire_catalog(start, end, on_confirm, dark, instant=True)


@st.dialog('Fim do preparo do dia', width='small', dismissible=False)
def _result(session, reset, back_to_trail):
    st.html('<span class="repertoire-result"></span>')
    result = counts(session)
    st.metric('Posições dominadas', f"{result['correct']} / {result['total']}")
    st.progress(result['correct'] / result['total'] if result['total'] else 1.0)
    if st.button('Avançar na trilha', type='primary', width='stretch'):
        back_to_trail()
        st.rerun()
    if st.button('Iniciar novo preparo', width='stretch'):
        if reset():
            st.rerun()


def _training(plan, save, reset, back_to_trail, dark, active_key='prep_repertoire_active'):
    if active_key == 'prep_repertoire_active':
        from opening_preparation_training import STYLE as GUIDED_STYLE, render_guided_training
        st.html('<style>' + GUIDED_STYLE + '</style>')
        render_guided_training(plan, save, reset, back_to_trail, dark, active_key)
    else:
        _free_training(plan, save, reset, back_to_trail, dark, active_key)


@st.fragment
def _free_training(plan, save, reset, back_to_trail, dark, active_key='prep_repertoire_active'):
    state = st.session_state
    session = session_for(plan)
    if session is None:
        back_to_trail()
        st.rerun()
    if advance(plan, session, time.time()):
        save(plan)
    if session['phase'] == 'complete':
        st.rerun()

    def answer():
        live = session_for(plan)
        if live and submit_move(plan, live, state.prep_repertoire_board.move, time.time()):
            save(plan)

    def on_tick():
        live = session_for(plan)
        event = state.opening_transition.tick
        if live and event == f"{live['token']}:{live['revision']}":
            if advance(plan, live, max(time.time(), live['next_at'])):
                save(plan)

    line = current_line(plan, session)
    board = board_for(session)
    expected = expected_move(plan, session)
    show_hint = session.get('mode') == 'learn' and session['phase'] == 'answer'
    with st.container(key='repertoire_focus', gap='xsmall'):
        interactive_board(board, key='prep_repertoire_board', on_move=answer,
            revision=f"{session['token']}:{session['revision']}",
            disabled=session['phase'] != 'answer', flip=line['side'] == 'black', dark=True,
            last_move=board.peek() if board.move_stack else None,
            hint_move=expected if show_hint else None,
            training_feedback=session['feedback'], training_mode=True,
            training_expected=expected if session['phase'] == 'answer' else None,
            animate_move=session.get('animation'))
        with st.container(key='repertoire_cancel', horizontal=True, horizontal_alignment='center'):
            st.button('Cancelar preparo', on_click=back_to_trail, key='repertoire_exit')
        if not state.get(active_key):
            st.rerun()
        transition(session, on_tick)

