"""Offline didactic endgame trail in the existing Finais entry."""
import sqlite3
import chess
import streamlit as st
from interactive_board import interactive_board
from endgame_lessons import LESSONS, lesson
import endgame_training as training
from preparation_repetition import revision


def render_endgames():
    from classroom_ui import training_token
    token = training_token()
    st.subheader('Finais · primeiros passos')
    st.caption('Três lições locais. Jogue o objetivo duas vezes; uma resposta com ajuda não conclui a lição. '
               'O progresso é salvo nesta conta após cada ação.')
    try:
        plan = training.load(token)
        for item in LESSONS:
            progress = plan['practice_progress'].get(item['id'], {})
            saved = plan['practice_sessions'].get(item['id'])
            status = ('Concluída · revisão ' + progress['due'] if progress.get('learned') else
                      'Em andamento' if saved else 'Disponível' if training.unlocked(plan, item['id']) else 'Bloqueada')
            with st.container(horizontal=True, vertical_alignment='center'):
                st.write(item['title'] + ' · ' + status)
                if st.button('Abrir ' + item['title'], disabled=not training.unlocked(plan, item['id']),
                             key='endgame_open_' + item['id']):
                    training.act(token, item['id'], 'begin')
                    st.rerun()
        identifier = plan.get('practice_current')
        if not identifier:
            st.info('Abra a primeira lição para começar.')
            return
        item = lesson(identifier)
        session = plan['practice_sessions'][identifier]
        st.markdown('**' + item['objective'] + '**')
        complete = session['phase'] == 'complete'
        checkpoint = session['checkpoint']
        board = chess.Board(session['result_fen'] if checkpoint else item['fen'])
        result = interactive_board(board, key='endgame_board_' + session['token'], on_move=lambda: None,
            revision=revision(session), epoch=session['token'], disabled=checkpoint or complete,
            dark=True, show_coordinates=True, training_mode=True,
            hint_move=item['uci'] if not checkpoint and session['hint_level'] >= 3 else None)
        event = getattr(result, 'move', None)
        if event and not checkpoint and not complete:
            _, changed = training.act(token, identifier, 'move', event)
            if changed:
                st.rerun()
        if checkpoint:
            st.info(training.feedback(item, session))
            if not complete and st.button('Repetir a posição', key='endgame_continue'):
                training.act(token, identifier, 'continue')
                st.rerun()
        if complete:
            st.success('Lição concluída. Próxima revisão: ' + plan['retention'][identifier]['due'])
            st.caption('A lição seguinte está liberada. Quando a revisão vencer, abra esta lição para praticar novamente.')
        else:
            for hint in item['hints'][:session['hint_level']]:
                st.write('Dica: ' + hint)
            if st.button('Próxima dica', disabled=session['hint_level'] >= 3, key='endgame_hint'):
                training.act(token, identifier, 'hint')
                st.rerun()
            if st.button('Ver solução explicada', key='endgame_solution'):
                training.act(token, identifier, 'solution')
                st.rerun()
        if complete or session['solution']:
            st.write(item['explanation'])
            initial = chess.Board(item['fen'])
            moves = [chess.Move.from_uci(uci) for uci in item['line']]
            st.write('Continuação ilustrativa: ' + initial.variation_san(moves))
            step = st.select_slider('Passo da solução', options=list(range(len(moves)+1)),
                                    value=0, key='endgame_solution_step_' + session['token'])
            for move in moves[:step]:
                initial.push(move)
            interactive_board(initial, key='endgame_solution_board_' + session['token'],
                on_move=lambda: None, revision=step, disabled=True, dark=True, show_coordinates=True)
    except (PermissionError, ValueError, OSError, sqlite3.Error) as error:
        st.warning('Não foi possível abrir ou salvar o treino: ' + str(error))
