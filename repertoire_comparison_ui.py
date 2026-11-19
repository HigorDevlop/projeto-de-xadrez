"""Read-only local comparison with explicit study/recall actions."""
import sqlite3
import chess
import streamlit as st
from interactive_board import interactive_board
import repertoire_comparison as comparison


def render(token):
    st.subheader('Partidas e repertório')
    if not st.toggle('Comparar com meu repertório', key='dashboard_repertoire_visible'):
        return
    try:
        data = comparison.report(token)
        st.caption('Compara posições locais, sem motor ou downloads. Divergir pode ser uma escolha intencional; '
                   'reentrada em uma posição conhecida é indicada separadamente.')
        for note in data['notes']:
            st.info(note)
        st.caption(f"{data['lines']} linhas válidas · {len(data['games'])} partidas · "
                   f"{data['skipped_games']} partidas e {data['skipped_lines']} linhas excluídas por formato ou identificação incompatível.")
        if not data['lines']:
            st.info('Nenhuma linha pessoal preparada ou linha de curso concluída foi encontrada nesta conta.')
        if not data['games']:
            st.info('Nenhuma partida local identificada com o Chess.com desta conta. São usados o histórico pessoal salvo e as análises arquivadas.')
            return
        labels = {'no_match': 'Sem posição de decisão correspondente', 'matched': 'Lances cobertos coincidem',
                  'findings': 'Há diferenças de lance ou ordem'}
        st.dataframe([{'Partida': game['title'], 'Posições comparadas': game['covered'],
                       'Observação': labels[game['status']]} for game in data['games']], hide_index=True)
        key = 'dashboard_repertoire_' + data['owner']
        selected = st.selectbox('Partida para comparar', range(len(data['games'])),
                                format_func=lambda i: data['games'][i]['title'], key=key+'_game')
        game = data['games'][selected]
        st.download_button('Baixar PGN da partida comparada', game['pgn'], file_name='partida-comparada.pgn',
                           mime='application/x-chess-pgn', key=key+'_pgn')
        if not game['findings']:
            st.info(labels[game['status']] + '. Isso não avalia os lances fora da cobertura das linhas disponíveis.')
            return
        at = st.selectbox('Posição encontrada', range(len(game['findings'])),
                          format_func=lambda i: f"Meio-lance {game['findings'][i]['ply']}: {game['findings'][i]['played']}", key=key+'_finding_'+str(selected))
        finding = game['findings'][at]
        if finding['status'] == 'reentry':
            st.info(f"Ordem diferente com reentrada comprovada após o meio-lance {finding['reentry']}. Não é uma classificação de erro.")
        else:
            st.info('O lance não está nas linhas comparadas nesta posição. Não foi encontrada reentrada posterior nessas linhas; isso não prova erro.')
        st.write('Lance jogado: ' + finding['played'])
        interactive_board(chess.Board(finding['fen']), on_move=lambda: None, disabled=True,
                          key=key+'_board_'+finding['id'], dark=True, show_coordinates=True)
        choice = st.selectbox('Linha usada como referência', range(len(finding['options'])),
            format_func=lambda i: finding['options'][i]['source']+' · '+finding['options'][i]['title']+
                                 ' · '+finding['options'][i]['expected_san'], key=key+'_line_'+finding['id'])
        option = finding['options'][choice]
        st.caption('Linha estudada/concluída.' if option['studied'] else 'Linha pessoal preparada; não há conclusão de estudo registrada.')
        st.write('Linha completa: ' + option['full_line'])
        st.write(f"Correspondência no meio-lance {option['reference_ply']} da linha; lance previsto: {option['expected_san']}.")
        st.write('Continuação a partir da posição exibida: ' + option['continuation'])
        if st.button('Abrir posição para estudo', key=key+'_study'):
            comparison.open_position(token, st.session_state, finding['id'])
            st.rerun()
        if st.button('Criar exercício desta linha', key=key+'_train'):
            comparison.open_position(token, st.session_state, finding['id'], line=option['line'], exercise=True)
            st.rerun()
        st.caption('Transposições exigem posições idênticas, incluindo turno, roque e en passant legal. '
                   'Relógios de lances são ignorados. Não há inferência por semelhança nem avaliação enxadrística.')
    except (PermissionError, ValueError, OSError, sqlite3.Error) as error:
        st.warning('Não foi possível comparar: ' + str(error))
