from copy import deepcopy
from playwright.sync_api import expect
from opening_course_state import select_course,begin_line,record_completion,active_session
from opening_training_state import lines_for,_start_quiz,board_for,expected_move
from opening_rounds import phases,phase_number,quiz_target
from test_browser_components import browser_page,mount


def boss_plan():
    plan=select_course(None,'boss-test','italian')
    plan['course_cycle']=dict(round=0,completed=[1,2,3,4])
    line=next(item for item in lines_for(plan).values() if item.get('stage')=='foundation' and item['branch']==5)
    return plan,line


def test_boss_is_fifty_and_completion_saves_precision_achievement_and_next_phase(tmp_path,monkeypatch):
    from preparation_state import save_plan,load_plan
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan,line=boss_plan()
    session=begin_line(plan,line['id'],'train');_start_quiz(plan,session)
    assert session['course_phase']==5 and len(session['quiz_queue'])==50
    assert record_completion(plan,session) is None
    assert phase_number(plan)==5 # An incomplete quiz cannot pass the boss.
    session.pop('practice_recorded',None)
    session.update(phase='complete',quiz_queue=[],quiz_states={str(i):'correct' for i in range(50)},quiz_first_answers={str(i):i<40 for i in range(50)})
    record_completion(plan,session)
    assert phase_number(plan)==6
    assert plan['phase_results']['5']['accuracy']==80.0
    assert 'phase_5' in plan['achievements']
    before=deepcopy(plan);record_completion(plan,session);assert plan==before
    save_plan(plan,namespace='openings');restored=load_plan('boss-test',namespace='openings')
    assert phases(restored)[4]['completed'] and phases(restored)[4]['accuracy']==80
    assert len(phases(restored))==50


def test_migrating_boss_preserves_answered_questions():
    plan,line=boss_plan()
    session=begin_line(plan,line['id'],'train');_start_quiz(plan,session)
    session['quiz_bank']={key:value for key,value in session['quiz_bank'].items() if int(key)<5}
    session.update(quiz_limit=5,quiz_queue=[1,2,3,4],quiz_states={'0':'correct',**{str(i):'pending' for i in range(1,5)}})
    restored=active_session(plan)
    assert restored['quiz_states']['0']=='correct'
    assert len(restored['quiz_bank'])==50 and len(restored['quiz_queue'])==49


def test_map_has_only_numbers_ten_bosses_and_saved_completion(browser_page):
    plan,line=boss_plan()
    plan['phase_results']={'1':{'accuracy':88.0}}
    page=browser_page;page.set_viewport_size({'width':1200,'height':950})
    mount(page,'opening_phase_trail.py',dict(phases=phases(plan),currentLine=line['id'],token='map-test'))
    expect(page.locator('.node')).to_have_count(50)
    expect(page.locator('.node.boss')).to_have_count(10)
    expect(page.locator('.node.learned')).to_have_count(4)
    expect(page.locator('.label,.trail-section,.start')).to_have_count(0)
    assert '88,0%' in page.locator('[data-phase="1"]').get_attribute('aria-label')
    page.locator('[data-phase="1"]').click()
    expect(page.get_by_role('status')).to_contain_text('88,0%')
    page.locator('[data-phase="5"]').click()
    assert page.evaluate('window.events[0].value.phase')==5
    expect(page.locator('[data-phase="6"]')).to_be_disabled()
    from pathlib import Path
    folder=Path(__file__).parent/'artifacts';folder.mkdir(exist_ok=True)
    page.screenshot(path=str(folder/'opening-50-phases.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')


def test_first_question_precision_tracks_error_without_counting_retry_as_first():
    from opening_course_state import receive_move
    plan,line=boss_plan();session=begin_line(plan,line['id'],'train');_start_quiz(plan,session)
    key=str(session['quiz_queue'][0]);board=board_for(session)
    wrong=next(move.uci() for move in board.legal_moves if move.uci()!=expected_move(plan,session))
    receive_move(plan,dict(uci=wrong,fen=board.fen(),revision=f"{session['token']}:{session['revision']}"),100)
    assert session['quiz_first_answers'][key] is False


def test_actual_fifty_answers_finish_boss_once():
    from opening_course_state import receive_move
    plan,line=boss_plan();session=begin_line(plan,line['id'],'train');_start_quiz(plan,session)
    for _ in range(50):
        event=dict(uci=expected_move(plan,session),fen=board_for(session).fen(),revision=f"{session['token']}:{session['revision']}")
        assert receive_move(plan,event,100)
    assert session['phase']=='complete'
    assert phase_number(plan)==6
    assert plan['phase_results']['5']['accuracy']==100
    assert not receive_move(plan,{'attempts':[event]},100)


def test_all_ten_bosses_have_fifty_questions_and_phase_fifty_stops(monkeypatch):
    from opening_rounds import next_lesson,complete
    plan,line=boss_plan()
    for number in range(5,51,5):
        plan['course_cycle']=dict(round=number//5-1,completed=[1,2,3,4])
        assert phase_number(plan)==number
        assert quiz_target(plan)[1]==50
    level=quiz_target(plan)[0]
    lessons=list(lines_for(plan).values())
    final=dict(line,id='last-phase',lesson_moves=level,stage='depth')
    lessons.append(final)
    monkeypatch.setattr('opening_training_state.lines_for',lambda plan:{item['id']:item for item in lessons})
    session=dict(course_phase=50,course_round=9,practice_intent='learn',quiz_queue=[],quiz_states={str(i):'correct' for i in range(50)},quiz_first_answers={str(i):True for i in range(50)})
    complete(plan,session,final)
    assert phase_number(plan)==51
    assert next_lesson(plan,lessons)==(None,None)
    assert all(item['completed'] for item in phases(plan))
    assert 'phase_50' in plan['achievements']
