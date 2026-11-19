import pytest

import classroom as rooms
import classroom_student_profiles as profiles
from test_classroom import room


def test_membership_profile_and_ratings_survive_logout(room):
    teacher,seat,_=room
    user=rooms.register_user('ana-aluna','password-aluna-123')
    rooms.save_chesscom_user(user,'ana_chess')
    rooms.join_room(user,seat['access_key'])
    rooms.update_student(teacher,seat['id'],'Ana Silva')
    data={'player_id':123,'ratings':{'Rápidas':1400,'Blitz':1200}}
    profiles.save(teacher,seat['id'],'ana_chess',data)
    original_keys=[row['access_key'] for row in rooms.students(teacher)]
    rooms.logout(teacher);rooms.logout(user)
    teacher=rooms.login_professor('mestre','senha-segura-123',seat['teacher_key'])
    user=rooms.login_user('ana-aluna','password-aluna-123')
    assert rooms.membership(user)['id']==seat['id']
    assert rooms.identity(rooms.room_session(user))['id']==seat['id']
    student=rooms.students(teacher)[0]
    assert student['linked'] and student['account_name']=='ana-aluna'
    assert student['name']=='Ana Silva' and student['chesscom']=='ana_chess'
    assert [row['access_key'] for row in rooms.students(teacher)]==original_keys
    assert profiles.load(teacher,seat['id'],'ana_chess')['data']==data
    assert profiles.load(teacher,seat['id'],'another_user') is None


def test_saved_profiles_are_private_to_the_teacher(room):
    teacher,seat,pupil=room
    owner=rooms.login_owner('creator','creator-password-123')
    other=rooms.register_professor('other-teacher','other-password-123',rooms.issue_professor_key(owner))
    for token in [other,pupil]:
        with pytest.raises(PermissionError):profiles.load(token,seat['id'],'ana_chess')
        with pytest.raises(PermissionError):profiles.save(token,seat['id'],'ana_chess',{})


def test_chesscom_profile_uses_public_identity_and_separate_current_ratings(monkeypatch):
    import chesscom
    calls=[]
    def response(url):
        calls.append(url)
        return {'player_id':123,'name':'Ana','joined':100} if not url.endswith('/stats') else {
            'chess_rapid':{'last':{'rating':1400},'best':{'rating':2000}},
            'chess_blitz':{'last':{'rating':1250}},'chess_bullet':{'last':{'rating':True}}}
    monkeypatch.setattr(chesscom,'get_json',response)
    result=chesscom.fetch_player_profile('ANA_Chess')
    assert result['player_id']==123
    assert result['ratings']=={'Rápidas':1400,'Blitz':1250,'Bullet':None,'Diárias':None}
    assert calls==[chesscom.API+'ana_chess',chesscom.API+'ana_chess/stats']
