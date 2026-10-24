"""Independent regression positions for the game-review evaluation pipeline."""
from io import StringIO
from threading import Event

import chess
import chess.engine
import chess.pgn
import pytest

from chess_review import classify, sacrifice_in_line
from stockfish_analysis import compare_move, review_chances, analyse_with_books, find_engine


def info(move, cp, color=chess.WHITE, **extras):
    return dict(score=chess.engine.PovScore(chess.engine.Cp(cp), color),
                pv=[chess.Move.from_uci(move)], **extras)


def test_chance_curve_is_symmetric_and_does_not_treat_won_positions_as_equal():
    equal = review_chances(info('e2e4',0), chess.WHITE)
    assert equal == .5
    assert review_chances(info('e2e4',200),chess.WHITE) == pytest.approx(
        1-review_chances(info('e2e4',200),chess.BLACK))
    equal_loss = equal-review_chances(info('e2e4',-300),chess.WHITE)
    winning_loss = review_chances(info('e2e4',1000),chess.WHITE)-review_chances(info('e2e4',700),chess.WHITE)
    assert equal_loss > .2 and winning_loss < .05
    # Review uses the same published curve even when engine self-play WDL is extreme.
    assert review_chances(info('e2e4',0,wdl=chess.engine.PovWdl(chess.engine.Wdl(1000,0,0),chess.WHITE)),chess.WHITE) == equal


@pytest.mark.parametrize('final_cp,expected', [(-10,'excellent'),(-400,'blunder')])
def test_important_loss_is_rechecked_and_can_be_downgraded(final_cp, expected):
    class Engine:
        calls=[]
        def analyse(self, board, limit, **kwargs):
            self.calls.append((limit,kwargs))
            return [info('e2e4',0), info('d2d4',-400 if len(self.calls)==1 else final_cp)]
    engine=Engine()
    best,played,_=compare_move(engine,chess.Board(),chess.Move.from_uci('d2d4'),
                               chess.engine.Limit(depth=12,time=.08),Event())
    assert len(engine.calls)==2
    budget,options=engine.calls[-1]
    assert budget.depth>12 and budget.time>.08
    assert options['multipv']==2
    assert set(options['root_moves'])=={chess.Move.from_uci('e2e4'),chess.Move.from_uci('d2d4')}
    assert classify(in_book=False,is_best=False,sacrifice=False,
                    best_expected=review_chances(best,chess.WHITE),
                    played_expected=review_chances(played,chess.WHITE))==expected


def test_played_second_candidate_reuses_same_search_instead_of_separate_score():
    class Engine:
        calls=0
        def analyse(self, board, limit, **kwargs):
            self.calls+=1
            return [info('e2e4',20),info('d2d4',15)]
    engine=Engine()
    compare_move(engine,chess.Board(),chess.Move.from_uci('d2d4'),
                 chess.engine.Limit(depth=12,time=.08),Event())
    assert engine.calls==1


def test_later_piece_loss_is_not_attributed_to_current_move():
    original=chess.Board('6k1/8/7p/8/4N3/8/8/R3K3 w - - 0 1')
    probe=original.copy()
    pv=[]
    for san in ['Ra2','Kh7','Ng5+','hxg5','Ra3','g4','Ra4']:
        move=probe.parse_san(san);pv.append(move);probe.push(move)
    assert not sacrifice_in_line(original,pv)


@pytest.mark.parametrize('in_book,second,played', [(True,.7,.8),(False,.96,.98),(False,.7,.78)])
def test_known_book_moves_already_winning_alternatives_and_loss_are_not_brilliant(in_book,second,played):
    assert classify(in_book=in_book,is_best=True,sacrifice=True,
                    best_expected=max(.8,played),played_expected=played,
                    second_expected=second)!='brilliant'


@pytest.mark.skipif(not find_engine(),reason='Stockfish not installed')
def test_real_engine_opening_and_fools_mate_have_sensible_labels():
    opening=chess.pgn.read_game(StringIO('1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *'))
    reviews=analyse_with_books(opening,find_engine(),quality='Rápida')['reviews']
    assert not any(r.category in {'brilliant','blunder'} for r in reviews.values())
    game=chess.pgn.read_game(StringIO('1. f3 e5 2. g4 Qh4#'))
    reviews=analyse_with_books(game,find_engine(),quality='Rápida')['reviews']
    assert reviews[3].category=='blunder'
    assert reviews[4].category=='best'
    assert reviews[4].white_mate==0
    assert all(0<=r.played_expected<=r.best_expected<=1 for r in reviews.values())


@pytest.mark.parametrize('color',[chess.WHITE,chess.BLACK])
@pytest.mark.parametrize('mate,expected',[(1,0),(3,2),(-2,-2)])
def test_mate_distance_is_for_position_after_the_reviewed_move(color,mate,expected):
    from stockfish_analysis import score_after_move
    result=score_after_move({'score':chess.engine.PovScore(chess.engine.Mate(mate),color)},color)
    assert result.pov(color).mate()==expected
    assert (result.pov(color).score(mate_score=100000)>0)==(mate>0)


def test_uncatalogued_root_is_compared_against_best_in_one_search():
    class Engine:
        calls=[]
        def analyse(self,board,limit,**kwargs):
            self.calls.append(kwargs)
            if 'root_moves' not in kwargs:
                return [info('e2e4',20),info('d2d4',15)]
            return [info('e2e4',20),info('g1f3',10)]
    engine=Engine()
    best,played,second=compare_move(engine,chess.Board(),chess.Move.from_uci('g1f3'),
                                   chess.engine.Limit(depth=12,time=.08),Event())
    assert len(engine.calls)==2 and engine.calls[1]['multipv']==2
    assert played['pv'][0]==chess.Move.from_uci('g1f3')
    assert best['pv'][0]==chess.Move.from_uci('e2e4')
    assert second is None  # a restricted search is not the global second choice


def test_piece_given_for_pawn_is_a_sacrifice_but_balanced_exchange_is_not():
    original=chess.Board('6k1/7p/8/8/8/3B4/8/R3K3 w - - 0 1')
    probe=original.copy();pv=[]
    for san in ['Bxh7+','Kxh7','Ra2','Kg6','Ra3']:
        move=probe.parse_san(san);pv.append(move);probe.push(move)
    assert sacrifice_in_line(original,pv)
    original=chess.Board('6k1/7b/8/8/8/3B4/8/R3K3 w - - 0 1')
    probe=original.copy();pv=[]
    for san in ['Bxh7+','Kxh7','Ra2','Kg6','Ra3']:
        move=probe.parse_san(san);pv.append(move);probe.push(move)
    assert not sacrifice_in_line(original,pv)


def test_sacrifice_requires_a_new_global_search_before_brilliant_label():
    board=chess.Board('6k1/7p/8/8/8/3B4/8/R3K3 w - - 0 1')
    probe=board.copy();pv=[]
    for san in ['Bxh7+','Kxh7','Ra2','Kg6','Ra3']:
        move=probe.parse_san(san);pv.append(move);probe.push(move)
    class Engine:
        calls=[]
        def analyse(self,position,limit,**kwargs):
            self.calls.append((limit,kwargs))
            return [dict(score=chess.engine.PovScore(chess.engine.Cp(100),chess.WHITE),pv=pv),
                    info('a1a2',0)]
    engine=Engine()
    best,played,second=compare_move(engine,board,pv[0],chess.engine.Limit(depth=12,time=.08),Event())
    assert len(engine.calls)==2
    assert 'root_moves' not in engine.calls[1][1]
    assert engine.calls[1][0].time>.08
    assert classify(in_book=False,is_best=True,sacrifice=sacrifice_in_line(board,played['pv']),
                    best_expected=review_chances(best,chess.WHITE),
                    played_expected=review_chances(played,chess.WHITE),second_expected=second)=='brilliant'
