from pathlib import Path

from playwright.sync_api import expect
from streamlit.testing.v1 import AppTest
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def test_remembered_session_enters_without_another_welcome_click():
    app = AppTest.from_string('''import streamlit as st
from welcome_screen import remembered_entry
remembered_entry({'name':'Test player'})
st.write('Pronto para estudar')
''').run()
    assert not app.exception
    assert any(item.value=='Pronto para estudar' for item in app.markdown)
    assert not app.button


def test_entry_artwork_login_and_tactics_without_forge(browser_page,coach_server):
    page = browser_page
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(coach_server)
    image = page.locator('.legends-art img')
    expect(image).to_be_visible()
    expect(page.get_by_role('textbox',name='Usuário',exact=True)).to_be_visible()
    assert image.evaluate('(img)=>img.complete && img.naturalWidth>1000')
    expect(page.locator('.legends-names span')).to_have_text(['Aberturas','Táticos','Análise','Finais'])
    previews = Path(__file__).resolve().parents[1]/'.build-tools/previews'
    previews.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(previews/'welcome-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    expect(image).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(previews/'welcome-mobile.png'),full_page=True)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('welcome-tester')
    page.get_by_role('textbox',name='Senha',exact=True).fill('welcome-test-password')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.set_viewport_size({'width':1440,'height':1000})
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Tático').click()
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.get_by_role('button',name='Mate em 1',exact=True).click()
    expect(page.locator('.st-key-tactics_board_panel .board')).to_be_visible()
    expect(page.get_by_text('Sua oficina',exact=True)).to_have_count(0)
    expect(page.locator('.forge')).to_have_count(0)
    expect(page.get_by_text('Voz da oficina',exact=True)).to_have_count(0)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
