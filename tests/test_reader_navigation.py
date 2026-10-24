from collections import Counter
from dataclasses import asdict
from pathlib import Path
import json
import re
import chess

import pytest
from playwright.sync_api import expect

from book_reader import ReaderPageCache, book_id, reader_title
from book_positions import BookPosition, SCAN_VERSION
from sample_books import sample_pdf
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server
import test_coach_chess_ui as desktop_tests


def test_image_buffer_prepares_neighbors_and_stays_bounded(monkeypatch):
    calls = Counter()
    def render(data, page):
        calls[page] += 1
        return f'image-{page}'.encode()
    monkeypatch.setattr('book_reader.pdf_page', render)
    cache = ReaderPageCache()
    entry = 'Book.pdf', b'pdf', {'count':30}
    try:
        assert cache.nearby('book', entry, 0)[1] == b'image-1'
        assert cache.nearby('book', entry, 1)[1] == b'image-1'
        assert calls[1] == 1
        for page in range(2, 25):
            cache.nearby('book', entry, page)
        assert len(cache.pages) <= 10
    finally:
        cache.close()


def test_reader_title_removes_download_suffixes():
    title = 'toaz.info-o-xadrez-dos-grandes-mestres-pr_1bdb851e5b125d35dc41686929ecb489'
    assert reader_title(title) == 'o xadrez dos grandes mestres'


@pytest.fixture
def reader_server(tmp_path, monkeypatch, request):
    project = Path(__file__).resolve().parents[1]
    name = 'toaz.info-livro-de-xadrez-pr_1bdb851e5b125d35dc41686929ecb489.pdf'
    data = sample_pdf()
    (tmp_path/'book.pdf').write_bytes(data)
    # The scope/latency test starts from already prepared position metadata.
    # Recognition itself is exercised by the scanned PDF integration tests.
    cache = tmp_path/'positions'/f'v{SCAN_VERSION}'/book_id(name, data)
    cache.mkdir(parents=True)
    for page in range(3):
        positions = []
        if page == 1:
            for index, move in enumerate([None, 'd4', 'e4']):
                board = chess.Board()
                if move:
                    board.push_san(move)
                positions.append(asdict(BookPosition(board.fen(), f'Diagrama {index+1}', 'diagrama do PDF')))
        (cache/f'{page}.json').write_text(json.dumps({'positions':positions, 'notice':''}))
    (tmp_path/'app.py').write_text(f'''
import sys
from pathlib import Path
sys.path.insert(0, {str(project)!r})
import streamlit as st
import time
from study_workspace import render_study
from book_positions import BookPositionService
class DelayedMetadata(BookPositionService):
    def result(self, identity, page):
        if page==1:
            if not hasattr(self, 'ready_after'):
                self.ready_after=time.monotonic()+1
            if time.monotonic()<self.ready_after:
                return None
        return super().result(identity, page)
st.set_page_config(layout='wide')
st.session_state.setdefault('study_upload_revision', 0)
st.session_state.setdefault('study_files', (({name!r}, Path({str(tmp_path/'book.pdf')!r}).read_bytes()),))
if '_book_position_service' not in st.session_state:
    st.session_state._book_position_service=DelayedMetadata({str(tmp_path/'positions')!r})
st.session_state.full_app_runs=st.session_state.get('full_app_runs',0)+1
st.html('<span id="full-app-runs">'+str(st.session_state.full_app_runs)+'</span>')
render_study(st.session_state.study_files, True, False)
''', encoding='utf8')
    monkeypatch.setattr(desktop_tests, 'ROOT', tmp_path)
    return request.getfixturevalue('coach_server')


def test_turning_pages_previews_immediately_without_rerunning_app(browser_page, reader_server):
    page = browser_page
    page.set_viewport_size({'width':1440, 'height':1000})
    page.goto(reader_server)
    page.get_by_role('button', name='Abrir livro').click()
    image = page.locator('.book-page-image')
    expect(image).to_have_attribute('data-page','0')
    expect(page.locator('.reader-title')).to_have_text('livro de xadrez')
    expect(page.locator('.book-page-preloads img[data-page="1"]')).to_have_count(1)
    def check_alignment():
        page.wait_for_function('''()=>{
          const image=document.querySelector('.book-page-image');
          const hosts=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot);
          let board=document.querySelector('.board');
          for(const host of hosts)board=board||host.shadowRoot.querySelector('.board');
          if(!image||!board)return false;
          const a=image.getBoundingClientRect(),b=board.getBoundingClientRect();
          return Math.abs(a.top-b.top)<=1 && Math.abs(a.bottom-b.bottom)<=1 && Math.abs(a.width-b.width)<=1 && Math.abs(b.height-b.width)<=1;
        }''', timeout=5000)
    check_alignment()
    runs = page.locator('#full-app-runs').inner_text()
    # The image changes in the click handler itself, before any server response.
    assert page.evaluate('''()=>{
      const image=document.querySelector('.book-page-image'), before=image.src;
      document.querySelector('.st-key-reader_next button').click();
      return image.src!==before;
    }''')
    expect(image).to_have_attribute('data-page','1')
    expect(page.locator('.st-key-reading_workspace')).to_have_attribute('data-ready-token', re.compile(':1$'))
    expect(page.get_by_text('Preparando as posições desta página…', exact=False)).to_have_count(0)
    diagrams = page.get_by_role('combobox', name='Diagrama da página')
    expect(diagrams).to_be_hidden()
    page.get_by_text('Opções de estudo',exact=True).click()
    expect(diagrams).to_be_visible()
    expect(page.get_by_role('button',name='Posição anterior',exact=False)).to_be_disabled()
    page.get_by_role('button',name='Próxima posição',exact=False).click()
    expect(page.get_by_text('Posição 2 de 3 · mesma página',exact=True)).to_be_visible()
    board = page.locator('.board')
    expect(board.locator('[data-square="e2"]')).to_have_attribute('aria-label','e2: peão branco')
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="d4"]')).to_have_attribute('aria-label','d4: peão branco')
    expect(image).to_have_attribute('data-page','1')
    page.get_by_role('button',name='Próxima posição',exact=False).click()
    expect(page.get_by_text('Posição 3 de 3 · mesma página',exact=True)).to_be_visible()
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
    expect(page.get_by_role('button',name='Próxima posição',exact=False)).to_be_disabled()
    expect(page.get_by_text('Posição 3 de 3 · mesma página',exact=True)).to_be_visible()
    page.get_by_role('button',name='Posição anterior',exact=False).click()
    expect(page.get_by_text('Posição 2 de 3 · mesma página',exact=True)).to_be_visible()
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="d4"]')).to_have_attribute('aria-label','d4: peão branco')
    page.get_by_role('button',name='Posição anterior',exact=False).click()
    expect(page.get_by_text('Posição 1 de 3 · mesma página',exact=True)).to_be_visible()
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="e2"]')).to_have_attribute('aria-label','e2: peão branco')
    expect(page.locator('#full-app-runs')).to_have_text(runs)
    page.get_by_text('Opções de estudo',exact=True).click()
    expect(diagrams).to_be_hidden()
    page.get_by_role('button',name='Começar estudos',exact=False).click()
    check_alignment()
    page.set_viewport_size({'width':1600,'height':900})
    check_alignment()
    assert image.evaluate('(e)=>e.getBoundingClientRect().width>=innerWidth*.43')
    page.screenshot(path='tests/artifacts/book-board-aligned.png', full_page=True)
    image.click(position={'x':20,'y':20})
    for key, target in [('ArrowRight','2'),('ArrowLeft','1'),('ArrowLeft','0'),('ArrowRight','1')]:
        page.keyboard.press(key)
        expect(image).to_have_attribute('data-page',target)
        expect(page.locator('#full-app-runs')).to_have_text(runs)
        expect(page.locator('html')).to_have_class('book-study-focus')
    # Both the optimistic move and its acknowledgement retain every square.
    board.locator('.square').evaluate_all('(nodes)=>window.studySquares=nodes')
    board.locator('[data-square="e2"]').evaluate('(e)=>window.fromSquare=e')
    board.locator('[data-square="e4"]').evaluate('(e)=>window.toSquare=e')
    revision = board.get_attribute('data-revision')
    assert page.evaluate('''()=>{
      window.fromSquare.click();window.toSquare.click();
      return window.toSquare.getAttribute('aria-label')==='e4: peão branco';
    }''')
    expect(board).not_to_have_attribute('data-revision',revision)
    assert page.evaluate('()=>window.studySquares.length===64 && window.studySquares.every(e=>e.isConnected)')
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 1')
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
    board.locator('[data-square="e7"]').click()
    board.locator('[data-square="e5"]').click()
    expect(page.locator('.move-counter')).to_have_text('Lance 2 de 2')
    assert page.evaluate('()=>window.studySquares.every(e=>e.isConnected)')
    # Clicking the board routes arrows to moves, without turning the page.
    page.keyboard.press('ArrowLeft')
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 2')
    expect(image).to_have_attribute('data-page','1')
    page.keyboard.press('ArrowRight')
    expect(page.locator('.move-counter')).to_have_text('Lance 2 de 2')
    expect(image).to_have_attribute('data-page','1')
    # Clicking the book changes the keyboard destination, retaining the game.
    image.click(position={'x':20,'y':20})
    page.keyboard.press('ArrowRight')
    expect(image).to_have_attribute('data-page','2')
    expect(page.locator('.move-counter')).to_have_text('Lance 2 de 2')
    page.keyboard.press('ArrowLeft')
    expect(image).to_have_attribute('data-page','1')
    # Empty board background selects it too; a new render must retain the scope.
    board.locator('[data-square="a4"]').click()
    page.keyboard.press('ArrowLeft')
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 2')
    expect(image).to_have_attribute('data-page','1')
    page.keyboard.press('ArrowRight')
    expect(page.locator('.move-counter')).to_have_text('Lance 2 de 2')
    page.get_by_role('button',name='Lance anterior',exact=True).click()
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 2')
    board.locator('[data-square="c7"]').click()
    board.locator('[data-square="c5"]').click()
    expect(page.locator('.move-counter')).to_have_text('Lance 2 de 2')
    expect(board.locator('[data-square="c5"]')).to_have_attribute('aria-label','c5: peão preto')
    expect(board.locator('[data-square="e5"]')).to_have_attribute('aria-label','e5: vazia')
    assert page.evaluate('()=>window.studySquares.every(e=>e.isConnected)')
    expect(page.locator('#full-app-runs')).to_have_text(runs)
    page.get_by_text('Opções de estudo',exact=True).click()
    page.get_by_role('button',name='Editar posição',exact=False).click()
    page.get_by_role('button',name='Concluir edição',exact=True).click()
    expect(page.get_by_role('button',name='Concluir edição',exact=True)).to_have_count(0)
    expect(page.get_by_role('button',name='Editar posição',exact=False)).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('html')).not_to_have_class('book-study-focus')
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)


def test_rapid_page_commands_keep_latest_target_and_board_can_restart(browser_page, reader_server):
    page = browser_page
    page.goto(reader_server)
    page.get_by_role('button', name='Abrir livro').click()
    image = page.locator('.book-page-image')
    expect(image).to_have_attribute('data-page', '0')
    expect(page.locator('.book-page-preloads img[data-page="1"]')).to_have_count(1)
    image.click()
    # All commands arrive before the server round trip, including key repeat.
    result = page.evaluate("""()=>{
      for(const key of ['ArrowRight','ArrowRight','ArrowLeft'])
        document.dispatchEvent(new KeyboardEvent('keydown',{key,repeat:true,bubbles:true}));
      return {page:window.__bookReaderNavigation.page,sequence:window.__bookReaderNavigation.sequence};
    }""")
    assert result == {'page':1, 'sequence':3}
    expect(image).to_have_attribute('data-page', '1')
    page.locator('.st-key-study_position [data-square="e2"]').click()
    page.locator('.st-key-study_position [data-square="e4"]').click()
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 1')
    page.get_by_text('Opções de estudo', exact=True).click()
    page.get_by_role('button', name='Reiniciar tabuleiro', exact=False).click()
    expect(page.locator('.move-counter')).to_have_text('Lance 0 de 0')
    expect(page.locator('.st-key-study_position [data-square="e2"]')).to_have_attribute('aria-label', 'e2: peão branco')
    expect(page.locator('.st-key-study_position [data-square="e4"]')).to_have_attribute('aria-label', 'e4: vazia')
    expect(image).to_have_attribute('data-page', '1')
    page.locator('.st-key-study_position [data-square="d2"]').click()
    page.locator('.st-key-study_position [data-square="d4"]').click()
    expect(page.locator('.move-counter')).to_have_text('Lance 1 de 1')
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
