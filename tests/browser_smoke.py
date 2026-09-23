"""Verificação real da interface: executar com o Python do ambiente virtual."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import socket
import re
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as temporary:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env = dict(os.environ, ACERVO_USER_PREFERENCE=str(Path(temporary)/'user.json'),
                   ACERVO_APPEARANCE_PREFERENCE=str(Path(temporary)/'appearance.json'))
        log = open(Path(temporary)/'server.log', 'w', encoding='utf-8')
        server = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'tests/ui_fixture.py',
            '--server.port', str(port), '--server.headless', 'true'], cwd=ROOT, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, env=env)
        try:
            for _ in range(60):
                try:
                    with urlopen(url+'/_stcore/health', timeout=1):
                        break
                except OSError:
                    time.sleep(.25)
            with sync_playwright() as driver:
                browser = driver.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width':1440,'height':1100}, permissions=['clipboard-read','clipboard-write'])
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(url)
                expect(page.locator('.opening')).to_be_visible(timeout=45000)
                expect(page.locator('.scene')).to_be_visible()
                page.get_by_role('button',name='Pular abertura',exact=True).click()
                expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute('aria-expanded','false')
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_be_visible()
                expect(page.locator('.recent-grid article')).to_have_count(8)
                expect(page.locator('.accuracy').first).to_contain_text('94,0%')
                page.locator('[data-testid="stMain"]').get_by_role('link',name='Análise',exact=False).click()
                search=page.locator('.st-key-question_launcher').bounding_box()
                assert search['y']<40 and search['x']>page.viewport_size['width']-100
                expect(page.get_by_role('button',name='Estudar',exact=False)).to_be_visible(timeout=45000)
                expect(page.locator('.board')).to_be_visible(timeout=30000)
                expect(page.locator('canvas.cat')).to_have_attribute('data-view','superior')
                assert page.locator('.cat-place').bounding_box()['width'] > 200
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_have_css('background-color','rgb(255, 250, 240)')
                expect(page.get_by_role('textbox',name='Pergunta rápida',exact=True)).to_be_hidden()
                expect(page.locator('.lesson')).to_be_hidden()
                assert not page.get_by_role('heading',name='Acervo de xadrez',exact=True).count()
                assert page.locator('.review-page').count()==0
                board=page.locator('.board').bounding_box()
                assert board['width']>300, board
                assert page.locator('.cat-place').bounding_box()['width'] > board['width'], board
                assert abs(board['x'] + board['width']/2 - 720) < 2, board
                profile=page.get_by_role('button',name='Selecionar foto do perfil').bounding_box()
                nick=page.get_by_text('Jogador',exact=True).bounding_box()
                assert nick['x']>profile['x']+profile['width'] and abs(nick['y']-profile['y'])<130
                page.get_by_role('button',name='Estudar',exact=False).click()
                expect(page.locator('.opening')).to_be_hidden()
                expect(page.locator('.lesson')).to_be_visible(timeout=30000)
                before=page.locator('.lesson-text').inner_text()
                for _ in range(10):
                    page.keyboard.press('ArrowRight')
                expect(page.locator('.move-counter')).to_have_text('Lance 10 de 10')
                expect(page.locator('.lesson-text')).to_contain_text('Be7')
                for _ in range(10):
                    page.keyboard.press('ArrowLeft')
                expect(page.locator('.move-counter')).to_have_text('Lance 0 de 10')
                expect(page.locator('.lesson-text')).to_have_text(before)
                page.keyboard.press('End')
                page.keyboard.press('Home')
                page.get_by_role('button',name='Próximo lance',exact=True).click()
                expect(page.locator('.lesson-text')).to_contain_text('e4')
                page.get_by_role('button',name='Pergunta rápida',exact=False).click()
                page.get_by_role('textbox',name='Pergunta rápida',exact=True).fill('Posso jogar e5?')
                page.keyboard.press('ArrowLeft')
                expect(page.locator('.move-counter')).to_have_text('Lance 1 de 10')
                started=time.perf_counter()
                page.get_by_role('button',name='Perguntar',exact=True).click()
                expect(page.get_by_text('e5 é legal para as pretas.',exact=False)).to_be_visible()
                elapsed=time.perf_counter()-started
                assert elapsed<5, elapsed
                print(f'PERGUNTA: {elapsed:.3f}s',flush=True)
                page.keyboard.press('Escape')
                page.get_by_role('button',name='Analisar Partida',exact=False).click()
                expect(page.get_by_role('radio',name='Análise Rápida',exact=True)).to_be_visible()
                expect(page.get_by_role('radio',name='Análise Mediana',exact=True)).to_be_visible()
                page.get_by_text('Análise Profunda',exact=True).click()
                page.get_by_role('button',name='Iniciar análise',exact=True).click()
                expect(page.get_by_text('Análise concluída.',exact=False)).to_be_visible()
                expect(page.locator('.review-page')).to_have_count(0)
                page.get_by_role('button',name='Anotações',exact=False).click()
                page.get_by_role('tab',name='PGN',exact=True).click()
                page.get_by_role('button',name='Copiar PGN',exact=True).click()
                expect(page.get_by_text('PGN copiado!',exact=True)).to_be_visible()
                copied=page.evaluate('navigator.clipboard.readText()')
                assert '1. e4 e5' in copied and 'O-O Be7' in copied
                page.keyboard.press('Escape')
                page.get_by_role('radio',name='☾ Escuro',exact=True).click()
                expect(page.locator('.stApp')).to_have_css('color','rgb(243, 244, 246)')
                expect(page.locator('.lesson')).to_have_css('background-color','rgb(32, 41, 54)')
                expect(page.locator('.lesson')).to_have_css('color','rgb(243, 244, 246)')
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_have_css('background-color','rgb(23, 30, 40)')
                artifacts=ROOT/'tests'/'artifacts'
                artifacts.mkdir(exist_ok=True)
                page.locator('.board').evaluate('(el)=>el.scrollIntoView({block:"start"})')
                expect(page.locator('canvas.cat')).to_have_attribute('data-pose','deitado',timeout=20000)
                board=page.locator('.board').bounding_box()
                assert abs(board['x'] + board['width']/2 - 720) < 2, board
                page.screenshot(path=str(artifacts/'estudo-escuro.png'),full_page=True)
                page.get_by_role('radio',name='Claro',exact=True).click()
                expect(page.locator('.lesson')).to_have_css('color','rgb(32, 37, 48)')
                page.screenshot(path=str(artifacts/'estudo-claro.png'),full_page=True)
                page.get_by_role('button',name='Fechar estudo',exact=False).click()
                page.locator('[data-testid="stExpandSidebarButton"]').click()
                sidebar=page.locator('[data-testid="stSidebar"]')
                expect(sidebar.get_by_role('button',name='Trocar Usuário',exact=False)).to_be_visible()
                sidebar.get_by_role('link',name='Tático',exact=False).click()
                expect(page.get_by_role('heading',name='Escolha um tema tático')).to_be_visible()
                expect(page.locator('.st-key-tactic_cards img')).to_have_count(20)
                assert page.locator('.st-key-tactic_cards img').evaluate_all('(els)=>els.every(img=>img.complete && img.naturalWidth>0)')
                page.screenshot(path=str(artifacts/'taticos.png'),full_page=True)
                assert page.get_by_role('link',name='Ver tático no Lichess').count()==0
                page.get_by_role('button',name='Mate em 1',exact=True).click()
                expect(page.get_by_role('heading',name='Jogam as pretas',exact=True)).to_be_visible(timeout=20000)
                expect(page.get_by_text('Próximo exercício pronto',exact=False)).to_be_visible()
                expect(page.locator('.forge')).to_be_visible()
                wrong=page.get_by_role('button',name='g8: cavalo preto',exact=True)
                wrong.scroll_into_view_if_needed()
                first=wrong.bounding_box()
                last=page.get_by_role('button',name='f6: vazia',exact=True).bounding_box()
                page.mouse.move(first['x']+first['width']/2,first['y']+first['height']/2)
                page.mouse.down()
                page.mouse.move(last['x']+last['width']/2,last['y']+last['height']/2,steps=10)
                page.mouse.up()
                expect(page.locator('.smith-comment')).to_contain_text('A espada foi prejudicada')
                expect(page.locator('.forge')).to_have_attribute('data-result','wrong')
                origin=page.get_by_role('button',name='d8: dama preto',exact=True)
                destination=page.get_by_role('button',name='h4: vazia',exact=True)
                origin.scroll_into_view_if_needed()
                start,end=origin.bounding_box(),destination.bounding_box()
                page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
                page.mouse.down(button='right')
                page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=12)
                page.mouse.up(button='right')
                expect(page.locator('.annotation-arrow')).to_have_count(1)
                page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
                page.mouse.down()
                page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=12)
                page.mouse.up()
                expect(page.locator('.annotation-arrow')).to_have_count(0)
                expect(page.get_by_text('Tático resolvido! Novo exercício carregado.',exact=True)).to_be_visible(timeout=20000)
                expect(page.get_by_role('button',name='d8: dama preto',exact=True)).to_be_visible()
                expect(page.locator('.forge')).to_have_attribute('data-result','recovered')
                expect(page.locator('.forge progress')).to_have_attribute('value','0')
                # O próximo exercício já está disponível; um acerto limpo concede afiação.
                origin=page.get_by_role('button',name='d8: dama preto',exact=True)
                destination=page.get_by_role('button',name='h4: vazia',exact=True)
                origin.scroll_into_view_if_needed()
                start,end=origin.bounding_box(),destination.bounding_box()
                page.mouse.move(start['x']+start['width']/2,start['y']+start['height']/2)
                page.mouse.down()
                page.mouse.move(end['x']+end['width']/2,end['y']+end['height']/2,steps=5)
                started=time.perf_counter()
                page.mouse.up()
                expect(page.locator('.forge')).to_have_attribute('data-result','correct')
                expect(page.locator('.forge progress')).to_have_attribute('value','12')
                elapsed=time.perf_counter()-started
                assert elapsed<1.5, elapsed
                print(f'RESPOSTA TÁTICA E PRÓXIMO EXERCÍCIO: {elapsed:.3f}s',flush=True)
                page.screenshot(path=str(artifacts/'forja-tatica.png'),full_page=True)
                assert page.get_by_role('button',name='Próximo tático',exact=True).count()==0
                page.get_by_role('combobox',name='Tema tático',exact=True).click()
                page.get_by_role('option',name='Cravada',exact=True).click()
                expect(page.get_by_role('combobox',name='Tema tático')).to_have_value('Cravada')
                sidebar.get_by_role('link',name='Preparo',exact=False).click()
                page.get_by_role('textbox',name='Preparo',exact=True).fill('Preparar a defesa siciliana.')
                page.get_by_role('textbox',name='Preparo',exact=True).press('Tab')
                sidebar.get_by_role('link',name='Tático',exact=False).click()
                sidebar.get_by_role('link',name='Preparo',exact=False).click()
                expect(page.get_by_role('textbox',name='Preparo',exact=True)).to_have_value('Preparar a defesa siciliana.')
                sidebar.get_by_text('Configurações',exact=True).click()
                page.get_by_text('Exibir abertura de Bobby Fischer ao entrar',exact=True).click()
                expect(page.get_by_role('switch',name='Exibir abertura de Bobby Fischer ao entrar')).not_to_be_checked()
                page.reload()
                expect(page.get_by_role('textbox',name='Preparo',exact=True)).to_be_visible(timeout=30000)
                expect(page.locator('.opening')).to_be_hidden()
                page.locator('[data-testid="stExpandSidebarButton"]').click()
                sidebar.get_by_text('Configurações',exact=True).click()
                expect(page.get_by_role('switch',name='Exibir abertura de Bobby Fischer ao entrar')).not_to_be_checked()
                page.get_by_text('Exibir abertura de Bobby Fischer ao entrar',exact=True).click()
                expect(page.get_by_role('switch',name='Exibir abertura de Bobby Fischer ao entrar')).to_be_checked()
                expect(page.locator('.opening')).to_be_hidden()
                page.set_viewport_size({'width':390,'height':844})
                page.goto(url)
                expect(page.locator('.opening')).to_be_visible(timeout=45000)
                expect(page.locator('.scene')).to_be_visible()
                page.get_by_role('button',name='Pular abertura',exact=True).click()
                expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute('aria-expanded','false')
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_be_visible()
                expect(page.locator('.recent-grid article')).to_have_count(8)
                page.locator('[data-testid="stMain"]').get_by_role('link',name='Análise',exact=False).click()
                search=page.locator('.st-key-question_launcher').bounding_box()
                assert search['y']<40 and search['x']>page.viewport_size['width']-100
                expect(page.get_by_role('button',name='Estudar',exact=False)).to_be_visible(timeout=45000)
                if page.locator('[data-testid="stSidebar"]').get_attribute('aria-expanded') == 'true':
                    page.locator('[data-testid="stSidebarCollapseButton"]').click()
                page.get_by_role('button',name='Estudar',exact=False).click()
                expect(page.locator('.opening')).to_be_hidden()
                expect(page.locator('.lesson')).to_be_visible(timeout=30000)
                mobile_board=page.locator('.board').bounding_box()
                mobile_lesson=page.locator('.lesson').bounding_box()
                assert mobile_board['width'] <= 390
                assert mobile_lesson['y'] >= mobile_board['y'] + mobile_board['height']
                page.screenshot(path=str(artifacts/'estudo-celular.png'),full_page=True)
                assert not errors, errors
                assert page.locator('[data-testid="stException"]').count()==0
                print('LAYOUT, NAVEGAÇÃO, ESTUDO, PERGUNTAS, PGN, TEMAS E TÁTICOS: OK',flush=True)
                browser.close()
        finally:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(server.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                server.terminate()
            server.wait(timeout=10)
            log.close()


if __name__=='__main__':
    main()
