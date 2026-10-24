import classroom as rooms
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def test_mandatory_login_creator_invites_and_remembered_access(browser_page,coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    rooms.bootstrap_owner('criador','password-criador-123')
    player=rooms.register_user('test-player','password-test-player')
    player_id=rooms.identity(player)['id']
    page=browser_page
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(coach_server+'/preparo')
    expect(page.get_by_role('button',name='Entrar',exact=True)).to_be_visible()
    expect(page.locator('.board')).to_have_count(0)
    expect(page.locator('.st-key-sidebar_navigation a')).to_have_count(0)
    expect(page.get_by_text('Superadministrador',exact=True)).to_have_count(0)
    expect(page.get_by_text('A conta do criador é configurada',exact=False)).to_have_count(0)
    page.screenshot(path='tests/artifacts/coach-required-login.png',full_page=True)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('criador')
    page.get_by_role('textbox',name='Senha',exact=True).fill('password-criador-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    expect(page.get_by_role('heading',name='Usuários',exact=True)).to_be_visible()
    page.wait_for_function("localStorage.getItem('coach_chess_device_v1')?.length>30")
    expect(page.get_by_role('textbox',name='Professor que receberá a chave',exact=True)).to_have_count(0)
    page.get_by_role('button',name='Criar chave',exact=False).click()
    expect(page.locator('[data-testid=stCode]')).to_have_count(1)
    first=page.locator('[data-testid=stCode]').inner_text()
    page.get_by_role('button',name='Criar chave',exact=False).click()
    expect(page.locator('[data-testid=stCode]')).not_to_have_text(first)
    assert len(rooms.admin_overview(rooms.login_owner('criador','password-criador-123'))['invitations'])==2
    expect(page.get_by_text('Validade para ativação: 15 minutos.',exact=True)).to_be_visible()
    page.get_by_role('button',name='Excluir',exact=True).first.click()
    expect(page.get_by_role('button',name='Excluir',exact=True)).to_have_count(1)
    assert len(rooms.admin_overview(rooms.login_owner('criador','password-criador-123'))['invitations'])==1
    page.screenshot(path='tests/artifacts/coach-superadministrator.png',full_page=True)
    page.get_by_role('tab',name='Usuários',exact=True).click()
    page.get_by_role('textbox',name='Buscar usuário',exact=True).fill('test-player')
    expect(page.locator('.user-detail h3')).to_have_text('test-player')
    page.screenshot(path='tests/artifacts/admin-users-redesign.png',full_page=True)
    page.locator('.st-key-admin_user_delete button').click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button',name='Cancelar',exact=True).click()
    assert rooms.identity(player)
    page.get_by_role('tab',name='Usuários',exact=True).click()
    page.locator('.st-key-admin_user_delete button').click()
    page.get_by_role('button',name='Excluir definitivamente',exact=False).click()
    expect(page.get_by_text('Conta excluída: test-player',exact=True)).to_be_visible()
    assert rooms.identity(player) is None
    page.reload()
    expect(page.get_by_role('heading',name='Usuários',exact=True)).to_be_visible()
    expect(page.get_by_role('textbox',name='Senha',exact=True)).to_have_count(0)
    expect(page.get_by_role('button',name='Continuar para o aplicativo',exact=True)).to_have_count(0)
    # A fresh tab establishes another Streamlit session, as reopening the app does.
    reopened_context=page.context.browser.new_context(storage_state=page.context.storage_state())
    reopened=reopened_context.new_page()
    reopened.goto(coach_server)
    expect(reopened.get_by_role('heading',name='Usuários',exact=True)).to_be_visible()
    expect(reopened.get_by_role('textbox',name='Senha',exact=True)).to_have_count(0)
    reopened_context.close()
    expect(page.get_by_text('MINHA SESSÃO',exact=True)).not_to_be_visible()
    page.get_by_text('Configurações',exact=True).click()
    expect(page.get_by_text('MINHA SESSÃO',exact=True)).to_be_visible()
    page.get_by_role('button',name='Sair e esquecer este navegador',exact=True).click()
    expect(page.get_by_role('button',name='Entrar',exact=True)).to_be_visible()
    page.wait_for_function("localStorage.getItem('coach_chess_device_v1')===null")
    page.reload()
    expect(page.get_by_role('button',name='Entrar',exact=True)).to_be_visible()
    expect(page.locator('.board')).to_have_count(0)
    assert page.locator('[data-testid=stException]').count()==0
