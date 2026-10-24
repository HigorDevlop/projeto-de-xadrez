"""Position editing for the analysis board, with explicit save/cancel."""
import chess
import chess.pgn
import streamlit as st

from study_workspace import apply_position_edit
from analysis_editor_palette import render as render_palette


def _castling_flags():
    state = st.session_state
    for symbol in 'KQkq':
        state[f'analysis_roque_{symbol}'] = symbol in state.analysis_edit_castling


def castling_changed():
    state = st.session_state
    state.analysis_edit_castling = [c for c in 'KQkq' if state.get(f'analysis_roque_{c}', False)]


def begin(board):
    state = st.session_state
    state.analysis_editing = True
    state.analysis_draft = board.fen()
    state.analysis_edit_turn = 'Brancas' if board.turn else 'Pretas'
    state.analysis_edit_castling = list(board.castling_xfen().replace('-', ''))
    _castling_flags()
    state.analysis_edit_tool = 'move'
    state.board_revision += 1
    state.pop('analysis_edit_error', None)


def changed(event=None):
    state = st.session_state
    if event is None:
        event = state.interactive_board.edit
    if not state.get('analysis_editing') or not isinstance(event, dict):
        return
    if event.get('revision') != state.board_revision or event.get('fen') != state.analysis_draft:
        return
    try:
        state.analysis_draft = apply_position_edit(state.analysis_draft, event)
        # Moving/removing a king or rook also clears the now-impossible roque.
        available = chess.Board(state.analysis_draft).castling_xfen()
        state.analysis_edit_castling = [c for c in state.analysis_edit_castling if c in available]
        _castling_flags()
        state.pop('analysis_edit_error', None)
    except (ValueError, KeyError) as error:
        state.analysis_edit_error = str(error)
    state.board_revision += 1


def sync():
    changed(st.session_state.interactive_board.sync)


def reset(empty=False):
    state = st.session_state
    state.analysis_draft = (chess.Board(None) if empty else chess.Board()).fen()
    state.analysis_edit_castling = [] if empty else list('KQkq')
    _castling_flags()
    state.analysis_edit_turn = 'Brancas'
    state.board_revision += 1


def cancel():
    st.session_state.analysis_editing = False
    st.session_state.board_revision += 1
    st.session_state.pop('analysis_edit_error', None)


def save(reset_game):
    state = st.session_state
    board = chess.Board(state.analysis_draft)
    turn = state.analysis_edit_turn == 'Brancas'
    if board.turn != turn:
        board.ep_square = None
    board.turn = turn
    board.set_castling_fen(''.join(c for c in 'KQkq' if c in state.analysis_edit_castling) or '-')
    if not board.is_valid():
        state.analysis_edit_error = 'Confira a posição: um rei de cada cor, peões fora da primeira e oitava fileiras, lado a jogar e roques válidos.'
        return
    game = chess.pgn.Game()
    game.setup(board)
    reset_game(game)
    state.analysis_editing = False
    state.pop('analysis_edit_error', None)


def controls(reset_game):
    state = st.session_state
    with st.container(border=True, key='analysis_editor_controls', gap='small'):
        st.subheader('Monte sua posição', anchor=False)
        st.caption('Arraste qualquer peça para qualquer casa. Para adicionar, selecione uma peça na paleta e clique no tabuleiro.')
        pieces, settings = st.columns([1.4, 1], gap='medium')
        with pieces:
            render_palette()
        with settings, st.container(key='analysis_editor_settings', gap='small'):
            st.segmented_control('Lado a jogar', ['Brancas', 'Pretas'], key='analysis_edit_turn', required=True)
            st.markdown('**Permitir roque**')
            white, black = st.columns(2, gap='small')
            for column, title, symbols in [(white, 'Brancas', 'KQ'), (black, 'Pretas', 'kq')]:
                with column:
                    st.caption(title)
                    for symbol, label in zip(symbols, ['Curto', 'Longo']):
                        st.checkbox(label, key=f'analysis_roque_{symbol}', on_change=castling_changed)
        st.divider()
        with st.container(horizontal=True, horizontal_alignment='distribute', vertical_alignment='center', key='analysis_editor_actions'):
            with st.container(horizontal=True, width='content'):
                st.button('Salvar posição e jogar', on_click=save, args=(reset_game,), type='primary', icon=':material/check:')
                st.button('Cancelar', on_click=cancel, type='tertiary')
            with st.popover('Recomeçar', icon=':material/restart_alt:'):
                st.button('Posição inicial', on_click=reset, width='stretch')
                st.button('Retirar todas as peças', on_click=reset, args=(True,), width='stretch')
        if state.get('analysis_edit_error'):
            st.error(state.analysis_edit_error)
