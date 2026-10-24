"""Continuous tactics: background replenishment never refreshes the page or board."""
from html import escape

import chess
import sqlite3
import streamlit as st

from tactics import THEMES, fetch_puzzle_range
from tactics_preview import answer_preview

BUFFER_SIZE = 3


# A timed fragment cannot directly rerun another fragment. Hand off through a
# component callback, the supported keyed-rerun API, only for an active change.
_READY = st.components.v2.component('tactics_ready', html='<span hidden></span>', js='''
export default function({data,setTriggerValue}){
  if(data.ready && window._coachTacticsCurtain){window._coachTacticsCurtain.remove();window._coachTacticsCurtain=null;clearTimeout(window._coachTacticsCurtainTimer);}
  if(data.refresh)setTriggerValue('ready',data.tick);
}''')


def pump_tactics(state, queue_job, reset_puzzle, advance_puzzle):
    """Only request a visual update when the active puzzle actually changes."""
    active_changed = False
    for slot in ('puzzle', 'puzzle_next'):
        record = state.jobs.get(slot)
        if not record or not record[1].done():
            continue
        key, future = state.jobs.pop(slot)
        if key != state.puzzle_request:
            continue
        try:
            result = future.result()
            if slot == 'puzzle':
                state.puzzle = result
                reset_puzzle()
                active_changed = True
            else:
                occupied = {p.id for p in state.puzzle_buffer} | set(state.puzzle_seen)
                if state.puzzle:
                    occupied.add(state.puzzle.id)
                if result.id in occupied:
                    raise ValueError('O serviço repetiu um exercício. Tente preparar outro.')
                state.puzzle_buffer.append(result)
                if state.puzzle_waiting:
                    advance_puzzle()
                    active_changed = True
            state.job_errors.pop((slot, key), None)
        except Exception as error:
            from offline_tactics import LocalBankExhausted
            if (slot=='puzzle_next' and isinstance(error,LocalBankExhausted)
                    and state.puzzle_seen and error.available>len(state.puzzle_buffer)+1):
                # Start another local round, retaining the current and buffered IDs.
                state.puzzle_seen=[]
                state.job_errors.pop((slot,key),None)
            else:state.job_errors[(slot, key)] = str(error)
    if (state.puzzle and len(state.puzzle_buffer) < BUFFER_SIZE
            and ('puzzle_next', state.puzzle_request) not in state.job_errors):
        theme, minimum, maximum, _ = state.puzzle_request
        excluded = {state.puzzle.id} | {p.id for p in state.puzzle_buffer} | set(state.puzzle_seen)
        queue_job('puzzle_next', state.puzzle_request, fetch_puzzle_range,
                  theme, minimum, maximum, excluded)
    return active_changed


@st.fragment(run_every=.5)
def buffer_status(queue_job, reset_puzzle, advance_puzzle):
    state = st.session_state
    if state.tactic_theme is None or state.active_tab != 'Tático':
        return
    pump_tactics(state, queue_job, reset_puzzle, advance_puzzle)
    state.tactic_poll_tick = state.get('tactic_poll_tick', 0) + 1
    if state.puzzle:
        def skip():
            advance_puzzle();state.puzzle_notice='';state.tactic_streak=0
            st.rerun('tactics_workspace')
        st.button('Pular',icon=':material/skip_next:',key='tactics_skip',disabled=not state.puzzle_buffer,on_click=skip,width='stretch')
    st.caption(f'{len(state.puzzle_buffer)} prontos')
    error = state.job_errors.get(('puzzle_next' if state.puzzle else 'puzzle', state.puzzle_request))
    if error:
        st.caption(error)
        if st.button('Preparar novamente', key='tactics_retry', icon=':material/refresh:'):
            slot = 'puzzle_next' if state.puzzle else 'puzzle'
            state.job_errors.pop((slot, state.puzzle_request), None)
            if not state.puzzle:
                theme, minimum, maximum, _ = state.puzzle_request
                queue_job('puzzle', state.puzzle_request, fetch_puzzle_range, theme, minimum, maximum)

    _READY(data={'refresh':state.puzzle_revision != state.get('puzzle_render_revision'),
                 'tick':state.tactic_poll_tick,'ready':bool(state.puzzle) or bool(state.job_errors.get(('puzzle',state.puzzle_request)))}, key='tactics_ready', height=0,
           on_ready_change=lambda:st.rerun('tactics_workspace'))


def style():
    st.html("""<style>
    .st-key-tactics_workbench{max-width:1380px;margin:auto;gap:18px}
    .tactics-kicker{font:600 10px system-ui;letter-spacing:2px;color:#bb9f70;margin:0 0 8px}.tactics-title{font:550 clamp(22px,3vw,31px)/1.25 system-ui;color:#e9eddf;margin:0;letter-spacing:-.6px}
    .st-key-tactics_board_panel{padding:10px;background:#121811;border:1px solid #384132;border-radius:14px;box-shadow:0 12px 32px #0004}
    .st-key-tactics_board_panel [data-stale=true]{opacity:1!important}.st-key-tactics_board_panel .board-floor{padding:0!important}
    .st-key-tactics_coach{padding:24px;border:1px solid #3d4435;border-radius:18px;background:linear-gradient(145deg,#20271e,#141a13);box-shadow:inset 0 1px #ffffff08,0 12px 32px #0003;gap:14px}
    .tactics-meta{font:11px system-ui;color:#899b80;margin:0}.tactics-status{font:12px system-ui;color:#adbb9d;min-height:18px}.tactics-status p{margin:0}
    .st-key-tactics_actions [data-testid=stHorizontalBlock]{gap:7px}.st-key-tactics_actions button{min-height:37px;font-size:12px;border-radius:10px;padding:5px 8px;background:#252e21;border-color:#45523b;color:#c5d2b9}.st-key-tactics_actions [data-testid=stCaptionContainer] p{font-size:10px;color:#86977b}
    .st-key-tactics_footer{padding:12px 2px;border-top:1px solid #ffffff0c}.st-key-tactics_footer p{font-size:11px;color:#89997f}.tactics-preparing{min-height:450px;display:grid;place-content:center;color:#9da78e;font:12px system-ui;letter-spacing:2px;background:#080b08}
    @media(max-width:700px){.st-key-tactics_coach{padding:20px}.st-key-tactics_board_panel{padding:5px}}
    @media(prefers-reduced-motion:reduce){.st-key-tactics_workbench *{animation:none!important;transition:none!important}}
    </style>""")


def render_workspace(choose_theme,reset_puzzle,puzzle_changed,advance_puzzle,queue_job,on_sync=None):
    from time import perf_counter
    from uuid import uuid4
    from interactive_board import interactive_board
    from tactics_progress import owner_for,summary
    from tactics_dashboard import render_stats
    state=st.session_state
    style()
    with st.container(key='tactics_workbench'):
        if state.tactic_theme is None:
            from tactics_orbit import render_orbit
            if not state.get('tactics_orbit_token'):state.tactics_orbit_token=uuid4().hex
            render_orbit(choose_theme,state.tactics_orbit_token)
            return
        theme_names={theme:label for label,theme in THEMES.items()}
        title,back=st.columns([4,1],vertical_alignment='center')
        with title:st.html('<p class="tactics-kicker">TÁTICOS</p><h2 class="tactics-title">'+escape(theme_names[state.tactic_theme])+'</h2>')
        back.button('Temas',icon=':material/blur_circular:',on_click=choose_theme,args=(None,),width='stretch')
        result=None
        minimum=state.get('rating_min') if state.get('rating_min') is not None else 0
        maximum=state.get('rating_max') if state.get('rating_max') is not None else 4000
        if minimum>maximum:
            st.error('A dificuldade mínima deve ser menor que a máxima.')
        else:
            request_key=state.tactic_theme,minimum,maximum,state.puzzle_nonce
            if request_key!=state.puzzle_request:
                for slot in ('puzzle','puzzle_next'):
                    if record:=state.jobs.pop(slot,None):record[1].cancel()
                state.puzzle_request,state.puzzle=request_key,None
                state.puzzle_buffer,state.puzzle_seen=[],[]
                reset_puzzle()
                queue_job('puzzle',request_key,fetch_puzzle_range,state.tactic_theme,minimum,maximum)
            pump_tactics(state,queue_job,reset_puzzle,advance_puzzle)
            state.puzzle_render_revision=state.puzzle_revision
            left,right=st.columns([1.8,1],gap='large')
            puzzle=state.puzzle
            with left,st.container(key='tactics_board_panel'):
                if puzzle:
                    board=chess.Board(puzzle.fen);player=board.turn
                    for move in puzzle.solution[:state.puzzle_progress]:board.push_uci(move)
                    done=state.puzzle_progress==len(puzzle.solution)
                    last=board.peek() if board.move_stack else chess.Move.from_uci(puzzle.last_move) if puzzle.last_move else None
                    result=interactive_board(board,flip=not player,on_move=puzzle_changed,on_sync=on_sync,key='puzzle_board',disabled=done,
                        revision=state.puzzle_revision,dark=True,table=False,last_move=last,stable_board=True,training_mode=True,
                        training_expected=None if done else puzzle.solution[state.puzzle_progress],training_feedback=state.get('puzzle_feedback'),
                        hint_move=state.get('puzzle_hint'),training_preview=answer_preview(puzzle.fen,tuple(puzzle.solution),state.puzzle_progress),show_coordinates=True)
                else:st.html('<div class="tactics-preparing">PREPARANDO TABULEIRO</div>')
            with right,st.container(key='tactics_coach'):
                try:stats=summary(owner_for(state),state.tactic_theme,session=state.get('tactic_session_id'))
                except (OSError,sqlite3.Error):
                    st.error('Não foi possível abrir seu histórico tático.');stats=None
                if stats:
                    running=bool(puzzle and state.puzzle_progress<len(puzzle.solution))
                    elapsed=(max(0,perf_counter()-state.get('tactic_clock_started',perf_counter()))
                             if running else state.get('tactic_last_seconds',0) if puzzle else 0)
                    render_stats(stats,elapsed,running,state.get('tactic_clock_key'))
                # One persistent status slot keeps all board nodes in place.
                message=''
                if state.get('puzzle_feedback',{}):
                    message='Correto' if state.puzzle_feedback.get('correct') else 'Tente outra ideia'
                st.html('<div class="tactics-status" role="status">'+escape(message)+'</div>')
                with st.container(key='tactics_actions'):
                    hint,restart,skip=st.columns(3,gap='small')
                    with hint:
                        def show_hint():
                            if puzzle and state.puzzle_progress<len(puzzle.solution):
                                state.puzzle_hint=puzzle.solution[state.puzzle_progress];state.puzzle_failed_ids.add(puzzle.id);state.tactic_streak=0
                        st.button('Dica',icon=':material/lightbulb:',width='stretch',on_click=show_hint,disabled=not puzzle or state.puzzle_progress==len(puzzle.solution))
                    with restart:st.button('Recomeçar',icon=':material/replay:',on_click=reset_puzzle,width='stretch',disabled=not puzzle)
                    with skip:buffer_status(queue_job,reset_puzzle,advance_puzzle)
                if state.get('tactic_save_error'):st.caption(state.tactic_save_error)
        with st.container(key='tactics_footer',horizontal=True,vertical_alignment='center'):
            if state.puzzle:st.caption(f'Lichess · {state.puzzle.rating} · Offline')
            with st.popover('Ajustes',icon=':material/tune:'):
                def change_theme():choose_theme(state.tactic_menu)
                st.selectbox('Tema',list(theme_names),index=list(theme_names).index(state.tactic_theme),format_func=theme_names.get,key='tactic_menu',on_change=change_theme)
                low,high=st.columns(2)
                low.number_input('Rating mínimo',min_value=0,max_value=4000,value=None,step=100,key='rating_min',placeholder='Livre')
                high.number_input('Rating máximo',min_value=0,max_value=4000,value=None,step=100,key='rating_max',placeholder='Livre')
    # Persisted component values survive a simultaneous background refresh.
    # Revisions make this fallback idempotent when the callback already ran.
    if on_sync is not None and result is not None:
        for field in ('move','sync'):
            event=getattr(result,field,None)
            if isinstance(event,dict) and event.get('revision')==state.puzzle_revision:
                before=state.puzzle_revision
                puzzle_changed(event)
                if state.puzzle_revision!=before:st.rerun(scope='fragment')
