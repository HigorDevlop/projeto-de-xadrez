import chess
import pytest
from playwright.sync_api import expect
import classroom as rooms
import classroom_courses as courses
import classroom_materials as materials
from interactive_board import position_data,piece_images,annotation_rows,game_frames
from test_browser_components import browser_page,mount
from test_coach_chess_ui import coach_server


def test_admin_preparation_opens_without_teachers_and_preserves_trail(browser_page,coach_server,tmp_path,monkeypatch):
    expect.set_options(timeout=30000)
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'classrooms.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    page=browser_page;page.set_viewport_size({'width':1440,'height':1100});page.goto(coach_server)
    page.get_by_role('textbox',name='Usuário',exact=True).fill('owner')
    page.get_by_role('textbox',name='Senha',exact=True).fill('password-owner-123')
    page.get_by_role('button',name='Entrar',exact=True).click()
    page.locator('.st-key-sidebar_navigation a').filter(has_text='Modo Preparo').click()
    expect(page.locator('.prep-profile strong')).to_contain_text('Laboratório')
    expect(page.get_by_text('Ainda não há alunos.',exact=False)).to_have_count(0)
    assert rooms.admin_overview(owner)['professors']==[]
    page.get_by_role('tab',name='Treino e provas',exact=True).click()
    page.locator('.tool[data-kind=line]').get_by_role('button',name='Adicionar',exact=False).click()
    dialog=page.get_by_role('dialog')
    dialog.get_by_role('textbox',name='Nome da atividade',exact=True).fill('Primeira linha')
    expect(page.locator('.board')).to_have_count(0)
    dialog.get_by_text('Conferir tabuleiro e comentários',exact=True).click()
    expect(page.locator('.board')).to_have_count(1)
    dialog.get_by_text('Conferir tabuleiro e comentários',exact=True).click()
    expect(page.locator('.board')).not_to_be_visible()
    dialog.get_by_role('button',name='Salvar atividade',exact=False).click()
    expect(page.get_by_text('Atividade salva.',exact=True)).to_be_visible()
    dialog.get_by_role('button',name='Fechar edição',exact=True).click()
    page.screenshot(path='tests/artifacts/teacher-material-clean-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    page.screenshot(path='tests/artifacts/teacher-material-clean-mobile.png',full_page=True)
    page.set_viewport_size({'width':1440,'height':1100})
    page.get_by_role('tab',name='Materiais e correções',exact=True).click()
    page.get_by_role('tab',name='Preparar material',exact=True).click()
    expect(page.locator('.node:not(.ghost)')).to_have_count(1)
    page.get_by_role('button',name='Disponibilizar trilha ao aluno',exact=True).click()
    expect(page.get_by_text('Trilha disponível · 1 atividades. O progresso anterior foi preservado.',exact=True)).to_be_visible()
    expect(page.get_by_role('tab',name='Cursos e manutenção',exact=True)).to_have_count(0)
    expect(page.locator('.node:not(.ghost)')).to_have_count(1)
    page.get_by_role('tab',name='Conversas',exact=True).click()
    expect(page.get_by_placeholder('Escreva uma mensagem')).to_be_visible()
    expect(page.locator('[data-testid=stException]')).to_have_count(0)


def test_creator_can_author_preview_and_reuse_courses_without_a_professor(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'workshop.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    seats=rooms.ensure_admin_room(owner)
    assert len(seats)==4 and rooms.ensure_admin_room(owner)==seats
    assert len(rooms.students(owner))==4
    assert not rooms.admin_overview(owner)['professors']
    source,target=seats[:2]
    material=materials.save_material(owner,source['id'],'Centro','line',dict(pgn='1. e4 e5 2. Nf3 *',side='white'))
    course=courses.save_course(owner,source['id'],'Curso do centro')
    preview=rooms.admin_preview_session(owner,source['id'])
    assert materials.list_materials(preview)[0]['id']==material
    ids=courses.assign_course(owner,course,target['id'])
    assert len(ids)==1 and ids[0]!=material
    assert materials.list_materials(owner,target['id'])[0]['result'] is None
    old_key=target['access_key']
    rooms.admin_maintain_student(owner,target['id'])
    assert rooms.students(owner)[1]['access_key']!=old_key
    courses.delete_course(owner,course)
    assert courses.list_courses(owner)==[] and materials.list_materials(owner,target['id'])
    ordinary=rooms.register_user('ordinary','password-ordinary-123')
    with pytest.raises(PermissionError):rooms.ensure_admin_room(ordinary)
    with pytest.raises(PermissionError):courses.list_courses(ordinary)


def test_teacher_cannot_access_creator_lab_or_courses(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'workshop.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    lab=rooms.ensure_admin_room(owner)[0]
    materials.save_material(owner,lab['id'],'Centro','line',dict(pgn='1. e4 e5 *',side='white'))
    course=courses.save_course(owner,lab['id'],'Curso privado')
    teacher=rooms.enter_professor('teacher','password-teacher-123',rooms.issue_professor_key(owner,'teacher'))
    seat=rooms.students(teacher)[0]
    assert courses.list_courses(teacher)==[]
    with pytest.raises(PermissionError):courses.assign_course(teacher,course,seat['id'])
    with pytest.raises(PermissionError):rooms.admin_preview_session(teacher,lab['id'])
    with pytest.raises(PermissionError):rooms.admin_preview_session(owner,seat['id'])


def test_ruled_notebook_is_beside_board_keeps_drafts_and_saves_source_position(browser_page):
    page=browser_page;page.set_viewport_size({'width':1400,'height':1000})
    frames=game_frames('1. e4 e5 *')
    data={**position_data(chess.Board()),'revision':0,'ply':0,'total':2,'navigation':True,
          'expanded':True,'epoch':'notebook','frames':frames,'pieces':piece_images(),
          'evaluationBar':True,'evaluation':{'cp':48,'mate':None},'analysisNotes':annotation_rows('1. e4 e5 *'),
          'notebook':dict(id='game',owner='one',entries=[],games=[],ack=None,status='')}
    mount(page,'interactive_board.py',data)
    page.add_style_tag(content='body{background:#090b09}')
    page.get_by_role('tab',name='Caderno',exact=True).click()
    editor=page.get_by_role('textbox',name='Pontos importantes do estudo',exact=True)
    editor.fill('Disputar o centro.\nDesenvolver as peças.')
    panel=page.locator('.analysis-notes').bounding_box();board=page.locator('.board').bounding_box()
    assert panel['x']>=board['x']+board['width'] and abs(panel['height']-board['height'])<2
    assert editor.evaluate('e=>getComputedStyle(e).backgroundImage').startswith('repeating-linear-gradient')
    page.get_by_role('button',name='Próximo lance',exact=True).click()
    expect(editor).to_have_value('')
    editor.fill('O peão chegou em e4.')
    page.get_by_role('button',name='Salvar anotação',exact=True).click()
    event=page.evaluate('window.events.findLast(e=>e.key==="note").value')
    assert event['body']=='O peão chegou em e4.' and event['fen']==frames[1]['fen']
    page.get_by_role('button',name='Lance anterior',exact=True).click()
    expect(editor).to_have_value('Disputar o centro.\nDesenvolver as peças.')
    assert page.locator('.evaluation-label').evaluate('e=>getComputedStyle(e).writingMode')=='horizontal-tb'
    expect(page.locator('.evaluation-readout')).to_contain_text('brancas')
    page.screenshot(path='tests/artifacts/analysis-notebook-side.png',full_page=True)
    page.get_by_role('tab',name='Anotações',exact=True).click()
    expect(page.locator('.notes-list')).to_be_visible()
