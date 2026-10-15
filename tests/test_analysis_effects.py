"""Special-move feedback and analysis layout in an actual browser."""
import chess
import chess.svg
import pytest

from chess_review import CATEGORIES, SPECIAL_CATEGORIES
from interactive_board import quality_badge
from test_browser_components import ROOT, board_data, browser_page, mount


def analyzed_position(category='brilliant', side='white', *, flipped=False, enabled=True):
    board = chess.Board()
    board.push_uci('e2e4')
    square, last = 'e4', ['e2', 'e4']
    if side == 'black':
        board.push_uci('e7e5')
        square, last = 'e5', ['e7', 'e5']
    data = board_data(fen=board.fen())
    for cell in data['cells']:
        piece = board.piece_at(chess.parse_square(cell['name']))
        cell['svg'] = chess.svg.piece(piece) if piece else ''
    if flipped:
        data['cells'].reverse()
    data.update(ply=len(board.move_stack), total=2, navigation=True, last=last,
                epoch='special-analysis', analysisEffects=enabled,
                badge=quality_badge(CATEGORIES[category], square, side))
    return data


@pytest.mark.parametrize('side', ['white', 'black'])
@pytest.mark.parametrize('category', list(CATEGORIES))
def test_badge_preserves_explicit_side_and_marks_only_special_categories(category, side):
    badge = quality_badge(CATEGORIES[category], 'd5', side)
    assert badge['side'] == side
    assert badge['square'] == 'd5'
    assert badge['special'] is (category in SPECIAL_CATEGORIES)
    assert badge['symbol'] == CATEGORIES[category].symbol


@pytest.mark.parametrize('flipped', [False, True])
@pytest.mark.parametrize('side,effect', [('white', 'lightning'), ('black', 'meteor')])
@pytest.mark.parametrize('category', sorted(SPECIAL_CATEGORIES))
def test_special_moves_affect_the_correct_piece_and_color(browser_page, category, side, effect, flipped):
    page = browser_page
    capture = category == 'brilliant' and not flipped
    if capture:
        page.clock.install()
    data = analyzed_position(category, side, flipped=flipped)
    mount(page, 'interactive_board.py', data)
    if capture:
        page.clock.run_for(350)
        artifacts = ROOT / 'tests' / 'artifacts'
        artifacts.mkdir(exist_ok=True)
        filename = 'efeito-raio.png' if side == 'white' else 'efeito-meteoro.png'
        page.screenshot(path=str(artifacts / filename))
    assert page.locator(f'.move-effect-layer[data-effect="{effect}"]').count() == 1
    assert page.locator('.move-effect-layer > *').count() > 0
    piece = page.locator(f'[data-square="{data["badge"]["square"]}"]')
    assert piece.evaluate('(element, side) => element.classList.contains("special-" + side)', side)
    assert page.locator('.square.special').count() == 1
    assert page.locator('.square.special-' + ('black' if side == 'white' else 'white')).count() == 0
    aura = piece.evaluate('(element) => getComputedStyle(element).getPropertyValue("--aura-color").trim()')
    red, green, blue = (int(aura[index:index + 2], 16) for index in (1, 3, 5))
    assert blue > red and blue > green if side == 'white' else red > green and red > blue
    assert piece.evaluate('(element) => getComputedStyle(element, "::before").animationName') != 'none'
    # The effect follows the destination even when the board is turned around.
    index = next(index for index, cell in enumerate(data['cells']) if cell['name'] == data['badge']['square'])
    ring = page.locator('.move-effect-layer .impact')
    assert float(ring.get_attribute('cx')) == index % 8 * 100 + 50
    assert float(ring.get_attribute('cy')) == index // 8 * 100 + 50


@pytest.mark.parametrize('category,enabled', [
    *[(category, True) for category in CATEGORIES if category not in SPECIAL_CATEGORIES],
    *[(category, False) for category in SPECIAL_CATEGORIES],
])
def test_ordinary_moves_and_non_analysis_views_have_no_effect(browser_page, category, enabled):
    page = browser_page
    mount(page, 'interactive_board.py', analyzed_position(category, enabled=enabled))
    assert page.locator('.square.special').count() == 0
    assert page.locator('.move-effect-layer > *').count() == 0
    assert page.locator('.move-effect-layer').get_attribute('data-effect') is None
    # The classification itself remains readable when animations are disabled.
    assert CATEGORIES[category].label in page.locator('.move-quality').inner_text()


def test_special_flag_is_required_even_with_analysis_enabled(browser_page):
    data = analyzed_position()
    data['badge']['special'] = False
    mount(browser_page, 'interactive_board.py', data)
    assert browser_page.locator('.square.special').count() == 0
    assert browser_page.locator('.move-effect-layer > *').count() == 0


@pytest.mark.parametrize('side', ['white', 'black'])
def test_reduced_motion_keeps_static_feedback_without_impact_svg(browser_page, side):
    page = browser_page
    page.emulate_media(reduced_motion='reduce')
    mount(page, 'interactive_board.py', analyzed_position(side=side))
    assert page.locator('.move-effect-layer > *').count() == 0
    assert page.locator('.move-effect-layer').get_attribute('data-effect') is None
    assert not page.locator('.move-effect-layer').is_visible()
    piece = page.locator('.square.special')
    assert piece.count() == 1
    assert piece.evaluate('(element) => getComputedStyle(element, "::before").animationName') == 'none'
    assert page.evaluate('document.getAnimations().length') == 0


def test_refresh_does_not_restart_impact_and_navigation_can_replay_it(browser_page):
    page = browser_page
    page.clock.install()
    initial = {**board_data(), 'ply': 0, 'total': 2, 'navigation': True}
    special = analyzed_position()
    normal = analyzed_position('best', 'black')
    data = {**special, 'frames': [initial, special, normal], 'navigation_ack': 0}
    mount(page, 'interactive_board.py', data)
    page.evaluate('window.originalImpact=document.querySelector(".move-effect-layer").firstElementChild')
    page.clock.run_for(400)
    page.evaluate('(data) => window.render(data)', {**data, 'dark': True})
    assert page.evaluate('window.originalImpact===document.querySelector(".move-effect-layer").firstElementChild')
    page.clock.run_for(1100)
    assert page.locator('.move-effect-layer > *').count() == 0
    assert page.locator('.square.special-white').count() == 1
    page.evaluate('(data) => window.render(data)', {**data, 'dark': False})
    assert page.locator('.move-effect-layer > *').count() == 0

    page.keyboard.press('ArrowRight')
    assert page.locator('.move-counter').inner_text() == 'Lance 2 de 2'
    assert page.locator('.square.special').count() == 0
    assert page.locator('.move-effect-layer > *').count() == 0
    page.keyboard.press('ArrowLeft')
    assert page.locator('.move-effect-layer[data-effect="lightning"]').count() == 1
    assert page.locator('.square.special-white').count() == 1
    # Moving away during the new impact clears it immediately as well.
    page.keyboard.press('ArrowRight')
    assert page.locator('.move-effect-layer > *').count() == 0
    assert page.locator('.square.special').count() == 0


@pytest.mark.parametrize('table', [False, True])
def test_expanded_analysis_board_is_large_centered_with_navigation_before_cat(browser_page, table):
    page = browser_page
    page.set_viewport_size({'width': 1440, 'height': 1100})
    data = {**analyzed_position(), 'mascot': True, 'expanded': True, 'table': table}
    mount(page, 'interactive_board.py', data)
    board = page.locator('.board').bounding_box()
    nav = page.get_by_role('navigation', name='Navegação de lances').bounding_box()
    cat = page.locator('.cat-place').bounding_box()
    assert board['width'] > 780
    assert abs(board['x'] + board['width'] / 2 - 720) < 1
    assert 0 <= nav['y'] - board['y'] - board['height'] <= 80
    assert cat['y'] >= nav['y'] + nav['height']
    assert cat['width'] >= board['width']
    assert cat['x'] + cat['width'] <= 1440
    assert page.evaluate('document.documentElement.scrollWidth') <= 1440
