from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import expect

from tactics import Puzzle
from tactics_workspace import pump_tactics
from test_browser_components import browser_page
import test_coach_chess_ui as desktop
from test_coach_chess_ui import coach_server


def test_buffer_replenishes_without_changing_active_puzzle_and_ignores_stale_results():
    puzzle = Puzzle('one', '6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1', ('a1a8',), 900, ('mateIn1',))
    key = ('mateIn1', 0, 4000, 1)
    state = SimpleNamespace(puzzle=puzzle, puzzle_buffer=[], puzzle_seen=[], puzzle_waiting=False,
                            jobs={}, job_errors={}, puzzle_request=key)
    calls = []
    def queue(slot, request, *args):
        if slot not in state.jobs:
            calls.append((slot, request, args))
            state.jobs[slot] = request, Future()
    def completed(value):
        future=Future();future.set_result(value);return future
    reset=lambda:None
    advance=lambda:None
    assert not pump_tactics(state,queue,reset,advance)
    for name in ('two','three','four'):
        state.jobs['puzzle_next'][1].set_result(replace(puzzle,id=name))
        assert not pump_tactics(state,queue,reset,advance)
        assert state.puzzle is puzzle
    assert len(state.puzzle_buffer)==3 and 'puzzle_next' not in state.jobs
    assert len(calls)==3
    assert calls[-1][2][-2]=={'one','two','three'}
    state.jobs['puzzle_next'] = ('other',0,4000,0), completed(replace(puzzle,id='stale'))
    assert not pump_tactics(state,queue,reset,advance)
    assert [p.id for p in state.puzzle_buffer]==['two','three','four']


def test_failed_prefetch_keeps_current_puzzle_and_does_not_retry_in_a_loop():
    key=('mix',0,4000,0)
    future=Future();future.set_exception(ValueError('Sem conexão'))
    puzzle=Puzzle('one','6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1',('a1a8',),900,())
    state=SimpleNamespace(puzzle=puzzle,puzzle_buffer=[],puzzle_seen=[],puzzle_waiting=False,
                          jobs={'puzzle_next':(key,future)},job_errors={},puzzle_request=key)
    def forbidden(*args):raise AssertionError('Não deve tentar novamente automaticamente')
    assert not pump_tactics(state,forbidden,forbidden,forbidden)
    assert state.puzzle is puzzle and state.job_errors['puzzle_next',key]=='Sem conexão'


def test_local_round_can_repeat_after_exhaustion_without_repeating_buffered_puzzles():
    from offline_tactics import LocalBankExhausted
    key=('mix',0,4000,0)
    first=Puzzle('one','6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1',('a1a8',),900,())
    future=Future();future.set_exception(LocalBankExhausted(4))
    state=SimpleNamespace(puzzle=first,puzzle_buffer=[replace(first,id='two')],puzzle_seen=['three','four'],
        puzzle_waiting=False,jobs={'puzzle_next':(key,future)},job_errors={},puzzle_request=key)
    requests=[]
    def queue(*args):requests.append(args)
    assert not pump_tactics(state,queue,lambda:None,lambda:None)
    assert state.puzzle is first and state.puzzle_seen==[]
    assert requests[0][-2]=={'one','two'} and not state.job_errors


@pytest.fixture
def tactics_server(tmp_path,monkeypatch,request):
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'app.py').write_text(f'''
import sys,runpy,time,itertools
sys.path.insert(0,{str(root)!r})
import streamlit as st
import tactics
if not hasattr(tactics,'test_counter'):tactics.test_counter=itertools.count()
def fetch(theme,minimum,maximum,exclude_id=None):
    time.sleep(.3)
    number=next(tactics.test_counter)
    return tactics.parse_puzzle({{'game':{{'pgn':'1. f3 e5 2. g4 *'}},
        'puzzle':{{'id':'exercise'+str(number),'initialPly':2,'rating':800,
                   'themes':['mateIn1'],'solution':['d8h4']}}}})
tactics.fetch_puzzle_range=fetch
st.session_state.full_runs=st.session_state.get('full_runs',0)+1
st.html('<span id="full-runs" hidden>'+str(st.session_state.full_runs)+'</span>')
runpy.run_path({str(root/'app.py')!r},run_name='__main__')
''',encoding='utf8')
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    return request.getfixturevalue('coach_server')


def test_continuous_tactics_keeps_page_and_board_mounted_during_prefetch_and_solves(browser_page,tactics_server):
    page=browser_page;page.set_viewport_size({'width':1440,'height':1050})
    page.goto(tactics_server)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('treino-continuo')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-treino-continuo')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_tactics button').evaluate('node=>node.click()')
    page.locator('.orb[data-theme=mateIn1]').evaluate('node=>node.click()')
    board=page.locator('.st-key-tactics_board_panel .board')
    expect(board).to_be_visible()
    backdrop=page.locator('[data-testid=stAppViewContainer]')
    assert 'data:image/png' in backdrop.evaluate('node=>getComputedStyle(node).backgroundImage')
    assert set(backdrop.evaluate('node=>getComputedStyle(node).backgroundAttachment').split(', '))=={'fixed'}
    board.evaluate("el=>{window.originalBoard=el;window.originalSquare=el.querySelector('[data-square=d8]')}")
    runs=page.locator('#full-runs').text_content()
    board.locator('[data-square=b8]').click()
    expect(board.locator('[data-square=b8]')).to_have_class(__import__('re').compile('.*selected.*'))
    expect(page.get_by_text('3 prontos',exact=True)).to_be_visible()
    assert page.evaluate('window.originalBoard.isConnected && window.originalSquare.isConnected')
    expect(board.locator('[data-square=b8]')).to_have_class(__import__('re').compile('.*selected.*'))
    # Wrong moves are acknowledged without replacing the board or giving points.
    board.locator('[data-square=c6]').click()
    expect(page.locator('.tactics-status')).to_contain_text('Tente outra ideia')
    for solved in range(1,5):
        old=board.get_attribute('data-revision')
        board.locator('[data-square=d8]').click();board.locator('[data-square=h4]').click()
        expect(board).not_to_have_attribute('data-revision',old)
        expect(page.locator('.solved')).to_have_text(str(solved)+' resolvidos')
        assert page.locator('#full-runs').text_content()==runs
        assert page.evaluate('window.originalBoard.isConnected && window.originalSquare.isConnected')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    output=Path(__file__).parent/'artifacts/tactics-continuous.png';output.parent.mkdir(exist_ok=True)
    page.screenshot(path=str(output),full_page=True)
    page.get_by_role('button',name='Dica',exact=False).click()
    expect(page.locator('.training-hint')).to_have_count(1)
    page.get_by_role('button',name='Recomeçar',exact=False).click()
    expect(page.locator('.training-hint')).to_have_count(0)
    old_meta=board.get_attribute('data-revision')
    page.get_by_role('button',name='Pular',exact=False).click()
    expect(board).not_to_have_attribute('data-revision',old_meta)
    assert page.locator('#full-runs').text_content()==runs
    assert page.evaluate('window.originalBoard.isConnected && window.originalSquare.isConnected')
    # Returning to the catalog stops the old background UI from reappearing.
    previous_xp=page.locator('.xp').text_content()
    page.locator('.st-key-sidebar_tactics button').evaluate('node=>node.click()')
    expect(page.locator('.orbit-start')).to_be_visible()
    page.wait_for_timeout(1200)
    expect(page.locator('.st-key-tactics_board_panel')).to_have_count(0)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)

    page.locator('.orb[data-theme=mateIn1]').evaluate('node=>node.click()')
    expect(page.locator('.solved')).to_have_text('0 resolvidos')
    expect(page.locator('.xp')).to_have_text(previous_xp)
    expect(page.locator('.prepare')).to_have_text('0%')
    expect(page.locator('.recent-time')).to_have_count(0)
    page.locator('.st-key-sidebar_nav_analise a').evaluate('node=>node.click()')
    expect(page.locator('.st-key-tactics_workbench')).to_have_count(0)
    assert 'data:image/png' not in backdrop.evaluate('node=>getComputedStyle(node).backgroundImage')
