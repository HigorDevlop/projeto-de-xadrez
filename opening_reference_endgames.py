"""Small playable endgame entry for the reference bottom navigation."""
import chess
import streamlit as st
from interactive_board import interactive_board
from opening_reference_style import title_html

EXERCISES = (
    ('Rei e dama', '7k/5K2/6Q1/8/8/8/8/8 w - - 0 1'),
    ('Rei e torre', '7k/5K2/8/8/8/8/8/6R1 w - - 0 1'),
    ('Promoção do peão', '7k/5P2/6K1/8/8/8/8/8 w - - 0 1'),
)


def render_endgames():
    state=st.session_state
    st.html(title_html('Finais',medal=False))
    selection=st.segmented_control('Exercício',[title for title,_ in EXERCISES],default=EXERCISES[0][0],width='stretch') or EXERCISES[0][0]
    name,fen=next(item for item in EXERCISES if item[0]==selection)
    if state.get('reference_endgame_name')!=name:
        state.reference_endgame_name=name
        state.reference_endgame_moves=[]
        state.reference_endgame_revision=0
        state.reference_endgame_message='Encontre o mate em um lance.'
    board=chess.Board(fen)
    for uci in state.reference_endgame_moves: board.push_uci(uci)
    with st.container(key='opening_lesson_board'):
        result=interactive_board(board,key='reference_endgame',on_move=lambda:None,
            revision=str(state.reference_endgame_revision),epoch=name,training_mode=True,
            disabled=board.is_checkmate(),dark=True,show_coordinates=True)
        event=getattr(result,'move',None)
        if isinstance(event,dict) and event.get('revision')==str(state.reference_endgame_revision) and event.get('fen')==board.fen():
            try:
                move=chess.Move.from_uci(event.get('uci',''))
                if move in board.legal_moves:
                    board.push(move)
                    if board.is_checkmate():
                        state.reference_endgame_moves.append(move.uci())
                        state.reference_endgame_message='Bom trabalho!'
                    else:
                        state.reference_endgame_message='Tente de novo! Encontre um lance que dê mate.'
                    state.reference_endgame_revision+=1
                    st.rerun()
            except ValueError:
                pass
        st.html('<div class="reference-feedback '+('success' if board.is_checkmate() else '')+'">'+state.reference_endgame_message+'</div>')
    if st.button('Recomeçar',type='primary'):
        state.pop('reference_endgame_name',None);st.rerun()
