from copy import deepcopy
import random
import chess
import pytest

from opening_achievements import quiz_limit,collection,record_achievements
from opening_course_state import select_course,ensure_course,begin_line,record_completion,active_session
from opening_training_state import board_for,expected_move,submit_move,advance,_start_quiz
from opening_levels import prepare_level
from preparation_state import save_plan,load_plan


def sample_lines(level=13,count=12):
    result=[]
    for index in range(count):
        seed=index
        while True:
            board=chess.Board();moves=[];rng=random.Random(seed)
            for san in 'e4 e5 Nf3 Nc6 Bc4'.split():
                move=board.parse_san(san);moves.append(move.uci());board.push(move)
            while len(moves)<2*level-1 and not board.is_game_over():
                move=rng.choice(list(board.legal_moves));moves.append(move.uci());board.push(move)
            if len(moves)==2*level-1: break
            seed+=100
        result.append(dict(id=f'line-{index}',moves=moves,side='white',opening='Italiana',
            stage='depth',branch=index+1,lesson_moves=level,variation='Teste',needs_preparation=False))
    return result


def review_plan(level):
    plan=select_course(None,'achievements-test','italian')
    plan['personal_lines']=sample_lines(level)
    progress=ensure_course(plan)
    for row in progress.values(): row['learned']=True
    session=begin_line(plan,'line-0','practice')
    return plan,session


@pytest.mark.parametrize('level,limit',[(5,5),(7,10),(9,20),(11,40),(13,50),(15,50),(21,50)])
def test_review_cap_uses_the_lesson_level(level,limit):
    assert quiz_limit(level)==limit
    plan,session=review_plan(level)
    assert session['quiz_limit']==limit
    assert len(session['quiz_states'])==limit
    assert len(session['quiz_queue'])==limit
    assert not any(item['earned'] for item in collection(plan))


def test_fifty_achievement_requires_completion_and_survives_reload(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan,session=review_plan(13)
    line=plan['personal_lines'][0]
    assert record_achievements(plan,session,line)==[]
    for _ in range(50):
        event=dict(uci=expected_move(plan,session),fen=board_for(session).fen(),revision=f"{session['token']}:{session['revision']}")
        assert submit_move(plan,session,event,0)
        assert advance(plan,session,session['next_at'])
    assert not session['quiz_queue']
    record_completion(plan,session)
    assert 'quiz_50' in plan['achievements']
    assert 'Memória de mestre' in session['new_achievements']
    original=deepcopy(plan['quiz_seen'])
    assert record_achievements(plan,session,line)==[]
    assert plan['quiz_seen']==original
    save_plan(plan,namespace='openings')
    restored=load_plan(plan['username'],namespace='openings')
    assert next(item for item in collection(restored) if item['id']=='quiz_50')['earned']
    assert load_plan('another-user',namespace='openings') is None


def test_shorter_quiz_and_exploration_never_award_fifty():
    plan,session=review_plan(5)
    session.update(quiz_queue=[],quiz_states={str(i):'correct' for i in range(5)})
    line=plan['personal_lines'][0]
    record_achievements(plan,session,line)
    assert 'quiz_5' in plan['achievements'] and 'quiz_50' not in plan['achievements']
    other=deepcopy(session)
    other.pop('achievements_recorded',None)
    other.update(practice_intent='explore',quiz_states={str(i):'correct' for i in range(50)})
    assert record_achievements(plan,other,line)==[]
    assert 'quiz_50' not in plan['achievements']


def test_local_engine_extends_5_7_9_11_13_without_changing_branch():
    from stockfish_analysis import find_engine
    if not find_engine(): pytest.skip('Stockfish local indisponível')
    plan=select_course(None,'level-engine','italian')
    from opening_training_state import lines_for
    source=list(lines_for(plan).values())[1]
    root=list(source['moves'])
    assert len(root)==9 and source['lesson_moves']==5
    for target in (7,9,11,13):
        result=prepare_level(plan,source,target)
        assert result['lesson_moves']==target
        assert len(result['moves'])==2*target-1
        assert result['moves'][:len(source['moves'])]==source['moves']
        assert result['moves'][:len(root)]==root
        assert result['branch']==source['branch']
        board=chess.Board()
        for uci in result['moves']:
            assert chess.Move.from_uci(uci) in board.legal_moves
            board.push_uci(uci)
        plan.setdefault('course_extensions',[]).append(result)
        source=result


def test_review_rotation_uses_old_material_after_the_cap():
    plan,session=review_plan(5)
    first={item['line']['id']+':'+str(item['ply']) for item in session['quiz_bank'].values()}
    session.update(quiz_queue=[],quiz_states=dict.fromkeys(session['quiz_states'], 'correct'))
    record_achievements(plan,session,plan['personal_lines'][0])
    session['phase']='complete'
    again=begin_line(plan,'line-0','practice')
    following={item['line']['id']+':'+str(item['ply']) for item in again['quiz_bank'].values()}
    assert following!=first and len(following)==5


def test_achievement_collection_renders_unlocked_and_locked_badges():
    import json
    from streamlit.testing.v1 import AppTest
    plan=dict(achievements={'quiz_50':{'day':'2026-10-23','title':'Memória de mestre'}},achievement_progress={'quiz':50})
    source='''import json
from opening_achievements_ui import render_achievements
render_achievements(json.loads(PAYLOAD))
'''.replace('PAYLOAD',repr(json.dumps(plan)))
    app=AppTest.from_string(source).run()
    assert not app.exception
    from opening_achievements import ACHIEVEMENTS
    assert app.status[0].label==f'Conquistas · 1/{len(ACHIEVEMENTS)}'
    assert any('Memória de mestre' in item.value for item in app.markdown)
    assert len(app.get('progress'))==len(ACHIEVEMENTS)


def test_achievements_are_separate_and_restore_when_returning_to_opening(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan=select_course(None,'same-owner','italian')
    plan.update(achievements={'quiz_50':{'day':'2026-10-23','title':'Memória de mestre'}},achievement_progress={'quiz':50})
    other=select_course(plan,'same-owner','caro')
    assert not any(item['earned'] for item in collection(other))
    assert all(item['progress']==0 for item in collection(other))
    save_plan(other,namespace='openings')
    restored=load_plan('same-owner',namespace='openings')
    assert not next(item for item in collection(restored) if item['id']=='quiz_50')['earned']
    returned=select_course(restored,'same-owner','italian')
    assert next(item for item in collection(returned) if item['id']=='quiz_50')['earned']
    assert next(item for item in collection(restored,include_library=True) if item['id']=='quiz_50')['earned']


def test_prepared_level_is_saved_and_started_by_the_background_monitor():
    import json
    from streamlit.testing.v1 import AppTest
    plan=select_course(None,'level-ui','italian')
    source=list(__import__('opening_training_state').lines_for(plan).values())[0]
    line=dict(source,id='prepared-test',needs_preparation=False)
    payload=repr(json.dumps(dict(plan=plan,line=line)))
    script='''import json
from concurrent.futures import Future
import streamlit as st
from opening_levels_ui import render_levels
if not st.session_state.get('seeded'):
    data=json.loads(PAYLOAD)
    st.session_state.seeded=True
    st.session_state.plan=data['plan']
    future=Future();future.set_result(data['line'])
    st.session_state.openings_level_job=dict(owner=data['plan']['username'],course=data['plan']['repertoire_ids'],future=future,auto_start=True)
def save(plan): st.session_state.saved=plan
def start(identifier,intent): st.session_state.started=identifier
render_levels(st.session_state.plan,save,start)
'''.replace('PAYLOAD',payload)
    app=AppTest.from_string(script).run(timeout=20)
    assert not app.exception
    assert app.session_state.started=='prepared-test'
    assert app.session_state.saved['course_extensions'][0]['id']=='prepared-test'
