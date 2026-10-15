from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from analysis_summary import _summary_html, summarize_reviews
from chess_review import CATEGORIES, MoveReview, player_accuracy


def review(ply=1, side='Brancas', category='best', expected_loss=0):
    return MoveReview(ply, str((ply + 1) // 2), side, 'e4', 'e2e4', category,
                      0, 20, None, 'e4', '', [], 'Exemplo.', expected_loss=expected_loss)


def test_counts_and_accuracy_accept_mapping_and_generator():
    reviews = [review(), review(2, 'Pretas', 'mistake', .15),
               review(3, 'Brancas', 'best'), review(4, 'Pretas', 'good', .03)]
    summary = summarize_reviews({item.ply: item for item in reviews})
    assert summary == summarize_reviews(item for item in reviews)
    assert summary['total'] == 4
    assert summary['totals'] == {'Brancas': 2, 'Pretas': 2}
    assert list(summary['counts']) == list(CATEGORIES)
    assert summary['counts']['best'] == {'Brancas': 2, 'Pretas': 0}
    assert summary['counts']['mistake'] == {'Brancas': 0, 'Pretas': 1}
    assert summary['accuracy'] == {'Brancas': 100, 'Pretas': player_accuracy(reviews, 'Pretas')}
    assert sum(sum(counts.values()) for counts in summary['counts'].values()) == 4


def test_no_moves_does_not_fabricate_accuracy():
    summary = summarize_reviews([])
    assert summary['total'] == 0
    assert summary['accuracy'] == {'Brancas': None, 'Pretas': None}
    html = _summary_html(summary)
    assert html.count('<strong>—</strong>') == 2
    assert '100,0%' not in html and '0,0%' not in html
    assert 'Sem lances analisados' in html


@pytest.mark.parametrize('value', [True, '94.2', -1, 101, float('nan'), float('inf'), None])
def test_invalid_official_accuracy_falls_back_to_estimate(value):
    html = _summary_html(summarize_reviews([review()]), {'white': value})
    assert '<strong>100,0%</strong>' in html
    assert 'Estimada · Stockfish' in html
    assert '<small>Chess.com</small>' not in html


def test_official_accuracy_is_distinguished_from_estimate_per_side():
    html = _summary_html(summarize_reviews([review(), review(2, 'Pretas')]), {'white': 94.2})
    assert '<strong>94,2%</strong><small>Chess.com</small>' in html
    assert '<strong>100,0%</strong><small>Estimada · Stockfish</small>' in html


def test_rows_use_current_registry_and_escape_labels(monkeypatch):
    first_key = next(iter(CATEGORIES))
    monkeypatch.setitem(CATEGORIES, first_key, replace(CATEGORIES[first_key], label='<b>Novo termo</b>', symbol='<&'))
    html = _summary_html(summarize_reviews([review(category=first_key)]))
    assert '<b>Novo termo</b>' not in html
    assert '&lt;b&gt;Novo termo&lt;/b&gt;' in html and '&lt;&amp;' in html
    assert html.count('<tr><th scope="row">') == len(CATEGORIES)
    assert 'aria-valuetext="1 de 1 lances (100%)"' in html


def test_summary_renders_in_streamlit_with_both_sides():
    app = AppTest.from_string('''
from analysis_summary import render_analysis_summary
from chess_review import MoveReview
reviews = [MoveReview(1, '1', 'Brancas', 'e4', 'e2e4', 'best', 0, 20, None, 'e4', '', [], 'Exemplo.')]
render_analysis_summary(reviews, {'white': 91.4}, dark=True)
''').run()
    assert not app.exception
    assert app.subheader[0].value == 'Resumo da qualidade dos lances'
    assert app.caption[0].value == '1 lance analisado · Brancas: 1 · Pretas: 0'
    html = app.get('html')[0].proto.body
    assert '91,4%' in html and '<small>Chess.com</small>' in html
    assert html.count('role="meter"') == 2 * len(CATEGORIES)
    assert 'Sem lances analisados' in html
