"""Local implementation of the published Lichess accuracy method.

Reference: https://lichess.org/page/accuracy and lila AccuracyPercent.scala.
Engine evaluations are local, so these are not official site scores.
"""
import math
from statistics import pstdev


def move_accuracy(before, after):
    if after >= before:
        return 100.0
    return max(0.0, min(100.0, 103.1668100711649 * math.exp(
        -.04354415386753951 * (before-after)*100) - 3.166924740191411 + 1))


def game_accuracy(reviews, side):
    ordered = sorted(reviews, key=lambda r: r.ply)
    if not ordered or any(getattr(r, 'accuracy_before', None) is None or
                          getattr(r, 'accuracy_after', None) is None for r in ordered):
        return None
    first = ordered[0]
    chances = [100*(first.accuracy_before if first.side == 'Brancas' else 1-first.accuracy_before)]
    chances.extend(100*(r.accuracy_after if r.side == 'Brancas' else 1-r.accuracy_after) for r in ordered)
    width = max(2, min(8, len(ordered)//10))
    windows = [chances[:width]] * max(0, min(width, len(chances))-2)
    windows.extend(chances[start:start+width] for start in range(max(1, len(chances)-width+1)))
    weights = [max(.5, min(12, pstdev(window))) for window in windows]
    entries = [(move_accuracy(r.accuracy_before, r.accuracy_after), weights[index])
               for index, r in enumerate(ordered) if r.side == side]
    if not entries:
        return None
    weighted = sum(score*weight for score, weight in entries)/sum(weight for _, weight in entries)
    harmonic = 0 if any(score == 0 for score, _ in entries) else len(entries)/sum(1/score for score, _ in entries)
    return round((weighted+harmonic)/2, 1)
