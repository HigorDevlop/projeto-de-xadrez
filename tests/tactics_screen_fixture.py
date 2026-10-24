"""Visual fixture using the real tactics callbacks, isolated from user files."""
import ast
from pathlib import Path
import sys
from time import perf_counter
from hashlib import sha256
from concurrent.futures import Future
import itertools
from types import SimpleNamespace
import streamlit as st
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import tactics_progress
from tactics_progress import record
from tactics import Puzzle,solve_move
from tactics_workspace import render_workspace
from presentation import apply_theme

st.set_page_config(layout='wide');apply_theme(True)
tactics_progress.owner_for=lambda state:'visual-tactics'
if 'seeded' not in st.session_state:
    st.session_state.update(seeded=True,tactic_theme=None,theme_mode='Escuro',active_tab='Tático',puzzle=None,
        puzzle_progress=0,puzzle_revision=0,puzzle_nonce=0,puzzle_request=None,puzzle_buffer=[],puzzle_seen=[],
        puzzle_waiting=False,puzzle_notice='',puzzle_message='',puzzle_feedback=None,puzzle_hint=None,
        puzzle_failed_ids=set(),puzzle_rewarded_ids=set(),tactic_streak=0,jobs={},job_errors={},forge_event=0,forge_sharpness=0)
    for i in range(12):record('visual-tactics','seed'+str(i),'seed'+str(i),'mix',True,True,16+i)
    for i in range(4):record('visual-tactics','miss'+str(i),'miss'+str(i),'mix',False,False)
tree=ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('reset_puzzle','puzzle_changed','puzzle_synced','advance_puzzle','choose_theme')]
import classroom,sqlite3
exec(compile(ast.Module(body=functions,type_ignores=[]),'fixture-callbacks','exec'),globals())
def queue_job(slot,key,fn,*args):
    if slot in st.session_state.jobs:return
    number=st.session_state.get('fixture_sequence',0)+1;st.session_state.fixture_sequence=number
    puzzle=Puzzle('visual'+str(number),'rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2',('d8h4',),907,('mateIn1',))
    future=Future();future.set_result(puzzle);st.session_state.jobs[slot]=(key,future)
@st.fragment(key='tactics_workspace')
def screen():render_workspace(choose_theme,reset_puzzle,puzzle_changed,advance_puzzle,queue_job,on_sync=puzzle_synced)
screen()
