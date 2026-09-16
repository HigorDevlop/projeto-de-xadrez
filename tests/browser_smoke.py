"""Optional DOM check: python tests/browser_smoke.py (Playwright + Edge)."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import socket
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    temp = tempfile.TemporaryDirectory()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = dict(os.environ, ACERVO_USER_PREFERENCE=str(Path(temp.name) / 'user.json'))
    server = subprocess.Popen(
        [sys.executable, '-m', 'streamlit', 'run', 'tests/ui_fixture.py', '--server.port', str(port),
         '--server.headless', 'true'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, env=env,
    )
    try:
        for _ in range(40):
            try:
                with urlopen(url + '/_stcore/health', timeout=1):
                    break
            except OSError:
                time.sleep(0.25)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1100})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url)
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=45000)
            print('LOADED', flush=True)
            assert page.locator('.coord').count() == 0
            sidebar = page.locator('[data-testid="stSidebar"]')
            assert sidebar.get_attribute('aria-expanded') == 'false'
            page.get_by_role('button', name='settings', exact=True).click()
            expect(page.get_by_role('combobox', name='Qualidade')).to_be_visible()
            expect(page.get_by_role('switch', name='Mostrar qualidade do lance')).to_be_visible()
            page.get_by_role('button', name='settings', exact=True).click()
            page.keyboard.press('ArrowRight')
            page.get_by_role('button', name='e4: peão branco', exact=True).wait_for(timeout=20000)
            expect(page.locator('.quality')).to_have_text('📖')
            expect(page.locator('.lesson-text:visible')).to_contain_text('📖 e4')
            first_lesson = page.locator('.lesson-text:visible').inner_text()
            page.keyboard.press('ArrowLeft')
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=20000)
            print('KEYBOARD_AND_BOOK_OK', flush=True)
            page.keyboard.press('End')
            page.get_by_role('button', name='f7: dama branco', exact=True).wait_for(timeout=20000)
            page.keyboard.press('Home')
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=20000)
            print('INPUT_GUARD_AND_BOUNDS_OK', flush=True)
            # Drag a piece with real pointer events and inspect the floating sprite.
            origin=page.get_by_role('button', name='d2: peão branco', exact=True)
            destination=page.get_by_role('button', name='d4: vazia', exact=True)
            origin.scroll_into_view_if_needed()
            start,end=origin.bounding_box(),destination.bounding_box()
            page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
            page.mouse.down()
            page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=12)
            expect(page.locator('.drag-ghost')).to_be_visible()
            page.mouse.up()
            page.get_by_role('button', name='d4: peão branco', exact=True).wait_for(timeout=20000)
            expect(page.locator('.drag-ghost')).to_have_count(0)
            expect(page.locator('.lesson-text:visible')).to_contain_text('📖 d4')
            assert page.locator('.lesson-text:visible').inner_text() != first_lesson
            print('ANIMATED_DRAG_OK',flush=True)
            # An illegal drag animates back without changing the position.
            origin=page.get_by_role('button',name='e7: peão preto',exact=True)
            destination=page.get_by_role('button',name='e4: vazia',exact=True)
            origin.scroll_into_view_if_needed()
            start,end=origin.bounding_box(),destination.bounding_box()
            page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
            page.mouse.down()
            page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=10)
            page.mouse.up()
            expect(page.locator('.drag-ghost')).to_have_count(0)
            expect(origin).to_be_visible()
            print('ILLEGAL_DROP_RETURN_OK',flush=True)
            expect(page.locator('.review-row')).to_have_count(10)
            assert page.locator('.review-page').evaluate('(el)=>el.scrollHeight <= el.clientHeight + 2')
            page.get_by_role('tab', name='Análise', exact=True).click()
            expect(page.get_by_role('button', name='Executar avaliação')).to_be_visible()
            expect(page.locator('.lesson-text:visible')).to_contain_text('d4')
            page.get_by_role('tab', name='Tático', exact=True).click()
            expect(page.get_by_role('button', name='Random · tático aleatório')).to_be_visible()
            expect(page.get_by_role('combobox', name='Tema do tático')).to_be_visible()
            page.get_by_role('button', name='arrow_back Voltar').click()
            expect(page.get_by_role('button', name='Executar avaliação')).to_be_visible()
            page.get_by_role('tab', name='Estudo com livros', exact=True).click()
            expect(page.get_by_text('Carregar livro desejado', exact=True)).to_be_visible()
            page.get_by_role('button', name='arrow_back Voltar').click()
            page.get_by_role('tab', name='Partida', exact=True).click()
            page.locator('[data-testid="stExpandSidebarButton"]').click()
            uploader = sidebar.locator('input[type=file]').first
            uploader.set_input_files({'name':'broken.png','mimeType':'image/png','buffer':b'not png'})
            expect(sidebar.get_by_text('Não foi possível abrir a foto.', exact=False)).to_be_visible()
            uploader.set_input_files(str(ROOT / 'assets/bobby-qualities.png'))
            expect(sidebar.get_by_role('img', name='Foto do perfil', exact=True)).to_be_visible()
            assert sidebar.get_by_role('img', name='Foto do perfil', exact=True).evaluate('(el)=>el.complete && el.naturalWidth>0')
            print('REVIEW_TUTOR_BACK_TABS_PHOTO_OK',flush=True)
            page.screenshot(path=str(Path(tempfile.gettempdir()) / 'acervo-new-layout.png'), full_page=True)
            page.goto(url + '/?fixture=brilliant')
            expect(page.locator('.lesson-text:visible')).to_contain_text('!! e4', timeout=30000)
            expect(page.locator('.square.brilliant')).to_have_attribute('data-square', 'e4')
            assert page.locator('.square.brilliant').evaluate("el=>getComputedStyle(el,'::before').animationName") == 'brilliant-aura'
            expect(page.get_by_role('img', name='Bobby Fischer: Brilhante', exact=True)).to_be_visible()
            page.screenshot(path=str(Path(tempfile.gettempdir()) / 'acervo-brilliant.png'), full_page=True)
            # A background text update must preserve an in-progress drag.
            origin=page.get_by_role('button', name='e7: peão preto', exact=True)
            destination=page.get_by_role('button', name='e5: vazia', exact=True)
            start,end=origin.bounding_box(),destination.bounding_box()
            page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
            page.mouse.down()
            page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=10)
            expect(page.locator('.drag-ghost')).to_be_visible()
            page.get_by_role('button', name='Reexplicar lance').evaluate('(el)=>el.click()')
            expect(page.locator('.lesson-text:visible')).to_contain_text('Observe a posição resultante')
            expect(page.locator('.drag-ghost')).to_be_visible()
            page.mouse.up()
            expect(page.get_by_role('button', name='e5: peão preto', exact=True)).to_be_visible()
            page.goto(url + '/?fixture=tactic')
            expect(page.get_by_text('Jogam as pretas', exact=True)).to_be_visible(timeout=30000)
            origin=page.get_by_role('button', name='d8: dama preto', exact=True)
            destination=page.get_by_role('button', name='h4: vazia', exact=True)
            start,end=origin.bounding_box(),destination.bounding_box()
            page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
            page.mouse.down()
            page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=12)
            page.mouse.up()
            expect(page.get_by_role('heading', name='Tático resolvido!', exact=True)).to_be_visible()
            page.get_by_role('button', name='Recomeçar tático', exact=True).click()
            expect(page.get_by_text('Jogam as pretas', exact=True)).to_be_visible()
            print('BLUE_AURA_BACKGROUND_DRAG_TACTIC_OK',flush=True)
            assert not errors, errors
            assert page.locator('[data-testid="stException"]').count() == 0
            print('JS_ERRORS', errors, flush=True)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
        temp.cleanup()


if __name__ == '__main__':
    main()
