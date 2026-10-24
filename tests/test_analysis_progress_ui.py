from pathlib import Path
import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page
import test_coach_chess_ui as desktop
from test_coach_chess_ui import coach_server


@pytest.fixture
def progress_server(tmp_path,monkeypatch,request):
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'app.py').write_text(f"""
import sys,runpy,time
sys.path.insert(0,{str(root)!r})
import stockfish_analysis
original=stockfish_analysis.analyse_with_books
def measured(*args,progress=None,**kwargs):
    def report(done,total,phase,*engine):
        if progress:progress(done,total,phase,*engine)
        if phase=='Avaliando os lances':time.sleep(1.2)
    return original(*args,progress=report,**kwargs)
stockfish_analysis.analyse_with_books=measured
runpy.run_path({str(root/'app.py')!r},run_name='__main__')
""",encoding='utf8')
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    return request.getfixturevalue('coach_server')


def test_progress_is_centered_updates_and_disappears_without_rebuilding_board(browser_page,progress_server):
    page=browser_page
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(progress_server)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('progresso-ui')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-progresso-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    page.get_by_text('Partida, histórico e importação',exact=True).click()
    page.get_by_role('button',name='Carregar PGN ou FEN',exact=False).click()
    page.get_by_role('textbox',name='Cole o PGN').fill('1. e4 e5 *')
    page.get_by_role('button',name='Carregar PGN e analisar',exact=True).click()
    page.get_by_role('button',name='Iniciar análise',exact=True).click()
    panel=page.locator('.st-key-analysis_progress_overlay')
    expect(panel).to_be_visible()
    expect(panel).to_contain_text('Stockfish')
    expect(panel.get_by_role('progressbar')).to_be_visible()
    expect(panel).to_contain_text('1 de 2 lances avaliados')
    box=panel.bounding_box()
    assert abs(box['x']+box['width']/2-720)<2
    assert abs(box['y']+box['height']/2-500)<2
    path=Path(__file__).resolve().parent/'artifacts'/'analysis-progress-centered.png'
    path.parent.mkdir(exist_ok=True)
    page.screenshot(path=str(path))
    expect(panel).to_have_count(0,timeout=30000)
    expect(page.locator('.quality-summary')).to_contain_text('Stockfish')
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
