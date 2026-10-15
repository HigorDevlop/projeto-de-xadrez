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


def set_theme(page, label):
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.get_attribute('aria-expanded') != 'true':
        page.locator('[data-testid="stExpandSidebarButton"]').click()
    settings = sidebar.locator('details').filter(has=page.get_by_text('Configurações', exact=True))
    if settings.get_attribute('open') is None:
        settings.locator('summary').click()
    settings.get_by_role('radio', name=re.compile(re.escape(label.split()[-1]) + '$')).click()
    expect(settings.get_by_text('Fundo de tela', exact=True)).to_be_visible()
    settings.locator('summary').click()
    page.locator('[data-testid="stSidebarCollapseButton"]').click()


def capture_variants(page, artifacts, name):
    """Confere a mesma página nos dois temas e em uma largura de telefone."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    expanded = sidebar.get_attribute('aria-expanded') == 'true'
    if expanded:
        page.locator('[data-testid="stSidebarCollapseButton"]').click()
    page.screenshot(path=str(artifacts/f'{name}-claro.png'), full_page=True)
    set_theme(page, '☾ Escuro')
    expect(page.locator('.stApp')).to_have_css('color', 'rgb(237, 243, 237)')
    page.screenshot(path=str(artifacts/f'{name}-escuro.png'), full_page=True)
    set_theme(page, '☀ Claro')
    page.set_viewport_size({'width':390, 'height':844})
    expect(page.locator('.stApp')).to_have_css('color', 'rgb(32, 43, 38)')
    assert page.locator('[data-testid="stMain"]').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
    page.screenshot(path=str(artifacts/f'{name}-celular.png'), full_page=True)
    page.set_viewport_size({'width':1440, 'height':1100})
    if expanded:
        page.locator('[data-testid="stExpandSidebarButton"]').click()


def main():
    with tempfile.TemporaryDirectory() as temporary:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env = dict(os.environ, ACERVO_USER_PREFERENCE=str(Path(temporary)/'user.json'),
                   ACERVO_APPEARANCE_PREFERENCE=str(Path(temporary)/'appearance.json'),
                   ACERVO_PREPARATION_DIR=str(Path(temporary)/'preparation'))
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
                expect(page.get_by_role('heading',name='Seu xadrez, em perspectiva.',exact=True)).to_be_visible(timeout=45000)
                expect(page.locator('.opening')).to_have_count(0)
                expect(page.get_by_role('button',name='Pular abertura',exact=True)).to_have_count(0)
                expect(page.locator('video')).to_have_count(0)
                sidebar=page.locator('[data-testid="stSidebar"]')
                expect(sidebar).to_have_attribute('aria-expanded','false')
                page.locator('[data-testid="stExpandSidebarButton"]').click()
                sidebar.get_by_role('link',name='Partida',exact=False).wait_for()
                assert sidebar.get_by_role('link',name='Anotações',exact=False).count()==0
                assert sidebar.get_by_role('link',name='Estudo com livros',exact=False).count()==0
                expect(sidebar.get_by_role('button',name='Selecionar foto do perfil')).to_be_visible()
                expect(sidebar.get_by_text('Jogador',exact=True)).to_be_visible()
                page.locator('[data-testid="stSidebarCollapseButton"]').click()
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_be_visible()
                expect(page.locator('.recent-grid article')).to_have_count(8)
                expect(page.locator('.accuracy').first).to_contain_text('94,0%')
                artifacts=ROOT/'tests'/'artifacts'
                artifacts.mkdir(exist_ok=True)
                page.screenshot(path=str(artifacts/'ultimas-oito-partidas.png'),full_page=True)
                capture_variants(page, artifacts, 'painel')
                page.get_by_role('button',name='Analisar partida 1',exact=True).click()
                expect(page.get_by_role('button',name='Estudar',exact=False)).to_be_visible(timeout=45000)
                expect(page.get_by_role('radio',name='Análise Rápida',exact=True)).to_be_visible()
                expect(page.locator('.move-counter')).to_have_text('Lance 10 de 10')
                page.keyboard.press('Home')
                expect(page.locator('.move-counter')).to_have_text('Lance 0 de 10')
                search=page.locator('.st-key-question_launcher').bounding_box()
                assert search['y']<40 and search['x']>page.viewport_size['width']-100
                expect(page.get_by_role('button',name='Estudar',exact=False)).to_be_visible(timeout=45000)
                expect(page.locator('.board')).to_be_visible(timeout=30000)
                expect(page.locator('canvas.cat')).to_have_attribute('data-view','superior')
                assert page.locator('.cat-place').bounding_box()['width'] > 200
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_have_css('background-color','rgb(255, 254, 250)')
                expect(page.get_by_role('textbox',name='Pergunta rápida',exact=True)).to_be_hidden()
                expect(page.locator('.lesson')).to_be_hidden()
                assert not page.get_by_role('heading',name='Acervo de xadrez',exact=True).count()
                assert page.locator('.review-page').count()==0
                board=page.locator('.board').bounding_box()
                assert board['width']>650, board
                assert page.locator('.cat-place').bounding_box()['width'] > board['width'], board
                assert abs(board['x'] + board['width']/2 - 720) < 2, board
                page.get_by_role('button',name='Estudar',exact=False).click()
                expect(page.locator('.opening')).to_be_hidden()
                try:
                    expect(page.locator('.lesson')).to_be_visible(timeout=30000)
                except AssertionError:
                    print('ESTADO AO ABRIR ESTUDO:', page.locator('#fixture-runtime').get_attribute('data-state'), flush=True)
                    raise
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
                expect(page.get_by_role('heading',name='Resumo da qualidade dos lances')).to_be_visible()
                expect(page.locator('.quality-summary tbody tr')).to_have_count(7)
                expect(page.locator('.quality-accuracy').first).to_contain_text('94,0%')
                page.locator('.quality-summary').scroll_into_view_if_needed()
                page.screenshot(path=str(artifacts/'resumo-analise.png'),full_page=True)
                expect(page.locator('.review-page')).to_have_count(0)
                page.get_by_role('button',name='Anotações',exact=False).click()
                expect(page.get_by_role('button',name='1. e4 ♞✧ Brilhante',exact=True)).to_have_css('background-color','rgb(0, 205, 181)')
                page.get_by_role('tab',name='PGN',exact=True).click()
                page.get_by_role('button',name='Copiar PGN',exact=True).click()
                expect(page.get_by_text('PGN copiado!',exact=True)).to_be_visible()
                copied=page.evaluate('navigator.clipboard.readText()')
                from io import StringIO
                import chess.pgn
                exported = chess.pgn.read_game(StringIO(copied))
                assert len(list(exported.mainline_moves())) == 10
                assert 'Brilhante ♞✧' in exported.variations[0].comment
                page.keyboard.press('Escape')
                set_theme(page, '☾ Escuro')
                expect(page.locator('.stApp')).to_have_css('color','rgb(237, 243, 237)')
                expect(page.locator('.lesson')).to_have_css('background-color','rgb(26, 39, 32)')
                expect(page.locator('.lesson')).to_have_css('color','rgb(237, 243, 237)')
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_have_css('background-color','rgb(26, 39, 32)')
                artifacts=ROOT/'tests'/'artifacts'
                artifacts.mkdir(exist_ok=True)
                page.locator('.board').evaluate('(el)=>el.scrollIntoView({block:"start"})')
                expect(page.locator('canvas.cat')).to_have_attribute('data-pose','deitado',timeout=20000)
                board=page.locator('.board').bounding_box()
                board_area=page.locator('.st-key-centered_board').bounding_box()
                assert abs(board['x'] + board['width']/2 - (board_area['x']+board_area['width']/2)) < 2, board
                assert board['width'] > 650, board
                page.screenshot(path=str(artifacts/'estudo-escuro.png'),full_page=True)
                set_theme(page, '☀ Claro')
                expect(page.locator('.lesson')).to_have_css('color','rgb(32, 43, 38)')
                page.screenshot(path=str(artifacts/'estudo-claro.png'),full_page=True)
                page.get_by_role('button',name='Fechar estudo',exact=False).click()
                page.locator('[data-testid="stExpandSidebarButton"]').click()
                sidebar=page.locator('[data-testid="stSidebar"]')
                sidebar.get_by_role('button',name='Minha conta',exact=False).click()
                expect(sidebar.get_by_role('button',name='Trocar usuário',exact=True)).to_be_visible()
                sidebar.get_by_text('Minha conta',exact=True).click()
                sidebar.get_by_text('Configurações',exact=True).click()
                expect(sidebar.get_by_role('switch',name='Exibir abertura de Bobby Fischer ao entrar')).to_have_count(0)
                sidebar.get_by_text('Mostrar mesa sob o tabuleiro',exact=True).click()
                expect(page.locator('.workspace')).not_to_have_class(re.compile(r'.*\btable\b.*'))
                sidebar.get_by_text('Mostrar mesa sob o tabuleiro',exact=True).click()
                expect(page.locator('.workspace')).to_have_class(re.compile(r'.*\btable\b.*'))
                sidebar.get_by_text('Configurações',exact=True).click()
                sidebar.get_by_role('link',name='Partida',exact=False).click()
                page.get_by_role('link',name='Abrir biblioteca',exact=True).click()
                expect(page.get_by_role('heading',name='Suas ideias, lance a lance.',exact=True)).to_be_visible()
                capture_variants(page, artifacts, 'anotacoes')
                from sample_books import sample_pdf
                page.locator('.st-key-study_book_upload_0 input[type="file"]').set_input_files(
                    {'name':'Manual.pdf','mimeType':'application/pdf','buffer':sample_pdf()})
                expect(page.get_by_role('button',name='Abrir livro',exact=True)).to_be_visible()
                page.screenshot(path=str(artifacts/'biblioteca.png'),full_page=True)
                page.get_by_role('button',name='Abrir livro',exact=True).click()
                expect(page.get_by_role('spinbutton',name='Ir para a página')).to_have_value('1')
                cover_src=page.locator('.st-key-book_page_reader img').get_attribute('src')
                page.get_by_role('button',name='Próxima página',exact=False).click()
                expect(page.get_by_role('spinbutton',name='Ir para a página')).to_have_value('2')
                expect(page.locator('.st-key-book_page_reader img')).not_to_have_attribute('src',cover_src)
                page.get_by_role('button',name='Editar posição',exact=False).click()
                page.get_by_role('combobox',name='Peça para colocar').click()
                page.get_by_role('combobox',name='Peça para colocar').fill('Dama branca')
                page.get_by_role('option',name=re.compile('Dama branca')).click()
                expect(page.locator('.workspace')).to_have_attribute('data-edit-tool','Q')
                page.locator('[data-square="e4"]').click()
                expect(page.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: dama branco')
                page.get_by_role('combobox',name='Peça para colocar').click()
                page.get_by_role('option',name='Apagar peça',exact=True).click()
                expect(page.locator('.workspace')).to_have_attribute('data-edit-tool','erase')
                page.locator('[data-square="e4"]').click()
                expect(page.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: vazia')
                page.get_by_role('button',name='Limpar tabuleiro',exact=True).click()
                page.get_by_role('button',name='Concluir edição',exact=True).click()
                expect(page.get_by_text('Confira a posição:',exact=False)).to_be_visible()
                page.get_by_role('button',name='Posição inicial',exact=True).click()
                page.get_by_role('button',name='Concluir edição',exact=True).click()
                expect(page.get_by_role('button',name='Editar posição',exact=False)).to_be_visible()
                board=page.locator('.board')
                board.scroll_into_view_if_needed()
                origin=page.locator('[data-square="e2"]').bounding_box()
                target=page.locator('[data-square="e4"]').bounding_box()
                page.mouse.move(origin['x']+origin['width']/2,origin['y']+origin['height']/2)
                page.mouse.down()
                page.mouse.move(target['x']+target['width']/2,target['y']+target['height']/2,steps=10)
                page.mouse.up()
                expect(page.locator('[data-square="e4"]')).to_have_attribute('aria-label','e4: peão branco')
                expect(page.get_by_role('spinbutton',name='Ir para a página')).to_have_value('2')
                page.screenshot(path=str(artifacts/'livro-e-tabuleiro.png'),full_page=True)
                capture_variants(page, artifacts, 'biblioteca-leitura')
                print('CAPA, PÁGINAS, EDIÇÃO E LANCES DURANTE A LEITURA: OK',flush=True)
                sidebar.get_by_role('link',name='Tático',exact=False).click()
                expect(page.get_by_role('heading',name='Escolha um tema tático')).to_be_visible()
                expect(page.locator('.st-key-tactic_cards img')).to_have_count(20)
                assert page.locator('.st-key-tactic_cards img').evaluate_all('(els)=>els.every(img=>img.complete && img.naturalWidth>0)')
                page.screenshot(path=str(artifacts/'taticos.png'),full_page=True)
                capture_variants(page, artifacts, 'taticos')
                assert page.get_by_role('link',name='Ver tático no Lichess').count()==0
                page.get_by_role('button',name='Mate em 1',exact=True).click()
                expect(page.get_by_role('heading',name='Jogam as pretas',exact=True)).to_be_visible(timeout=20000)
                expect(page.get_by_text('Próximo exercício pronto',exact=False)).to_be_visible()
                expect(page.locator('.forge')).to_be_visible()
                expect(page.get_by_role('heading',name='Oficina tática',exact=True)).to_have_count(0)
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
                expect(page.get_by_role('heading',name='Preparo',exact=True)).to_be_visible()
                expect(page.get_by_role('textbox',name='Preparo',exact=True)).to_have_count(0)
                expect(page.get_by_text('Tempo de preparação',exact=True)).to_be_visible()
                expect(page.get_by_label('Data de início',exact=True)).to_be_visible()
                expect(page.get_by_label('Data de término',exact=True)).to_be_visible()
                page.get_by_text('Desempenho',exact=True).click()
                expect(page.locator('[data-testid="stVegaLiteChart"]')).to_be_visible()
                page.get_by_role('button',name='Ruy Lopez · Brancas',exact=False).click()
                page.get_by_role('button',name='Criar meu preparo',exact=True).click()
                expect(page.locator('.trail')).to_be_visible(timeout=30000)
                expect(page.locator('.day.current')).to_be_enabled()
                expect(page.get_by_label('Data de início',exact=True)).to_have_count(0)
                page.screenshot(path=str(artifacts/'preparo-questionario-e-mapa.png'),full_page=True)
                capture_variants(page, artifacts, 'preparo')
                sidebar.get_by_role('link',name='Tático',exact=False).click()
                sidebar.get_by_role('link',name='Preparo',exact=False).click()
                expect(page.locator('.trail')).to_be_visible()
                page.reload()
                expect(page.locator('.trail')).to_be_visible(timeout=30000)
                expect(page.locator('.day.locked').first).to_be_disabled()
                print('QUESTIONÁRIO, GRÁFICO, MAPAS E PERSISTÊNCIA DO PREPARO: OK',flush=True)
                expect(page.locator('.opening')).to_be_hidden()
                expect(page.locator('video')).to_have_count(0)
                page.set_viewport_size({'width':390,'height':844})
                page.goto(url)
                expect(page.get_by_role('heading',name='Seu xadrez, em perspectiva.',exact=True)).to_be_visible(timeout=45000)
                expect(page.locator('.opening')).to_have_count(0)
                expect(page.locator('[data-testid="stSidebar"]')).to_have_attribute('aria-expanded','false')
                expect(page.get_by_role('button',name='Pergunta rápida',exact=False)).to_be_visible()
                expect(page.locator('.recent-grid article')).to_have_count(8)
                page.screenshot(path=str(artifacts/'inicio-celular.png'),full_page=True)
                page.locator('[data-testid="stMain"]').get_by_role('link',name='Análise',exact=False).click()
                expect(page.get_by_role('button',name='Estudar',exact=False)).to_be_visible(timeout=45000)
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
