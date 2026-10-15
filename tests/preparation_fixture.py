"""Aplicativo isolado para verificar o preparo sem rede nem Stockfish real."""
from copy import deepcopy
from datetime import timedelta
from io import StringIO
import os
from pathlib import Path
import sys

import chess
import chess.pgn


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MOVES = ('1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 d6 5. d3 a6 '
         '6. O-O h6 7. Re1 Nge7 8. Nbd2 O-O 9. Bb3 Ba7 10. Nf1 Ng6 '
         '11. h3 Qh4 12. a3')


def fixture_history():
    games = []
    for number, result in enumerate(('1-0', '0-1'), 1):
        pgn = (f'[White "Jogador"]\n[Black "Adversário {number}"]\n'
               f'[Opening "Italian Game"]\n[ECO "C50"]\n[Result "{result}"]\n\n'
               f'{MOVES} {result}')
        games.append({'pgn': pgn, 'url': f'fixture-preparation-{number}', 'rules': 'chess',
                      'end_time': 1790000000 + number,
                      'white': {'username': 'Jogador', 'rating': 1600},
                      'black': {'username': f'Adversário {number}', 'rating': 1550}})
    return games


def opening_line(number=1):
    pairs = [('e2e4', 'e7e5'), ('g1f3', 'b8c6'), ('f1c4', 'f8c5'),
             ('c2c3', 'g8f6'), ('d2d3', None)]
    if number == 2:
        pairs[-2:] = [('d2d3', 'g8f6'), ('c2c3', None)]
    board, steps = chess.Board(), []
    for index, (uci, reply) in enumerate(pairs, 1):
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        step = {'fen': board.fen(), 'uci': uci, 'san': board.san(move),
                'explanation': f'Decisão {index}: desenvolva as peças e prepare o centro.'}
        board.push(move)
        if reply:
            step['reply'] = reply
            board.push_uci(reply)
        steps.append(step)
    return {'id': f'fixture-line-{number}', 'label': f'Italian Game · linha {number}',
            'opening': 'Italian Game', 'side': 'white', 'steps': steps,
            'source_pgn': fixture_history()[0]['pgn']}


def fixture_material():
    source = fixture_history()[0]['pgn']
    game = chess.pgn.read_game(StringIO(source))
    assert game is not None and not game.errors
    node = list(game.mainline())[22]
    board = node.parent.board()
    correct = chess.Move.from_uci('f3h4')
    assert node.move.uci() == 'a2a3'
    assert correct in board.legal_moves and board.piece_at(chess.H4) == chess.Piece(chess.QUEEN, chess.BLACK)
    exercise = {
        'id': 'fixture-missed-queen', 'fen': board.fen(), 'uci': correct.uci(),
        'san': board.san(correct), 'line': [correct.uci()], 'source_pgn': source,
        'source_ply': 23, 'opening': 'Italian Game', 'side': 'white',
        'expected_loss': .25, 'phase': 'middlegame', 'theme': 'Capturas e trocas',
        'explanation': 'Na partida de teste você jogou a3. Nxh4 captura a dama que ficou sem defesa.',
    }
    return {'opening_lines': [opening_line(1), opening_line(2)],
            'middlegame': [deepcopy(exercise)], 'tactics': [deepcopy(exercise)],
            'analyzed_games': 2,
            'weaknesses': [{'phase': 'middlegame', 'theme': 'Capturas e trocas',
                            'count': 1, 'sample_moves': 12, 'mean_loss': .25,
                            'description': 'Um lance da partida de teste deixou escapar a captura da dama.'}]}


def build_fixture_material(history, username, selected_openings, engine_path, cancel=None, progress=None):
    if progress:
        progress('Preparando duas linhas e a captura perdida na partida de teste…')
    return fixture_material()


def main():
    import streamlit as st
    import preparation_data
    from preparation_state import STAGE_SECONDS, load_plan, new_plan, save_plan, today, plan_path

    st.set_page_config(page_title='Preparo · teste local', layout='wide')
    preparation_data.build_training_material = build_fixture_material
    import preparation_workspace
    preparation_workspace.build_training_material = build_fixture_material

    seed_marker = plan_path('Jogador').with_suffix('.seeded')
    if os.environ.get('ACERVO_PREP_FIXTURE_SEEDED') == '1' and not seed_marker.exists():
        if load_plan('Jogador') is None:
            day = today()
            save_plan(new_plan('Jogador', day, day + timedelta(days=2), ['Italian Game'], fixture_material()))
        seed_marker.touch()

    def elapse_training_budget():
        plan = st.session_state.get('prep_plan')
        if plan and plan.get('active'):
            plan['active']['last_tick'] -= STAGE_SECONDS

    with st.sidebar:
        st.button('Teste local: completar 30 minutos', on_click=elapse_training_budget)
    preparation_workspace.render_preparation(fixture_history(), 'Jogador', __file__, dark=False, table=False)


if __name__ == '__main__':
    main()
