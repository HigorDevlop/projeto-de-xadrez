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


def quality_key(game):
    """Ignore annotations while retaining game identity and actual played moves."""
    payload = [sorted(game.headers.items()), game.board().fen(),
               [move.uci() for move in game.mainline_moves()]]
    return sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def _quality_path(game_key):
    folder = Path(os.environ.get('ACERVO_PERFORMANCE_DIR', Path(__file__).parent / 'data/performance'))
    return folder / f'{game_key}.json'


def save_game_quality(game, reviews):
    summary = summarize_reviews(reviews)
    if not summary['total']:
        return
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
    counts = dict.fromkeys(CATEGORIES, 0)
    analyzed = 0
    for game in games:
        try:
            report = json.loads(_quality_path(game['quality_key']).read_text(encoding='utf-8'))
            if report.get('version') != 1:
                continue
            side = 'Brancas' if game['side'] == 'white' else 'Pretas'
            values = {key: report['counts'][key][side] for key in CATEGORIES}
            if any(type(value) is not int or value < 0 for value in values.values()):
                continue
            if sum(values.values()):
                analyzed += 1
                for key, value in values.items():
                    counts[key] += value
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
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
.stMainBlockContainer:has(.st-key-performance_dashboard){max-width:1600px;padding:4.6rem 1.5rem 1rem}
.st-key-performance_dashboard{background:#160d29;border:1px solid #57426e;border-radius:16px;padding:16px 18px 12px;color:#f6f2ff}
.st-key-performance_dashboard [data-testid="stVerticalBlock"]{gap:10px}
.st-key-performance_dashboard [data-testid="stHorizontalBlock"]{gap:16px}
.st-key-performance_dashboard h1{font:400 27px/1.2 'Segoe UI',sans-serif!important;color:#f6f2ff!important;padding:0!important;text-align:right;letter-spacing:-.5px}
.st-key-performance_dashboard h3{font:600 13px/1.3 'Segoe UI',sans-serif!important;color:#fff!important;padding:0 0 7px!important;border-bottom:1px solid #9a8eac;margin:0!important}
.st-key-performance_dashboard p,.st-key-performance_dashboard label{font-family:'Segoe UI',sans-serif!important;color:#dfd7ec!important;font-size:11px!important}
.st-key-performance_dashboard [class*="st-key-dash_card"]{background:#352749;border:1px solid #4b3b61;border-radius:11px;padding:12px 14px}
.st-key-performance_dashboard .dash-summary{display:flex;justify-content:space-between;gap:12px;align-items:center}
.st-key-performance_dashboard .dash-summary span{font:11px 'Segoe UI',sans-serif;color:#dbd2e9}
.st-key-performance_dashboard .dash-summary strong{font:600 32px 'Segoe UI',sans-serif;color:#fff}
.st-key-performance_dashboard .dash-rates{display:flex;justify-content:space-around;text-align:center;gap:8px;font:11px 'Segoe UI',sans-serif;color:#ded6ec}
.st-key-performance_dashboard .dash-rates strong{display:block;font-size:17px;color:#fff;margin:4px 0}
.st-key-performance_dashboard .dash-empty{height:231px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:9px;color:#c9bedb;font:12px 'Segoe UI',sans-serif;text-align:center}
.st-key-performance_dashboard .dash-rates i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
.st-key-performance_dashboard .dash-empty strong{font-size:16px;color:#fff}
.st-key-performance_dashboard [data-testid="stButtonGroup"] button{background:#251936!important;border:1px solid #75618e!important;color:#fff!important;min-height:30px!important;padding:3px 10px!important}
.st-key-performance_dashboard [data-testid="stButtonGroup"] button[aria-checked="true"]{background:#777dc5!important;border-color:#aeb2ec!important}
.st-key-performance_dashboard [data-testid="stCaptionContainer"] p{font-size:10px!important;color:#c6bad6!important;margin:0!important}
.st-key-performance_dashboard .dash-footer{font:10px 'Segoe UI',sans-serif;color:#bcaed0;text-align:right}
@media(max-width:700px){.stMainBlockContainer:has(.st-key-performance_dashboard){padding:4rem .6rem 1rem}.st-key-performance_dashboard{padding:12px}.st-key-performance_dashboard h1{font-size:23px!important;text-align:left}}
</style>"""


def _style(chart, height):
    return chart.properties(height=height).configure(
        background='transparent', font='Segoe UI', padding={'left': 2, 'right': 12, 'top': 10, 'bottom': 0},
    ).configure_view(stroke=None).configure_axis(
        labelColor='#e9e2f3', titleColor='#d3c8e2', labelFontSize=10,
        titleFontSize=10, titleFontWeight='normal', labelPadding=6,
        grid=False, domain=False, ticks=False,
    ).configure_legend(labelColor='#eee8f5', labelFontSize=10, title=None)


def _daily_chart(data):
    days = list(dict.fromkeys(row['Dia'] for row in data['daily']))
    rows = [{'Dia': day, 'Partidas': sum(row['Partidas'] for row in data['daily'] if row['Dia'] == day)} for day in days]
    peak = max((row['Partidas'] for row in rows), default=1)
    base = alt.Chart(alt.Data(values=rows)).encode(
        x=alt.X('Dia:N', sort=days, title=None, axis=alt.Axis(labelAngle=0 if len(days) == 7 else -60),
                scale=alt.Scale(paddingInner=.35, paddingOuter=.2)),
        y=alt.Y('Partidas:Q', title=None, axis=None, scale=alt.Scale(domain=[0, max(1, peak * 1.18)])),
        tooltip=['Dia:N', 'Partidas:Q'],
    )
    bars = base.mark_bar(color='#8689d1', cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
    labels = base.mark_text(dy=-8, color='#ffffff', fontSize=10).encode(text='Partidas:Q')
    return _style(bars + labels, 220)


def _opening_chart(data):
    rows = data['openings'][:5]
    base = alt.Chart(alt.Data(values=rows)).encode(
        y=alt.Y('Abertura:N', sort=[r['Abertura'] for r in rows], title=None,
                axis=alt.Axis(labelLimit=140, labelFontSize=9), scale=alt.Scale(paddingInner=.35)),
        x=alt.X('Partidas:Q', title=None, axis=None,
                scale=alt.Scale(domain=[0, max((r['Partidas'] for r in rows), default=1) * 1.2])),
        tooltip=['Abertura:N', 'Partidas:Q', 'Vitórias:Q', 'Derrotas:Q',
                 alt.Tooltip('Vitória (%):Q', format='.1f'), alt.Tooltip('Derrota (%):Q', format='.1f')],
    )
    bars = base.mark_bar(color='#8286c9', stroke='#b3b5e7', strokeWidth=.5)
    labels = base.mark_text(align='left', dx=5, color='#fff', fontSize=10).encode(text='Partidas:Q')
    return _style(bars + labels, 140)


def _result_chart(data):
    rows = [{'Resultado': label, 'Partidas': data['totals'].get(key, 0)} for key, label in RESULTS.items()]
    chart = alt.Chart(alt.Data(values=rows)).mark_arc(innerRadius=42, outerRadius=65, stroke='#352749', strokeWidth=2).encode(
        theta=alt.Theta('Partidas:Q'),
        color=alt.Color('Resultado:N', scale=alt.Scale(domain=list(RESULTS.values()), range=['#9298eb', '#b49acb', '#e2dfed']), legend=None),
        tooltip=['Resultado:N', 'Partidas:Q'],
    )
    return _style(chart, 134)


def _quality_chart(counts):
    rows = [{'Qualidade': category.label, 'Lances': counts[key]} for key, category in CATEGORIES.items()]
    peak = max(counts.values(), default=1)
    base = alt.Chart(alt.Data(values=rows)).encode(
        x=alt.X('Qualidade:N', sort=[r['Qualidade'] for r in rows], title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=10), scale=alt.Scale(paddingInner=.45)),
        y=alt.Y('Lances:Q', title=None, axis=None, scale=alt.Scale(domain=[0, max(1, peak * 1.2)])),
        tooltip=['Qualidade:N', 'Lances:Q'],
    )
    bars = base.mark_bar(color='#9b9fdf', cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
    labels = base.mark_text(dy=-8, color='#fff', fontSize=10).encode(text='Lances:Q')
    return _style(bars + labels, 235)


def render_dashboard(history, username, dark=False, *, complete=False):
    st.html(DASHBOARD_CSS)
    with st.container(key='performance_dashboard'):
        st.title('dashboard | Desempenho')
        if not username:
            st.info('Entre com seu usuário do Chess.com no menu lateral para ver seu desempenho.')
            return
        left, right = st.columns([.37, .63], gap='small')
        with left:
            with st.container(key='dash_card_filters'):
                period = st.segmented_control('Período do painel', ['Últimos 7 dias', 'Últimos 30 dias'],
                                              default='Últimos 7 dias', key='dashboard_period',
                                              label_visibility='collapsed') or 'Últimos 7 dias'
                end = today()
                data = dashboard_data(history, username, end, 7 if period == 'Últimos 7 dias' else 30)
                total = data['total']
                st.html(f'<div class="dash-summary"><span>{data["start"]:%d/%m/%Y} — {end:%d/%m/%Y}<br>Partidas no período</span><strong>{total}</strong></div>')
            if not total:
                st.info('Nenhuma partida concluída neste período no histórico carregado.')
                return
            with st.container(key='dash_card_openings'):
                st.subheader('Aberturas mais usadas')
                st.altair_chart(_opening_chart(data), width='stretch', theme=None)
            with st.container(key='dash_card_results'):
                st.subheader('Taxas de vitória e derrota')
                st.altair_chart(_result_chart(data), width='stretch', theme=None)
                rates = ''.join(f'<div><i style="background:{color}"></i>{label}<strong>{100 * data["totals"].get(key, 0) / total:.1f}%</strong>{data["totals"].get(key, 0)} partidas</div>'
                                for (key, label), color in zip(RESULTS.items(), ['#9298eb', '#b49acb', '#e2dfed'])).replace('.', ',')
                st.html(f'<div class="dash-rates">{rates}</div>')
        with right:
            with st.container(key='dash_card_daily'):
                st.subheader('Evolução das partidas')
                st.altair_chart(_daily_chart(data), width='stretch', theme=None)
            with st.container(key='dash_card_quality'):
                st.subheader('Qualidade dos lances')
                counts, analyzed = quality_counts(data['games'])
                count = sum(counts.values())
                if count:
                    st.altair_chart(_quality_chart(counts), width='stretch', theme=None)
                else:
                    st.html('<div class="dash-empty"><strong>Sem lances avaliados</strong><span>Analise uma partida para preencher este gráfico.</span></div>')
                st.caption(f'{analyzed} de {total} partidas analisadas · {count} lances seus avaliados')
        coverage = 'Período completo' if complete else 'Histórico parcial · carregando período completo'
        st.html(f'<div class="dash-footer">{coverage} · Taxas incluem empates · Avaliações locais do Stockfish</div>')
