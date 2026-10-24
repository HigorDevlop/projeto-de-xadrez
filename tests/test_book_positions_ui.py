from io import BytesIO
import chess
import chess.svg
import classroom as rooms
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from playwright.sync_api import expect

from test_browser_components import browser_page
from test_coach_chess_ui import coach_server


def test_pdf_page_changes_load_prepared_diagrams_without_editing(browser_page, coach_server, tmp_path, monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB', str(tmp_path/'classrooms.sqlite3'))
    rooms.register_user('leitor', 'senha-leitor-123')
    page = browser_page
    page.set_viewport_size({'width':1440, 'height':1000})
    pages = []
    for move in ['e4', 'd4']:
        board = chess.Board()
        board.push_san(move)
        page.set_content('<style>body{margin:0}</style>'+chess.svg.board(board, size=420, coordinates=False,
                         colors={'square light':'#ffffff', 'square dark':'#bbbbbb'}))
        tile = Image.open(BytesIO(page.locator('svg').screenshot())).convert('RGB')
        image = Image.new('RGB', (700,1000), 'white')
        image.paste(tile,(130,240))
        pages.append(image)
    output = BytesIO()
    pages[0].save(output,format='PDF',save_all=True,append_images=pages[1:],resolution=100)
    # Exercise artwork plus explicit turn metadata; purely scanned diagrams
    # have their own integration test.
    writer = PdfWriter()
    for original, move in zip(PdfReader(BytesIO(output.getvalue())).pages, ['e4', 'd4']):
        overlay_writer = PdfWriter()
        overlay = overlay_writer.add_blank_page(width=float(original.mediabox.width), height=float(original.mediabox.height))
        overlay[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({
            NameObject('/F1'): DictionaryObject({NameObject('/Type'):NameObject('/Font'),
                NameObject('/Subtype'):NameObject('/Type1'), NameObject('/BaseFont'):NameObject('/Helvetica')})})})
        position = chess.Board()
        position.push_san(move)
        position.turn = chess.WHITE
        content = DecodedStreamObject()
        content.set_data(f'BT /F1 6 Tf 20 20 Td ({position.fen()}) Tj ET'.encode())
        overlay[NameObject('/Contents')] = overlay_writer._add_object(content)
        writer.add_page(original).merge_page(overlay)
    output = BytesIO()
    writer.write(output)
    page.goto(coach_server)
    page.get_by_role('textbox', name='Usuário', exact=True).fill('leitor')
    page.get_by_role('textbox', name='Senha', exact=True).fill('senha-leitor-123')
    page.get_by_role('button', name='Entrar', exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Estudo com livros').click()
    page.locator('[class*="st-key-study_book_upload_"] input[type="file"]').set_input_files(
        {'name':'Livro de posições.pdf','mimeType':'application/pdf','buffer':output.getvalue()})
    page.get_by_role('button',name='Abrir livro').click()
    board = page.locator('.board')
    expect(board.locator('[data-square="e2"]')).to_have_attribute('aria-label','e2: peão branco')
    expect(page.get_by_role('button',name='Carregar posição da página',exact=False)).to_be_hidden()
    page.get_by_text('Opções de estudo',exact=True).click()
    page.get_by_role('button',name='Carregar posição da página',exact=False).click(timeout=45000)
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
    expect(page.get_by_role('button', name='Começar estudos', exact=False)).to_be_visible()
    expect(page.get_by_text('Posição 1 · página 1 · FEN',exact=True)).to_be_visible()
    page.get_by_role('button', name='Começar estudos', exact=False).click()
    expect(page.locator('html')).to_have_class('book-study-focus')
    expect(page.locator('.st-key-reading_workspace')).to_have_css('position','fixed')
    image = page.locator('.book-page-image')
    expect(image).to_have_css('object-fit','contain')
    assert image.evaluate('(e)=>e.complete && e.naturalWidth>0')
    assert image.evaluate('(e)=>e.getBoundingClientRect().width>=innerWidth*.43')
    assert page.locator('.st-key-book_page_reader').evaluate('(e)=>e.scrollHeight<=e.clientHeight+1')
    expect(page.get_by_text('Quem joga nesta posição?',exact=True)).to_be_visible()
    image.click(position={'x':20,'y':20})
    page.keyboard.press('ArrowRight')
    expect(page.get_by_role('button',name='Página 2 de 2',exact=False)).to_be_visible()
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="d4"]')).to_have_attribute('aria-label','d4: peão branco', timeout=10000)
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: vazia')
    expect(page.locator('html')).to_have_class('book-study-focus')
    image.click(position={'x':20,'y':20})
    page.keyboard.press('ArrowLeft')
    expect(board.locator('[data-square="d4"]')).to_have_attribute('aria-label','d4: peão branco')
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
    board.locator('[data-square="e4"]').click()
    board.locator('[data-square="e5"]').click()
    expect(board.locator('[data-square="e5"]')).to_have_attribute('aria-label','e5: peão branco')
    expect(page.locator('html')).to_have_class('book-study-focus')
    page.screenshot(path='tests/artifacts/book-focus.png',full_page=True)
    page.keyboard.press('Escape')
    expect(page.locator('html')).not_to_have_class('book-study-focus')
    expect(page.get_by_role('button', name='Começar estudos', exact=False)).to_be_visible()
    expect(board.locator('[data-square="e5"]')).to_have_attribute('aria-label','e5: peão branco')
    expect(page.locator('[data-testid="stException"]')).to_have_count(0)
    image.click(position={'x':20,'y':20})
    page.keyboard.press('ArrowRight')
    expect(board.locator('[data-square="e5"]')).to_have_attribute('aria-label','e5: peão branco')
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="d4"]')).to_have_attribute('aria-label','d4: peão branco')
    image.click(position={'x':20,'y':20})
    page.keyboard.press('ArrowRight')  # End of book remains on the last page.
    expect(page.get_by_role('button',name='Página 2 de 2',exact=False)).to_be_visible()
    page.screenshot(path='tests/artifacts/book-page-synchronized.png',full_page=True)
    # A fresh session has no upload widget data; the same account retrieves its book.
    page.reload()
    page.get_by_role('textbox', name='Usuário', exact=True).fill('leitor')
    page.get_by_role('textbox', name='Senha', exact=True).fill('senha-leitor-123')
    page.get_by_role('button', name='Entrar', exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Estudo com livros').click()
    expect(page.get_by_role('button', name='Abrir livro')).to_have_count(1)
    assert page.locator('[class*="st-key-study_book_upload_"] input[type="file"]').evaluate('(e)=>e.files.length') == 0
    page.get_by_role('button', name='Abrir livro').click()
    expect(board.locator('[data-square="e2"]')).to_have_attribute('aria-label','e2: peão branco')
    expect(page.get_by_role('button',name='Carregar posição da página',exact=False)).to_be_hidden()
    page.get_by_text('Opções de estudo',exact=True).click()
    page.get_by_role('button',name='Carregar posição da página',exact=False).click()
    expect(board.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
