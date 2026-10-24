"""Real browser: form submission must use the newly selected UCI engine."""
from playwright.sync_api import expect
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server
from engine_catalog import find_berserk
import pytest


@pytest.mark.skipif(not find_berserk(),reason='Berserk not installed')
def test_user_can_choose_berserk_then_stockfish_without_automatic_analysis(browser_page,coach_server):
    page=browser_page
    page.goto(coach_server)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('motores-ui')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-motores-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    board=page.locator('.st-key-analysis_board_focus')
    board.locator('[data-square="e2"]').click()
    board.locator('[data-square="e4"]').click()
    board.locator('[data-square="e7"]').click()
    board.locator('[data-square="e5"]').click()
    page.get_by_role('button',name='Analisar Partida',exact=False).click()
    selector=page.get_by_role('combobox',name='Motor de avaliação')
    selector.click()
    page.get_by_role('option',name='Berserk',exact=True).click()
    expect(page.get_by_text('Estimada · Berserk 14',exact=True)).to_have_count(0)
    page.get_by_role('button',name='Iniciar análise',exact=True).click()
    expect(page.locator('.quality-summary')).to_contain_text('Berserk 14',timeout=45000)
    page.get_by_role('button',name='Analisar Partida',exact=False).click()
    expect(selector).to_have_value('Berserk')
    selector.click()
    page.get_by_role('option',name='Stockfish',exact=True).click()
    # The old result remains until submitting the form, with its original source.
    expect(page.locator('.quality-summary')).to_contain_text('Berserk 14')
    page.get_by_role('button',name='Iniciar análise',exact=True).click()
    expect(page.locator('.quality-summary')).to_contain_text('Stockfish',timeout=45000)
    expect(page.locator('.quality-summary')).not_to_contain_text('Berserk')
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
