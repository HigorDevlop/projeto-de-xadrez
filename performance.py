"""Comparações de volume entre vitórias e derrotas por janela temporal."""
from datetime import datetime, timedelta
from preparation_state import LOCAL_ZONE
from preparation_data import _records


def comparative_records(history, username):
    return [{'date': datetime.fromtimestamp(row['timestamp'], LOCAL_ZONE).date(),
             'result': row['outcome']}
            for row in _records(history, username)
            if row['outcome'] in {'wins', 'losses', 'draws'} and row['timestamp']]


def comparison_buckets(records, period, today, cycle=None):
    if period == 'Ciclo atual' and cycle:
        start, finish = cycle
        lower, upper = start, min(today, finish)
        width = 7
    else:
        width = 7 if period == '7 dias' else 30
        lower, upper = today - timedelta(days=width-1), today
    if upper < lower:
        return []
    span = (upper - lower).days + 1
    days_per_bucket = 1 if period == '7 dias' else 7
    buckets = []
    for offset in range(0, span, days_per_bucket):
        first, last = lower + timedelta(days=offset), min(upper, lower + timedelta(days=offset+days_per_bucket-1))
        buckets.append({'period': first.strftime('%d/%m') if first == last else f'{first.day}–{last.day}/{last.month:02d}',
                        'wins': 0, 'losses': 0, 'draws': 0})
    for row in records:
        if lower <= row['date'] <= upper:
            index = min((row['date'] - lower).days // days_per_bucket, len(buckets)-1)
            buckets[index][row['result']] += 1
    return buckets


def comparison_totals(buckets):
    wins, losses = sum(b['wins'] for b in buckets), sum(b['losses'] for b in buckets)
    volume = wins + losses
    return {'wins': wins, 'losses': losses, 'draws': sum(b.get('draws', 0) for b in buckets),
            'volume': volume, 'win_share': round(wins * 100 / volume, 1) if volume else None,
            'loss_share': round(losses * 100 / volume, 1) if volume else None}


def preparation_comparison_chart(rows, period_order, dark=False):
    """Reference-style grouped columns, scoped to the preparation page."""
    import altair as alt
    from design_tokens import palette

    colors = palette(dark)
    peak = max((row['Partidas'] for row in rows), default=0)
    base = alt.Chart(alt.Data(values=rows)).encode(
        x=alt.X('Período:N', sort=period_order, title='Período',
                axis=alt.Axis(labelAngle=0, labelPadding=12, titlePadding=16,
                              domain=True, domainColor=colors['border'], grid=False)),
        xOffset=alt.XOffset('Resultado:N', sort=['Vitórias', 'Derrotas'],
                           scale=alt.Scale(paddingInner=.2)),
        y=alt.Y('Partidas:Q', title=None,
                scale=alt.Scale(domain=[0, max(1, peak * 1.2)], nice=True),
                axis=alt.Axis(tickMinStep=1, format=',.0f', grid=False, domain=False)),
        tooltip=[alt.Tooltip('Período:N'), alt.Tooltip('Resultado:N'),
                 alt.Tooltip('Partidas:Q', format=',.0f'),
                 alt.Tooltip('Percentual no comparativo:Q', format='.1f', title='% no total')],
    )
    bars = base.mark_bar().encode(
        color=alt.Color('Resultado:N',
            scale=alt.Scale(domain=['Vitórias', 'Derrotas'], range=['#0B1038', '#C74620']),
            legend=alt.Legend(title=None, orient='top-right', direction='horizontal',
                              symbolType='square', symbolSize=90, padding=6)))
    labels = base.mark_text(dy=-9, color=colors['muted'], fontSize=12).encode(
        text=alt.Text('Partidas:Q', format=',.0f'))
    return (bars + labels).properties(
        height=350,
        title=alt.TitleParams(text='Vitórias e derrotas por período', anchor='middle',
                              fontSize=18, fontWeight=600, color=colors['ink'], offset=20),
        description='Barras verticais agrupadas: vitórias em azul-marinho e derrotas em laranja, com o total sobre cada barra.',
    ).configure(background=colors['background'], font='Segoe UI', padding=20).configure_view(
        stroke=None
    ).configure_axis(
        labelColor=colors['muted'], titleColor=colors['muted'], labelFontSize=12,
        titleFontSize=13, titleFontWeight='normal', ticks=False,
    ).configure_legend(labelColor=colors['ink'], labelFontSize=12)



def render_comparative_chart(history, username, dark=False, *, context='painel', compact=False, plan=None):
    import altair as alt
    import streamlit as st
    from datetime import date
    from design_tokens import palette
    from preparation_state import load_plan, today as local_today

    active_plan = plan or (load_plan(username) if username else None)
    periods = ['7 dias', '30 dias'] + (['Ciclo atual'] if active_plan else [])
    with st.container(key=f'{context}_performance'):
        st.subheader('Vitórias × derrotas', anchor=False)
        period = st.segmented_control('Período', periods, default='7 dias', key=f'{context}_performance_period') or periods[0]
        cycle = ((date.fromisoformat(active_plan['start']), date.fromisoformat(active_plan['end']))
                 if period == 'Ciclo atual' and active_plan else None)
        buckets = comparison_buckets(comparative_records(history, username), period, local_today(), cycle)
        totals = comparison_totals(buckets)
        wins, losses, draws = st.columns(3)
        wins.metric('Vitórias', totals['wins'])
        losses.metric('Derrotas', totals['losses'])
        draws.metric('Empates', totals['draws'])
        if totals['volume']:
            wins.caption(f'{totals["win_share"]:.1f}% das decisões'.replace('.', ','))
            losses.caption(f'{totals["loss_share"]:.1f}% das decisões'.replace('.', ','))
        if not totals['volume']:
            st.caption('Sem vitórias ou derrotas registradas neste período.')
            return
        period_order = [item['period'] for item in buckets]
        rows = [{'Período': item['period'], 'Resultado': label, 'Partidas': item[key],
                 'Percentual no comparativo': round(item[key] * 100 / totals['volume'], 1)}
                for item in buckets for key, label in (('wins', 'Vitórias'), ('losses', 'Derrotas'))]
        if context == 'preparo':
            st.altair_chart(preparation_comparison_chart(rows, period_order, dark=dark), width='stretch', theme=None)
            st.caption(f'{totals["volume"]} partidas com resultado · os empates aparecem à parte.')
            return
        positive, negative = palette(dark)['accent'], '#CB5964' if dark else '#B13746'
        peak = max(row['Partidas'] for row in rows)
        colors = palette(dark)
        base = alt.Chart(alt.Data(values=rows)).encode(
            x=alt.X('Período:N', sort=period_order, title=None,
                    scale=alt.Scale(paddingInner=.35, paddingOuter=.2),
                    axis=alt.Axis(labelAngle=0, labelPadding=12, grid=False)),
            y=alt.Y('Partidas:Q', title='Partidas',
                    scale=alt.Scale(domain=[0, max(1, peak * 1.2)], nice=True, zero=True),
                    axis=alt.Axis(tickMinStep=1, tickCount=5, format='d', titlePadding=12, grid=True)),
            xOffset=alt.XOffset('Resultado:N', sort=['Vitórias', 'Derrotas'],
                               scale=alt.Scale(paddingInner=.25, paddingOuter=.1)),
            tooltip=['Período:N', 'Resultado:N', alt.Tooltip('Partidas:Q', format='d')],
        )
        bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            color=alt.Color('Resultado:N', sort=['Vitórias', 'Derrotas'],
                            scale=alt.Scale(domain=['Vitórias', 'Derrotas'], range=[positive, negative]),
                            legend=alt.Legend(title=None, orient='top', direction='horizontal',
                                              offset=18, columnPadding=24, symbolType='circle')),
        )
        labels = base.mark_text(dy=-9, color=colors['ink'], fontSize=12).encode(
            text=alt.Text('Partidas:Q', format='d'))
        chart = (bars + labels).properties(
            height=260 if compact else 320,
            description='Barras verticais separadas por data: vitórias em verde e derrotas em vermelho, com os valores acima.',
        ).configure(background='transparent', font='Segoe UI').configure_view(stroke=None).configure_axis(
            labelColor=colors['muted'], titleColor=colors['muted'], labelFontSize=12,
            titleFontSize=12, titleFontWeight='normal', gridColor=colors['border'],
            gridOpacity=.4, domain=False, ticks=False
        ).configure_legend(labelColor=colors['ink'], titleColor=colors['ink'], labelFontSize=12)
        st.altair_chart(chart, width='stretch', theme=None)
        st.caption(f'{totals["volume"]} partidas com vitória ou derrota · empates contados à parte.')
