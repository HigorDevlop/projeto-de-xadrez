from hashlib import sha256
import json
from pathlib import Path
import socket

import chess
import pytest
from playwright.sync_api import expect
from tactics import THEMES,Puzzle,fetch_puzzle_range,fetch_puzzle_pair,parse_database_row,solve_move
from offline_tactics import bank_count,bank_path
from test_browser_components import browser_page
import test_coach_chess_ui as desktop
from test_coach_chess_ui import coach_server


@pytest.mark.parametrize('theme',list(THEMES.values()))
def test_each_theme_selects_from_packaged_bank_without_network(theme,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('O treino não deve usar a rede')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr('tactics.urlopen',forbidden)
    puzzle=fetch_puzzle_range(theme,0,4000)
    assert theme=='mix' or theme in puzzle.themes
    assert puzzle.id!=fetch_puzzle_range(theme,0,4000,{puzzle.id}).id
    assert puzzle.solution[0] in [move.uci() for move in chess.Board(puzzle.fen).legal_moves]


def test_bank_integrity_and_local_prefetch():
    manifest=json.loads(bank_path().with_name('manifest.json').read_text())
    assert sha256(bank_path().read_bytes()).hexdigest()==manifest['sha256']
    assert bank_count()==manifest['count']>=30000
    assert min(manifest['themes'].values())>=40
    first,second=fetch_puzzle_pair('mix',700,1800)
    assert first.id!=second.id and 700<=first.rating<=1800 and 700<=second.rating<=1800


def test_database_setup_move_and_alternative_mates():
    row={'PuzzleId':'sample','FEN':'q3k1nr/1pp1nQpp/3p4/1P2p3/4P3/B1PP1b2/B5PP/5K2 b k - 0 17',
         'Moves':'e8d7 a2e6 d7d8 f7f8','Rating':'1760','Themes':'mate mateIn2 middlegame short'}
    puzzle=parse_database_row(row)
    board=chess.Board(row['FEN']);board.push_uci('e8d7')
    assert puzzle.fen==board.fen() and puzzle.solution==('a2e6','d7d8','f7f8')
    mate=Puzzle('twoMates','7k/5K2/8/6Q1/8/8/8/8 w - - 0 1',('g5h5',),900,('mateIn1',))
    assert solve_move(mate,0,'g5g8',mate.fen)==(1,'Tático resolvido!')


@pytest.fixture
def offline_server(tmp_path,monkeypatch,request):
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'app.py').write_text(f'''
import sys,runpy,socket
sys.path.insert(0,{str(root)!r})
original_connect=socket.socket.connect
def offline_connect(self,address):
    if isinstance(address,tuple) and address[0] not in ('localhost','127.0.0.1','::1'):
        raise OSError('Rede externa bloqueada no teste offline')
    return original_connect(self,address)
socket.socket.connect=offline_connect
runpy.run_path({str(root/'app.py')!r},run_name='__main__')
''',encoding='utf8')
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    return request.getfixturevalue('coach_server')


def test_real_tactics_and_openings_work_with_external_network_blocked(browser_page,offline_server):
    from offline_tactics import _bank
    path=bank_path();puzzles,_=_bank(str(path),path.stat().st_mtime_ns)
    by_fen={chess.Board(p.fen).fen():p for p in puzzles if 'mateIn1' in p.themes}
    page=browser_page;page.set_viewport_size({'width':1440,'height':1050})
    page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(offline_server) else route.abort())
    page.goto(offline_server)
    page.get_by_text('Criar conta de usuário',exact=True).click()
    page.get_by_role('textbox',name='Usuário',exact=True).fill('treino-sem-internet')
    page.get_by_role('textbox',name='Senha',exact=True).fill('senha-offline-treino')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Táticos').click()
    page.locator('.orb[data-theme=mateIn1]').evaluate('node=>node.click()')
    board=page.locator('.st-key-tactics_board_panel .board');expect(board).to_be_visible()
    for solved in range(1,5):
        revision=board.get_attribute('data-revision')
        uci=by_fen[board.get_attribute('data-fen')].solution[0]
        page.locator(f'[data-square="{uci[:2]}"]').click();page.locator(f'[data-square="{uci[2:4]}"]').click()
        if len(uci)==5:
            page.locator('.promotion button').filter(has_text={'q':'Dama','r':'Torre','b':'Bispo','n':'Cavalo'}[uci[4]]).click()
        expect(page.locator('.solved')).to_have_text(str(solved)+' resolvidos')
        expect(board).not_to_have_attribute('data-revision',revision)
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Aberturas').click()
    expect(page.locator('.home')).to_be_visible()
    page.locator('[data-id=italian]').first.click()
    page.get_by_role('button',name='Treinar',exact=True).click()
    expect(page.locator('.board')).to_be_visible()
    expect(page.locator('.training-hint')).to_have_count(1)
    # The first Italian lesson starts with e4 for White.
    page.locator('[data-square=e2]').click();page.locator('[data-square=e4]').click()
    expect(page.locator('[data-square=e4] svg')).to_have_count(1)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
