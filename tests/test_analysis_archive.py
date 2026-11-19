from dataclasses import replace
import sqlite3
from types import SimpleNamespace
from io import StringIO
import chess.pgn
import pytest
import classroom as rooms
import analysis_archive as archive
from book_study import BookReference
from test_classroom import room
from test_analysis_summary import review

PGN='[White "Ana"]\n[Black "Bia"]\n\n1. e4 e5 *'


def result():
    return dict(reviews={1:review(),2:replace(review(2,'Pretas'),san='e5',uci='e7e5',white_cp=-30,accuracy_before=.55,accuracy_after=.45)},
        explanations={0:'Inicial',1:'Texto'},references={0:[BookReference('Livro','Citação','tema',('centro',))]},position=None,engine_name='Stockfish')


def test_archive_survives_logout_and_fresh_connection_with_all_evaluations(room):
    token,seat,other=room
    report=result();key=archive.save(token,PGN,report,ply=2,settings={'quality':'Profunda'},accuracies={'white':90})
    rooms.logout(token)
    token=rooms.login_professor('mestre','senha-segura-123',seat['teacher_key'])
    saved=archive.load(token,pgn=PGN)
    assert saved['reviews']==report['reviews'] and saved['references']==report['references']
    assert saved['explanations']==report['explanations'] and saved['ply']==2
    assert saved['settings']=={'quality':'Profunda'} and saved['accuracies']=={'white':90}
    assert archive.load(other,key) is None and archive.listing(other)==[]
    assert len(archive.listing(token))==1
    state=type('State',(dict,),dict(__getattr__=dict.__getitem__,__setattr__=dict.__setitem__))(game=PGN,analysis_generation=7)
    assert archive.restore(state,saved)
    assert state.loaded_analysis==(PGN,state.analysis_signature,7) and state.analysis_requested
    assert state.reviews[2].white_cp==-30


def test_standalone_fen_is_saved_and_new_position_has_no_old_result(room):
    token,_,_=room
    game=chess.pgn.Game();game.setup(chess.Board('8/8/5k2/8/5P2/8/5K2/8 w - - 0 40'))
    position=dict(engine_name='Stockfish',cp=120,mate=None,line='Kf3',result=None)
    report=dict(reviews={},explanations={0:'Final'},references={},position=position,engine_name='Stockfish')
    archive.save(token,str(game),report)
    assert archive.load(token,pgn=str(game))['position']==position
    game.setup(chess.Board())
    assert archive.load(token,pgn=str(game)) is None


def test_failed_partial_analysis_does_not_replace_saved_report(room):
    token,_,_=room
    archive.save(token,PGN,result())
    partial=result();partial['reviews'].pop(2)
    with pytest.raises(ValueError):archive.save(token,PGN,partial)
    assert len(archive.load(token,pgn=PGN)['reviews'])==2
    second=result();second['reviews'][1].white_cp=88
    archive.save(token,PGN,second)
    assert len(archive.listing(token))==1 and archive.load(token,pgn=PGN)['reviews'][1].white_cp==88
