"""Compact, accessible summary of the move reviews from a completed analysis."""
from collections.abc import Mapping
from html import escape
import math

import streamlit as st

from chess_review import CATEGORIES, player_accuracy, canonical_category
from design_tokens import palette
from quality_icons import icon_html


SIDES = ('Brancas', 'Pretas')


def summarize_reviews(reviews):
    """Count recognized reviews and estimate accuracy without changing their data.

    Accepts a mapping of ply to MoveReview or any iterable of MoveReview.
    Unknown categories/sides are excluded, so every counted move belongs to one
    of the categories shown. An empty side has accuracy None, never a guessed 0.
    """
    values = reviews.values() if isinstance(reviews, Mapping) else (reviews or ())
    recognized = [review for review in values
                  if canonical_category(review.category) in CATEGORIES and review.side in SIDES]
    counts = {key: dict.fromkeys(SIDES, 0) for key in CATEGORIES}
    totals = dict.fromkeys(SIDES, 0)
    for review in recognized:
        counts[canonical_category(review.category)][review.side] += 1
        totals[review.side] += 1
    return {
        'total': len(recognized),
        'totals': totals,
        'counts': counts,
        'accuracy': {side: player_accuracy(recognized, side) for side in SIDES},
        'engines': sorted({review.engine_name for review in recognized}),
    }


def _accuracy(summary, official, side):
    key = 'white' if side == 'Brancas' else 'black'
    value = official.get(key, official.get(side))
    if (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0 <= value <= 100):
        return float(value), 'Chess.com'
    estimate = summary['accuracy'][side]
    engines = ', '.join(summary.get('engines', ())) or 'motor local'
    return estimate, f'Estimada · {engines}' if estimate is not None else 'Sem lances analisados'


def _summary_html(summary, official_accuracies=None, dark=False):
    official = official_accuracies if isinstance(official_accuracies, Mapping) else {}
    cards = []
    for side in SIDES:
        value, source = _accuracy(summary, official, side)
        accuracy = f'{value:.1f}%'.replace('.', ',') if value is not None else '—'
        cards.append(
            f'<div class="quality-accuracy"><span>Precisão das {side.lower()}</span>'
            f'<strong>{accuracy}</strong><small>{escape(source)}</small></div>'
        )
    rows = []
    for key, category in CATEGORIES.items():
        label = escape(category.label)
        color, ink = escape(category.color, quote=True), escape(category.ink, quote=True)
        cells = []
        for side in SIDES:
            count, total = summary['counts'][key][side], summary['totals'][side]
            percent = 100 * count / total if total else 0
            description = f'{count} de {total} lances ({percent:.0f}%)' if total else 'Sem lances analisados'
            cells.append(
                '<td><div class="quality-count">'
                f'<span>{count}</span><div class="quality-track" role="meter" '
                f'aria-label="{side}: {label}" aria-valuemin="0" aria-valuemax="100" '
                f'aria-valuenow="{percent:.2f}" aria-valuetext="{description}">'
                f'<div style="width:{percent:.2f}%;background:{color}"></div></div></div></td>'
            )
        rows.append(
            '<tr><th scope="row"><div class="quality-term">'
            f'<span class="quality-symbol" aria-hidden="true" style="background:{color};color:{ink}">'
            f'{icon_html(category)}</span>'
            f'<span title="{escape(category.description, quote=True)}">{label}</span>'
            '</div></th>' + ''.join(cells) + '</tr>'
        )
    colors = palette(dark)
    theme = (f"--q-ink:{colors['ink']};--q-muted:{colors['muted']};--q-card:{colors['soft']};"
             f"--q-line:{colors['border']};--q-track:{colors['border']};--q-accent:{colors['accent']}")
    return '''<style>
    .quality-summary {color:var(--q-ink);container-type:inline-size;font-family:'Segoe UI',system-ui,sans-serif}
    .quality-summary .quality-accuracies {display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px}
    .quality-summary .quality-accuracy {display:flex;flex-direction:column;gap:6px;padding:18px 20px;background:var(--q-card);border:1px solid var(--q-line);border-radius:14px}
    .quality-summary .quality-accuracy>span {font-size:12px;font-weight:600;color:var(--q-muted)}
    .quality-summary .quality-accuracy>strong {font:650 38px/1.2 'Segoe UI',sans-serif;letter-spacing:-1.5px;font-variant-numeric:tabular-nums;color:var(--q-ink)}
    .quality-summary .quality-accuracy>small {font-size:12px;color:var(--q-muted)}
    .quality-summary table {width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed}
    .quality-summary thead th {font-size:11px;color:var(--q-muted);font-weight:600;letter-spacing:.02em;padding:0 12px 12px;text-align:left;border-bottom:1px solid var(--q-line)}
    .quality-summary thead th:first-child {width:46%;padding-left:0}
    .quality-summary tbody th {font-weight:600;padding:11px 6px 11px 0;text-align:left}
    .quality-summary td {padding:11px 12px}
    .quality-summary tbody tr+tr {border-top:1px solid var(--q-line)}
    .quality-summary .quality-term {display:flex;align-items:center;gap:10px;line-height:1.3}
    .quality-summary .quality-symbol {display:flex;flex:none;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;font:800 18px/1 'Segoe UI',sans-serif;letter-spacing:-1px;box-shadow:inset 0 1px 0 #ffffff40,0 2px 5px #0003}
    .quality-summary .quality-count {display:flex;align-items:center;gap:10px;font-variant-numeric:tabular-nums}
    .quality-summary .quality-count>span {min-width:2ch;text-align:right;font-weight:600}
    .quality-summary .quality-track {height:7px;flex:1;background:var(--q-track);border-radius:8px;overflow:hidden;box-shadow:inset 0 1px 2px #0003}
    .quality-summary .quality-track>div {height:100%;border-radius:4px}
    .quality-summary .quality-note {color:var(--q-muted);font-size:12px;line-height:1.5;margin:16px 0 0}
    .quality-summary .quality-accuracy:first-child {border-top:2px solid #e3e3df}
    .quality-summary .quality-accuracy:last-child {border-top:2px solid #777d88}
    .quality-summary tbody tr:hover {background:#ffffff03}
    .quality-summary tbody th,.quality-summary td {padding-top:9px;padding-bottom:9px}
    @container(max-width:420px) {
      .quality-summary .quality-accuracy {padding:12px;gap:3px}
      .quality-summary .quality-accuracy>strong {font-size:26px}
      .quality-summary td,.quality-summary thead th {padding-left:6px;padding-right:6px}
      .quality-summary .quality-count {gap:5px}
      .quality-summary .quality-term {gap:7px;font-size:13px}
      .quality-summary .quality-symbol {width:28px;height:30px;font-size:15px}
    }
    </style>''' + (
        f'<section class="quality-summary" style="{theme}" aria-label="Qualidade dos lances por jogador">'
        f'<div class="quality-accuracies">{"".join(cards)}</div>'
        '<table aria-label="Classificações dos lances de brancas e pretas">'
        '<thead><tr><th scope="col">Classificação</th><th scope="col">Brancas</th>'
        f'<th scope="col">Pretas</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
        '<p class="quality-note">As barras mostram a proporção dos lances analisados de cada jogador. '
        'A precisão estimada usa a perda no indicador de chances da análise local; não é a precisão oficial do Lichess.</p></section>'
    )


def render_analysis_summary(reviews, official_accuracies=None, dark=False):
    """Render the current categories with per-side counts and accuracy provenance."""
    summary = summarize_reviews(reviews)
    with st.container(border=True, key='analysis_summary'):
        st.subheader('Resumo da qualidade dos lances', anchor=False)
        total = summary['total']
        if total:
            noun = 'lance analisado' if total == 1 else 'lances analisados'
            st.caption(f"{total} {noun} · Brancas: {summary['totals']['Brancas']} · Pretas: {summary['totals']['Pretas']}")
        else:
            st.caption('Nenhum lance analisado ainda.')
        st.html(_summary_html(summary, official_accuracies, dark))


def analysis_sidebar_html(reviews, official_accuracies=None, headers=None):
    """Side-by-side player comparison for the board's summary tab."""
    summary=summarize_reviews(reviews)
    official=official_accuracies if isinstance(official_accuracies,Mapping) else {}
    headers=headers or {}
    values=sorted(reviews.values() if isinstance(reviews,Mapping) else reviews,key=lambda r:r.ply)
    samples=[r for r in values if r.white_cp is not None or r.white_mate is not None]
    graph=''
    if samples:
        points=[]
        for index,review in enumerate(samples):
            cp=(1000 if review.white_mate>0 else -1000) if review.white_mate is not None else review.white_cp
            y=50-45*math.tanh(cp/400)
            points.append(f'{index*300/max(1,len(samples)-1):.2f},{y:.2f}')
        graph=('<svg class="review-graph" viewBox="0 0 300 100" role="img" aria-label="Avaliação ao longo da partida, perspectiva das brancas">'
               '<path d="M0 50H300" stroke="#596052" stroke-width="1"/>'
               '<polyline points="'+ ' '.join(points)+'" fill="none" stroke="#efa338" stroke-width="2.5"/>'+
               ('<circle cx="'+points[0].split(',')[0]+'" cy="'+points[0].split(',')[1]+'" r="3" fill="#efa338"/>' if len(points)==1 else '')+'</svg>')
    players=[]
    for side,key,piece in [('Brancas','White','♔'),('Pretas','Black','♚')]:
        value,source=_accuracy(summary,official,side)
        score=f'{value:.1f}%'.replace('.',',') if value is not None else '—'
        players.append('<div class="review-player"><b>'+escape(headers.get(key,side))+'</b><div class="review-avatar">'+piece+'</div><strong>'+score+'</strong><small>'+escape(source)+'</small></div>')
    rows=[]
    for key,category in CATEGORIES.items():
        counts=summary['counts'][key]
        rows.append(f'<div class="review-count-row"><b>{counts["Brancas"]}</b><span><i style="--review-color:{escape(category.color,quote=True)}">{icon_html(category)}</i>{escape(category.label)}</span><b>{counts["Pretas"]}</b></div>')
    return (graph+'<div class="review-players">'+''.join(players)+'</div><p class="review-score-title">Precisão · Brancas / Pretas</p>'+''.join(rows)+
            '<p class="review-footnote">Análise local · '+escape(', '.join(summary['engines']))+'. Precisão local pelo método Lichess; pode diferir de outros aplicativos. Os valores oficiais importados são identificados como Chess.com.</p>')
