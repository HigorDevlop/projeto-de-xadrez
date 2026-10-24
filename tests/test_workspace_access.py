from workspace_access import allowed_pages


def test_user_cannot_open_management_or_performance_and_preparation_requires_room():
    personal=set(allowed_pages('user'))
    classroom=set(allowed_pages('user',True))
    assert {'Partida','Análise','Tático','Estudo com livros','Aberturas'}<=personal
    assert not personal & {'Desempenho','Preparo','Usuários','Anotações'}
    assert classroom-personal=={'Preparo'}
    assert not classroom & {'Desempenho','Usuários','Anotações'}


def test_professor_can_supervise_students_without_global_user_management():
    teacher=set(allowed_pages('professor'))
    assert {'Desempenho','Preparo'}<=teacher
    assert not teacher & {'Usuários','Anotações'}
    assert teacher<=set(allowed_pages('admin'))
    assert 'Usuários' in allowed_pages('admin')
