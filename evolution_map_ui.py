"""Evidence-first evolution map in the existing home workspace."""
from datetime import timedelta
import sqlite3
import streamlit as st
import evolution_map as evolution
from preparation_state import today


def render(token):
    st.subheader('Mapa de evolução')
    if not st.toggle('Mostrar mapa de evolução', key='dashboard_evolution_visible'):
        return
    try:
        days = st.selectbox('Período do mapa', [7, 30],
                            format_func=lambda n: f'Últimos {n} dias', key='dashboard_evolution_days')
        end = today()
        data = evolution.collect(token, end=end, days=days)
        start = end-timedelta(days=days-1)
        st.caption(f"Perfil de treino: {data['name']} · {start:%d/%m/%Y} a {end:%d/%m/%Y} · "
                   f"comparado com {start-timedelta(days=days):%d/%m/%Y} a {start-timedelta(days=1):%d/%m/%Y}")
        st.caption('Somente registros locais. Sem nova análise de partidas, nota geral ou diagnóstico de fraqueza.')
        groups = evolution.aggregate(data['rows'], end=end, days=days)
        for source in evolution.SOURCES:
            st.markdown('**' + source + '**')
            available = [group for group in groups if group['source'] == source]
            if not available:
                st.info(f'{source}: dados insuficientes — nenhum registro utilizável nos dois períodos.')
                continue
            for group in available:
                with st.container(border=True):
                    st.write(group['theme'])
                    current, before = group['current'], group['previous']
                    st.caption(evolution.METRICS[source])
                    st.write('Atual: ' + _value(current['value']) + ' · anterior: ' + _value(before['value']))
                    st.caption(f"Amostras: {current['samples']} atuais e {before['samples']} anteriores "
                               f"({evolution.UNITS[source]}); registros: {current['records']} e {before['records']}.")
                    if not group['sufficient']:
                        st.info(f'Dados insuficientes para comparar: mínimo de {evolution.MIN_SAMPLES[source]} '
                                f'{evolution.UNITS[source]} em cada período. Isso não indica uma fraqueza.')
                    else:
                        unit = 'minutos' if source == 'Preparos' else 'pontos percentuais'
                        st.write(f"Variação observada: {group['delta']:+.1f} {unit}.")
                        st.caption('Comparação descritiva das amostras; não demonstra mudança de habilidade.')
                    with st.expander('Evidências e treino · ' + group['theme']):
                        evidence = group['evidence']
                        st.dataframe([{'Data': r['day'], 'Registro': r['id'], 'Evidência': r['detail']}
                                      for r in evidence], hide_index=True)
                        key = 'dashboard_evolution_' + data['owner'] + '_' + source + '_' + group['theme']
                        index = st.selectbox('Registro para abrir', range(len(evidence)),
                            format_func=lambda i, evidence=evidence: evidence[i]['day'] + ' · ' + evidence[i]['detail'], key=key)
                        row = evidence[index]
                        label = ('Treinar esta posição' if row['action'].get('train') else 'Abrir análise desta partida') if source == 'Partidas' else 'Abrir treino relacionado'
                        if st.button(label, key=key + '_open'):
                            evolution.open_training(token, st.session_state, row)
                            st.rerun()
        with st.expander('Fontes e limites do mapa'):
            st.write('Análises salvas: classificações dos seus lances por fase e motor. '
                     'Aberturas: acerto inicial salvo nas fases concluídas. '
                     'Táticos: lances corretos divididos pelas tentativas registradas. '
                     'Preparos: soma dos minutos dos resumos diários da própria conta de aluno.')
            st.write('Os mínimos de amostra evitam apresentar uma comparação baseada em um único treino; '
                     'não são testes de significância estatística. Ausência de registro não é contabilizada como erro ou falta.')
            for note in data['notes']:
                st.caption(note)
    except (PermissionError, ValueError, OSError, sqlite3.Error) as error:
        st.warning('Não foi possível abrir o mapa: ' + str(error))


def _value(value):
    return 'sem dados' if value is None else f'{value:.1f}'
