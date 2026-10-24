import chess
import classroom as rooms
from playwright.sync_api import expect
from test_browser_components import browser_page, drag
from test_coach_chess_ui import coach_server


def test_branch_edit_save_and_resume(browser_page, coach_server, tmp_path, monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'classrooms.sqlite3'))
    rooms.register_user('analista', 'senha-analista-123')
    page = browser_page
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto(coach_server + '/analise')
    page.get_by_role('textbox', name='Usuário', exact=True).fill('analista')
    page.get_by_role('textbox', name='Senha', exact=True).fill('senha-analista-123')
    page.get_by_role('button', name='Entrar', exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Análise').click()
    expect(page.get_by_role('heading', name='Análise de partidas', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='Estudar', exact=True)).to_have_count(0)
    expect(page.get_by_role('button', name='Livros', exact=True)).to_have_count(0)
    expect(page.locator('.lesson')).to_be_hidden()
    page.locator('[data-testid=stMain]').evaluate('(e)=>e.scrollTop=0')
    page.screenshot(path='tests/artifacts/analysis-board-first-top.png', full_page=True)
    page.get_by_text('Partida, histórico e importação', exact=True).click()
    old_revision = page.locator('.board').get_attribute('data-revision')
    page.get_by_role('button', name='Nova partida · jogar livremente').click()
    board = page.locator('.board')
    expect(board).not_to_have_attribute('data-revision', old_revision)
    expect(page.locator('.move-counter')).to_have_text('Lance 0 de 0')
    expect(board.locator('[data-square="e2"]')).to_have_attribute('aria-label', 'e2: peão branco')
    def move(origin, target):
        board.locator(f'[data-square="{origin}"]').click()
        board.locator(f'[data-square="{target}"]').click()
        expect(page.locator('.move-counter')).to_have_text('Lance 1 de 1')
        # Acknowledgement unlocks the board; subsequent navigation is local.
        expect(board).not_to_have_attribute('data-revision', move.revision)
        move.revision = board.get_attribute('data-revision')
    move.revision = board.get_attribute('data-revision')
    for origin, target in [('e2','e4'), ('d2','d4'), ('c2','c4')]:
        if origin != 'e2':
            page.keyboard.press('ArrowLeft')
            expect(page.locator('.move-counter')).to_have_text('Lance 0 de 1')
        move(origin, target)
    page.get_by_role('button', name='Editar tabuleiro').click()
    controls = page.locator('.st-key-analysis_editor_controls')
    expect(controls).to_be_visible()
    expect(controls.get_by_role('button', name='♔ Rei branco', exact=True)).to_be_visible()
    expect(page.locator('.st-key-analysis_toolbar')).to_have_count(0)
    controls.screenshot(path='tests/artifacts/analysis-editor-refined.png')
    for source, target, label in [('a1','e5','torre branco'), ('e5','a1','torre branco'),
                                 ('a8','e6','torre preto'), ('e6','a8','torre preto')]:
        board.scroll_into_view_if_needed()
        revision = board.get_attribute('data-revision')
        drag(page, source, target)
        expect(board).not_to_have_attribute('data-revision', revision)
        expect(board.locator(f'[data-square="{target}"]')).to_have_attribute('aria-label', f'{target}: {label}')
    controls.get_by_role('button', name='Apagar peça', exact=True).click()
    expect(page.locator('.workspace')).to_have_attribute('data-edit-tool','erase')
    revision = board.get_attribute('data-revision')
    board.locator('[data-square="e2"]').click()
    expect(board).not_to_have_attribute('data-revision', revision)
    expect(board.locator('[data-square="e2"]')).to_have_attribute('aria-label','e2: vazia')
    controls.get_by_role('button', name='♘ Cavalo branco', exact=True).click()
    expect(page.locator('.workspace')).to_have_attribute('data-edit-tool','N')
    # Existing black pieces remain freely draggable while a white piece is selected.
    for source, target in [('b8','e5'), ('e5','b8')]:
        board.scroll_into_view_if_needed()
        revision = board.get_attribute('data-revision')
        drag(page, source, target)
        expect(board).not_to_have_attribute('data-revision', revision)
        expect(board.locator(f'[data-square="{target}"]')).to_have_attribute('aria-label', f'{target}: cavalo preto')
    board.locator('[data-square="e4"]').click()
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: cavalo branco')
    controls.get_by_role('radio', name='Brancas', exact=True).click()
    page.get_by_role('button', name='Salvar posição e jogar').click()
    expect(controls).to_have_count(0)
    expect(page.locator('.move-counter')).to_have_text('Lance 0 de 0')
    move.revision = board.get_attribute('data-revision')
    move('g1','f3')
    expect(board.locator('[data-square="f3"]')).to_have_attribute('aria-label','f3: cavalo branco')
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    page.screenshot(path='tests/artifacts/analysis-board-first.png', full_page=True)
