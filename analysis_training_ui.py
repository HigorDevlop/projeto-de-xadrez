"""Small analysis-to-recall workflow, without engine calls."""
import sqlite3
import chess
import streamlit as st

import analysis_archive
import analysis_training as training
import classroom as rooms
from interactive_board import interactive_board
from preparation_state import today


def render(pgn, *, ready=False):
    token = st.session_state.get('classroom_token')
    if not token:
        return
    try:
        owner = rooms.identity(token)
        if not owner:
            return
        prefix = 'analysis_training_' + owner['id']
        with st.expander('Treinar posições da partida', icon=':material/fitness_center:',
                         expanded=st.session_state.get('analysis_training_open', False)):
            st.caption('Treino local com análises salvas ou linhas do repertório. Nenhuma nova análise será iniciada.')
            saved = analysis_archive.load(token, pgn=pgn) if ready else None
            candidates = {ply: r for ply, r in (saved or {}).get('reviews', {}).items()
                          if r.category in training.CATEGORIES}
            if candidates:
                ply = st.selectbox('Posição da partida', list(candidates),
                    format_func=lambda p: f'{p} · {candidates[p].side} · {candidates[p].number} {candidates[p].san}',
                    key=prefix + '_position_' + saved['id'])
                if st.button('Criar exercício desta posição', key=prefix + '_create'):
                    key = training.create(token, saved['id'], ply)
                    st.session_state[prefix + '_choice'] = key
                    st.success('Posição disponível para revisão. Posições repetidas mantêm o progresso.')
            else:
                st.caption('Abra uma análise salva com erros ou imprecisões para criar um exercício.')
            items = {item['id']: item for item in training.listing(token)}
            if not items:
                return
            due = sum(item['due'] <= str(today()) for item in items.values())
            st.caption(f'{due} posição(ões) para revisar hoje.')
            key = st.selectbox('Meus exercícios', list(items),
                format_func=lambda k: f"Lance {items[k]['ply']} · revisão {items[k]['due']} · {k[:6]}",
                key=prefix + '_choice')
            exercise = items[key]
            result_key = prefix + '_result_' + key
            result = st.session_state.get(result_key)
            board = chess.Board(exercise['fen'])
            st.caption('Posição antes do lance jogado · ' + ('Brancas jogam' if board.turn else 'Pretas jogam'))
            interactive_board(board, on_move=lambda: None, disabled=True, flip=not board.turn,
                              key=prefix + '_board_' + key, revision=exercise['revision'])
            if exercise['due'] <= str(today()):
                # Do not disclose the previous answer when the next review becomes due.
                result = None
                with st.form(prefix + '_attempt_' + key + '_' + str(exercise['revision'])):
                    uci = st.selectbox('Seu lance', [m.uci() for m in board.legal_moves],
                                       format_func=lambda u: board.san(chess.Move.from_uci(u)), index=None)
                    send = st.form_submit_button('Registrar tentativa')
                if send:
                    if not uci:
                        st.warning('Escolha um lance antes de registrar.')
                    else:
                        result = training.submit(token, key, uci, exercise['revision'])
                        st.session_state[result_key] = result
                        st.rerun()
            else:
                st.caption('Próxima revisão: ' + exercise['due'])
            if result:
                repertoire = result.get('source') == 'repertoire'
                if result['matched']:
                    st.success('Você lembrou o lance da linha escolhida.' if repertoire else 'Você encontrou o lance recomendado.')
                else:
                    st.info('Seu lance difere da linha escolhida; isso não o classifica como erro.' if repertoire else
                            'Seu lance difere da recomendação salva; alternativas não foram reavaliadas.')
                st.write('Sua tentativa: ' + result['attempt'])
                st.write(('Linha do repertório: ' if repertoire else 'Recomendação: ') + (result['best_line'] or result['best_san']))
                if not result['best_line']:
                    st.caption('Esta análise antiga contém apenas o melhor lance, sem a continuação recomendada.')
                st.write(result['explanation'] or 'Esta análise não contém uma explicação textual.')
                st.caption(f"{result['engine']} · lance da partida: {result['played']} · próxima revisão: {result['due']}")
    except (ValueError, PermissionError, OSError, sqlite3.Error) as error:
        st.warning(str(error))
