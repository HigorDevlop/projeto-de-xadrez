from io import BytesIO
from PIL import Image
import pytest
import classroom as rooms
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def photo(color):
    out=BytesIO()
    Image.new('RGB',(500,300),color).save(out,format='PNG')
    return out.getvalue()


def test_photo_persists_for_authenticated_identity_and_isolated_accounts(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'photos.sqlite3'))
    owner=rooms.bootstrap_owner('criador','password-criador-123')
    teacher=rooms.enter_professor('teacher','teacher-password-123',rooms.issue_professor_key(owner,'teacher'))
    pupil=rooms.login_student(rooms.students(teacher)[0]['access_key'])
    assert rooms.load_profile_photo(owner) is None
    expected=rooms.save_profile_photo(owner,photo('red'))
    assert Image.open(BytesIO(expected)).size==(320,320)
    rooms.logout(owner)
    owner=rooms.login_owner('criador','password-criador-123')
    assert rooms.load_profile_photo(owner)==expected
    assert rooms.load_profile_photo(teacher) is None
    assert rooms.load_profile_photo(pupil) is None
    pupil_photo=rooms.save_profile_photo(pupil,photo('blue'))
    assert rooms.load_profile_photo(owner)==expected
    assert rooms.load_profile_photo(pupil)==pupil_photo
    ordinary=rooms.register_user('ordinary','ordinary-password-123')
    personal_photo=rooms.save_profile_photo(ordinary,photo('yellow'))
    rooms.join_room(ordinary,rooms.students(teacher)[1]['access_key'])
    assert rooms.load_profile_photo(ordinary)==personal_photo
    assert rooms.load_profile_photo(rooms.login_user('ordinary','ordinary-password-123'))==personal_photo
    with pytest.raises(ValueError):rooms.save_profile_photo(owner,b'invalid image')
    assert rooms.load_profile_photo(owner)==expected
    restored=rooms.restore_device(rooms.remember_device(owner))
    assert rooms.load_profile_photo(restored)==expected
    rooms.logout(pupil)
    with pytest.raises(PermissionError):rooms.save_profile_photo(pupil,photo('green'))


def test_uploaded_avatar_survives_reload_and_logout(browser_page,coach_server,tmp_path,monkeypatch):
    from playwright.sync_api import expect
    expect.set_options(timeout=30000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('criador','password-criador-123')
    page=browser_page
    page.goto(coach_server)
    def login(remember=False):
        page.get_by_role('textbox',name='Usuário',exact=True).fill('criador')
        page.get_by_role('textbox',name='Senha',exact=True).fill('password-criador-123')
        page.get_by_role('button',name='Entrar',exact=True).click()
        expect(page.get_by_role('heading',name='Usuários',exact=True)).to_be_visible()
    login(True)
    page.locator('.file').set_input_files({'name':'photo.png','mimeType':'image/png','buffer':photo('red')})
    expect(page.locator('.editor')).to_be_visible()
    page.get_by_role('button',name='Usar foto',exact=True).click()
    expect(page.locator('.avatar img')).to_be_visible()
    source=page.locator('.avatar img').get_attribute('src')
    assert rooms.load_profile_photo(owner)
    page.wait_for_function("localStorage.getItem('coach_chess_device_v1')?.length>30")
    page.reload()
    expect(page.locator('.avatar img')).to_have_attribute('src',source)
    page.get_by_text('Configurações',exact=True).click()
    page.get_by_role('button',name='Sair e esquecer este navegador',exact=True).click()
    expect(page.get_by_role('button',name='Entrar',exact=True)).to_be_visible()
    login()
    expect(page.locator('.avatar img')).to_have_attribute('src',source)
    assert page.locator('[data-testid=stException]').count()==0
