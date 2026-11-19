import pytest
from playwright.sync_api import expect
from tactics_progress import record,summary
from tactics import THEMES
from test_browser_components import browser_page,mount


def test_points_are_persistent_isolated_and_duplicate_safe(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    assert record('one','first','p1','fork',True,True,12,True)==5
    assert record('one','first','p1','fork',True,True,12,True)==0
    assert record('one','repeat','p1','fork',True,True,15,True)==0
    record('one','wrong','p2','fork',False,False)
    row=summary('one','fork')
    assert row['xp']==5 and row['solved']==2 and row['hits']==2 and row['errors']==1
    assert row['preparation']==5 and row['known']==1 and row['goal']==20
    assert row['average']==13.5
    assert summary('another','fork')['xp']==0
    assert summary('one','pin')['preparation']==0


def test_rank_increases_and_assisted_solutions_award_less(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    for i in range(40):assert record('one',str(i),'p'+str(i),'mix',True,True,10)==5
    assert summary('one')['rank']=='Prata 1' and summary('one')['xp']==200
    assert record('one','help','help','mix',True,True,30,False)==1
    assert summary('one')['known']==41


def test_new_training_clears_metrics_but_keeps_lifetime_rank(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    for i in range(40):record('one','old:'+str(i),'p'+str(i),'mix',True,True,10)
    old=summary('one',session='old')
    new=summary('one',session='new')
    assert old['solved']==40 and old['rank']=='Prata 1'
    assert new['rank']=='Prata 1' and new['xp']==200
    assert new['solved']==new['hits']==new['errors']==new['preparation']==0
    assert new['recent']==[] and new['average'] is None
    record('one','new:1','another','mix',True,True,12)
    assert summary('one',session='new')['solved']==1
    assert summary('one',session='old')['solved']==40


def test_orbit_drag_keyboard_and_black_transition(browser_page):
    from tactic_art import theme_symbol
    page=browser_page;page.set_viewport_size({'width':1200,'height':900})
    data=dict(themes=[dict(id=value,label=label,art=theme_symbol(value)) for label,value in THEMES.items()],token='orbit-test')
    mount(page,'tactics_orbit.py',data)
    expect(page.locator('.orb')).to_have_count(len(THEMES))
    expect(page.locator('.orb .orb-diagram>svg')).to_have_count(len(THEMES))
    assert page.locator('.orb[data-theme=fork] .orb-diagram').inner_html()!=page.locator('.orb[data-theme=pin] .orb-diagram').inner_html()
    stage=page.locator('.orbit-stage').bounding_box()
    page.mouse.move(stage['x']+stage['width']/2,stage['y']+stage['height']*.52)
    page.mouse.down();page.mouse.move(stage['x']+stage['width']/2-205,stage['y']+stage['height']*.52,steps=10);page.mouse.up()
    expect(page.locator('.orbit-selection h2')).to_have_text('Garfo / ataque duplo')
    assert not page.evaluate('window.events.length')
    page.locator('.orb.selected').focus();page.keyboard.press('ArrowRight')
    expect(page.locator('.orbit-selection h2')).to_have_text('Cravada')
    page.get_by_role('button',name='Começar').click()
    expect(page.get_by_role('status',name='Carregando treino')).to_be_visible()
    page.wait_for_function('window.events.length===1')
    assert page.evaluate('window.events[0].value.theme')=='pin'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


def test_dashboard_has_pie_preparation_time_and_rank(browser_page,tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    record('one','a','p1','mix',True,True,16)
    record('one','b','p2','mix',False,False)
    page=browser_page
    mount(page,'tactics_dashboard.py',dict(summary('one'),elapsed=62,running=False))
    expect(page.locator('.accuracy')).to_have_text('50%')
    expect(page.locator('.clock')).to_have_text('01:02')
    expect(page.locator('.rank-name')).to_have_text('Bronze 1')
    expect(page.locator('.prepare-detail')).to_have_text('1/50 exercícios diferentes')
    expect(page.get_by_role('img')).to_have_attribute('aria-label','1 acertos e 1 erros')


def test_recent_times_keep_five_latest_completions_per_account(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    for i in range(7):record('one',str(i),'p'+str(i),'mix',True,True,i+10)
    record('one','wrong','wrong','mix',False,False)
    record('another','private','private','mix',True,True,999)
    assert [item['seconds'] for item in summary('one')['recent']]==[16,15,14,13,12]
    assert summary('empty')['recent']==[]


def test_clock_resets_stops_and_recent_times_fade(browser_page,tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    for i in range(6):record('one',str(i),'p'+str(i),'mix',True,True,10+i)
    page=browser_page
    page.clock.install()
    data=dict(summary('one'),elapsed=32,running=True,clock_key=1)
    mount(page,'tactics_dashboard.py',data)
    page.clock.fast_forward(1100)
    expect(page.locator('.clock')).to_have_text('00:33')
    data.update(elapsed=0,clock_key=2)
    page.evaluate('(data)=>window.render(data)',data)
    expect(page.locator('.clock')).to_have_text('00:00')
    page.clock.fast_forward(1100)
    expect(page.locator('.clock')).to_have_text('00:01')
    data.update(elapsed=12,running=False)
    page.evaluate('(data)=>window.render(data)',data)
    page.clock.fast_forward(5000)
    expect(page.locator('.clock')).to_have_text('00:12')
    expect(page.locator('.recent-time')).to_have_text(['00:15','00:14','00:13','00:12','00:11'])
    assert page.locator('.recent-time').last.evaluate('node=>Number(getComputedStyle(node).opacity)')<.5
    record('one','new','new','mix',True,True,7)
    page.evaluate('(data)=>window.render(data)',dict(summary('one'),elapsed=0,running=True))
    expect(page.locator('.recent-time')).to_have_text(['00:07','00:15','00:14','00:13','00:12'])


def test_restart_same_exercise_starts_a_fresh_clock():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    class State(dict):
        __getattr__=dict.__getitem__
        __setattr__=dict.__setitem__
    puzzle=SimpleNamespace(id='same')
    state=State(puzzle=puzzle,puzzle_revision=3,tactic_clock_puzzle='same',
                tactic_clock_started=10,tactic_last_seconds=25,job_errors={},puzzle_request=None)
    tree=ast.parse(Path('app.py').read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='reset_puzzle')
    namespace=dict(st=SimpleNamespace(session_state=state),perf_counter=lambda:100)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'reset-test','exec'),namespace)
    namespace['reset_puzzle']()
    assert state.tactic_clock_started==100 and state.tactic_last_seconds==0
    assert state.tactic_clock_key==4 and state.puzzle is puzzle


def test_full_screen_orbit_stats_and_instant_solves(browser_page,tmp_path):
    import os,socket,subprocess,sys,time
    from pathlib import Path
    from urllib.request import urlopen
    root=Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    logfile=tmp_path/'server.log'
    with logfile.open('w') as log:
        process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(root/'tests/tactics_screen_fixture.py'),
            '--server.address=127.0.0.1','--server.headless=true',f'--server.port={port}','--browser.gatherUsageStats=false'],
            cwd=root,env=dict(os.environ,ACERVO_PREPARATION_DIR=str(tmp_path/'progress'),COACH_CLASSROOM_DB=str(tmp_path/'rooms.sqlite3')),
            stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        url=f'http://127.0.0.1:{port}';deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if process.poll() is not None:raise AssertionError(logfile.read_text(errors='replace'))
            try:urlopen(url+'/_stcore/health',timeout=.5).close();break
            except OSError:time.sleep(.1)
        page=browser_page;page.set_viewport_size({'width':1440,'height':1050});page.goto(url)
        expect(page.locator('.orb')).to_have_count(len(THEMES))
        folder=root/'tests/artifacts';folder.mkdir(exist_ok=True)
        page.screenshot(path=str(folder/'tactics-orbit.png'),full_page=True)
        page.get_by_role('button',name='Começar',exact=True).click()
        expect(page.locator('.board')).to_be_visible()
        expect(page.locator('.xp')).to_have_text('60 XP')
        expect(page.locator('.rank-name')).to_have_text('Bronze 2')
        page.locator('.board').evaluate('node=>window.tacticBoard=node')
        page.locator('[data-square=d8]').click();page.locator('[data-square=h4]').click()
        expect(page.locator('.xp')).to_have_text('65 XP')
        assert page.locator('.board').evaluate('node=>node===window.tacticBoard')
        expect(page.locator('.solved')).to_have_text('1 resolvidos')
        expect(page.locator('[data-testid=stException]')).to_have_count(0)
        page.screenshot(path=str(folder/'tactics-compact.png'),full_page=True)
        expect(page.get_by_text('Opções do treino',exact=True)).to_have_count(0)
        page.get_by_role('button',name='Ajustes').click()
        expect(page.get_by_role('spinbutton',name='Rating mínimo',exact=True)).to_be_visible()
        page.keyboard.press('Escape')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:
        process.terminate();process.wait(timeout=15)
