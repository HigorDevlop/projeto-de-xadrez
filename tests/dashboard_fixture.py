"""Isolated visual fixture; never included in application maintenance."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from performance_dashboard import render_dashboard,save_game_quality
from test_performance_dashboard import archived
from test_analysis_summary import review
import chess.pgn
from io import StringIO

st.set_page_config(layout='wide')
history=[archived(i,result=['1-0','0-1','1/2-1/2'][i%3],side='black' if i%4==0 else 'white',days=i%7,
                  opening=['Italian Game','Caro-Kann Defense','Sicilian Defense','Queen’s Gambit'][i%4]) for i in range(32)]
for record in history:
    save_game_quality(chess.pgn.read_game(StringIO(record['pgn'])),[review(1,'Brancas','best'),review(2,'Pretas','excellent'),review(3,'Brancas','inaccuracy')])
render_dashboard(history,'player',True,complete=True)
