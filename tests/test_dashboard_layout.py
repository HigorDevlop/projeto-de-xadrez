import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import pytest
from urllib.request import urlopen
from playwright.sync_api import expect
from test_browser_components import browser_page


@pytest.mark.parametrize('fixture,charts',[('dashboard_fixture.py',4),('diagnostics_dashboard_fixture.py',6)])
def test_dashboard_is_one_full_width_page_with_readable_results(browser_page,tmp_path,fixture,charts):
    root=Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(root/'tests'/fixture),
        '--server.headless=true',f'--server.port={port}','--browser.gatherUsageStats=false'],cwd=root,
        env=dict(os.environ,ACERVO_PERFORMANCE_DIR=str(tmp_path)),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        url=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                urlopen(url+'/_stcore/health',timeout=1).close();break
            except OSError:time.sleep(.1)
        page=browser_page;page.set_viewport_size({'width':1600,'height':1000});page.goto(url)
        expect(page.get_by_role('heading',name='Desempenho',exact=True)).to_be_visible()
        expect(page.locator('.dash-kpis>div')).to_have_count(4)
        expect(page.locator('[data-testid=stException]')).to_have_count(0)
        expect(page.get_by_role('tab')).to_have_count(0)
        expect(page.locator('[data-testid=stVegaLiteChart]')).to_have_count(charts)
        page.wait_for_function('(total)=>document.querySelectorAll("[data-testid=stVegaLiteChart] .marks").length>=total',arg=charts)
        if charts==6:
            expect(page.get_by_role('heading',name='Onde você está errando',exact=True)).to_be_visible()
            expect(page.locator('.diag-insights')).to_contain_text('Meio-jogo')
            expect(page.get_by_role('button',name='Rever este lance no tabuleiro',exact=False)).to_be_visible()
        # Unchanged reports must keep the actual HUD and chart nodes across timer ticks.
        page.evaluate("window.stableDashboardNodes=[document.querySelector('.hud-console'),...document.querySelectorAll('[data-testid=stVegaLiteChart] .marks')]")
        page.wait_for_timeout(11000)
        assert page.evaluate("window.stableDashboardNodes.every(node=>node.isConnected)")
        expect(page.locator('[data-testid=stException]')).to_have_count(0)
        assert page.locator('.st-key-performance_dashboard').bounding_box()['width']>1500
        folder=root/'tests/artifacts';folder.mkdir(exist_ok=True)
        page.screenshot(path=str(folder/('performance-futuristic-diagnostics.png' if charts==6 else 'performance-full-page.png')),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:
        process.terminate();process.wait(timeout=15)


def test_quality_chart_refreshes_when_background_report_arrives(browser_page,tmp_path,monkeypatch):
    import json
    import chess.pgn
    from io import StringIO
    from chess_review import CATEGORIES
    from performance_dashboard import quality_key
    from test_performance_dashboard import archived
    root=Path(__file__).resolve().parents[1]
    fixture=tmp_path/'live_quality.py'
    item=archived(1)
    fixture.write_text(f'''import sys
sys.path.insert(0,{str(root)!r})
import streamlit as st
from performance_dashboard import render_dashboard
st.set_page_config(layout='wide')
render_dashboard([{item!r}],'player',complete=True,auto_diagnostics=False)
''',encoding='utf-8')
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(fixture),'--server.headless=true',f'--server.port={port}','--browser.gatherUsageStats=false'],cwd=root,env=dict(os.environ,ACERVO_PERFORMANCE_DIR=str(tmp_path)),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        url=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:urlopen(url+'/_stcore/health',timeout=1).close();break
            except OSError:time.sleep(.1)
        page=browser_page;page.goto(url)
        quality=page.locator('.st-key-dash_card_quality')
        expect(quality).to_contain_text('0 de 1 partidas analisadas')
        folder=tmp_path/'quality';folder.mkdir()
        key=quality_key(chess.pgn.read_game(StringIO(item['pgn'])))
        counts=dict.fromkeys(CATEGORIES, 0);counts['best']=2
        (folder/f'{key}-white.json').write_text(json.dumps(dict(version=1,complete=True,moves=2,counts=counts)))
        expect(quality).to_contain_text('1 de 1 partidas analisadas',timeout=20000)
        expect(quality.locator('[data-testid=stVegaLiteChart]')).to_have_count(1)
        expect(page.locator('.hud-main-gauge')).to_contain_text('1 de 1 partidas',timeout=20000)
        expect(page.locator('[data-testid=stException]')).to_have_count(0)
    finally:process.terminate();process.wait(timeout=15)
