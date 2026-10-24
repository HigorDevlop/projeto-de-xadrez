import chess
import chess.engine

from opening_initiative import choose_options,MAX_STYLE_LOSS_CP,analyse_options
from personal_openings import positions
from test_personal_openings import game


def info(board,uci,cp=0,mate=None,**extra):
    score=chess.engine.Mate(mate) if mate is not None else chess.engine.Cp(cp)
    return dict(pv=[chess.Move.from_uci(uci)],score=chess.engine.PovScore(score,board.turn),depth=20,**extra)


def test_an_active_alternative_must_stay_close_to_the_best_score():
    board=chess.Board();board.push_san('e4');board.push_san('e5')
    options=choose_options(board,[info(board,'g1f3',40),info(board,'f1c4',30),info(board,'d1h5',-160)],played='g1f3')
    assert options[0]['move']=='f1c4'
    assert all(item['loss_cp']<=MAX_STYLE_LOSS_CP for item in options)
    assert 'd1h5' not in [item['move'] for item in options]
    assert any(item['move']=='g1f3' for item in options)


def test_black_evaluation_is_compared_from_black_perspective():
    board=chess.Board();board.push_san('e4')
    entries=[info(board,'e7e5',40),info(board,'c7c5',30),info(board,'g8f6',-100)]
    options=choose_options(board,entries,played='e7e5')
    assert options[0]['move']=='c7c5'
    assert 'g8f6' not in [item['move'] for item in options]


def test_style_never_replaces_a_forced_mate_or_uses_a_bound_as_a_solid_comparison():
    board=chess.Board('7k/5K2/8/6Q1/8/8/8/8 w - - 0 1')
    options=choose_options(board,[info(board,'g5h5',mate=1),info(board,'g5g8',mate=1)])
    assert len(options)==1 and options[0]['kind']=='Principal do motor'
    board=chess.Board()
    options=choose_options(board,[info(board,'e2e4',50,lowerbound=True),info(board,'d2d4',45)])
    assert len(options)==1 and options[0]['move']=='e2e4'


def test_user_choices_are_counted_only_once_per_imported_game():
    one=game(url='one')
    rows=positions([one,one,game(url='two'),game('e4 e5 Bc4 Nc6 Nf3 Bc5',url='three')],'alice')
    row=next(row for row in rows if row['prefix']==['e2e4','e7e5'])
    assert row['played']=={'g1f3':2,'f1c4':1}
    assert row['count']==3


def test_a_played_move_outside_the_top_candidates_is_still_evaluated():
    board=chess.Board()
    class Engine:
        def __init__(self): self.requests=[]
        def analyse(self,position,limit,multipv=None,root_moves=None):
            self.requests.append(root_moves)
            if root_moves: return info(position,list(root_moves)[0].uci(),-80)
            return [info(position,'e2e4',30),info(position,'d2d4',25)]
    engine=Engine()
    options,played=analyse_options(engine,board,chess.engine.Limit(depth=20,time=.1),'a2a3')
    assert played['pv'][0].uci()=='a2a3'
    assert engine.requests[-1]==[chess.Move.from_uci('a2a3')]
    assert all(option['move']!='a2a3' for option in options)


def test_only_one_sound_move_is_not_presented_as_several_style_options():
    board=chess.Board()
    options=choose_options(board,[info(board,'e2e4',50),info(board,'a2a3',-100)],played='e2e4')
    assert len(options)==1
    assert options[0]['kind']=='Principal do motor'


def test_preparation_offers_a_real_alternative_to_the_users_habit(monkeypatch):
    import personal_openings
    monkeypatch.setattr(personal_openings,'find_engine',lambda:'local-test-engine')
    class Engine:
        id={'name':'Test Stockfish'}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def configure(self,options): pass
        def analyse(self,board,limit,multipv=None,root_moves=None):
            return [info(board,'g1f3',40),info(board,'f1c4',30),info(board,'d1h5',-100)]
    games=[game(url='one'),game(url='two')]
    plan=personal_openings.prepare('owner','alice',games,count=1,engine_factory=lambda *a,**kw:Engine())
    preferred=plan['personal_lines'][0]
    assert preferred['played_san']=='Nf3' and preferred['played_count']==2
    assert preferred['suggested_san']=='Bc4' and preferred['is_alternative']
    assert preferred['played_cp']==40 and preferred['candidate_cp']==30
    assert preferred['style_loss_cp']==10
    assert all(line['moves'][line['context_plies']]!='d1h5' for line in plan['personal_lines'])
