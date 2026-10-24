import chess
import pytest
import classroom as rooms
import classroom_materials as materials
import analysis_notebook as notebook


@pytest.fixture
def room(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'room.sqlite3'))
    owner=rooms.bootstrap_owner('owner','password-owner-123')
    teacher=rooms.enter_professor('teacher','password-teacher-123',rooms.issue_professor_key(owner,'teacher'))
    other=rooms.enter_professor('other','password-other-123',rooms.issue_professor_key(owner,'other'))
    student=rooms.students(teacher)[0]
    pupil=rooms.login_student(student['access_key'])
    outsider=rooms.login_student(rooms.students(other)[0]['access_key'])
    return teacher,student['id'],pupil,other,outsider


def exam():
    return dict(questions=[
        dict(kind='closed',prompt='Qual peça joga em L?',options=['Bispo','Cavalo'],answer=1,weight=2),
        dict(kind='open',prompt='Nome da peça mais valiosa?',answer='Rei | O rei',weight=3),
        dict(kind='open',prompt='Explique o plano.',answer='',weight=5)])


def test_keys_ownership_publication_and_hidden_answer_keys(room):
    teacher,student,pupil,other,outsider=room
    identifier=materials.save_material(teacher,student,'Prova','exam',exam(),False)
    assert materials.list_materials(pupil)==[]
    with pytest.raises(PermissionError):materials.submit_exam(pupil,identifier,[1,'Rei','Centro'])
    with pytest.raises(PermissionError):materials.list_materials(other,student)
    with pytest.raises(PermissionError):materials.save_material(other,student,'Outra','exam',exam())
    materials.set_published(teacher,identifier,True)
    visible=materials.list_materials(pupil)[0]
    assert all('answer' not in q for q in visible['payload']['questions'])
    assert materials.list_materials(teacher,student)[0]['payload']['questions'][0]['answer']==1
    with pytest.raises(PermissionError):materials.submit_exam(outsider,identifier,[1,'Rei','Centro'])
    with pytest.raises(PermissionError):materials.grade_exam(pupil,identifier,[2,3,5],['','',''])


def test_automatic_and_manual_grading_are_persistent_and_single_submission(room):
    teacher,student,pupil,other,_=room
    identifier=materials.save_material(teacher,student,'Prova','exam',exam())
    result=materials.submit_exam(pupil,identifier,[1,'  O RÉI! ','Atacar o centro'])
    assert result['score']==5 and result['maximum']==10 and result['pending']==1
    assert materials.submit_exam(pupil,identifier,[0,'errado','outro'])==result
    with pytest.raises(PermissionError):materials.grade_exam(other,identifier,[2,3,5],['','',''])
    with pytest.raises(ValueError):materials.grade_exam(teacher,identifier,[3,3,5],['','',''])
    corrected=materials.grade_exam(teacher,identifier,[2,3,4],['Correto','Correto','Explique também o desenvolvimento'])
    assert corrected['pending']==0 and corrected['percent']==90
    assert materials.list_materials(pupil)[0]['result']==corrected


def test_bans_revoke_material_access(room):
    teacher,student,pupil,_,_=room
    materials.save_material(teacher,student,'Prova','exam',exam())
    for i in range(3):rooms.warn(teacher,student,'Ausência '+str(i))
    with pytest.raises(PermissionError):materials.list_materials(pupil)


def test_line_training_only_accepts_assigned_sequence_and_records_completion(room):
    teacher,student,pupil,_,_=room
    identifier=materials.save_material(teacher,student,'Linha italiana','line',dict(pgn='1. e4 e5 2. Nf3 Nc6 3. Bc4 *',side='white'))
    board=chess.Board()
    with pytest.raises(ValueError):materials.check_training(pupil,identifier,4,'f1c4',board.fen())
    miss=materials.check_training(pupil,identifier,0,'d2d4',board.fen())
    assert not miss['correct'] and miss['progress']==0
    assert materials.check_training(pupil,identifier,0,'e2e4',board.fen())['progress']==2
    board.push_uci('e2e4');board.push_uci('e7e5')
    assert materials.check_training(pupil,identifier,2,'g1f3',board.fen())['progress']==4
    board.push_uci('g1f3');board.push_uci('b8c6')
    assert materials.check_training(pupil,identifier,4,'f1c4',board.fen())['completed']
    saved=materials.list_materials(teacher,student)[0]['progress']
    assert saved['completed']==1 and saved['errors']==1
    assert materials.restart_training(pupil,identifier)==0
    assert materials.list_materials(pupil)[0]['progress']['progress']==0


def test_black_lines_tactics_and_studied_game_comments(room):
    teacher,student,pupil,_,_=room
    identifier=materials.save_material(teacher,student,'Defesa','line',dict(pgn='1. e4 e5 2. Nf3 Nc6 *',side='black'))
    board=chess.Board();board.push_uci('e2e4')
    assert materials.check_training(pupil,identifier,1,'e7e5',board.fen())['progress']==3
    fen='6rk/6pp/8/4N3/8/8/8/6K1 w - - 0 1'
    tactic=materials.save_material(teacher,student,'Mate abafado','tactic',dict(fen=fen,solution=['e5f7']))
    assert materials.check_training(pupil,tactic,0,'e5f7',fen)['completed']
    game=materials.save_material(teacher,student,'Partida estudada','game',dict(pgn='1. e4 {Controle do centro} e5 *',side='white'))
    item=next(i for i in materials.list_materials(pupil) if i['id']==game)
    assert 'Controle do centro' in item['payload']['pgn']
    with pytest.raises(ValueError):materials.save_material(teacher,student,'Inválido','tactic',dict(fen=fen,solution=['a1a8']))


def test_notebook_is_private_and_survives_login_with_position_notes(tmp_path,monkeypatch):
    monkeypatch.setenv('COACH_CLASSROOM_DB',str(tmp_path/'notebooks.sqlite3'))
    one=rooms.register_user('one','password-one-123');two=rooms.register_user('two','password-two-123')
    key=notebook.game_key('1. e4 e5 *');board=chess.Board();board.push_uci('e2e4')
    notebook.save_entry(one,key,board.epd(),'1. e4',board.fen(),'Disputar o centro',pgn='1. e4 e5 *')
    assert notebook.saved_games(two)==[] and notebook.saved_games(two,key) is None
    assert notebook.saved_games(one,key)['pgn']=='1. e4 e5 *'
    assert notebook.entries(two,key)==[]
    rooms.logout(one);restored=rooms.login_user('one','password-one-123')
    assert notebook.entries(restored,key)[0]['body']=='Disputar o centro'
    assert notebook.game_key('1. e4 {Comentário} e5 *')==key
    notebook.save_entry(restored,key,'general','Resumo','','Desenvolver antes de atacar')
    assert len(notebook.entries(restored,key))==2
    with pytest.raises(PermissionError):notebook.entries(None,key)
