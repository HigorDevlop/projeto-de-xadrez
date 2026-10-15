"""Dados locais para testar a interface sem serviços externos."""
from pathlib import Path
from io import StringIO
from html import escape
import json
import runpy
import sys
import time
import chess
import chess.pgn
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import stockfish_analysis
import tactics
import chesscom
import preparation_data
from dataclasses import replace
from book_study import prepare_explanations
from chess_review import CATEGORIES, MoveReview

def prepared(game, engine, rating, book, study, quality, cancel):
    result = prepare_explanations(game, study, cancel)
    board = game.board()
    categories = list(CATEGORIES)
    for ply, move in enumerate(game.mainline_moves(), 1):
        san = board.san(move)
        category = categories[(ply - 1) % len(categories)]
        result['reviews'][ply] = MoveReview(ply, str(board.fullmove_number),
            'Brancas' if board.turn else 'Pretas', san, move.uci(), category,
            0, 20, None, san, '', [], result['explanations'][ply], expected_loss=.01)
        board.push(move)
    return result

stockfish_analysis.find_engine = lambda: 'motor-de-teste'
stockfish_analysis.analyse_with_books = prepared
chesscom.fetch_rating = lambda user: (1600, 'Teste local')


def preparation_material(history, username, selected_openings, engine_path, cancel=None, progress=None):
    if progress:
        progress('Preparando material local para o teste da interface…')
    game = chess.pgn.read_game(StringIO(history[0]['pgn']))
    board, steps = game.board(), []
    moves = list(game.mainline_moves())
    for index, move in enumerate(moves):
        if board.turn == chess.WHITE and len(steps) < 5:
            step = {'fen': board.fen(), 'uci': move.uci(), 'san': board.san(move),
                    'explanation': 'Linha determinística usada apenas no teste da interface.'}
            if index + 1 < len(moves) and len(steps) < 4:
                step['reply'] = moves[index + 1].uci()
            steps.append(step)
        board.push(move)
    line = {'id': 'fixture-preparation-line', 'label': 'Ruy Lopez · linha de teste',
            'opening': 'Ruy Lopez', 'side': 'white', 'source_pgn': history[0]['pgn'], 'steps': steps}
    return {'opening_lines': [line], 'middlegame': [], 'tactics': [], 'weaknesses': [],
            'analyzed_games': min(len(history), 12)}


preparation_data.build_training_material = preparation_material
def next_puzzle(theme, minimum, maximum, exclude=None):
    puzzle = tactics.parse_puzzle({'game': {'pgn': '1. f3 e5 2. g4 *'},
        'puzzle': {'id': 'fixtureA', 'initialPly': 2, 'rating': 800,
                   'themes': ['mateIn1'], 'solution': ['d8h4']}})
    excluded = {exclude} if isinstance(exclude, str) else set(exclude or ())
    identifier = next(f'fixture{i}' for i in range(1000) if f'fixture{i}' not in excluded)
    return replace(puzzle, id=identifier, themes=(theme,))
tactics.fetch_puzzle_range = next_puzzle
if not st.session_state.get('_fixture_ready'):
    st.session_state._fixture_ready = True
    st.session_state.game = '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 *'
    st.session_state.archive_user = st.session_state.history_loaded_user = 'Jogador'
    st.session_state.history_games = [
        {'rules': 'chess', 'pgn': f'[White "Jogador"]\n[Black "Oponente{i}"]\n[Opening "Ruy Lopez"]\n[ECO "C84"]\n[Result "1-0"]\n\n'+st.session_state.game.replace('*', '1-0'),
         'white': {'username': 'Jogador'}, 'black': {'username': f'Oponente{i}'},
         'end_time': int(time.time())-i*3600, 'url': f'fixture-game-{i}',
         'accuracies': {'white': 94-i*.7, 'black': 91-i*.5}} for i in range(9)]
st.session_state._fixture_runs = st.session_state.get('_fixture_runs', 0) + 1
original_button = st.button

def traced_button(*args, **kwargs):
    if kwargs.get('key') == 'study_toggle':
        original_callback = kwargs['on_click']
        def trace(*callback_args):
            st.session_state.setdefault('_fixture_study_calls', []).append(list(callback_args))
            original_callback(*callback_args)
        kwargs['on_click'] = trace
    return original_button(*args, **kwargs)

st.button = traced_button
try:
    runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
finally:
    st.button = original_button
snapshot = {name: st.session_state.get(name) for name in ('_fixture_runs', '_fixture_study_calls', 'study_open', 'ply', 'navigation_ack')}
st.html('<span id="fixture-runtime" hidden data-state="' + escape(json.dumps(snapshot), quote=True) + '"></span>')
