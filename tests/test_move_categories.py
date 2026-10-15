"""Public move-rating contract and the annotations a reader sees in PGN."""
from io import StringIO

import chess
import chess.pgn
import pytest

from chess_review import CATEGORIES, MoveReview, canonical_category, classify, export_review


EXPECTED_CATEGORIES = (
    ('brilliant', 'Brilhante', '♞✧'),
    ('best', 'Melhor', '♛◇'),
    ('excellent', 'Excelente', '♜◈'),
    ('good', 'Bom', '♝⋄'),
    ('inaccuracy', 'Imprecisão', '♟⌁'),
    ('mistake', 'Erro', '♚⨯'),
    ('blunder', 'Capivorada', '♟‼'),
)


def rating(**overrides):
    values = dict(in_book=False, is_best=False, sacrifice=False,
                  best_expected=.8, played_expected=.8)
    values.update(overrides)
    return classify(**values)


def relative_luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= .04045
              else ((channel + .055) / 1.055) ** 2.4 for channel in channels]
    return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))


def test_seven_categories_have_distinct_readable_markers():
    assert [(key, category.label, category.symbol) for key, category in CATEGORIES.items()] == list(EXPECTED_CATEGORIES)
    assert len({category.symbol for category in CATEGORIES.values()}) == 7
    assert len({category.color.lower() for category in CATEGORIES.values()}) == 7
    for category in CATEGORIES.values():
        light, dark = sorted((relative_luminance(category.color),
                              relative_luminance(category.ink)), reverse=True)
        assert (light + .05) / (dark + .05) >= 4.5, category.label


def test_all_seven_ratings_can_be_reached_from_analysis():
    examples = {
        'brilliant': dict(sacrifice=True, played_expected=.79, second_expected=.7, rating=800),
        'best': dict(is_best=True, second_expected=.79),
        'excellent': dict(played_expected=.79),
        'good': dict(played_expected=.77),
        'inaccuracy': dict(played_expected=.73),
        'mistake': dict(played_expected=.65),
        'blunder': dict(played_expected=.5),
    }
    assert {name: rating(**values) for name, values in examples.items()} == {
        name: name for name in examples
    }


@pytest.mark.parametrize('second_expected', [None, .79, .6])
def test_equal_score_alternative_is_not_mislabeled_as_engine_choice(second_expected):
    assert rating(is_best=False, second_expected=second_expected) == 'excellent'


@pytest.mark.parametrize('second_expected,expected', [
    (None, 'best'), (.60001, 'best'), (.6, 'brilliant'), (.59999, 'brilliant'),
])
def test_brilliant_forcing_choice_requires_a_clear_tenth_point_gap(second_expected, expected):
    assert rating(is_best=True, best_expected=.7, played_expected=.7,
                  second_expected=second_expected) == expected


@pytest.mark.parametrize('loss,expected', [
    (.01999, 'excellent'), (.02, 'good'), (.04999, 'good'),
    (.05, 'inaccuracy'), (.09999, 'inaccuracy'), (.1, 'mistake'),
    (.2, 'mistake'), (.20001, 'blunder'),
])
def test_expected_point_loss_boundaries(loss, expected):
    assert rating(played_expected=.8 - loss) == expected
    # Even an engine-choice flag cannot hide a recorded loss of evaluation.
    assert rating(is_best=True, played_expected=.8 - loss) == expected


def test_brilliant_sacrifice_rule_keeps_rating_tolerance():
    example = dict(played_expected=.781, second_expected=.7, rating=800)
    assert rating(sacrifice=True, **example) == 'brilliant'
    assert rating(sacrifice=False, **example) == 'excellent'
    assert rating(sacrifice=True, **{**example, 'rating': 2400}) == 'excellent'
    assert rating(sacrifice=True, **{**example, 'second_expected': None}) == 'excellent'
    assert rating(sacrifice=True, best_expected=.5, played_expected=.49,
                  second_expected=.3, rating=800) == 'excellent'


@pytest.mark.parametrize('example', [
    dict(is_best=True, second_expected=.6),
    dict(sacrifice=True, played_expected=.79, second_expected=.7, rating=800),
])
def test_genial_and_brilliant_now_produce_one_rating(example):
    result = rating(**example)
    assert result == 'brilliant'
    assert result != 'great'
    assert 'great' not in CATEGORIES


def test_legacy_great_category_maps_to_brilliant_without_changing_other_ratings():
    assert canonical_category('great') == 'brilliant'
    for category in CATEGORIES:
        assert canonical_category(category) == category


@pytest.mark.parametrize('in_book,missed_opportunity', [(True, False), (False, True), (True, True)])
def test_book_and_missed_opportunity_are_context_not_extra_ratings(in_book, missed_opportunity):
    context = dict(in_book=in_book, missed_opportunity=missed_opportunity)
    assert rating(is_best=True, **context) == 'best'
    assert rating(played_expected=.65, **context) == 'mistake'
    assert rating(played_expected=.5, **context) == 'blunder'


def test_export_preserves_game_and_shows_every_rating():
    game = chess.pgn.read_game(StringIO(
        '[Event "Estudo anotado"]\n\n'
        '1. e4! {Comentário do leitor.} (1. d4 d5) e5 '
        '2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 *'
    ))
    original = str(game)
    reviews = []
    for ply, (node, (category, _, _)) in enumerate(zip(game.mainline(), EXPECTED_CATEGORIES), 1):
        reviews.append(MoveReview(
            ply=ply, number=str((ply + 1) // 2), side='Brancas' if ply % 2 else 'Pretas',
            san=node.san(), uci=node.move.uci(), category=category, loss=0,
            white_cp=20 + ply, white_mate=None, best_san=node.san(), line='',
            sources=[], explanation=f'Explicação do lance {ply}.',
        ))

    exported = chess.pgn.read_game(StringIO(export_review(game, reviews)))
    assert not exported.errors
    assert exported.headers['Event'] == 'Estudo anotado'
    assert list(exported.mainline_moves()) == list(game.mainline_moves())
    assert exported.variations[1].move == chess.Move.from_uci('d2d4')
    assert 'Comentário do leitor.' in exported.variations[0].comment
    assert chess.pgn.NAG_GOOD_MOVE in exported.variations[0].nags
    for ply, (node, (_, label, symbol)) in enumerate(zip(exported.mainline(), EXPECTED_CATEGORIES), 1):
        assert f'{label} {symbol}.' in node.comment
        assert f'Explicação do lance {ply}.' in node.comment
        assert node.eval().white().score() == 20 + ply
    assert str(game) == original


def test_export_of_legacy_genial_review_uses_merged_brilliant_label():
    game = chess.pgn.read_game(StringIO('1. e4 {Anotação anterior.} e5 *'))
    review = MoveReview(1, '1', 'Brancas', 'e4', 'e2e4', 'great', 0, 20, None,
                        'e4', '', [], 'Melhor continuação isolada.')
    exported = chess.pgn.read_game(StringIO(export_review(game, [review])))
    comment = exported.variations[0].comment
    assert 'Brilhante ♞✧.' in comment
    assert 'GENIAL' not in comment
    assert 'Anotação anterior.' in comment
    assert review.category == 'great'
