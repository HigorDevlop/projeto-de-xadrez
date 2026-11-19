"""Personal results dashboard, with saved counts from completed local analyses."""
from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import altair as alt
import streamlit as st

from analysis_summary import summarize_reviews
from chess_review import CATEGORIES
from preparation_data import _records
from preparation_state import LOCAL_ZONE, today


RESULTS = {'wins': 'Vitórias', 'losses': 'Derrotas', 'draws': 'Empates'}
RESULT_COLORS=['#11e5ff','#ff27c3','#fff500']
QUALITY_COLORS=['#11e5ff','#69ff24','#acff2b','#fff500','#ffae48','#ff745f','#ff27c3']


def quality_key(game):
    """Ignore annotations while retaining game identity and actual played moves."""
    payload = [sorted(game.headers.items()), game.board().fen(),
               [move.uci() for move in game.mainline_moves()]]
    return sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def _quality_path(game_key):
    folder = Path(os.environ.get('ACERVO_PERFORMANCE_DIR', Path(__file__).parent / 'data/performance'))
    return folder / f'{game_key}.json'


def save_game_quality(game, reviews):
    reviews=list(reviews.values()) if isinstance(reviews,dict) else list(reviews)
    summary = summarize_reviews(reviews)
    if not summary['total']:
        return
    from game_phase_diagnostics import from_reviews
    from_reviews(game,reviews)
    path = _quality_path(quality_key(game))
    payload = json.dumps({'version': 1, 'counts': summary['counts'], 'totals': summary['totals']})
    if path.is_file() and path.read_text(encoding='utf-8') == payload:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as file:
        temporary = Path(file.name)
        file.write(payload)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def quality_counts(games):
    from dashboard_auto_analysis import individual_counts,load
    counts = dict.fromkeys(CATEGORIES, 0)
    analyzed = 0
    for game in games:
        values=individual_counts(game['quality_key'],game['side'])
        automatic=load(game['quality_key'],game['side'])
        if automatic and (not values or automatic['moves']>sum(values.values())):
            values=automatic['counts']
        if values:
            analyzed+=1
            for key,value in values.items():counts[key]+=value
    return counts, analyzed


@st.cache_data(max_entries=16, show_spinner=False)
def dashboard_data(history, username, end, days=7):
    start = end - timedelta(days=days - 1)
    records = [row for row in _records(history, username)
               if row['outcome'] in RESULTS and row['timestamp']
               and start <= datetime.fromtimestamp(row['timestamp'], LOCAL_ZONE).date() <= end]
    totals = Counter(row['outcome'] for row in records)
    openings = {}
    daily = {start + timedelta(days=i): Counter() for i in range(days)}
    sides = {'white': Counter(), 'black': Counter()}
    lengths = Counter({'Até 20': 0, '21–40': 0, '41–60': 0, '61+': 0})
    games, move_total = [], 0
    for record in records:
        day = datetime.fromtimestamp(record['timestamp'], LOCAL_ZONE).date()
        outcome = record['outcome']
        daily[day][outcome] += 1
        sides[record['side']][outcome] += 1
        opening = openings.setdefault(record['opening'], Counter())
        opening[outcome] += 1
        # Count only the connected player's moves, including games starting from a FEN.
        first_is_player = record['game'].board().turn == (record['side'] == 'white')
        moves = sum(1 for index, _ in enumerate(record['game'].mainline_moves())
                    if (index % 2 == 0) == first_is_player)
        move_total += moves
        lengths['Até 20' if moves <= 20 else '21–40' if moves <= 40 else '41–60' if moves <= 60 else '61+'] += 1
        games.append({'quality_key': quality_key(record['game']), 'side': record['side']})
    opening_rows = []
    for name, outcomes in sorted(openings.items(), key=lambda pair: (-sum(pair[1].values()), pair[0])):
        total = sum(outcomes.values())
        opening_rows.append({'Abertura': name, 'Partidas': total,
                             'Vitórias': outcomes['wins'], 'Derrotas': outcomes['losses'], 'Empates': outcomes['draws'],
                             'Vitória (%)': round(100 * outcomes['wins'] / total, 1),
                             'Derrota (%)': round(100 * outcomes['losses'] / total, 1)})
    return {'total': len(records), 'totals': dict(totals), 'openings': opening_rows,
            'daily': [{'Data': day.isoformat(), 'Dia': day.strftime('%d/%m'), 'Resultado': label, 'Partidas': outcomes[key]}
                      for day, outcomes in daily.items() for key, label in RESULTS.items()],
            'sides': [{'Cor': 'Brancas' if side == 'white' else 'Pretas',
                       'Partidas': sum(outcomes.values()),
                       **{label: outcomes[key] for key, label in RESULTS.items()},
                       'Vitória (%)': round(100 * outcomes['wins'] / sum(outcomes.values()), 1)
                       if sum(outcomes.values()) else None}
                      for side, outcomes in sides.items()],
            'lengths': [{'Seus lances por partida': label, 'Partidas': count} for label, count in lengths.items()],
            'moves': move_total, 'games': games, 'start': start}



DASHBOARD_CSS = """<style>
.stMainBlockContainer:has(.st-key-performance_dashboard){max-width:none;width:100%;padding:4rem 1.5rem 1rem}
.st-key-performance_dashboard{background:#0a0a0a;border:1px solid #2b2b2b;border-radius:16px;min-height:calc(100dvh - 90px);padding:24px;color:#edf2eb}
.st-key-performance_dashboard [data-testid="stVerticalBlock"]{gap:10px}
.st-key-performance_dashboard [data-testid="stHorizontalBlock"]{gap:16px}
.st-key-performance_dashboard h1{font:400 27px/1.2 'Segoe UI',sans-serif!important;color:#f6f2ff!important;padding:0!important;text-align:left;letter-spacing:-.5px}
.st-key-performance_dashboard h3{font:600 15px/1.3 'Segoe UI',sans-serif!important;color:#fff!important;padding:0 0 7px!important;border-bottom:1px solid #3a433c;margin:0!important}
.st-key-performance_dashboard p,.st-key-performance_dashboard label{font-family:'Segoe UI',sans-serif!important;color:#d8ded8!important;font-size:13px!important}
.st-key-performance_dashboard [class*="st-key-dash_card"]{background:linear-gradient(145deg,#1d1d1d,#121212);border:1px solid #2b2b2b;border-radius:11px;padding:12px 14px}
.st-key-performance_dashboard .dash-summary{display:flex;justify-content:space-between;gap:12px;align-items:center}
.st-key-performance_dashboard .dash-summary span{font:11px 'Segoe UI',sans-serif;color:#a9b5ab}
.st-key-performance_dashboard .dash-summary strong{font:600 32px 'Segoe UI',sans-serif;color:#fff}
.st-key-performance_dashboard .dash-rates{display:flex;justify-content:space-around;text-align:center;gap:8px;font:11px 'Segoe UI',sans-serif;color:#bac6bc}
.st-key-performance_dashboard .dash-rates strong{display:block;font-size:17px;color:#fff;margin:4px 0}
.st-key-performance_dashboard .dash-empty{height:231px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:9px;color:#aebcaf;font:12px 'Segoe UI',sans-serif;text-align:center}
.st-key-performance_dashboard .dash-rates i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
.st-key-performance_dashboard .dash-empty strong{font-size:16px;color:#fff}
.st-key-performance_dashboard [data-testid="stButtonGroup"] button{background:#172a25!important;border:1px solid #345648!important;color:#fff!important;min-height:30px!important;padding:3px 10px!important}
.st-key-performance_dashboard [data-testid="stButtonGroup"] button[aria-checked="true"]{background:#286650!important;border-color:#6db395!important}
.st-key-performance_dashboard [data-testid="stCaptionContainer"] p{font-size:10px!important;color:#aab7ad!important;margin:0!important}
.st-key-performance_dashboard .dash-footer{font:10px 'Segoe UI',sans-serif;color:#96a79a;text-align:right}
@media(max-width:700px){.stMainBlockContainer:has(.st-key-performance_dashboard){padding:4rem .6rem 1rem}.st-key-performance_dashboard{padding:12px}.st-key-performance_dashboard h1{font-size:23px!important;text-align:left}}
</style>"""


def _style(chart,height):
    return chart.properties(height=height).configure(
        background='transparent',font='Segoe UI',padding={'left':4,'right':22,'top':18,'bottom':4}
    ).configure_view(stroke=None).configure_axis(
        labelColor='#aab9bf',titleColor='#899da6',labelFontSize=12,titleFontSize=11,
        titleFontWeight='normal',labelPadding=9,domain=False,ticks=False,
        gridColor='#eccaff30',gridOpacity=1
    ).configure_legend(labelColor='#c5d0d3',labelFontSize=12,title=None,symbolType='circle',symbolSize=65,padding=10)


def _daily_chart(data):
    days=list(dict.fromkeys(row['Dia'] for row in data['daily']))
    totals=[{'Dia':day,'Partidas':sum(row['Partidas'] for row in data['daily'] if row['Dia']==day),
             **{label:sum(row['Partidas'] for row in data['daily'] if row['Dia']==day and row['Resultado']==label) for label in RESULTS.values()}} for day in days]
    base=alt.Chart(alt.Data(values=totals)).encode(
        x=alt.X('Dia:N',sort=days,title=None,axis=alt.Axis(labelAngle=0,labelOverlap=True,grid=True)),
        y=alt.Y('Partidas:Q',title=None,axis=alt.Axis(tickMinStep=1,tickCount=5,grid=True),scale=alt.Scale(domainMin=0)),
        tooltip=['Dia:N','Partidas:Q','Vitórias:Q','Derrotas:Q','Empates:Q'])
    area=base.mark_area(color=alt.Gradient(gradient='linear',stops=[alt.GradientStop(color='#fc39d5',offset=0),alt.GradientStop(color='#54088a00',offset=1)],x1=0,x2=0,y1=0,y2=1),opacity=.6)
    line=base.mark_line(color='#fff500',strokeWidth=2.5)
    points=base.mark_point(filled=True,fill='#8423b4',stroke='#fff500',strokeWidth=2,size=80)
    return _style(area+line+points,240)


def _opening_chart(data):
    rows=data['openings'][:5]
    peak=max((row['Partidas'] for row in rows),default=1)
    base=alt.Chart(alt.Data(values=rows)).encode(
        y=alt.Y('Abertura:N',sort=[r['Abertura'] for r in rows],title=None,axis=alt.Axis(labelLimit=210,labelFontSize=12),scale=alt.Scale(paddingInner=.48)),
        x=alt.X('Partidas:Q',title=None,axis=alt.Axis(tickMinStep=1,tickCount=4,grid=True),scale=alt.Scale(domain=[0,max(1,peak*1.25)])),
        tooltip=['Abertura:N','Partidas:Q','Vitórias:Q','Derrotas:Q',alt.Tooltip('Vitória (%):Q',format='.1f')])
    bars=base.mark_bar(color='#ff51d4',cornerRadiusEnd=1,size=19)
    labels=base.mark_text(align='left',dx=7,color='#dce7e9',fontSize=12,fontWeight=600).encode(text='Partidas:Q')
    return _style(bars+labels,245)


def _result_chart(data):
    rows=[{'Resultado':label,'Partidas':data['totals'].get(key,0)} for key,label in RESULTS.items()]
    total=data['total'];rate=100*data['totals'].get('wins',0)/total if total else 0
    arcs=alt.Chart(alt.Data(values=rows)).mark_arc(innerRadius=68,outerRadius=95,stroke='#4b087c',strokeWidth=4,cornerRadius=4).encode(
        theta=alt.Theta('Partidas:Q'),color=alt.Color('Resultado:N',scale=alt.Scale(domain=list(RESULTS.values()),range=RESULT_COLORS),legend=None),tooltip=['Resultado:N','Partidas:Q'])
    center=alt.Chart(alt.Data(values=[{'label':f'{rate:.1f}%'.replace('.',',')}])).mark_text(color='#e3edf0',fontSize=28,fontWeight=600,dy=-5).encode(text='label:N')
    subtitle=alt.Chart(alt.Data(values=[{'label':'de vitórias'}])).mark_text(color='#92a7ad',fontSize=12,dy=22).encode(text='label:N')
    return _style(arcs+center+subtitle,230)


def _quality_chart(counts):
    total=sum(counts.values())
    rows=[{'Qualidade':category.label,'Lances':counts[key],'Proporção':counts[key]/total if total else 0} for key,category in CATEGORIES.items()]
    peak=max(counts.values(),default=1)
    names=[r['Qualidade'] for r in rows]
    base=alt.Chart(alt.Data(values=rows)).encode(
        y=alt.Y('Qualidade:N',sort=names,title=None,axis=alt.Axis(labelFontSize=12),scale=alt.Scale(paddingInner=.4)),
        x=alt.X('Lances:Q',title=None,axis=alt.Axis(tickMinStep=1,tickCount=5,grid=True),scale=alt.Scale(domain=[0,max(1,peak*1.23)])),
        tooltip=['Qualidade:N','Lances:Q',alt.Tooltip('Proporção:Q',format='.1%')])
    bars=base.mark_bar(cornerRadiusEnd=4,size=20).encode(color=alt.Color('Qualidade:N',scale=alt.Scale(domain=names,range=QUALITY_COLORS),legend=None))
    labels=base.mark_text(align='left',dx=8,color='#dce7e9',fontSize=12,fontWeight=600).encode(text='Lances:Q')
    return _style(bars+labels,260)



def _render_kpis(data,history,username):
    from game_phase_diagnostics import window,aggregate
    from dashboard_auto_analysis import records_for,queue
    from dashboard_purple import console
    counts,analyzed=quality_counts(data['games'])
    records=records_for(history,username,today(),30 if (today()-data['start']).days>6 else 7)
    st.html(console(data,aggregate(window(history,username)),counts,analyzed,queue().status(records)))


def _render_quality(data,history,username,auto):
    from dashboard_auto_analysis import ensure,records_for
    days=30 if (today()-data['start']).days>6 else 7
    records=ensure(history,username,days) if auto else records_for(history,username,today(),days)
    counts,analyzed=quality_counts(data['games']);count=sum(counts.values())
    st.subheader('Qualidade dos seus lances')
    from dashboard_refresh import render_queue
    render_queue(records)
    if count:
        st.altair_chart(_quality_chart(counts),width='stretch',theme=None)
    else:
        st.html('<div class="dash-empty"><strong>Sem lances avaliados</strong><span>As partidas entram automaticamente na fila de análise.</span></div>')
    st.caption(f'{analyzed} de {data["total"]} partidas analisadas · {count} lances seus avaliados')
    if auto:
        from stockfish_analysis import find_engine
        if not find_engine():st.warning('Stockfish não foi encontrado. Configure o motor para ativar as análises automáticas.')
        else:st.caption('Atualização automática enquanto o aplicativo estiver aberto. Novas partidas têm prioridade na fila após aparecerem no Chess.com.')


def render_dashboard(history, username, dark=False, *, complete=False,auto_diagnostics=True):
    from dashboard_purple import CSS
    st.html(DASHBOARD_CSS)
    st.html(CSS)
    with st.container(key='performance_dashboard'):
        heading,controls=st.columns([2,1],vertical_alignment='center')
        with heading:
            st.html('<div class="dash-eyebrow">COACH / CENTRAL DE EVOLUÇÃO</div>')
            st.title('Desempenho')
        if not username:
            st.info('Entre com seu usuário do Chess.com no menu lateral para ver seu desempenho.')
            return
        with controls:period = st.segmented_control('Período do painel', ['Últimos 7 dias', 'Últimos 30 dias'],
                                      default='Últimos 7 dias', key='dashboard_period',label_visibility='collapsed') or 'Últimos 7 dias'
        end=today()
        data=dashboard_data(history,username,end,7 if period=='Últimos 7 dias' else 30)
        total=data['total']
        st.caption(f'{username} · {data["start"]:%d/%m/%Y} a {end:%d/%m/%Y}')
        if not total:
            st.info('Nenhuma partida concluída neste período no histórico carregado.')
            return
        from dashboard_refresh import watch_reports
        watch_reports(history,username,30 if period=='Últimos 30 dias' else 7,auto_diagnostics)
        with st.container(key='dash_card_daily'):
            st.subheader('Atividade e resultados')
            st.altair_chart(_daily_chart(data),width='stretch',theme=None)
        _render_kpis(data,history,username)
        results,quality,openings=st.columns([1,1.35,1.2],gap='medium')
        with results,st.container(key='dash_card_results'):
            st.subheader('Vitórias, derrotas e empates')
            st.altair_chart(_result_chart(data),width='stretch',theme=None)
            rates=''.join(f'<div><i style="background:{color}"></i>{label}<strong>{100*data["totals"].get(key,0)/total:.1f}%</strong>{data["totals"].get(key,0)} partidas</div>' for (key,label),color in zip(RESULTS.items(),RESULT_COLORS)).replace('.',',')
            st.html(f'<div class="dash-rates">{rates}</div>')
        with quality,st.container(key='dash_card_quality'):
            _render_quality(data,history,username,auto_diagnostics)
        with openings,st.container(key='dash_card_openings'):
            st.subheader('Aberturas mais jogadas')
            st.altair_chart(_opening_chart(data),width='stretch',theme=None)
            sides=''.join(f'<span>{row["Cor"]}: <strong>{row["Vitória (%)"]:.1f}% de vitórias</strong> · {row["Partidas"]} partidas</span>' if row['Partidas'] else f'<span>{row["Cor"]}: sem partidas</span>' for row in data['sides'])
            st.html('<div class="dash-side">'+sides+'</div>')
        from dashboard_diagnostics_ui import render_diagnostics
        render_diagnostics(history,username,complete,auto_diagnostics)
        longest=max(data['lengths'],key=lambda row:row['Partidas'])
        st.html(f'<div class="dash-details"><span>Seus lances no período: <b>{data["moves"]}</b></span><span>Aberturas diferentes: <b>{len(data["openings"])}</b></span><span>Duração mais comum: <b>{longest["Seus lances por partida"]} lances seus</b></span></div>')
        coverage='Período completo' if complete else 'Histórico parcial · carregando período completo'
        st.html(f'<div class="dash-footer">{coverage} · Resultados do histórico do Chess.com · Qualidade calculada nas análises locais</div>')
