from opening_course_state import select_course,course_lines,begin_line,record_completion
from opening_training_state import lines_for,_start_quiz
from opening_rounds import cycle,target,next_lesson,quiz_target


def finish(plan,line):
    session=begin_line(plan,line['id'],'train')
    assert session is not None
    _start_quiz(plan,session)
    assert {item['line']['id'] for item in session['quiz_bank'].values()}=={line['id']}
    assert len(session['quiz_queue'])==quiz_target(plan,session)[1]
    session.update(mode='quiz',quiz_queue=[],quiz_states=dict.fromkeys(session['quiz_states'], 'correct'),phase='complete')
    record_completion(plan,session)
    return session


def test_every_line_restarts_in_order_then_advances_two_moves_together():
    plan=select_course(None,'cycle-test','italian')
    roots=[line for line in lines_for(plan).values() if line.get('stage')=='foundation']
    assert len(roots)==5
    for round_number,quota in [(0,5),(1,10)]:
        assert target(plan)==(5,quota)
        for root in roots:
            expected,_=next_lesson(plan,list(lines_for(plan).values()))
            assert expected['id']==root['id']
            session=finish(plan,root)
            assert session['course_round']==round_number
            assert session.get('cycle_recorded')
            record_completion(plan,session) # Duplicate acknowledgements cannot advance twice.
        assert cycle(plan)['round']==round_number+1
        assert cycle(plan)['completed']==[]
    assert target(plan)==(7,20)
    lesson,source=next_lesson(plan,list(lines_for(plan).values()))
    assert source['branch']==1
    assert not any(item['unlocked'] for item in course_lines(plan) if item.get('lesson_moves',5)>7)
    import chess
    for root in roots:
        board=chess.Board();moves=list(root['moves'])
        for uci in moves: board.push_uci(uci)
        while len(moves)<13:
            move=next(iter(board.legal_moves));moves.append(move.uci());board.push(move)
        plan.setdefault('course_extensions',[]).append(dict(root,id=root['id']+'-7',course_id='italian',moves=moves,stage='depth',lesson_moves=7))
    for root in roots:
        lesson,source=next_lesson(plan,list(lines_for(plan).values()))
        assert lesson['branch']==root['branch'] and lesson['lesson_moves']==7
        finish(plan,lesson)
    assert target(plan)==(9,40)
    _,source=next_lesson(plan,list(lines_for(plan).values()))
    assert source['branch']==1 and source['lesson_moves']==7


def test_incomplete_or_wrong_quiz_does_not_advance_round():
    from opening_rounds import complete
    plan=select_course(None,'cycle-test','italian')
    line=next(iter(lines_for(plan).values()))
    session=begin_line(plan,line['id'],'train')
    _start_quiz(plan,session)
    session.update(quiz_queue=[],quiz_states={str(i):'correct' for i in range(4)})
    complete(plan,session,line)
    assert cycle(plan)['completed']==[]
