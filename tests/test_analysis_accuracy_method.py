import math
from types import SimpleNamespace
import pytest
from analysis_accuracy import move_accuracy,game_accuracy


def test_published_move_curve_and_uncertainty_bonus():
    assert move_accuracy(.5,.5)==100
    assert move_accuracy(.4,.6)==100
    expected=103.1668100711649*math.exp(-.04354415386753951*10)-3.166924740191411+1
    assert move_accuracy(.6,.5)==pytest.approx(expected)


def test_consecutive_evaluations_color_and_harmonic_aggregation():
    rows=[SimpleNamespace(ply=1,side='Brancas',accuracy_before=.5,accuracy_after=.4),
          SimpleNamespace(ply=2,side='Pretas',accuracy_before=.6,accuracy_after=.5),
          SimpleNamespace(ply=3,side='Brancas',accuracy_before=.5,accuracy_after=.5)]
    score=move_accuracy(.5,.4)
    weighted=(score*5+100*.5)/5.5
    harmonic=2/(1/score+1/100)
    assert game_accuracy(rows,'Brancas')==round((weighted+harmonic)/2,1)
    assert game_accuracy(rows,'Pretas')==round(score,1)
    assert game_accuracy(rows[::-1],'Brancas')==game_accuracy(rows,'Brancas')
    assert game_accuracy([],'Brancas') is None
