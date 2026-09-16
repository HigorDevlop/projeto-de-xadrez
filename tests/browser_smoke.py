"""Optional DOM check: python tests/browser_smoke.py (Playwright + Edge)."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    server = subprocess.Popen(
        [sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.port', '8502',
         '--server.headless', 'true'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
    )
    try:
        for _ in range(40):
            try:
                with urlopen('http://127.0.0.1:8502/_stcore/health', timeout=1):
                    break
            except OSError:
                time.sleep(0.25)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1100})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto('http://127.0.0.1:8502')
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=45000)
            print('LOADED', flush=True)
            assert page.locator('.coord').count() == 0
            sidebar = page.locator('[data-testid="stSidebar"]')
            assert sidebar.get_attribute('aria-expanded') == 'false'
            page.get_by_role('heading', name='Tabuleiro', exact=True).click()
            page.keyboard.press('ArrowRight')
            page.get_by_role('button', name='e4: peão branco', exact=True).wait_for(timeout=20000)
            expect(page.locator('.quality')).to_have_text('📖')
            page.keyboard.press('ArrowLeft')
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=20000)
            print('KEYBOARD_AND_BOOK_OK', flush=True)
            field = page.get_by_role('textbox', name='O que você quer entender?')
            field.fill('meu plano')
            field.press('ArrowRight')
            expect(page.get_by_role('button', name='e2: peão branco', exact=True)).to_be_visible()
            page.get_by_role('heading', name='Tabuleiro', exact=True).click()
            page.keyboard.press('End')
            page.get_by_role('button', name='f7: dama branco', exact=True).wait_for(timeout=20000)
            page.keyboard.press('Home')
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=20000)
            print('INPUT_GUARD_AND_BOUNDS_OK', flush=True)
            page.get_by_role('tab', name='Estudo com livros', exact=True).click()
            page.get_by_role('heading', name='Carregar livro', exact=True).wait_for(timeout=20000)
            expect(page.get_by_text('Escolha o livro desejado', exact=True)).to_be_visible()
            assert page.locator('.square').count() == 0
            page.get_by_role('tab', name='Análise', exact=True).click()
            page.get_by_role('button', name='e2: peão branco', exact=True).wait_for(timeout=20000)
            print('STUDY_TAB_OK', flush=True)
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
            print('ANIMATED_DRAG_OK',flush=True)
            page.get_by_role('button', name='Analisar partida').click()
            page.get_by_text('1 lance classificado.', exact=True).wait_for(timeout=45000)
            assert page.get_by_role('heading', name='Leitura do lance', exact=True).count() == 0
            assert page.locator('[data-testid="stMetric"]').count() == 2
            assert page.locator('[data-testid="stDataFrame"]').count() == 1
            expect(page.get_by_role('heading', name='Resumo do lance', exact=True)).to_have_count(0)
            page.get_by_role('img', name='Bobby Fischer virtual: sério', exact=True).wait_for(timeout=10000)
            page.get_by_role('button', name='Reexplicar lance').click()
            page.get_by_role('img', name='Bobby Fischer virtual: pensativo', exact=True).wait_for(timeout=20000)
            print('PORTRAIT_AND_SUMMARY_OK', flush=True)
            card=page.locator('.st-key-bobby_explanation')
            expect(card.get_by_role('heading',name='Bobby Fischer',exact=True)).to_be_visible()
            assert 'd4' in card.inner_text()
            assert 'Orientação básica' not in card.inner_text()
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
            page.get_by_role('heading', name='Tabuleiro', exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(Path(tempfile.gettempdir()) / 'acervo-new-layout.png'), full_page=True)
            assert not errors, errors
            assert page.locator('[data-testid="stException"]').count() == 0
            print('JS_ERRORS', errors, flush=True)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == '__main__':
    main()
