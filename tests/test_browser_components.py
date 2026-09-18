"""Exercise real browser pointer/file events without starting a Streamlit server.

Optional test dependency: playwright, plus a locally installed Edge or Chromium.
"""
import ast
from io import BytesIO
import json
import os
from pathlib import Path

import chess
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def browser_page():
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as driver:
        edge = Path(os.environ.get('PROGRAMFILES(X86)', '')) / 'Microsoft/Edge/Application/msedge.exe'
        try:
            browser = driver.chromium.launch(executable_path=str(edge) if edge.is_file() else None, headless=True)
        except playwright.Error:
            pytest.skip('No installed browser for component integration tests')
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        yield page
        assert not errors
        browser.close()


def mount(page, filename, data):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    call = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == 'component')
    component = {item.arg: ast.literal_eval(item.value) for item in call.keywords}
    page.set_content('<style>' + component['css'] + '</style><main>' + component['html'] + '</main>')
    script = component['js'].replace('export default function', 'window.componentRender = function', 1)
    page.add_script_tag(content=script + '''
      window.events=[];
      window.render=(data)=>window.componentRender({data,parentElement:document.querySelector('main'),
        setTriggerValue:(key,value)=>window.events.push({key,value})});
    ''')
    page.evaluate('(data)=>window.render(data)', data)


def board_data(revision=0, fen=chess.STARTING_FEN):
    board = chess.Board(fen)
    cells = []
    for rank in range(7, -1, -1):
        for file in range(8):
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            cells.append({'name': chess.square_name(square), 'label': chess.square_name(square),
                          'color': 'light' if (file+rank)%2 else 'dark',
                          'svg': '<svg><circle cx="30" cy="30" r="20"/></svg>' if piece else ''})
    return {'fen': board.fen(), 'cells': cells, 'revision': revision,
            'legal': [move.uci() for move in board.legal_moves], 'last': [], 'badge': None,
            'ply': 0, 'total': 0, 'navigation': False}


def drag(page, origin, target):
    first = page.locator(f'[data-square="{origin}"]').bounding_box()
    last = page.locator(f'[data-square="{target}"]').bounding_box()
    page.mouse.move(first['x']+first['width']/2, first['y']+first['height']/2)
    page.mouse.down()
    page.mouse.move(last['x']+last['width']/2, last['y']+last['height']/2, steps=8)
    page.mouse.up()


def test_rejected_move_and_repeated_reset_do_not_freeze_drag(browser_page):
    page = browser_page
    mount(page, 'interactive_board.py', board_data())
    for revision in range(4):
        drag(page, 'e2', 'e4')
        page.wait_for_function('(count)=>window.events.length===count', arg=revision+1)
        event = page.evaluate('window.events.at(-1)')
        assert event['value']['uci'] == 'e2e4'
        assert event['value']['revision'] == revision
        # Wrong puzzle answer: same FEN, new revision acknowledges and resets it.
        page.evaluate('(data)=>window.render(data)', board_data(revision+1))
        assert page.locator('.drag-ghost').count() == 0
        assert page.locator('.square.dragging').count() == 0
    # Completion disables legal moves; restart restores the same board.
    disabled = board_data(5)
    disabled['legal'] = []
    page.evaluate('(data)=>window.render(data)', disabled)
    page.evaluate('(data)=>window.render(data)', board_data(6))
    drag(page, 'd2', 'd4')
    page.wait_for_function('window.events.length===5')


def test_native_picker_crop_cancel_and_replace(browser_page):
    page = browser_page
    mount(page, 'profile_avatar.py', {'photo': None})
    source = BytesIO()
    photo = Image.new('RGB', (600, 300), 'red')
    photo.paste('blue', (300, 0, 600, 300))
    photo.save(source, format='PNG')
    with page.expect_file_chooser() as picker:
        page.get_by_role('button', name='Selecionar foto do perfil').click()
    picker.value.set_files({'name': 'foto.png', 'mimeType': 'image/png', 'buffer': source.getvalue()})
    page.locator('.editor').wait_for(state='visible')
    page.locator('.zoom').fill('2')
    page.get_by_role('button', name='Cancelar', exact=True).click()
    assert page.evaluate('window.events.length') == 0
    page.locator('.file').set_input_files({'name': 'foto.png', 'mimeType': 'image/png', 'buffer': source.getvalue()})
    page.locator('.editor').wait_for(state='visible')
    bounds = page.locator('canvas').bounding_box()
    page.mouse.move(bounds['x']+160, bounds['y']+160)
    page.mouse.down()
    page.mouse.move(bounds['x']+60, bounds['y']+160, steps=5)
    page.mouse.up()
    page.get_by_role('button', name='Usar foto', exact=True).click()
    cropped = page.evaluate('window.events[0].value')
    import base64
    result = Image.open(BytesIO(base64.b64decode(cropped.split(',')[1])))
    assert result.size == (320, 320)
    page.evaluate('(photo)=>window.render({photo})', cropped)
    assert page.locator('.avatar img').count() == 1
    assert page.locator('.avatar').inner_text() == ''
    assert not page.locator('.editor').is_visible()
