from copy import deepcopy
import chess

from opening_repertoires import selected_courses
from opening_course_state import select_course, course_lines, ensure_course, begin_line, active_session
from opening_training_state import _start_quiz, board_for, expected_move, submit_move, advance
from opening_quiz import quiz_data
from preparation_state import today, save_plan, load_plan
from test_browser_components import browser_page
from test_opening_course_ui import course_server


def test_italian_foundations_and_depths_never_leave_the_italian():
    course=selected_courses(['italian'])[0]
    prefix=['e2e4','e7e5','g1f3','b8c6','f1c4']
    foundations=[line for line in course['lines'] if line['stage']=='foundation']
    assert len(foundations)==5
    assert all(line['stage']=='foundation' for line in foundations)
    assert len({tuple(line['moves']) for line in foundations})==5
    roots={line['branch']:line['moves'] for line in foundations}
    depths=[line for line in course['lines'] if line['stage']=='depth']
    assert [line['branch'] for line in depths]==sorted(line['branch'] for line in depths)
    for line in course['lines']:
        assert line['moves'][:5]==prefix
        assert line['opening']=='Italiana'
        if line['stage']=='depth':
            root=roots[line['branch']]
            assert line['moves'][:len(root)]==root
            assert len(line['moves'])>len(root)
            assert line['lesson_moves'] in range(7,99,2)


def test_five_foundations_repeat_before_depth_unlocks():
    plan=select_course(None,'curriculum','italian')
    progress=ensure_course(plan)
    for index in range(5):
        rows=course_lines(plan)
        assert next(row for row in rows if row['unlocked'] and not row['learned'])['id']==rows[index]['id']
        progress[rows[index]['id']]['learned']=True
        plan['course_cycle']['completed'].append(rows[index]['branch'])
    plan['course_cycle'].update(round=2,completed=[])
    following=next(row for row in course_lines(plan) if row['unlocked'] and not row['learned'])
    assert following['stage']=='depth' and following['branch']==1


def test_quiz_grows_with_learned_lines_and_keeps_branch_identity_after_reload(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    plan=select_course(None,'cumulative','italian')
    progress=ensure_course(plan)
    sizes=[]
    for index in range(5):
        rows=course_lines(plan)
        session=begin_line(plan,rows[index]['id'],'train')
        _start_quiz(plan,session)
        data=quiz_data(rows[index],session)
        sizes.append(len(data['positions']))
        if index:
            assert session['quiz_bank']
            ids={item['line']['id'] for item in session['quiz_bank'].values()}
            assert ids<={row['id'] for row in rows[:index+1]}
            assert len(data['positions'])<=session['quiz_limit']
            save_plan(plan,namespace='openings')
            restored=load_plan('cumulative',namespace='openings')
            assert active_session(restored)['quiz_bank']==session['quiz_bank']
            for _ in range(len(session['quiz_queue'])):
                key=session['quiz_queue'][0]
                frame=quiz_data(rows[index],session)['positions'][str(key)]
                assert board_for(session).fen()==frame['fen']
                assert expected_move(plan,session)==frame['trainingExpected']
                event=dict(uci=frame['trainingExpected'],fen=frame['fen'],revision=f"{session['token']}:{session['revision']}")
                assert submit_move(plan,session,event,1)
                assert advance(plan,session,session['next_at'])
            assert not session['quiz_queue']
        progress[rows[index]['id']]['learned']=True
        plan['course_cycle']['completed'].append(rows[index]['branch'])
    assert sizes==[5,5,5,5,50] # The fifth phase is always a boss.


def test_old_foreign_lesson_cannot_resume_inside_italian():
    plan=select_course(None,'migration','italian')
    plan['practice_sessions']={'foreign:learn':dict(line_id='italian-old-philidor',phase='answer')}
    plan['practice_current']='foreign:learn'
    ensure_course(plan)
    assert active_session(plan) is None
    valid=course_lines(plan)[0]['id']
    plan['practice_sessions']={'trap:learn':dict(line_id=valid,custom_line=dict(moves=['e2e4','e7e5','g1f3','d7d6']))}
    plan['practice_current']='trap:learn'
    ensure_course(plan)
    assert active_session(plan) is None


def test_resuming_a_line_quiz_does_not_add_other_lines():
    plan=select_course(None,'quiz-resume','italian')
    rows=course_lines(plan)
    progress=ensure_course(plan)
    progress[rows[0]['id']]['learned']=True
    session=begin_line(plan,rows[0]['id'],'train')
    _start_quiz(plan,session)
    previous=len(quiz_data(rows[0],session)['positions'])
    progress[rows[1]['id']]['learned']=True
    restored=begin_line(plan,rows[0]['id'],'train')
    assert restored is session
    assert len(quiz_data(rows[0],session)['positions'])<=5
    assert session['quiz_scope']==[rows[0]['id']]


def test_cumulative_quiz_browser_and_server_reconcile_errors(browser_page):
    from interactive_board import position_data,piece_images
    from test_browser_components import mount
    from opening_course_state import receive_move
    plan=select_course(None,'browser-cumulative','italian')
    rows=course_lines(plan)
    progress=ensure_course(plan)
    for row in rows[:4]: progress[row['id']]['learned']=True
    plan['course_cycle']['completed']=[1,2,3,4]
    session=begin_line(plan,rows[4]['id'],'train')
    _start_quiz(plan,session)
    data=dict(position_data(board_for(session)),revision=f"{session['token']}:{session['revision']}",
        epoch=session['token'],ply=0,total=0,navigation=False,trainingMode=True,
        trainingExpected=expected_move(plan,session),quiz=quiz_data(rows[4],session),
        syncRecovery=True,instant=True,pieces=piece_images(),disabled=False)
    page=browser_page
    mount(page,'interactive_board.py',data)
    for index in range(12):
        uci=expected_move(plan,session)
        if index%3==0:
            uci=next(move.uci() for move in board_for(session).legal_moves if move.uci()!=uci)
        page.locator(f'[data-square={uci[:2]}]').click()
        page.locator(f'[data-square={uci[2:4]}]').click()
        event=page.evaluate("window.events.filter(e=>e.key==='move').at(-1).value")
        receive_move(plan,event,100)
        if not session['quiz_queue']: break
        client=page.evaluate("document.querySelector('main')._quizLocal")
        assert client['quiz']['queue']==session['quiz_queue']
        assert client['quiz']['states']==session['quiz_states']
        assert client['fen']==board_for(session).fen()


def test_curriculum_trail_groups_the_five_bases_before_depth(browser_page,course_server):
    from playwright.sync_api import expect
    from pathlib import Path
    page=browser_page
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto(course_server[0])
    page.locator('[data-id=italian]').first.click()
    expect(page.get_by_role('heading',name='Italian Game',exact=True)).to_be_visible()
    expect(page.locator('.node')).to_have_count(50)
    expect(page.locator('.node.boss')).to_have_count(10)
    expect(page.locator('.course-trail .label,.trail-section')).to_have_count(0)
    folder=Path(__file__).resolve().parents[1]/'tests/artifacts'
    folder.mkdir(exist_ok=True)
    page.screenshot(path=str(folder/'italian-curriculum.png'),full_page=True)
    page.locator('[data-phase="1"]').click()
    expect(page.locator('.training-hint')).to_have_count(1)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
