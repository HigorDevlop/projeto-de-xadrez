import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from playwright.sync_api import expect
from test_browser_components import browser_page


def test_dashboard_is_one_full_width_page_with_readable_results(browser_page,tmp_path):
    root=Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(root/'tests/dashboard_fixture.py'),
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
        expect(page.locator('[data-testid=stVegaLiteChart]')).to_have_count(4)
        assert page.locator('.st-key-performance_dashboard').bounding_box()['width']>1500
        folder=root/'tests/artifacts';folder.mkdir(exist_ok=True)
        page.screenshot(path=str(folder/'performance-full-page.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:
        process.terminate();process.wait(timeout=15)
