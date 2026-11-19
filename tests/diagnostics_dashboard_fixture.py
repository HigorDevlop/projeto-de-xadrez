"""Synthetic, reproducible visual data for the phase diagnostics."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime
from io import StringIO
from dataclasses import replace
import streamlit as st
import chess.pgn
from performance_dashboard import render_dashboard,save_game_quality
from preparation_state import today,LOCAL_ZONE
from test_fast_navigation import PGN
from test_analysis_summary import review

st.set_page_config(layout='wide')
from presentation import apply_theme
apply_theme(True)
history=[]
for index in range(3):
    game=chess.pgn.read_game(StringIO(PGN))
    game.headers.update(White='player',Black='opponent',Event='Fixture '+str(index),Result='1-0')
    board=game.board();reviews=[]
    for ply,move in enumerate(game.mainline_moves(),1):
        side='Brancas' if board.turn else 'Pretas'
        bad=board.turn and board.fullmove_number>=11
        reviews.append(replace(review(ply,side,'mistake' if bad else 'best',.15 if bad else 0),loss=220 if bad else 0))
        board.push(move)
    save_game_quality(game,reviews)
    day=today()
    history.append(dict(url='fixture-'+str(index),end_time=datetime(day.year,day.month,day.day,12,tzinfo=LOCAL_ZONE).timestamp(),pgn=str(game)))
render_dashboard(history,'player',True,complete=True,auto_diagnostics=False)
