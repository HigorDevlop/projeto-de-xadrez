import chess
import pytest
from classroom_line_segments import segment,previous_line
from classroom_materials import parse_pgn,validate,training_moves

PGN='1. e4 {Centro} e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O 7. Re1 a6 8. Bb3 Ba7 *'


def test_segments_continue_at_exact_previous_position_and_keep_comments():
    first=validate('line',segment(PGN,0,2,'white'))
    second=validate('line',dict(segment(PGN,4,3,'white',previous=first),continuation=True))
    board,moves=training_moves(first,'line')
    for move in moves:board.push_uci(move)
    next_board,next_moves=training_moves(second,'line')
    assert next_board.fen()==board.fen()
    assert len(moves)==4 and len(next_moves)==6
    assert 'Centro' in first['pgn']
    third=segment(PGN,10,2,'white',previous=second)
    for move in next_moves:next_board.push_uci(move)
    assert parse_pgn(third['pgn']).board().fen()==next_board.fen()


def test_teacher_can_extend_a_finished_source_but_cannot_replace_earlier_moves():
    first=segment('1. e4 e5 2. Nf3 Nc6 *',0,2,'white')
    with pytest.raises(ValueError,match='terminou'):segment(first['source_pgn'],4,2,'white',previous=first)
    extended=segment(PGN,4,2,'white',previous=first)
    assert len(list(parse_pgn(extended['pgn']).mainline_moves()))==4
    with pytest.raises(ValueError,match='Mantenha'):
        segment('1. d4 d5 2. c4 e6 3. Nc3 Nf6 *',4,1,'white',previous=first)
    with pytest.raises(ValueError):validate('line',dict(first,pgn='1. d4 d5 *'))


def test_previous_line_follows_teacher_order_and_skips_other_event_types():
    line=dict(id='a',kind='line',reviewed=True,payload=segment(PGN,0,2,'white'))
    target=dict(id='b',kind='line',reviewed=False)
    draft=dict(steps=[dict(id='one',items=[line]),dict(id='two',items=[dict(id='video',kind='video')]),dict(id='three',items=[target])])
    assert previous_line(draft,'three','b') is line
    assert previous_line(draft,'one','a') is None

def test_published_continuation_is_playable_and_reordering_requires_review(room):
    import classroom_trails as trails
    import classroom_materials as materials
    teacher,student,pupil,_=room
    first=segment(PGN,0,2,'white')
    draft=trails.load_draft(teacher,student)
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='add'),[dict(title='Primeiro trecho',kind='line',payload=first,reviewed=True)])
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='add_event',kind='line'))
    step=draft['steps'][1];item=step['items'][0]
    second=dict(segment(PGN,4,2,'white',previous=first),continuation=True)
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='save_item',step=step['id'],item=item['id'],title='Continuação',payload=second,reviewed=True))
    trails.publish(teacher,student,draft['revision'])
    assigned=next(entry for entry in materials.list_materials(pupil) if entry['title']=='Continuação')
    board,moves=materials.training_moves(assigned['payload'],'line')
    result=materials.check_training(pupil,assigned['id'],0,moves[0],board.fen())
    assert result['correct'] and result['progress']==2
    draft=trails.edit_draft(teacher,student,draft['revision'],dict(action='order',order=[s['id'] for s in draft['steps']][::-1]))
    with pytest.raises(ValueError,match='continuação'):trails.publish(teacher,student,draft['revision'])

from test_classroom_trails import room


def test_exhausted_sequence_is_extended_without_changing_history():
    from classroom_line_segments import extend_sequence
    from stockfish_analysis import find_engine
    if not find_engine():pytest.skip('Local engine unavailable')
    first=segment('1. e4 e5 2. Nf3 Nc6 *',0,2,'white')
    extended=extend_sequence(first['source_pgn'],8)
    moves=list(parse_pgn(extended).mainline_moves())
    assert len(moves)==8
    assert moves[:4]==list(parse_pgn(first['pgn']).mainline_moves())
    next_block=segment(extended,4,2,'white',previous=first)
    assert parse_pgn(next_block['pgn']).board().fen()==parse_pgn(first['pgn']).end().board().fen()
    assert len(list(parse_pgn(next_block['pgn']).mainline_moves()))==4
