from datetime import datetime, timedelta
from io import StringIO

import chess.pgn
import pytest
from streamlit.testing.v1 import AppTest

from performance_dashboard import dashboard_data, quality_counts, quality_key, save_game_quality
from preparation_state import LOCAL_ZONE, today
from test_analysis_summary import review


def archived(number, *, result='1-0', side='white', days=0, opening='Italian Game'):
    day = today() - timedelta(days=days)
    white, black = ('player', 'opponent') if side == 'white' else ('opponent', 'player')
    return {'url': f'game-{number}', 'end_time': datetime(day.year, day.month, day.day, 12, tzinfo=LOCAL_ZONE).timestamp(),
            'pgn': f'[White "{white}"]\n[Black "{black}"]\n[Opening "{opening}"]\n[Result "{result}"]\n\n1. e4 e5 2. Nf3 Nc6 {result}'}


def test_window_results_denominators_duplicates_and_player_moves():
    records = [archived(1), archived(2, result='1-0', side='black'), archived(3, result='1/2-1/2'),
               archived(4, days=6), archived(5, days=7), archived(6, days=-1), archived(7, result='*')]
    data = dashboard_data(records + [records[0]], 'PLAYER', today())
    assert data['total'] == 4
    assert data['totals'] == {'wins': 2, 'losses': 1, 'draws': 1}
    assert data['openings'][0]['Vitória (%)'] == 50
    assert data['openings'][0]['Derrota (%)'] == 25
    assert data['moves'] == 8
    assert sum(row['Partidas'] for row in data['daily']) == 4
    assert data['sides'][1]['Vitória (%)'] == 0
    assert dashboard_data(records, 'player', today(), 30)['total'] == 5
    assert dashboard_data(records, 'unrelated', today())['total'] == 0


def test_dashboard_fetch_covers_month_boundary_without_hundred_game_cap(monkeypatch):
    import chesscom
    calls = []
    monkeypatch.setattr(chesscom, 'fetch_archives', lambda user: ['2026/10', '2026/09', '2026/08'])
    def fetch(user, month):
        calls.append(month)
        return [{'url': f'{month}-{i}', 'pgn': '1. e4 *', 'end_time': i} for i in range(120)]
    monkeypatch.setattr(chesscom, 'fetch_games', fetch)
    assert len(chesscom.fetch_dashboard_games('player', '2026/09', '2026/10')) == 240
    assert calls == ['2026/10', '2026/09']


def test_saved_quality_counts_only_connected_side_and_replaces_reanalysis(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR', str(tmp_path))
    item = archived(1)
    game = chess.pgn.read_game(StringIO(item['pgn']))
    games = dashboard_data([item], 'player', today())['games']
    assert quality_counts(games)[1] == 0
    save_game_quality(game, [review(1, 'Brancas', 'best'), review(2, 'Pretas', 'blunder')])
    counts, analyzed = quality_counts(games)
    assert analyzed == 1 and counts['best'] == 1 and counts['blunder'] == 0
    save_game_quality(game, [review(1, 'Brancas', 'excellent')])
    counts, analyzed = quality_counts(games)
    assert analyzed == 1 and counts['best'] == 0 and counts['excellent'] == 1
    game.comment = 'Annotation does not change the identity.'
    assert quality_key(game) == games[0]['quality_key']
    next(tmp_path.glob('*.json')).write_text('invalid', encoding='utf8')
    assert quality_counts(games)[1] == 0


@pytest.mark.parametrize('dark', [False, True])
def test_dashboard_renders_both_filters_with_quality_and_empty_states(tmp_path, monkeypatch, dark):
    monkeypatch.setenv('ACERVO_PERFORMANCE_DIR', str(tmp_path))
    records = [archived(1), archived(2, result='0-1')]
    game = chess.pgn.read_game(StringIO(records[0]['pgn']))
    save_game_quality(game, [review()])
    source = f'from performance_dashboard import render_dashboard\nrender_dashboard({records!r}, "player", {dark!r})'
    app = AppTest.from_string(source, default_timeout=15).run()
    assert not app.exception
    assert len(app.get('vega_lite_chart')) == 4
    assert not app.dataframe
    assert not app.get('progress')
    assert any('1 de 2 partidas' in caption.value for caption in app.caption)
    app.button_group[0].set_value('Últimos 30 dias').run()
    assert not app.exception
    for record in tmp_path.glob('*.json'):
        record.unlink()
    app.run()
    assert not app.exception
    assert len(app.get('vega_lite_chart')) == 3
    assert any('0 de 2 partidas analisadas' in caption.value for caption in app.caption)
    empty = AppTest.from_string('from performance_dashboard import render_dashboard\nrender_dashboard([], "player")').run()
    assert not empty.exception
    assert any('Nenhuma partida concluída' in info.value for info in empty.info)
