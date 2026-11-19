import chess
import pytest
import classroom_materials as materials
import classroom_tactic_blocks as blocks
import classroom_trails as trails
from test_classroom_trails import room,add,candidate


def pack(count=10):
    entries=[]
    for square in list(chess.SQUARES)[8:8+count]:
        board=chess.Board('6rk/6pp/8/4N3/8/8/8/6K1 w - - 0 1');board.set_piece_at(square,chess.Piece(chess.PAWN,chess.WHITE))
        entries.append(dict(fen=board.fen(),solution=['e5f7'],source='Professor'))
    return dict(puzzles=entries,instructions='Encontre o mate.')


def assign(teacher,student,count=10,same_stage=True):
    draft=trails.load_draft(teacher,student)
    draft=add(teacher,student,draft,[dict(kind='tactic',title='Bloco',payload=pack(count),reviewed=True)])
    step=draft['steps'][0]['id'];block=draft['steps'][0]['items'][0]['id']
    draft=add(teacher,student,draft,[candidate('exam','Depois do bloco')],step if same_stage else None)
    trails.publish(teacher,student,draft['revision'])
    following=draft['steps'][-1]['items'][-1]['id']
    return block,following


def solve(token,identifier,fail_indices=()):
    payload,state=blocks.get_state(token,identifier)
    while state['index']<len(payload['puzzles']):
        board,moves,_=blocks.position(payload,state);index=state['index']
        if index in fail_indices:
            state,correct=blocks.act(token,identifier,index,state['ply'],'e5d3',board.fen())
            assert not correct
        state,correct=blocks.act(token,identifier,index,state['ply'],moves[state['ply']],board.fen())
        assert correct
    return state


def test_one_block_holds_many_puzzles_and_exactly_ninety_percent_unlocks_next_activity(room):
    teacher,student,pupil,_=room;identifier,following=assign(teacher,student)
    assert len(materials.list_materials(pupil))==1
    with pytest.raises(PermissionError):materials.submit_exam(pupil,following,[1])
    state=solve(pupil,identifier,[0])
    assert blocks.summary(pack(),state)['percent']==90 and state['passed']
    assert following in [entry['id'] for entry in materials.list_materials(pupil)]
    assert materials.submit_exam(pupil,following,[1])['score']==1
    with pytest.raises(ValueError):blocks.act(pupil,identifier,0,0,'e5f7',pack()['puzzles'][0]['fen'])


def test_below_ninety_blocks_next_stage_and_retry_cannot_erase_failed_exercises_mid_round(room):
    teacher,student,pupil,_=room;identifier,following=assign(teacher,student,same_stage=False)
    state=solve(pupil,identifier,[0,1])
    assert blocks.summary(pack(),state)['percent']==80 and not state['passed']
    assert trails.student_trail(pupil)[1]['blocked']
    assert trails.student_trail(pupil)[1]['reason']=='tactics'
    with pytest.raises(PermissionError):materials.submit_exam(pupil,following,[1])
    blocks.act(pupil,identifier,10,0,action='restart')
    state=solve(pupil,identifier)
    assert state['passed'] and len(state['history'])==2
    assert not trails.student_trail(pupil)[1]['blocked']
    blocks.act(pupil,identifier,10,0,action='restart')
    assert blocks.get_state(pupil,identifier)[1]['passed']


def test_skip_wrong_position_duplicates_and_other_professor_are_rejected(room):
    teacher,student,pupil,other=room;identifier,_=assign(teacher,student,2)
    with pytest.raises(PermissionError):blocks.get_state(other,identifier)
    with pytest.raises(PermissionError):blocks.act(teacher,identifier,0,0,action='restart')
    payload,state=blocks.get_state(pupil,identifier)
    with pytest.raises(ValueError):blocks.act(pupil,identifier,1,0,'e5f7',payload['puzzles'][0]['fen'])
    with pytest.raises(ValueError):blocks.act(pupil,identifier,0,0,'e5f7',chess.STARTING_FEN)
    state,_=blocks.act(pupil,identifier,0,0,action='skip')
    assert state['results']==[False]
    with pytest.raises(ValueError):materials.validate('tactic',dict(puzzles=[payload['puzzles'][0]]*2))
    with pytest.raises(ValueError):materials.validate('tactic',dict(puzzles=[]))
