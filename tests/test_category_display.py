"""Browser checks for readable, consistent move classifications on the board."""
import chess
import chess.svg
import pytest

from chess_review import CATEGORIES
from test_browser_components import board_data, browser_page, mount


def reviewed_position(category, *, dark=False, revision=1):
    board = chess.Board()
    board.push_uci('e2e4')
    data = board_data(revision=revision, fen=board.fen())
    for cell in data['cells']:
        piece = board.piece_at(chess.parse_square(cell['name']))
        cell['svg'] = chess.svg.piece(piece) if piece else ''
    data.update(dark=dark, navigation=True, ply=1, total=1, last=['e2', 'e4'],
                badge={'square': 'e4', 'symbol': category.symbol, 'label': category.label,
                       'color': category.color, 'ink': category.ink,
                       'description': category.description})
    return data


def rgb(hex_color):
    return 'rgb(' + ', '.join(str(int(hex_color[index:index + 2], 16))
                            for index in (1, 3, 5)) + ')'


def contrast(background, foreground):
    def luminance(value):
        channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
                  for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))

    first, second = sorted((luminance(background), luminance(foreground)))
    return (second + .05) / (first + .05)


@pytest.mark.parametrize('dark', [False, True], ids=['claro', 'escuro'])
@pytest.mark.parametrize('width', [390, 1280], ids=['celular', 'desktop'])
def test_seven_categories_are_readable_and_match_piece_badges(browser_page, dark, width):
    page = browser_page
    page.set_viewport_size({'width': width, 'height': 1000})
    page.emulate_media(reduced_motion='reduce')
    assert len(CATEGORIES) == 7
    assert len({category.symbol for category in CATEGORIES.values()}) == 7
    assert len({category.color.lower() for category in CATEGORIES.values()}) == 7
    first = next(iter(CATEGORIES.values()))
    mount(page, 'interactive_board.py', reviewed_position(first, dark=dark))
    page.evaluate("dark => { document.body.style.background = dark ? '#171c20' : '#f5f0e6'; }", dark)

    for revision, category in enumerate(CATEGORIES.values(), 2):
        page.evaluate('(data) => window.render(data)',
                      reviewed_position(category, dark=dark, revision=revision))
        status = page.locator('.move-quality')
        assert status.is_visible()
        assert status.get_attribute('role') == 'status'
        assert category.symbol in status.inner_text()
        assert category.label in status.inner_text()
        assert page.locator('.quality').count() == 1
        badge = page.locator('[data-square="e4"] .quality')
        assert badge.is_visible()
        assert badge.inner_text() == category.symbol
        assert badge.get_attribute('title') == category.label
        badge_colors = badge.evaluate('(element) => { const style = getComputedStyle(element); '
                                      'return [style.backgroundColor, style.color]; }')
        assert badge_colors == [rgb(category.color), rgb(category.ink)]
        # The readable status repeats the colored sign, not only the name in plain text.
        colors = status.evaluate('''element => [element, ...element.querySelectorAll('*')]
            .filter(item => item.getBoundingClientRect().width > 0)
            .map(item => { const style = getComputedStyle(item);
                return [style.backgroundColor, style.color]; })''')
        assert badge_colors in colors
        assert contrast(category.color, category.ink) >= 4.5

        status_box = status.bounding_box()
        navigation_box = page.get_by_role('navigation', name='Navegação de lances').bounding_box()
        assert status_box['y'] >= navigation_box['y'] + navigation_box['height']
        assert status_box['x'] >= 0
        assert status_box['x'] + status_box['width'] <= width
        assert status.evaluate('element => element.scrollWidth <= element.clientWidth')
        # Check actual rendered text extents, including the longest name on a phone.
        text_boxes = status.evaluate('''element => {
            const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
            const rectangles = [];
            while (walker.nextNode()) {
                const range = document.createRange(); range.selectNodeContents(walker.currentNode);
                for (const rect of range.getClientRects()) if (rect.width && rect.height)
                    rectangles.push({left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom});
            }
            return rectangles;
        }''')
        assert text_boxes
        for text_box in text_boxes:
            assert text_box['left'] >= status_box['x'] - 1
            assert text_box['right'] <= status_box['x'] + status_box['width'] + 1
            assert text_box['top'] >= status_box['y'] - 1
            assert text_box['bottom'] <= status_box['y'] + status_box['height'] + 1


@pytest.mark.parametrize('dark', [False, True], ids=['claro', 'escuro'])
def test_navigation_and_refresh_clear_previous_category(browser_page, dark):
    page = browser_page
    initial = board_data()
    initial.update(dark=dark, navigation=True, ply=0, total=1)
    reviewed = reviewed_position(CATEGORIES['best'], dark=dark)
    data = {**reviewed, 'frames': [initial, reviewed], 'epoch': 'classification-navigation',
            'navigation_ack': 0}
    mount(page, 'interactive_board.py', data)
    assert page.locator('.move-quality').is_visible()
    page.keyboard.press('ArrowLeft')
    assert page.locator('.move-counter').inner_text() == 'Lance 0 de 1'
    assert not page.locator('.move-quality').is_visible()
    assert page.locator('.quality').count() == 0
    page.keyboard.press('ArrowRight')
    assert page.locator('.move-quality').is_visible()
    assert page.locator('[data-square="e4"] .quality').inner_text() == CATEGORIES['best'].symbol

    unrated = {**reviewed, 'badge': None}
    refreshed = {**data, **unrated, 'frames': [initial, unrated], 'navigation_ack': 2}
    page.evaluate('(data) => window.render(data)', refreshed)
    assert not page.locator('.move-quality').is_visible()
    assert page.locator('.quality').count() == 0
    assert page.locator('.move-counter').inner_text() == 'Lance 1 de 1'
