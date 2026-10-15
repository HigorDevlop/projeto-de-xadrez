"""Automatic position recall in preparation, isolated from free opening lessons."""
import time
import chess
import streamlit as st

from interactive_board import interactive_board
from preparation_repetition import (repertoire_session, current_exercise, revision,
    submit_repertoire, counts)


STYLE = '''
.stApp:has(.repertoire-focus) [data-testid="stSidebar"],
.stApp:has(.repertoire-focus) [data-testid="stHeader"],
.stApp:has(.repertoire-focus) .st-key-question_launcher,
.stApp:has(.repertoire-focus) .st-key-navigation_back,
.stApp:has(.repertoire-focus) .st-key-workspace_identity,
.stApp:has(.repertoire-focus) .st-key-page_heading{display:none!important}
.stApp:has(.repertoire-focus) .stMainBlockContainer{max-width:800px;padding:24px 20px 28px}
.stApp:has(.repertoire-focus){background:#081219!important;--chess-ink:#f5f5f5;--chess-muted:#9ba4a9;--chess-border:#252e34;--chess-accent:#ff8500}
.st-key-repertoire_focus{width:min(100%,640px,calc(100dvh - 360px))!important;margin-inline:auto;color:#f5f5f5}
.st-key-repertoire_focus h3,.st-key-repertoire_exit button{color:#f5f5f5!important}
.st-key-repertoire_header{gap:8px!important;position:relative;padding:0 48px;min-height:40px;justify-content:center}
.st-key-repertoire_header h3{font:600 20px/1.3 'Segoe UI',sans-serif!important;text-align:center;letter-spacing:0!important;padding:0!important}
.st-key-repertoire_exit{position:absolute;left:0;top:0}
.st-key-repertoire_exit button{border:0!important;background:transparent!important;min-width:40px}
.st-key-repertoire_exit button p{font-size:0!important}
.repertoire-mode{color:var(--chess-muted);font:500 12px/1.4 'Segoe UI',sans-serif;text-align:center;margin:0}
.repertoire-progress{height:5px;border-radius:6px;overflow:hidden;background:var(--chess-border);margin:6px 0 10px}
.repertoire-progress span{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,#dc4700,#ff8a00);transition:width .2s}
.repertoire-prompt{background:#232c32;padding:12px 8px;text-align:center;font:600 16px/1.4 'Segoe UI',sans-serif;color:#f5f5f5}
.repertoire-counters{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}
.repertoire-counter{text-align:center;font:600 11px/1.4 'Segoe UI',sans-serif;color:var(--counter)}
.repertoire-counter strong{display:block;background:var(--counter-bg);color:white;font-size:24px;border-radius:12px;padding:12px 4px;margin-top:6px}
.repertoire-marks{display:flex;justify-content:center;gap:10px;margin:14px 0;flex-wrap:wrap}
.repertoire-mark{width:24px;height:24px;border-radius:6px;background:#242d33}
.repertoire-mark.correct{background:#58bd12}.repertoire-mark.wrong{background:#c53e52}.repertoire-mark.unknown{background:#bb810e}
.st-key-repertoire_coach{min-height:72px;justify-content:center;text-align:center}
.repertoire-instruction{font:500 16px/1.4 'Segoe UI',sans-serif;color:var(--chess-ink);margin:0;text-align:center}
.repertoire-instruction.correct{color:white;background:#439516;padding:16px;width:100%;border-radius:4px}
.repertoire-instruction.wrong{color:var(--chess-ink)}
.repertoire-explanation{font:13px/1.4 'Segoe UI',sans-serif;color:var(--chess-muted);text-align:center;margin:5px 0 0}
.st-key-repertoire_actions{min-height:46px;justify-content:center}
.st-key-repertoire_actions button{min-height:44px;border-radius:12px!important}
.st-key-repertoire_actions button[kind="primary"]{background:linear-gradient(100deg,#d74400,#ff8800)!important;color:white!important;border:0!important}
.st-key-repertoire_actions button[kind="secondary"]{background:#242d33!important;color:#f5f5f5!important;border:0!important}
@media(min-width:900px){
 .stApp:has(.repertoire-focus) .stMainBlockContainer{max-width:1240px;padding:24px 32px 36px}
 .st-key-repertoire_focus{width:min(100%,1040px)!important}
}
@media(max-width:640px){
 .stApp:has(.repertoire-focus) .stMainBlockContainer{padding:16px 12px 24px}
 .st-key-repertoire_focus{width:100%!important;max-width:480px}
 .st-key-repertoire_header h3{font-size:18px!important}
}
@media(max-height:600px) and (max-width:899px){.st-key-repertoire_focus{width:min(100%,480px)!important}}
@media(prefers-reduced-motion:reduce){.repertoire-progress span{transition:none}}

.st-key-repertoire_focus{width:min(100%,1040px)!important;gap:8px!important}
.st-key-repertoire_board{width:min(100%,max(180px,calc(100dvh - 240px)),780px)!important;margin-inline:auto}
.st-key-repertoire_focus:has(.repertoire-counters) .st-key-repertoire_board{width:min(100%,max(180px,calc(100dvh - 240px)),780px)!important}
.stApp:has(.repertoire-focus) [data-testid="stSidebarCollapsedControl"]{display:none!important}
@media(max-width:640px){.st-key-repertoire_header h3{font-size:18px!important}.st-key-repertoire_coach{min-height:60px}}
body:has(.repertoire-result) [data-testid="stDialog"]{backdrop-filter:blur(8px);background:#20302724}
body:has(.repertoire-result) [role="dialog"]{border-radius:20px;border:1px solid var(--chess-border)}
'''


def render_progress(session):
    result = counts(session)
    st.caption(f"Erro: {result['error']} · Não sei: {result['learning']} · Correto: {result['correct']} · A fazer: {result['unanswered']}")
    st.progress(result['correct'] / result['total'] if result['total'] else 1.0,
                text=f"{result['correct']} / {result['total']} posições dominadas")


def render_feedback(session):
    feedback = session.get('feedback')
    if feedback:
        if not feedback['correct']:
            st.caption('Jogada incorreta. Essa posição aparecerá novamente.')
        elif feedback['status'] == 'correct':
            st.caption('Posição dominada. Correto!')
        else:
            st.caption('Boa jogada. Essa posição aparecerá novamente para confirmar o aprendizado.')


@st.fragment
def render_guided_training(plan, save, reset, back_to_trail, dark, active_key='prep_repertoire_active'):
    state = st.session_state
    session = repertoire_session(plan)
    if session is None:
        back_to_trail()
        st.rerun()
    if session['phase'] == 'complete':
        st.rerun()

    def answer():
        live = repertoire_session(plan)
        if live and submit_repertoire(plan, live, state.prep_repertoire_board.move, time.time()):
            save(plan)

    exercise = current_exercise(session)
    with st.container(key='repertoire_focus', gap='xsmall'):
        with st.container(key='repertoire_header', gap=None):
            st.button('Voltar à trilha', icon=':material/arrow_back:', type='tertiary',
                      on_click=back_to_trail, key='repertoire_exit', width=40)
            st.subheader(exercise['opening'], anchor=False)
        if not state.get(active_key):
            st.rerun()
        with st.container(key='repertoire_board'):
            interactive_board(chess.Board(exercise['fen']), key='prep_repertoire_board',
                on_move=answer, revision=revision(session),
                flip=exercise['side'] == 'black', dark=True, training_mode=True, show_coordinates=True)
        st.write('Jogue com as brancas.' if exercise['side'] == 'white' else 'Jogue com as pretas.')
        render_feedback(session)
        render_progress(session)
