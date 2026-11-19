from copy import deepcopy
import chess
from opening_course_state import select_course, begin_line, course_lines, receive_move, active_session
from opening_training_state import _start_quiz, current_line, board_for, expected_move
from opening_error_review import record, identity
from test_opening_quiz import event


def test_quiz_uses_actual_errors_and_keeps_quota_and_legal_frames():
    plan=select_course(None,'errors-test','italian')
    line=course_lines(plan)[0]
    session=begin_line(plan,line['id'])
    session.update(mode='recall',hint=False)
    wrong=next(m.uci() for m in board_for(session).legal_moves if m.uci()!=expected_move(plan,session))
    assert receive_move(plan,event(plan,session,wrong),100)
    assert len(plan['opening_errors'])==1
    _start_quiz(plan,session)
    assert session['quiz_error_based'] and len(session['quiz_bank'])==5
    assert {item['ply'] for item in session['quiz_bank'].values()}=={0}
    for _ in range(5):
        assert receive_move(plan,event(plan,session),100)
    assert session['phase']=='complete'


def test_only_errors_from_taught_lines_of_current_opening_are_used():
    plan=select_course(None,'errors-test','italian')
    lines=course_lines(plan)
    first,other=lines[:2]
    session=begin_line(plan,first['id'])
    record(plan,session,first,2)
    other_ply=next(ply for ply in range(0,len(other['moves']),2) if identity(other,ply) not in {identity(first,p) for p in range(0,len(first['moves']),2)})
    record(plan,session,other,other_ply)
    foreign=select_course(None,'errors-test','caro')
    record(plan,session,course_lines(foreign)[0],3)
    _start_quiz(plan,session)
    assert {identity(item['line'],item['ply']) for item in session['quiz_bank'].values()}=={identity(first,2)}
    plan['practice_progress'][other['id']]['learned']=True
    _start_quiz(plan,session)
    assert {identity(item['line'],item['ply']) for item in session['quiz_bank'].values()}=={identity(first,2),identity(other,other_ply)}


def test_old_pending_quiz_keeps_answers_and_replaces_only_unanswered_positions():
    plan=select_course(None,'errors-test','italian')
    line=course_lines(plan)[0]
    session=begin_line(plan,line['id'])
    _start_quiz(plan,session)
    assert receive_move(plan,event(plan,session),100)
    answered={k:deepcopy(v) for k,v in session['quiz_bank'].items() if session['quiz_states'][k]=='correct'}
    states=deepcopy(session['quiz_states'])
    record(plan,session,line,4)
    session['quiz_policy']=2
    active_session(plan)
    assert session['quiz_states']==states
    for key,item in answered.items(): assert session['quiz_bank'][key]==item
    for key in session['quiz_queue']: assert session['quiz_bank'][str(key)]['ply']==4
    board=chess.Board()
    for uci in line['moves'][:4]: board.push_uci(uci)
    assert board_for(session).fen()==board.fen()
    assert expected_move(plan,session)==line['moves'][4]


def test_no_errors_falls_back_to_taught_line_without_changing_course():
    plan=select_course(None,'errors-test','italian')
    session=begin_line(plan,course_lines(plan)[0]['id'])
    _start_quiz(plan,session)
    assert not session['quiz_error_based']
    assert {item['line']['id'] for item in session['quiz_bank'].values()}=={session['line_id']}

def test_errors_survive_save_and_boss_uses_fifty_error_questions(tmp_path, monkeypatch):
    from preparation_state import save_plan, load_plan
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    plan=select_course(None,'persistent-errors','italian')
    line=course_lines(plan)[0]
    session=begin_line(plan,line['id'])
    record(plan,session,line,4)
    save_plan(plan,namespace='openings')
    plan=load_plan('persistent-errors',namespace='openings')
    session=active_session(plan)
    session['course_phase']=5
    _start_quiz(plan,session)
    assert session['quiz_error_based'] and session['quiz_limit']==50
    assert len(session['quiz_bank'])==50
    assert {item['ply'] for item in session['quiz_bank'].values()}=={4}


def test_legacy_recovered_errors_are_imported_before_new_quiz_replaces_bank():
    plan=select_course(None,'legacy-errors','italian')
    line=course_lines(plan)[0]
    session=begin_line(plan,line['id'])
    _start_quiz(plan,session)
    question=next(key for key,item in session['quiz_bank'].items() if item['ply']==4)
    session['quiz_states'][question]='correct'
    session['quiz_first_answers'][question]=False
    session['quiz_policy']=2
    _start_quiz(plan,session)
    assert session['quiz_error_based']
    assert {item['ply'] for item in session['quiz_bank'].values()}=={4}
