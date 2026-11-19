import classroom as rooms
from test_coach_chess_ui import coach_server
from test_browser_components import browser_page


def test_preparation_empty_states_editor_and_mobile(browser_page,coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('creator','creator-password-123')
    invite=rooms.issue_professor_key(owner)
    rooms.register_professor('professor','teacher-password-123',invite)
    page=browser_page;page.set_viewport_size({'width':1440,'height':1000})
    page.goto(coach_server)
    page.get_by_role('radio',name='Professor',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('professor')
    page.get_by_role('textbox',name='Senha',exact=True).fill('teacher-password-123')
    page.get_by_role('textbox',name='Chave especial do Professor (obrigatória)',exact=True).fill(invite)
    page.get_by_role('button',name='Entrar',exact=True).click()
    expect(page.locator('.prep-hero h2')).to_have_text('Modo Preparo')
    for tab,slug in [('Alunos e acessos','keys'),('Rotina individual','routine'),('Dashboard','dashboard'),('Presença e advertências','attendance'),('Conversas','chat'),('Aulas','lessons')]:
        page.get_by_role('tab',name=tab,exact=True).click()
        if tab=='Conversas':expect(page.get_by_placeholder('Escreva uma mensagem')).to_be_visible()
        if tab=='Aulas':expect(page.get_by_role('button',name='Iniciar aula ao vivo',exact=False)).to_be_visible()
        expect(page.locator('[data-testid=stException]')).to_have_count(0)
        page.screenshot(path=f'tests/artifacts/redesign-{slug}-desktop.png',full_page=True)
    page.get_by_role('tab',name='Dashboard',exact=True).click()
    page.get_by_role('combobox',name='Selecionar aluno',exact=True).click()
    page.get_by_role('option',name='Aluno 2',exact=True).click()
    page.get_by_role('button',name='Criar rotina',exact=True).click()
    expect(page.locator('.prep-profile strong')).to_have_text('Aluno 2')
    expect(page.get_by_role('tab',name='Rotina individual',exact=True)).to_have_attribute('aria-selected','true')
    expect(page.locator('.prep-plan')).to_be_visible()
    page.set_viewport_size({'width':390,'height':844})
    for tab,slug in [('Rotina individual','routine'),('Conversas','chat'),('Aulas','lessons')]:
        page.get_by_role('tab',name=tab,exact=True).click()
        if tab=='Conversas':expect(page.get_by_placeholder('Escreva uma mensagem')).to_be_visible()
        if tab=='Aulas':expect(page.get_by_role('button',name='Iniciar aula ao vivo',exact=False)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2')
        page.screenshot(path=f'tests/artifacts/redesign-{slug}-mobile.png',full_page=True)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
