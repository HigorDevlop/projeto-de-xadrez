"""Exercise real browser pointer/file events without starting a Streamlit server.

Optional test dependency: playwright, plus a locally installed Edge or Chromium.
"""
import ast
import base64
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
    component = {item.arg: ((ROOT / 'assets/cat-photoreal.js').read_text(encoding='utf-8')
                            if filename == 'cat_mascot.py' and item.arg == 'js' else ast.literal_eval(item.value))
                 for item in call.keywords}
    page.set_content('<style>' + component.get('css', '') + '</style><main>' + component['html'] + '</main>')
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


def image_asset(filename):
    return 'data:image/png;base64,' + base64.b64encode((ROOT / 'assets' / filename).read_bytes()).decode()


def drag(page, origin, target, button='left'):
    first = page.locator(f'[data-square="{origin}"]').bounding_box()
    last = page.locator(f'[data-square="{target}"]').bounding_box()
    page.mouse.move(first['x']+first['width']/2, first['y']+first['height']/2)
    page.mouse.down(button=button)
    page.mouse.move(last['x']+last['width']/2, last['y']+last['height']/2, steps=8)
    page.mouse.up(button=button)


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


@pytest.mark.parametrize('pgn', [
    '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 *',
    '1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 *',
    '[SetUp "1"]\n[FEN "4k3/P7/8/8/8/8/8/4K3 w - - 0 23"]\n\n23. a8=Q+ Kd7 *',
    '1. f3 e5 2. g4 Qh4# 0-1',
])
def test_all_arrows_update_positions_and_lessons_without_server_wait(browser_page, pgn):
    from io import StringIO
    import chess.pgn
    page = browser_page
    game = chess.pgn.read_game(StringIO(pgn))
    board = game.board()
    frames = [board_data(fen=board.fen())]
    for move in game.mainline_moves():
        board.push(move)
        frames.append(board_data(fen=board.fen()))
    for index, frame in enumerate(frames):
        frame.update(ply=index, total=len(frames)-1, navigation=True)
    data = {**frames[0], 'frames': frames, 'epoch': 'game-1', 'navigation_ack': 0,
            'study': True, 'explanations': {str(i): f'Explicação {i}' for i in range(len(frames))}}
    mount(page, 'interactive_board.py', data)
    for direction, indices in [('ArrowRight', range(1, len(frames))), ('ArrowLeft', range(len(frames)-2, -1, -1))]:
        for index in indices:
            page.keyboard.press(direction)
            assert page.locator('.move-counter').inner_text() == f'Lance {index} de {len(frames)-1}'
            assert page.locator('.lesson-text').inner_text() == f'Explicação {index}'
            # A late server render must never undo more recent user navigation.
            page.evaluate('(data)=>window.render(data)', data)
            assert page.locator('.lesson-text').inner_text() == f'Explicação {index}'
    page.keyboard.press('ArrowLeft')
    page.get_by_role('button', name='Último lance', exact=True).click()
    assert page.locator('.move-counter').inner_text() == f'Lance {len(frames)-1} de {len(frames)-1}'
    page.keyboard.press('ArrowRight')
    page.get_by_role('button', name='Posição inicial', exact=True).click()
    page.keyboard.press('ArrowRight')
    page.wait_for_function('window.events.length>0')
    page.wait_for_timeout(60)
    assert page.evaluate('window.events.at(-1).value.to') == 1
    # Explicitly selecting another game resets the local index and pending events.
    replacement = {**data, 'epoch': 'game-2', 'ply': 0}
    page.evaluate('(data)=>window.render(data)', replacement)
    assert page.locator('.move-counter').inner_text().startswith('Lance 0 ')


def test_keyboard_ignores_text_fields_and_clipboard_preserves_pgn(browser_page):
    page = browser_page
    pgn = '[White "José"]\n[Black "Ana"]\n\n1. e4 {Comentário completo.} e5 *'
    mount(page, 'pgn_clipboard.py', {'pgn': pgn, 'dark': True})
    assert page.get_by_role('textbox', name='PGN completo').input_value() == pgn
    page.evaluate("Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copied=text},configurable:true})")
    page.get_by_role('button', name='Copiar PGN').click()
    assert page.evaluate('window.copied') == pgn
    assert page.get_by_role('status').inner_text() == 'PGN copiado!'



def video_asset(filename):
    return 'data:video/mp4;base64,' + base64.b64encode((ROOT / 'assets' / filename).read_bytes()).decode()


def test_opening_plays_cinematic_video_once_and_skip_survives_reruns(browser_page):
    page = browser_page
    data = {'source': video_asset('fischer-karpov-opening.mp4'), 'enabled': True}
    mount(page, 'study_entrance.py', data)
    page.wait_for_function("document.querySelector('video').currentTime > .1")
    assert page.locator('video').evaluate('(v)=>v.videoWidth') == 1920
    page.get_by_role('button', name='Pular abertura').click()
    assert not page.locator('.opening').is_visible()
    assert page.evaluate('window.events') == [{'key': 'finished', 'value': True}]
    page.evaluate('(data)=>window.render(data)', data)
    assert not page.locator('.opening').is_visible()
    page.evaluate('(data)=>window.render(data)', {**data, 'enabled': False})
    page.evaluate('(data)=>window.render(data)', data)
    assert not page.locator('.opening').is_visible()
    assert page.evaluate('window.events.length') == 1


@pytest.mark.parametrize('flipped', [False, True])
def test_right_drag_arrows_toggle_persist_on_refresh_and_clear_on_move(browser_page, flipped):
    page = browser_page
    data = board_data()
    if flipped:
        data['cells'].reverse()
    mount(page, 'interactive_board.py', data)
    drag(page, 'e2', 'e4', button='right')
    assert page.locator('.annotation-arrow').count() == 1
    assert page.evaluate('window.events.length') == 0
    page.evaluate('(data)=>window.render(data)', data)
    assert page.locator('.annotation-arrow').count() == 1
    drag(page, 'g1', 'f3', button='right')
    assert page.locator('.annotation-arrow').count() == 2
    drag(page, 'e2', 'e4', button='right')
    assert page.locator('.annotation-arrow').count() == 1
    drag(page, 'e2', 'e4')
    page.wait_for_function('window.events.length===1')
    assert page.locator('.annotation-arrow').count() == 0
    assert page.evaluate('window.events[0].value.uci') == 'e2e4'
    data['revision'] += 1
    page.evaluate('(data)=>window.render(data)', data)
    drag(page, 'a1', 'a8', button='right')
    assert page.locator('.annotation-arrow').count() == 1
    moved = chess.Board()
    moved.push_uci('e2e4')
    changed = board_data(2, moved.fen())
    page.evaluate('(data)=>window.render(data)', changed)
    assert page.locator('.annotation-arrow').count() == 0


def test_disabled_opening_does_not_load_video_or_replay_when_enabled(browser_page):
    page = browser_page
    mount(page, 'study_entrance.py', {'source': '', 'enabled': False})
    assert not page.locator('.opening').is_visible()
    assert page.locator('video').get_attribute('src') is None
    page.evaluate('(source)=>window.render({enabled:true,source})', video_asset('fischer-karpov-opening.mp4'))
    assert not page.locator('.opening').is_visible()


def test_demo_plays_legal_solutions_and_can_pause(browser_page):
    from tactic_demo import demo_frames
    page = browser_page
    frames = demo_frames()
    assert len(frames) == 8
    mount(page, 'tactic_demo.py', {'frames': frames, 'dark': True})
    page.wait_for_function("document.querySelector('.caption').textContent==='Exercício resolvido!'", timeout=4000)
    page.get_by_role('button', name='Pausar demonstração').click()
    index = page.evaluate('document.querySelector("main")._demo.index')
    page.evaluate('(data)=>window.render(data)', {'frames': frames, 'dark': False})
    assert page.evaluate('document.querySelector("main")._demo.index') == index
    assert page.get_by_role('button', name='Reproduzir demonstração').is_visible()


def test_forge_photoreal_video_only_plays_for_clean_success(browser_page):
    page = browser_page
    data = {'event': 0, 'result': 'idle', 'sharpness': 0, 'dark': True,
            'source': video_asset('forge-photoreal.mp4'), 'poster': ''}
    mount(page, 'tactics_forge.py', data)
    page.evaluate('()=>{HTMLMediaElement.prototype.play=async function(){window.plays=(window.plays||0)+1}}')
    assert 'A forja está pronta' in page.get_by_role('status').inner_text()
    correct = {**data, 'event': 1, 'result': 'correct', 'sharpness': 12}
    page.evaluate('(data)=>window.render(data)', correct)
    assert page.evaluate('window.plays') == 1
    page.evaluate('(data)=>window.render(data)', {**correct, 'dark': False})
    assert page.evaluate('window.plays') == 1
    wrong = {**data, 'event': 2, 'result': 'wrong', 'sharpness': 12}
    page.evaluate('(data)=>window.render(data)', wrong)
    assert 'não concederá afiação' in page.get_by_role('status').inner_text()
    assert page.locator('progress').get_attribute('value') == '12'
    page.evaluate('(data)=>window.render(data)', {**wrong, 'event':3, 'result':'recovered'})
    assert page.evaluate('window.plays') == 1
    assert 'Sem afiação' in page.get_by_role('status').inner_text()


def test_sidebar_initialization_closes_once_and_respects_user_open(browser_page):
    page = browser_page
    page.set_content('')
    mount(page, 'page_chrome.py', {})
    page.evaluate('''()=>{
      const sidebar=document.createElement('aside');sidebar.dataset.testid='stSidebar';sidebar.setAttribute('aria-expanded','true');
      sidebar.innerHTML='<div data-testid="stSidebarCollapseButton"><button>Fechar menu</button></div>';
      sidebar.querySelector('button').onclick=()=>sidebar.setAttribute('aria-expanded','false');
      document.body.append(sidebar);
    }''')
    page.wait_for_function("document.querySelector('aside').getAttribute('aria-expanded')==='false'")
    page.evaluate("document.querySelector('aside').setAttribute('aria-expanded','true');window.render({})")
    assert page.locator('aside').get_attribute('aria-expanded') == 'true'


def test_move_is_submitted_before_animation_and_old_refresh_does_not_unlock(browser_page):
    page = browser_page
    page.clock.install()
    data = board_data()
    mount(page, 'interactive_board.py', data)
    page.evaluate("Element.prototype.animate=function(){return {finished:new Promise(()=>{}),cancel(){}}}")
    drag(page, 'e2', 'e4')
    assert page.evaluate('window.events.length') == 1
    page.evaluate('(data)=>window.render(data)', data)
    drag(page, 'd2', 'd4')
    assert page.evaluate('window.events.length') == 1
    page.evaluate('(data)=>window.render(data)', board_data(1))
    drag(page, 'd2', 'd4')
    assert page.evaluate('window.events.length') == 2


@pytest.mark.parametrize('mobile', [False, True])
def test_cat_peeks_enters_sits_and_rests_without_covering_board(browser_page, mobile):
    page = browser_page
    page.set_viewport_size({'width': 390 if mobile else 1440, 'height': 1000})
    page.clock.install()
    mount(page, 'cat_mascot.py', {'atlas': image_asset('cat-photoreal-atlas.png')})
    page.evaluate('''mobile=>{
      const floor=document.createElement('div');floor.className='workspace mascot';
      const size=mobile?320:600;
      floor.style.cssText='position:relative;margin-top:100px';
      floor.innerHTML='<div class="board" style="margin:auto;width:'+size+'px;height:'+size+'px;background:#629269"></div><div class="cat-place" style="position:absolute;top:'+(mobile?340:380)+'px;right:0;width:'+(mobile?140:220)+'px;height:220px"></div>';
      document.body.prepend(floor);
    }''', mobile)
    page.locator('canvas').wait_for(state='visible')
    page.clock.run_for(1700)
    assert page.locator('canvas').get_attribute('data-pose') == 'olhando-acima'
    peek = page.locator('canvas').bounding_box()
    assert peek['x'] < 0 < peek['x'] + peek['width']
    artifacts = ROOT / 'tests/artifacts'
    artifacts.mkdir(exist_ok=True)
    page.screenshot(path=str(artifacts / f'cat-peek-{mobile}.png'))
    page.clock.run_for(1600)
    assert page.locator('canvas').get_attribute('data-pose') == 'recolhendo'
    assert page.locator('canvas').bounding_box()['x'] < peek['x']
    page.clock.run_for(2500)
    assert page.locator('canvas').get_attribute('data-pose') == 'entrando-direita'
    page.clock.run_for(3400)
    assert page.locator('canvas').get_attribute('data-pose') == 'observando'
    page.screenshot(path=str(artifacts / f'cat-sitting-{mobile}.png'))
    page.clock.run_for(1600)
    assert page.locator('canvas').get_attribute('data-pose') == 'deitando'
    page.clock.run_for(1700)
    assert page.locator('canvas').get_attribute('data-pose') == 'deitado'
    position = page.locator('canvas').bounding_box()
    board = page.locator('.board').bounding_box()
    assert position['x'] >= board['x']+board['width'] or position['y'] >= board['y']+board['height']
    first = page.locator('canvas').evaluate('(c)=>c.toDataURL()')
    page.clock.run_for(900)
    assert page.locator('canvas').evaluate('(c)=>c.toDataURL()') != first
    page.evaluate('()=>{document.querySelector("main")._catScene.pause();window.render({});}')
    page.clock.run_for(100)
    assert page.locator('canvas').bounding_box() == position
    assert page.locator('canvas').get_attribute('data-pose') == 'deitado'
    page.screenshot(path=str(artifacts / f'cat-resting-{mobile}.png'))


@pytest.mark.parametrize('width', [390, 1024, 1440, 1837])
@pytest.mark.parametrize('study', [False, True])
def test_board_stays_centered_with_cat_outside_squares(browser_page, width, study):
    page = browser_page
    page.set_viewport_size({'width': width, 'height': 933})
    mount(page, 'interactive_board.py', {**board_data(), 'mascot': True, 'navigation': True, 'study': study, 'explanations': {'0': 'Partida'}})
    board = page.locator('.board').bounding_box()
    cat = page.locator('.cat-place').bounding_box()
    assert abs(board['x']+board['width']/2-width/2) < 1
    assert cat['x'] >= board['x']+board['width'] or cat['y'] >= board['y']+board['height']
    assert cat['x']+cat['width'] <= width
    assert cat['width'] >= board['width'] * .98
    assert page.evaluate('document.documentElement.scrollWidth') <= width


def test_cat_reduced_motion_stays_still_and_waits_for_opening(browser_page):
    page = browser_page
    page.emulate_media(reduced_motion='reduce')
    page.clock.install()
    page.evaluate('window.__chessIntroActive=true')
    mount(page, 'cat_mascot.py', {'atlas': image_asset('cat-photoreal-atlas.png')})
    page.evaluate('''()=>{
      const floor=document.createElement('div');floor.className='workspace mascot';
      floor.innerHTML='<div class="board" style="width:400px;height:400px"></div><div class="cat-place" style="width:200px;height:200px"></div>';
      document.body.prepend(floor);
    }''')
    page.clock.run_for(1500)
    assert not page.locator('canvas').is_visible()
    assert page.evaluate('window.__chessCatVisit.elapsed') == 0
    page.evaluate('window.__chessIntroActive=false')
    page.locator('canvas').wait_for(state='visible')
    assert page.locator('canvas').get_attribute('data-pose') == 'deitado'
    first = page.locator('canvas').evaluate('(c)=>c.toDataURL()')
    page.clock.run_for(2000)
    assert page.locator('canvas').evaluate('(c)=>c.toDataURL()') == first


def test_opening_escape_releases_mascot(browser_page):
    page = browser_page
    mount(page, 'study_entrance.py', {'source': video_asset('fischer-karpov-opening.mp4'), 'enabled': True})
    assert page.evaluate('window.__chessIntroActive') is True
    page.keyboard.press('Escape')
    assert not page.locator('.opening').is_visible()
    assert page.evaluate('window.__chessIntroActive') is False
    assert page.evaluate('window.events') == [{'key': 'finished', 'value': True}]


def test_board_editor_places_erases_and_moves_without_chess_legality(browser_page):
    page = browser_page
    data = {**board_data(), 'editing': True, 'editTool': 'Q', 'legal': [], 'table': True}
    mount(page, 'interactive_board.py', data)
    page.locator('[data-square="e4"]').click()
    event = page.evaluate('window.events.at(-1)')
    assert event['key'] == 'edit' and event['value']['piece'] == 'Q'
    assert event['value']['to'] == 'e4'
    data.update(editTool='erase', revision=1)
    page.evaluate('(data)=>window.render(data)', data)
    page.locator('[data-square="a1"]').click()
    assert page.evaluate('window.events.at(-1).value.piece') == ''
    data.update(editTool='move', revision=2)
    page.evaluate('(data)=>window.render(data)', data)
    drag(page, 'e2', 'e5')
    assert page.evaluate('window.events.at(-1).value.from') == 'e2'
    assert page.evaluate('window.events.at(-1).value.to') == 'e5'
    assert page.locator('.workspace').evaluate('(el)=>el.classList.contains("table")')
    page.evaluate('(data)=>window.render(data)', {**data, 'table': False})
    assert not page.locator('.workspace').evaluate('(el)=>el.classList.contains("table")')


def test_gallery_has_eight_boards_and_opens_selected_game(browser_page):
    from recent_games import cards_data
    page = browser_page
    item = {'pgn': '1. e4 e5 *', 'white': {'username': 'demo'}, 'black': {'username': 'opponent'},
            'end_time': 1, 'accuracies': {'white': 92.5}}
    mount(page, 'recent_games.py', {'cards': cards_data([item], 'demo', {}), 'dark': True, 'revision': 'history1'})
    assert page.locator('.mini-board').count() == 8
    assert page.locator('.accuracy').first.inner_text() == 'Precisão: 92,5% · Chess.com'
    assert page.locator('article.empty').count() == 7
    page.get_by_role('button', name='Analisar partida 1', exact=True).click()
    assert page.evaluate('window.events.at(-1).value') == {'index': 0, 'action': 'analyse', 'revision': 'history1'}
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth') == 390


def test_forge_encourages_each_success_without_repeating_on_refresh(browser_page):
    page = browser_page
    data = {'source': '', 'poster': '', 'sharpness': 0, 'event': 0, 'result': 'idle', 'speak': False}
    mount(page, 'tactics_forge.py', data)
    assert page.locator('h3').count() == 0
    phrases = []
    for event in range(1, 5):
        update = {**data, 'event': event, 'result': 'progress'}
        page.evaluate('(data)=>window.render(data)', update)
        phrase = page.get_by_role('status').inner_text()
        assert phrase
        phrases.append(phrase)
        page.evaluate('(data)=>window.render(data)', update)
        assert page.get_by_role('status').inner_text() == phrase
    assert len(set(phrases)) == 4
