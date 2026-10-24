import chess
import pytest
from interactive_board import legal_move_previews, position_data, piece_images
from test_browser_components import browser_page, mount, drag


@pytest.mark.parametrize("fen,uci", [
    (chess.STARTING_FEN, "e2e4"),
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1"),
    ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8q"),
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6"),
])
def test_preview_matches_legal_position(fen, uci):
    board = chess.Board(fen)
    board.push_uci(uci)
    assert legal_move_previews(fen)[uci] == board.fen()


@pytest.mark.parametrize("gesture", ["click", "drag"])
def test_move_is_painted_before_server_acknowledges(browser_page, gesture):
    page = browser_page
    board = chess.Board()
    data = {**position_data(board), 'revision': 0, 'ply': 0, 'total': 0,
            'navigation': False, 'badge': None, 'pieces': piece_images(),
            'previewFen': board.fen(), 'movePreviews': legal_move_previews(board.fen())}
    mount(page, 'interactive_board.py', data)
    if gesture == 'drag':
        drag(page, 'e2', 'e4')
    else:
        page.locator('[data-square="e2"]').click()
        page.locator('[data-square="e4"]').click()
    assert page.locator('[data-square="e4"]').get_attribute('aria-label') == 'e4: peão branco'
    assert page.locator('.turn-label').inner_text() == 'Pretas jogam'
    assert page.locator('[data-square="e2"]').get_attribute('aria-label') == 'e2: vazia'
    events = page.evaluate('window.events')
    assert events[-1]['value']['fen'] == chess.STARTING_FEN
    assert events[-1]['value']['uci'] == 'e2e4'
    board.push_uci('e2e4')
    page.evaluate('(d)=>window.render(d)', {**data, **position_data(board), 'revision': 1, 'ply': 1,
        'previewFen': board.fen(), 'movePreviews': legal_move_previews(board.fen())})
    page.locator('[data-square="e7"]').click()
    page.locator('[data-square="e5"]').click()
    assert page.locator('[data-square="e5"]').get_attribute('aria-label') == 'e5: peão preto'
    assert page.locator('.turn-label').inner_text() == 'Brancas jogam'
    assert page.evaluate('window.events').pop()['value']['uci'] == 'e7e5'


def test_branch_immediately_after_rewinding_uses_displayed_position(browser_page):
    from interactive_board import game_frames
    page = browser_page
    page.clock.install()
    pgn = '1. e4 e5 *'
    board = chess.Board()
    board.push_uci('e2e4')
    board.push_uci('e7e5')
    data = {**position_data(board), 'revision': 4, 'ply': 2, 'total': 2,
            'navigation': True, 'epoch': 'branch', 'navigation_ack': 0,
            'frames': game_frames(pgn), 'pieces': piece_images(), 'badge': None}
    mount(page, 'interactive_board.py', data)
    page.keyboard.press('Home')
    page.locator('[data-square="d2"]').click()
    page.locator('[data-square="d4"]').click()
    page.clock.run_for(500)
    events = page.evaluate('window.events')
    assert events[-1]['key'] == 'move'
    assert events[-1]['value']['uci'] == 'd2d4'
    assert events[-1]['value']['ply'] == 0
    assert events[-1]['value']['fen'] == chess.STARTING_FEN


def test_editor_repositions_all_32_pieces_without_move_rules(browser_page):
    from study_workspace import apply_position_edit
    page = browser_page
    board = chess.Board()
    data = {**position_data(board), 'revision': 0, 'ply': 0, 'total': 0,
            'navigation': False, 'badge': None, 'pieces': piece_images(),
            'editing': True, 'editTool': 'move', 'syncRecovery': True}
    mount(page, 'interactive_board.py', data)
    for origin in [chess.square_name(square) for square in sorted(board.piece_map())]:
        original = board.piece_at(chess.parse_square(origin))
        for source, target in [(origin, 'e4'), ('e4', origin)]:
            page.locator(f'[data-square="{source}"]').click()
            page.locator(f'[data-square="{target}"]').click()
            event = page.evaluate('window.events.at(-1)')
            assert event['key'] == 'edit' and event.get('persistent')
            assert event['value']['from'] == source and event['value']['to'] == target
            assert event['value']['fen'] == board.fen()
            board = chess.Board(apply_position_edit(board.fen(), event['value']))
            data.update(position_data(board))
            data['revision'] += 1
            page.evaluate('(d)=>window.render(d)', data)
            assert board.piece_at(chess.parse_square(target)) == original
    assert len(page.evaluate('window.events')) == 64


def test_editor_recovers_an_unacknowledged_edit(browser_page):
    page = browser_page
    page.clock.install()
    board = chess.Board()
    data = {**position_data(board), 'revision': 0, 'ply': 0, 'total': 0,
            'navigation': False, 'badge': None, 'pieces': piece_images(),
            'editing': True, 'editTool': 'move', 'syncRecovery': True}
    mount(page, 'interactive_board.py', data)
    page.locator('[data-square="h8"]').click()
    page.locator('[data-square="d4"]').click()
    first = page.evaluate('window.events.at(-1)')
    page.clock.run_for(2100)
    retry = page.evaluate('window.events.at(-1)')
    assert first['key'] == 'edit' and retry['key'] == 'sync'
    assert first['value'] == retry['value']


def test_turn_indicator_follows_editor_choice(browser_page):
    page = browser_page
    data = {**position_data(chess.Board()), 'revision': 0, 'ply': 0, 'total': 0,
            'navigation': False, 'badge': None, 'pieces': piece_images(),
            'editing': True, 'editTool': 'move', 'turnOverride': 'b'}
    mount(page, 'interactive_board.py', data)
    assert page.locator('.turn-label').inner_text() == 'Pretas jogam'
    page.evaluate('(d)=>window.render(d)', {**data, 'turnOverride': 'w'})
    assert page.locator('.turn-label').inner_text() == 'Brancas jogam'
    page.evaluate('(d)=>window.render(d)', {**data, 'editing': False})
    assert page.locator('.turn-label').inner_text() == 'Brancas jogam'
