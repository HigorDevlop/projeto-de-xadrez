"""Asynchronous seven-day diagnostics and actionable critical positions."""
from html import escape

import altair as alt
import streamlit as st

import game_phase_diagnostics as diagnostics


def _phase_chart(report):
    from performance_dashboard import _style
    rows=[{'Fase':row['phase'],'Erros (%)':row['rate'],'Erros':row['errors'],
           'Lances avaliados':row['moves'],'Imprecisões':row['inaccuracies']} for row in report['phases']]
    chart=alt.Chart(alt.Data(values=rows)).mark_bar(cornerRadiusEnd=5,size=28).encode(
        y=alt.Y('Fase:N',sort=list(diagnostics.PHASES),title=None),
        x=alt.X('Erros (%):Q',title='Erros e erros graves por 100 lances seus',scale=alt.Scale(domain=[0,max(10,max(row['Erros (%)'] for row in rows)*1.25)])),
        color=alt.Color('Fase:N',scale=alt.Scale(domain=list(diagnostics.PHASES),range=['#11e5ff','#ff27c3','#fff500']),legend=None),
        tooltip=['Fase:N','Lances avaliados:Q','Erros:Q',alt.Tooltip('Erros (%):Q',format='.1f'),'Imprecisões:Q'])
    return _style(chart,180)


def _move_chart(report):
    from performance_dashboard import _style
    rows=[{'Lance':row['number'],'Erros':row['errors'],'Lances avaliados':row['moves'],
           'Taxa (%)':100*row['errors']/row['moves']} for row in report['numbers']]
    return _style(alt.Chart(alt.Data(values=rows)).mark_bar(color='#42d9e8',cornerRadiusTopLeft=2,cornerRadiusTopRight=2).encode(
        x=alt.X('Lance:O',title='Número real do lance',axis=alt.Axis(labelOverlap=True,labelAngle=0)),
        y=alt.Y('Erros:Q',title='Ocorrências de erro',axis=alt.Axis(tickMinStep=1)),
        tooltip=['Lance:O','Erros:Q','Lances avaliados:Q',alt.Tooltip('Taxa (%):Q',format='.1f')]),180)


def render_diagnostics(history,username,complete=False,auto=True):
    records=diagnostics.window(history,username)
    if not records:return
    report=diagnostics.aggregate(records)
    with st.container(key='dash_card_diagnostics'):
        st.html('<div class="diag-eyebrow">RAIO-X / ÚLTIMOS 7 DIAS</div>')
        st.subheader('Onde você está errando')
        st.caption(f"{report['analyzed']} de {report['total']} partidas com diagnóstico por fase · somente seus lances entram nas taxas.")
        if auto and complete:
            from dashboard_auto_analysis import ensure
            ensure(history,username)
        elif not complete and auto:st.caption('Carregando o período completo para concluir o diagnóstico.')
        if not report['analyzed']:
            st.info('O diagnóstico aparece conforme as partidas terminam de ser avaliadas.');return
        worst=report['worst'];hotspot=report['hotspot']
        phase_text=worst['phase'] if worst else 'Sem erro relevante'
        detail=f"{worst['rate']:.1f}% · {worst['errors']} erros em {worst['moves']} lances" if worst else 'Nenhum erro ou erro grave nos lances avaliados'
        move_text=f"Lance {hotspot['number']}" if hotspot else 'Amostra insuficiente'
        move_detail=f"{hotspot['errors']} erros em {hotspot['moves']} ocorrências" if hotspot else f"O destaque exige ao menos {report['minimum_samples']} ocorrências do lance"
        st.html('<div class="diag-insights"><div><small>MAIOR TAXA DE ERROS</small><strong>'+escape(phase_text)+'</strong><span>'+escape(detail)+'</span></div><div><small>LANCE PARA REVISAR</small><strong>'+escape(move_text)+'</strong><span>'+escape(move_detail)+'</span></div></div>')
        if report['close_phases']:
            st.caption('Taxas próximas em '+worst['phase']+' e '+', '.join(report['close_phases'])+'. Compare também o número de lances avaliados em cada fase.')
        if report['analyzed']<report['total']:st.caption('Diagnóstico parcial: o destaque pode mudar até o fim da análise.')
        left,right=st.columns(2,gap='medium')
        with left:
            st.markdown('**Abertura, meio-jogo e final**')
            st.altair_chart(_phase_chart(report),width='stretch',theme=None)
        with right:
            st.markdown('**Em qual número de lance os erros aparecem**')
            st.altair_chart(_move_chart(report),width='stretch',theme=None)
        with st.expander('Ver números por fase e critério do diagnóstico'):
            st.dataframe([{'Fase':row['phase'],'Lances':row['moves'],'Erros e graves':row['errors'],
                'Imprecisões':row['inaccuracies'],'Taxa de erros (%)':round(row['rate'],1)} for row in report['phases']],hide_index=True,width='stretch')
            st.caption('Abertura: até o lance 10. Final: até 13 pontos de material em peças, ou sem damas e até 20 pontos. As demais posições são meio-jogo. A fase é calculada antes de cada lance; peões e reis não entram nessa contagem.')
            st.caption('O Stockfish compara o lance jogado com as melhores alternativas. Perda de 5 a menos de 10 pontos percentuais no indicador de chances é imprecisão, de 10 a 20 é erro e acima de 20 é erro grave. A classificação automática atualiza também o gráfico de qualidade. Diagnósticos rápidos anteriores são substituídos conforme essa análise termina.')
        critical=report['critical'][:20]
        if critical:
            from chess_review import CATEGORIES
            identifier=lambda row:str(row['game_id'])+':'+str(row['ply'])
            previous=st.session_state.get('dashboard_critical_move')
            if previous not in {identifier(row) for row in critical}:
                preserved=next((row for row in report['critical'] if identifier(row)==previous),None)
                if preserved:critical.append(preserved)
            lookup={identifier(row):row for row in critical}
            st.html('<div class="diag-eyebrow">02 / REVISÃO DE POSIÇÕES</div>')
            selected=st.selectbox('Revisar lance crítico',list(lookup),format_func=lambda key:
                f"{lookup[key]['number']}{'.' if lookup[key]['side']=='white' else '...'} {lookup[key]['san']} · {lookup[key]['phase']}",key='dashboard_critical_move')
            item=lookup[selected]
            move=f"{item['number']}{'.' if item['side']=='white' else '...'} {item['san']}"
            loss=f"{100*item['loss_chances']:.1f}".replace('.',',')+' pp'
            category=CATEGORIES[item['category']].label
            st.html('<div class="hud-review"><div class="hud-review-move"><small>LANCE JOGADO</small><strong>'+escape(move)+'</strong><span class="hud-review-phase">'+escape(item['phase']+' · '+category)+'</span></div><div class="hud-loss"><small>PERDA NO INDICADOR DE CHANCES</small><strong>'+loss+'</strong></div><div class="hud-best"><small>ALTERNATIVA DO MOTOR</small><strong>'+escape(item['best_san'] or '—')+'</strong></div></div>')
            if st.button('Rever este lance no tabuleiro',icon=':material/travel_explore:',key='dashboard_open_critical',type='primary',width='stretch'):
                record=next(row for row in records if row['id']==item['game_id'])
                st.session_state.dashboard_review_request=dict(pgn=record['pgn'],ply=item['ply'])
                st.session_state.requested_page='Análise';st.rerun()
