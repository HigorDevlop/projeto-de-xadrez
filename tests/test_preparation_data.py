from concurrent.futures import CancelledError
from io import StringIO
from threading import Event
from types import SimpleNamespace

import chess
import chess.pgn
import pytest

import preparation_data as prep
from stockfish_analysis import find_engine


MOVES = ('1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 '
         '6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 11. c4 c6')


def archived(number=1, *, result='1-0', side='white', opening='Ruy Lopez', eco='C84', moves=MOVES):
    headers = {'White': 'Jogador' if side == 'white' else 'Adversário',
               'Black': 'Jogador' if side == 'black' else 'Adversário', 'Result': result}
    if opening is not None:
        headers['Opening'] = opening
    if eco is not None:
        headers['ECO'] = eco
    pgn = '\n'.join(f'[{key} "{value}"]' for key, value in headers.items()) + '\n\n' + moves + ' ' + result
    return {'url': f'https://www.chess.com/game/live/{number}', 'end_time': number,
            'pgn': pgn, 'white': {'username': headers['White']}, 'black': {'username': headers['Black']}}


def test_stats_count_real_results_colors_and_ignore_duplicates_unfinished_and_other_players():
    white = [archived(1), archived(2, result='0-1'), archived(3, result='1/2-1/2')]
    black = archived(4, result='0-1', side='black')
    unfinished = archived(5, result='*')
    unrelated = archived(6)
    unrelated['white']['username'] = 'Outro usuário'
    rows = prep.opening_stats(white + [white[0], black, unfinished, unrelated], 'jOgAdOr')
    assert len(rows) == 2
    assert rows[0] == {'opening': 'Ruy Lopez', 'eco': 'C84', 'color': 'white', 'games': 3,
                       'wins': 1, 'draws': 1, 'losses': 1, 'win_rate': 33.3,
                       'game_ids': [white[2]['url'], white[1]['url'], white[0]['url']]}
    assert rows[1]['color'] == 'black' and rows[1]['win_rate'] == 100
    assert prep.opening_stats(white, '') == []


def test_stats_use_chess_com_result_and_opening_url_when_headers_missing():
    item = archived(result='*', opening=None)
    item['white']['result'] = 'timevsinsufficient'
    item['pgn'] = item['pgn'].replace('[ECO "C84"]',
        '[ECO "B20"]\n[ECOUrl "https://www.chess.com/openings/Sicilian-Defense-2.Nf3-d6"]')
    row = prep.opening_stats([item], 'Jogador')[0]
    assert row['opening'] == 'Sicilian Defense'
    assert row['draws'] == 1 and row['win_rate'] == 0 and row['eco'] == 'B20'


def test_missing_opening_is_identified_from_local_catalogue():
    item = archived(opening=None, eco=None, moves='1. e4 c5')
    row = prep.opening_stats([item], 'Jogador')[0]
    assert row['opening'] == 'Sicilian Defense' and row['eco'] == 'B20'


def test_missing_engine_no_selection_and_cancel_do_not_invent_training(monkeypatch):
    launches = []
    monkeypatch.setattr(prep, 'analyse_with_books', lambda *args, **kwargs: launches.append(args))
    result = prep.build_training_material([archived()], 'Jogador', ['Ruy Lopez'], '')
    assert result == {'opening_lines': [], 'middlegame': [], 'tactics': [], 'weaknesses': [], 'analyzed_games': 0}
    assert prep.build_training_material([archived()], 'Jogador', [], __file__) == result
    assert launches == []
    cancel = Event()
    cancel.set()
    with pytest.raises(CancelledError):
        prep.build_training_material([archived()], 'Jogador', ['Ruy Lopez'], '', cancel=cancel)


class FakeEngine:
    id = {'name': 'Stockfish test'}

    def __init__(self):
        self.config = None
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def configure(self, options):
        self.config = options

    def analyse(self, board, limit, multipv=1, root_moves=None):
        self.calls.append((board.fen(), root_moves))
        options = list(root_moves or board.legal_moves)[:multipv]
        results = []
        for first in options:
            probe = board.copy()
            line = [first]
            probe.push(first)
            for _ in range(5):
                if probe.is_game_over():
                    break
                move = next(iter(probe.legal_moves))
                line.append(move)
                probe.push(move)
            results.append({'pv': line})
        return results


def fake_reviews(game, *args, **kwargs):
    reviews, board = {}, game.board()
    for ply, played in enumerate(game.mainline_moves(), 1):
        best = next(move for move in board.legal_moves if move != played)
        reviews[ply] = SimpleNamespace(expected_loss={1: .04999, 2: .9, 3: .05, 21: .25}.get(ply, 0),
                                       best_san=board.san(best))
        board.push(played)
    return {'reviews': reviews}


@pytest.fixture
def fake_stockfish(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(prep, 'analyse_with_books', fake_reviews)
    monkeypatch.setattr(prep.chess.engine.SimpleEngine, 'popen_uci', lambda *args, **kwargs: engine)
    return engine


def test_training_uses_only_players_verified_errors_and_legal_preloaded_solutions(fake_stockfish):
    updates = []
    result = prep.build_training_material([archived()], 'Jogador', ['Ruy Lopez'], __file__, progress=updates.append)
    assert result['analyzed_games'] == 1
    assert [row['source_ply'] for row in result['tactics']] == [21, 3]
    assert [row['source_ply'] for row in result['middlegame']] == [21]
    assert fake_stockfish.config == {'Threads': 1, 'Hash': 64}
    assert len(result['opening_lines']) >= 2
    assert any('Analisando partida 1 de 1' in update for update in updates)
    assert all(row['sample_moves'] == 11 for row in result['weaknesses'])
    for exercise in result['tactics']:
        game = chess.pgn.read_game(StringIO(exercise['source_pgn']))
        board = game.board()
        moves = list(game.mainline_moves())
        for move in moves[:exercise['source_ply'] - 1]:
            board.push(move)
        assert board.fen() == exercise['fen']
        assert exercise['side'] == 'white' and board.turn == chess.WHITE
        assert exercise['uci'] == exercise['line'][0]
        assert exercise['uci'] != moves[exercise['source_ply'] - 1].uci()
        assert exercise['expected_loss'] >= .05
        assert 'Na sua partida você jogou' in exercise['explanation']
        for uci in exercise['line']:
            move = chess.Move.from_uci(uci)
            assert move in board.legal_moves
            board.push(move)


def test_opening_lessons_have_five_player_decisions_and_legal_automatic_replies(fake_stockfish):
    result = prep.build_training_material([archived(side='black')], 'Jogador', ['Ruy Lopez'], __file__)
    for lesson in result['opening_lines']:
        assert lesson['side'] == 'black'
        assert 1 <= len(lesson['steps']) <= 5
        board = chess.Board(lesson['steps'][0]['fen'])
        for index, step in enumerate(lesson['steps']):
            assert board.turn == chess.BLACK and board.fen() == step['fen']
            move = chess.Move.from_uci(step['uci'])
            assert move in board.legal_moves and board.san(move) == step['san']
            board.push(move)
            if step.get('reply'):
                board.push_uci(step['reply'])
            elif index < len(lesson['steps']) - 1:
                pytest.fail('A lesson skipped an opponent response')


def test_batches_are_capped_at_twelve_relevant_games_and_selections_preserve_color(fake_stockfish, monkeypatch):
    analyzed = []
    def analyze(game, *args, **kwargs):
        analyzed.append(game)
        return {'reviews': {}}
    monkeypatch.setattr(prep, 'analyse_with_books', analyze)
    history = [archived(i) for i in range(1, 20)] + [archived(100, side='black')]
    selected = [{'opening': 'Ruy Lopez', 'eco': 'C84', 'color': 'white'}]
    result = prep.build_training_material(history, 'Jogador', selected, __file__)
    assert len(analyzed) == result['analyzed_games'] == 12
    assert all(game.headers['White'] == 'Jogador' for game in analyzed)
    assert result['tactics'] == result['middlegame'] == result['weaknesses'] == []


def test_cancel_releases_shared_engine_lock(fake_stockfish, monkeypatch):
    cancel = Event()
    original = fake_stockfish.analyse
    def analyze(*args, **kwargs):
        cancel.set()
        return original(*args, **kwargs)
    monkeypatch.setattr(fake_stockfish, 'analyse', analyze)
    with pytest.raises(CancelledError):
        prep.build_training_material([archived()], 'Jogador', ['Ruy Lopez'], __file__, cancel=cancel)
    assert prep._ENGINE_LOCK.acquire(blocking=False)
    prep._ENGINE_LOCK.release()


@pytest.mark.skipif(not find_engine(), reason='Stockfish not installed')
def test_real_stockfish_builds_a_solution_to_an_actual_mating_error():
    game = archived(result='0-1', opening='Barnes Opening', eco='A00', moves='1. f3 e5 2. g4 Qh4#')
    result = prep.build_training_material([game], 'Jogador', ['Barnes Opening'], find_engine())
    assert result['analyzed_games'] == 1
    assert result['opening_lines']
    mistakes = [row for row in result['tactics'] if row['source_ply'] == 3]
    assert len(mistakes) == 1
    exercise = mistakes[0]
    assert exercise['uci'] != 'g2g4' and exercise['expected_loss'] >= .05
    board = chess.Board(exercise['fen'])
    for uci in exercise['line']:
        board.push_uci(uci)
    assert result['weaknesses']
