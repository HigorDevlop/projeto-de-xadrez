"""Navigation remains local and responsive while server acknowledgments arrive."""
from io import StringIO

import chess
import chess.pgn
import chess.svg
import pytest

from test_browser_components import board_data, browser_page, drag, mount


PGN = ('1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 '
       '6. Bc4 Nf6 7. Qb3 Qe7 8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 '
       '11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6 '
       '15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0')


def navigation_data():
    game = chess.pgn.read_game(StringIO(PGN))
    assert not game.errors
    board = game.board()
    frames = [{'fen': board.fen(), 'legal': ' '.join(move.uci() for move in board.legal_moves),
               'last': [], 'badge': None}]
    for move in game.mainline_moves():
        board.push(move)
        frames.append({'fen': board.fen(), 'legal': ' '.join(move.uci() for move in board.legal_moves),
                       'last': [chess.square_name(move.from_square), chess.square_name(move.to_square)],
                       'badge': None})
    return {**board_data(), 'frames': frames, 'ply': 0, 'total': len(frames) - 1,
            'epoch': 'opera', 'navigation_ack': 0, 'navigation': True, 'study': True,
            'explanations': {str(index): f'Estudo do lance {index}.' for index in range(len(frames))},
            'pieces': {symbol: chess.svg.piece(chess.Piece.from_symbol(symbol)) for symbol in 'PNBRQKpnbrqk'}}


def acknowledged(data, ply, sequence):
    position = board_data(fen=data['frames'][ply]['fen'])
    return {**data, **position, 'frames': data['frames'], 'ply': ply, 'total': data['total'],
            'navigation': True, 'navigation_ack': sequence, 'last': data['frames'][ply]['last']}


@pytest.mark.parametrize('control', ['keyboard', 'buttons'])
def test_thirty_steps_paint_locally_and_send_one_final_position(browser_page, control):
    page = browser_page
    data = navigation_data()
    mount(page, 'interactive_board.py', data)
    result = page.evaluate('''async control => {
        const original = [...document.querySelectorAll('.square')], positions = [];
        for (let index = 1; index <= 30; index++) {
            if (control === 'keyboard') document.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight'}));
            else document.querySelector('[data-nav="next"]').click();
            positions.push({counter:document.querySelector('.move-counter').textContent,
                lesson:document.querySelector('.lesson-text').textContent,
                same:original.every((square, offset) => document.querySelectorAll('.square')[offset] === square),
                events:window.events.length});
            await new Promise(resolve => requestAnimationFrame(resolve));
        }
        window.originalSquares = original;
        return positions;
    }''', control)
    for index, position in enumerate(result, 1):
        assert position == {'counter': f'Lance {index} de {data["total"]}',
                            'lesson': f'Estudo do lance {index}.', 'same': True, 'events': 0}
    page.wait_for_function('window.events.length === 1')
    assert page.evaluate('window.events') == [
        {'key': 'navigate', 'value': {'to': 30, 'epoch': 'opera', 'sequence': 30}}]
    assert page.locator('[data-square="d7"]').get_attribute('aria-label') == 'd7: cavalo preto'
    # Acknowledging the final position must not replace any square or request analysis.
    page.evaluate('(data) => window.render(data)', acknowledged(data, 30, 30))
    assert page.evaluate('window.originalSquares.every((square, index) => document.querySelectorAll(".square")[index] === square)')
    assert page.evaluate('window.events.length') == 1


def test_delayed_and_out_of_order_acknowledgments_never_rewind_board(browser_page):
    page = browser_page
    data = navigation_data()
    mount(page, 'interactive_board.py', data)
    page.evaluate('''() => {
        window.originalSquares = [...document.querySelectorAll('.square')];
        for(let i=0; i<10; i++) document.querySelector('[data-nav="next"]').click();
    }''')
    page.wait_for_function('window.events.length === 1')
    page.evaluate('() => { for(let i=0; i<15; i++) document.querySelector("[data-nav=next]").click(); }')
    page.evaluate('(data) => window.render(data)', acknowledged(data, 10, 10))
    assert page.locator('.move-counter').inner_text() == f'Lance 25 de {data["total"]}'
    assert page.locator('.lesson-text').inner_text() == 'Estudo do lance 25.'
    page.evaluate('() => { for(let i=0; i<5; i++) document.querySelector("[data-nav=previous]").click(); }')
    page.evaluate('(data) => window.render(data)', acknowledged(data, 5, 5))
    assert page.locator('.move-counter').inner_text() == f'Lance 20 de {data["total"]}'
    # Browser RPCs can themselves pause longer than the debounce on a busy machine.
    # Wait for the latest cursor, independently of an intermediate idle-period sync.
    page.wait_for_function('window.events.at(-1)?.value.sequence === 30')
    assert page.evaluate('window.events.at(-1)') == {
        'key': 'navigate', 'value': {'to': 20, 'epoch': 'opera', 'sequence': 30}}
    page.evaluate('(data) => window.render(data)', acknowledged(data, 20, 30))
    page.evaluate('(data) => window.render(data)', acknowledged(data, 10, 10))
    assert page.locator('.move-counter').inner_text() == f'Lance 20 de {data["total"]}'
    assert page.locator('.lesson-text').inner_text() == 'Estudo do lance 20.'
    assert page.evaluate('window.originalSquares.every((square, index) => document.querySelectorAll(".square")[index] === square)')
    assert all(event['key'] == 'navigate' for event in page.evaluate('window.events'))


def test_external_control_flushes_cursor_and_new_game_cancels_pending_sync(browser_page):
    page = browser_page
    page.clock.install()
    data = navigation_data()
    mount(page, 'interactive_board.py', data)
    page.evaluate('''() => {
        const question=document.createElement('button');question.textContent='Perguntar sobre a posição';
        question.addEventListener('click',()=>{window.nativeClickSawSync=window.events.length;});
        document.body.append(question);
        for(let i=0; i<6; i++) document.querySelector('[data-nav="next"]').click();
    }''')
    assert page.evaluate('window.events.length') == 0
    # Press/focus must not start a server update before the native control can click.
    page.get_by_role('button', name='Perguntar sobre a posição').dispatch_event('pointerdown')
    page.get_by_role('button', name='Perguntar sobre a posição').dispatch_event('focusin')
    assert page.evaluate('window.events.length') == 0
    page.get_by_role('button', name='Perguntar sobre a posição').click()
    assert page.evaluate('window.nativeClickSawSync') == 0
    assert page.evaluate('window.events.at(-1).value.to') == 6
    page.evaluate('document.querySelector("[data-nav=next]").click()')
    page.evaluate('(data) => window.render(data)', {**data, 'epoch': 'another-game'})
    page.clock.run_for(450)
    assert page.evaluate('window.events.length') == 1
    assert page.locator('.move-counter').inner_text() == f'Lance 0 de {data["total"]}'


def test_training_hint_and_feedback_refresh_independently_of_user_arrows(browser_page):
    page = browser_page
    page.emulate_media(reduced_motion='reduce')
    data = {**board_data(), 'trainingHint': 'e2e4', 'trainingFeedback': {'square': 'e4', 'correct': False}}
    mount(page, 'interactive_board.py', data)
    assert page.locator('.training-hint').count() == 1
    assert page.locator('[data-square="e4"]').evaluate('element => element.classList.contains("training-wrong")')
    drag(page, 'a1', 'a3', button='right')
    assert page.locator('.annotation-arrow').count() == 1
    data['trainingFeedback']['correct'] = True
    page.evaluate('(data) => window.render(data)', data)
    assert page.locator('.training-wrong').count() == 0
    assert page.locator('.training-correct').count() == 1
    assert page.locator('.training-hint').count() == 1
    assert page.locator('.annotation-arrow').count() == 1
    page.evaluate('(data) => window.render(data)', {**data, 'trainingHint': None, 'trainingFeedback': None})
    assert page.locator('.training-hint, .training-correct, .training-wrong').count() == 0
    assert page.locator('.annotation-arrow').count() == 1
    drag(page, 'e2', 'e4')
    page.wait_for_function('window.events.length === 1')
    assert page.evaluate('window.events[0].value.uci') == 'e2e4'


def test_read_only_replay_never_restores_legal_moves_from_local_frames(browser_page):
    page = browser_page
    data = {**navigation_data(), 'disabled': True, 'legal': []}
    mount(page, 'interactive_board.py', data)
    page.keyboard.press('ArrowRight')
    assert page.locator('.move-counter').inner_text() == f'Lance 1 de {data["total"]}'
    assert page.locator('.square.movable').count() == 0
    drag(page, 'e7', 'e5')
    assert page.locator('[data-square="e7"]').get_attribute('aria-label') == 'e7: peão preto'
    assert page.locator('[data-square="e5"]').get_attribute('aria-label') == 'e5: vazia'
    page.wait_for_function('window.events.length > 0')
    assert all(event['key'] == 'navigate' for event in page.evaluate('window.events'))
    assert page.locator('.drag-ghost').count() == 0


def test_read_only_payload_cannot_change_cached_editable_frames(monkeypatch):
    import interactive_board as component

    monkeypatch.setattr(component, '_BOARD', lambda **kwargs: kwargs['data'])
    arguments = {'board': chess.Board(), 'on_move': lambda: None, 'pgn': PGN}
    readonly = component.interactive_board(**arguments, disabled=True)
    assert readonly['disabled'] is True
    assert readonly['legal'] == []
    assert all(frame['legal'] == '' for frame in readonly['frames'])
    editable = component.interactive_board(**arguments)
    assert editable['legal']
    assert all(frame['legal'] for frame in editable['frames'][:-1])
    assert all('cells' not in frame for frame in editable['frames'])


def test_board_without_preloaded_pgn_requests_its_next_position_immediately(browser_page):
    page = browser_page
    data = {**board_data(), 'navigation': True, 'total': 1, 'epoch': 'server-position'}
    mount(page, 'interactive_board.py', data)
    page.evaluate('document.querySelector("[data-nav=next]").click()')
    assert page.evaluate('window.events') == [
        {'key': 'navigate', 'value': {'to': 1, 'epoch': 'server-position', 'sequence': 1}}]
    board = chess.Board()
    board.push_uci('e2e4')
    response = {**data, **board_data(fen=board.fen()), 'navigation': True,
                'total': 1, 'ply': 1, 'navigation_ack': 1}
    page.evaluate('(data) => window.render(data)', response)
    assert page.locator('.move-counter').inner_text() == 'Lance 1 de 1'
    assert page.get_by_role('button', name='Próximo lance').is_disabled()
