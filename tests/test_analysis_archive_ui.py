import sqlite3
from pathlib import Path
from playwright.sync_api import expect
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def test_fen_analysis_reopens_in_fresh_session_without_another_engine_run(browser_page,coach_server,tmp_path):
    page=browser_page;page.set_default_timeout(45000);expect.set_options(timeout=45000)
    page.goto(coach_server)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('analista-salvo')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-usuario-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    page.get_by_text('Partida, histórico e importação',exact=True).click()
    page.get_by_role('button',name='Carregar PGN ou FEN',exact=False).click()
    page.get_by_role('textbox',name='Posição FEN',exact=True).fill('8/8/5k2/8/5P2/8/5K2/8 w - - 0 40')
    page.get_by_role('button',name='Carregar FEN e analisar',exact=True).click()
    page.get_by_role('radio',name='Rápida',exact=True).click()
    page.get_by_role('button',name='Iniciar análise',exact=True).click()
    expect(page.get_by_text('Análise salva nesta conta · pode fechar e retomar sem executar o motor novamente.',exact=True)).to_be_visible(timeout=60000)
    readout=page.locator('.evaluation-readout').inner_text()
    dbpath=tmp_path/'classrooms.sqlite3'
    with sqlite3.connect(dbpath) as db:
        before=db.execute('SELECT updated,payload FROM saved_analyses').fetchall()
    assert len(before)==1 and 'position' in before[0][1]
    fresh=page.context.browser.new_context(storage_state=page.context.storage_state())
    second=fresh.new_page();second.goto(coach_server)
    second.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    expect(second.get_by_text('Análise salva nesta conta · pode fechar e retomar sem executar o motor novamente.',exact=True)).to_be_visible()
    expect(second.locator('[data-testid=stException]')).to_have_count(0)
    expect(second.locator('.evaluation-readout')).to_have_text(readout)
    expect(second.get_by_text('Análises salvas · 1',exact=True)).to_be_visible()
    with sqlite3.connect(dbpath) as db:assert db.execute('SELECT updated,payload FROM saved_analyses').fetchall()==before
    second.screenshot(path='tests/artifacts/saved-fen-futuristic.png',full_page=True)
    fresh.close()
