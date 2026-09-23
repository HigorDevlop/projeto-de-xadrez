"""Dados locais para testar a interface sem serviços externos."""
from pathlib import Path
import runpy
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import stockfish_analysis
import tactics
import chesscom
from dataclasses import replace
from book_study import prepare_explanations

def prepared(game, engine, rating, book, study, quality, cancel):
    return prepare_explanations(game, study, cancel)

stockfish_analysis.find_engine = lambda: 'motor-de-teste'
stockfish_analysis.analyse_with_books = prepared
chesscom.fetch_rating = lambda user: (1600, 'Teste local')
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
        {'rules': 'chess', 'pgn': f'[White "Jogador"]\n[Black "Oponente{i}"]\n\n'+st.session_state.game,
         'white': {'username': 'Jogador'}, 'black': {'username': f'Oponente{i}'},
         'end_time': 1790000000-i*3600, 'url': f'fixture-game-{i}',
         'accuracies': {'white': 94-i*.7, 'black': 91-i*.5}} for i in range(9)]
runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
