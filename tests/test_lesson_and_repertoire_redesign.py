from pathlib import Path
import pytest
from playwright.sync_api import expect
from test_browser_components import browser_page
from test_coach_chess_ui import coach_server
import test_coach_chess_ui as desktop

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def library_server(tmp_path,monkeypatch,request):
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    reads=tmp_path/'reads.txt';reads.write_text('0')
    source=f'''
import sys
from pathlib import Path
sys.path.insert(0,{str(ROOT)!r})
import streamlit as st
import classroom as rooms
import classroom_community as community
from community_ui import lesson_room
from presentation import apply_theme
st.set_page_config(layout='wide');apply_theme(True)
if 'test_teacher' not in st.session_state:
    owner=rooms.bootstrap_owner('fixture-owner','fixture-password')
    token=rooms.register_professor('fixture-teacher','fixture-password',rooms.issue_professor_key(owner))
    st.session_state.test_teacher=token
    community.publish_video(token,'Aula salva',media=Path({str(ROOT/'assets/forge-photoreal.mp4')!r}).read_bytes(),mime='video/mp4')
if not hasattr(community,'_test_media_original'):
    community._test_media_original=community.video_media
    def read(*args,**kwargs):
        path=Path({str(reads)!r});path.write_text(str(int(path.read_text())+1))
        return community._test_media_original(*args,**kwargs)
    community.video_media=read
token=st.session_state.test_teacher
lesson_room(token,rooms.identity(token)['id'],teacher=True)
'''
    (tmp_path/'app.py').write_text(source,encoding='utf8')
    return request.getfixturevalue('coach_server'),reads


def test_publish_is_lazy_one_player_and_close_releases_video(browser_page,library_server):
    expect.set_options(timeout=40000)
    page=browser_page;url,reads=library_server
    page.set_viewport_size(dict(width=1440,height=1000));page.goto(url)
    expect(page.get_by_text('Aula salva',exact=True)).to_be_visible()
    expect(page.locator('video')).to_have_count(0)
    assert reads.read_text()=='0'
    page.get_by_role('button',name='Assistir',exact=True).click()
    expect(page.locator('video')).to_have_count(1)
    assert reads.read_text()=='1'
    page.get_by_role('button',name='Atualizar aulas',exact=False).click()
    expect(page.locator('video')).to_have_count(1)
    assert reads.read_text()=='1'
    page.get_by_role('button',name='Publicar vídeo',exact=False).click()
    page.get_by_role('textbox',name='Título da aula',exact=True).fill('Novo vídeo pronto')
    page.locator('input[type=file]').set_input_files(ROOT/'assets/forge-photoreal.mp4')
    page.get_by_role('button',name='Publicar',exact=True).click()
    expect(page.get_by_text('Novo vídeo pronto',exact=True)).to_be_visible()
    expect(page.locator('video')).to_have_count(0)
    assert reads.read_text()=='1'
    page.locator('[class*=st-key-recording_row_]').filter(has_text='Novo vídeo pronto').get_by_role('button',name='Assistir',exact=True).click()
    expect(page.locator('video')).to_have_count(1)
    assert reads.read_text()=='2'
    page.get_by_role('button',name='Fechar vídeo',exact=False).click()
    expect(page.locator('video')).to_have_count(0)
    page.screenshot(path='tests/artifacts/lessons-compact-desktop.png',full_page=True)
    page.set_viewport_size(dict(width=390,height=844))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    page.screenshot(path='tests/artifacts/lessons-compact-mobile.png',full_page=True)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)


@pytest.fixture
def personal_server(tmp_path,monkeypatch,request):
    monkeypatch.setattr(desktop,'ROOT',tmp_path)
    (tmp_path/'app.py').write_text(f'''
import sys
sys.path.insert(0,{str(ROOT)!r})
import chess
import streamlit as st
from personal_openings_ui import render_personal_openings
from personal_openings import storage_key
from preparation_state import new_plan,today,save_plan
from presentation import apply_theme
st.set_page_config(layout='wide');apply_theme(True)
if 'seeded' not in st.session_state:
    plan=new_plan(storage_key('fixture','alice'),today(),today(),[dict(id='personal',opening='Repertório',side='both')])
    lines=[]
    rows=[('C50','white','Principal do motor','e4 e5 Nf3 Nc6 Bc4 Bc5',2),('C58','white','Iniciativa com segurança','e4 e5 Bc4 Nf6 d3 Nc6',2),('C50','white','Opção sólida','e4 e5 Nc3 Nf6 d3 d5',2),('B10','black','Principal do motor','e4 c6 d4 d5',1),('C50','white','Principal do motor','e4 e5 Nf3 Nc6 Bc4 Bc5',4)]
    for i,(eco,side,kind,san,context) in enumerate(rows):
        board=chess.Board();moves=[];suggested=''
        for ply,move in enumerate(san.split()):
            if ply==context:suggested=move
            parsed=board.parse_san(move);moves.append(parsed.uci());board.push(parsed)
        lines.append(dict(id='fixture-'+str(i),opening=eco,side=side,recommendation=kind,variation=eco+' · '+kind,moves=moves,context_plies=context,depth=18,engine='Stockfish',suggested_san=suggested,played_san='Nf3' if side=='white' else 'e5',frequency=8,played_count=5,reasons=['Desenvolva suas peças.']))
    plan.update(repertoire_mode=True,repertoire_ids=[],personal_lines=lines,source_games=8,engine='Stockfish',recommendation_version=2,training_days={{}},retention={{}})
    save_plan(plan,namespace='openings');st.session_state.seeded=True
render_personal_openings('fixture','alice')
if st.session_state.get('openings_active'):st.success('TREINO ABERTO')
''',encoding='utf8')
    return request.getfixturevalue('coach_server')


def test_history_trails_show_only_progress_and_open_the_selected_opening(browser_page,personal_server):
    page=browser_page;page.set_viewport_size(dict(width=1440,height=1000));page.goto(personal_server)
    expect(page.locator('.personal-intro h3')).to_have_text('Suas trilhas')
    panel=page.locator('.st-key-personal_repertoire')
    expect(panel.locator('[role=combobox]')).to_have_count(0)
    for label in ('Com quais peças?','Escolha a posição','Mais precisa','Opções de preparação'):
        expect(panel.get_by_text(label,exact=True)).to_have_count(0)
    expect(panel.get_by_role('button',name='Começar',exact=True)).to_have_count(2)
    page.screenshot(path='tests/artifacts/personal-trails-desktop.png',full_page=True)
    page.set_viewport_size(dict(width=390,height=844))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    page.screenshot(path='tests/artifacts/personal-trails-mobile.png',full_page=True)
    row=panel.locator('[class*=st-key-personal_trail_]').filter(has_text='Defesa Caro-Kann').first
    row.get_by_role('button',name='Começar',exact=True).click()
    expect(panel.get_by_role('heading',name='Defesa Caro-Kann',exact=True)).to_be_visible()
    expect(panel.get_by_role('button',name='1',exact=True)).to_be_visible()
    expect(panel.get_by_role('button',name='Começar treino',exact=False)).to_be_visible()
    page.screenshot(path='tests/artifacts/personal-trail-course-mobile.png',full_page=True)
    panel.get_by_role('button',name='Começar treino',exact=False).click()
    expect(page.get_by_text('TREINO ABERTO',exact=True)).to_be_visible()
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
