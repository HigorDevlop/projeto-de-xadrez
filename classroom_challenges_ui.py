"""Room challenge controls, using the shared board and authenticated services."""
from uuid import uuid4
import sqlite3
import chess
import streamlit as st
import classroom as rooms
import classroom_challenges as challenges
from interactive_board import interactive_board


def teacher(token):
    with st.expander('Desafios de posição da minha sala'):
        try:
            actor = rooms.identity(token)
            if not actor or actor['role'] not in ('professor', 'admin'):
                raise PermissionError('Entre como professor.')
            prefix = 'prep_challenge_' + actor['id']
            nonce = st.session_state.setdefault(prefix + '_publication', uuid4().hex)
            st.caption('Publica para os alunos ativos da sua sala. Uma tentativa por aluno, comparada ao lance '
                       'esperado pelo professor; alternativas não são avaliadas por um motor.')
            with st.form(prefix + '_form_' + nonce):
                title = st.text_input('Título do desafio', max_chars=150)
                fen = st.text_input('Posição FEN', value=chess.STARTING_FEN)
                instruction = st.text_area('Instrução para os alunos', max_chars=5000)
                solution = st.text_input('Lance esperado (UCI, por exemplo e2e4)', max_chars=5)
                send = st.form_submit_button('Publicar desafio na minha sala')
            if send:
                challenges.publish(token, title, fen, instruction, solution, nonce)
                st.success('Desafio publicado. Reenvios desta publicação não criam cópias.')
            if st.button('Preparar novo desafio', key=prefix + '_new'):
                st.session_state[prefix + '_publication'] = uuid4().hex
                st.rerun()
            rows = challenges.results(token)
            st.caption(f"Participação: {sum(r['result'] is not None for r in rows)} envios / {len(rows)} atribuições.")
            if rows:
                st.dataframe([dict(Desafio=r['title'], Publicação=r['challenge'][:8], Aluno=r['name'],
                    Estado='Acesso revogado' if r['banned'] else 'Enviado' if r['result'] else 'Pendente',
                    Lance=r['result']['san'] if r['result'] else '—',
                    Resultado=('Coincide com o gabarito' if r['result']['correct'] else 'Difere do gabarito') if r['result'] else '—')
                    for r in rows], hide_index=True)
        except (PermissionError, ValueError, OSError, sqlite3.Error) as error:
            st.warning(str(error))


def student(token):
    with st.expander('Desafios de posição da sala'):
        try:
            items = challenges.student_challenges(token)
            if not items:
                st.caption('Nenhum desafio publicado para você.')
                return
            actor = rooms.identity(token)
            choices = {item['id']: item for item in items}
            selected = st.selectbox('Desafio', list(choices), format_func=lambda k: choices[k]['title'],
                                    key='prep_challenge_choice_' + actor['id'])
            item = choices[selected]
            st.write(item['instructions'])
            st.caption('Ao jogar no tabuleiro, você envia sua tentativa única. Ela será salva; não há dica de gabarito antes do envio.')
            board = chess.Board(item['fen'])
            result = item['result']
            last = chess.Move.from_uci(result['uci']) if result else None
            if last:
                board.push(last)
            component = interactive_board(board, on_move=lambda: None, key='prep_challenge_board_' + selected,
                revision=selected, disabled=bool(result), flip=chess.Board(item['fen']).turn == chess.BLACK,
                last_move=last, show_coordinates=True, dark=True)
            event = getattr(component, 'move', None)
            if not result and isinstance(event, dict) and event.get('revision') == selected:
                challenges.submit(token, selected, event.get('fen'), event.get('uci'))
                st.rerun()
            if result:
                st.info('Sua tentativa: ' + result['san'] + '. ' + ('Coincide com o lance esperado.' if result['correct']
                    else 'Difere do lance esperado; isso não demonstra, por si só, que o lance seja ruim.'))
                st.write('Lance esperado pelo professor: ' + result['solution_san'])
        except (PermissionError, ValueError, OSError, sqlite3.Error) as error:
            st.warning(str(error))
