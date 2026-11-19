import pytest
from classroom_materials import validate
from classroom_position_notes import positions,visible_notes
from classroom_line_segments import segment

PGN='1. e4 e5 2. Nf3 Nc6 *'


def test_instructions_are_bound_to_valid_positions_and_keep_move_labels():
    frames=positions(PGN)
    payload=dict(pgn=PGN,side='white',position_notes=[dict(ply=i,fen=frames[i]['fen'],text=text) for i,text in [(0,'Controle o centro'),(1,'O peão ocupa e4'),(2,'Desenvolva o cavalo')]])
    checked=validate('line',payload)
    assert visible_notes(checked,0)==[dict(label='Posição inicial',text='Controle o centro')]
    assert visible_notes(checked,2)==[dict(label='Após 1. e4',text='O peão ocupa e4'),dict(label='Após 1... e5',text='Desenvolva o cavalo')]
    with pytest.raises(ValueError):validate('line',dict(payload,position_notes=[dict(ply=1,fen=frames[2]['fen'],text='Errada')]))
    with pytest.raises(ValueError):validate('line',dict(payload,position_notes=payload['position_notes']*2))


def test_continuation_notes_reference_the_segment_fen_and_not_the_initial_board():
    payload=segment(PGN,2,1,'white')
    frames=positions(payload['pgn'])
    payload['position_notes']=[dict(ply=0,fen=frames[0]['fen'],text='Agora desenvolva uma peça.')]
    checked=validate('line',payload)
    assert checked['position_notes'][0]['fen']==positions(PGN)[2]['fen']
    assert positions(checked['pgn'])[1]['label']=='Após 2. Nf3'
