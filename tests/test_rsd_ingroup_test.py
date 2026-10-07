"""Time-varying in-group rule and tone/vocabulary classifiers."""

import numpy as np

from scripts.analysis.rsd_ingroup_test import (
    cohens_d,
    effect_flag,
    keyword_tone,
    logistic_irls,
    mantel_haenszel_or,
    mantel_haenszel_rd,
    vocab_counts,
    walk_ingroup,
    walk_rolling,
)


def test_ingroup_uses_only_earlier_reviews_and_stays_unidentified_until_n():
    reviews = [(1.0, "a"), (2.0, "a"), (3.0, "b"), (4.0, "b"), (5.0, "c"), (6.0, "c")]
    flags, first, final, n_reviewers = walk_ingroup(
        reviews,
        [0.5, 2.5, 4.5, 5.0, 7.0],
        ["a", "a", "a", "a", "a"],
        top_n=2,
    )
    assert flags[0] is None  # no reviews yet
    assert flags[1] is None  # only "a" has reviewed
    assert flags[2] is True  # a and b, a is inside
    assert flags[3] is True  # review at t=5 is not yet counted
    assert flags[4] is False  # three people tied; login order drops "a"
    assert n_reviewers == 3
    assert set(final) == {"c", "b"}
    assert first["a"] == 4.5
    assert "c" in first


def test_same_timestamp_review_does_not_count():
    flags, _, _, _ = walk_ingroup(
        [(5.0, "a")],
        [5.0],
        ["a"],
        top_n=1,
    )
    assert flags == [None]


def test_nack_hedge_is_not_negative_and_vocab_skips_it():
    assert keyword_tone("Not a NACK, this looks fine") == 0.0
    assert keyword_tone("Concept NACK") == -1.0
    assert keyword_tone("ACK 0123abcd") == 1.0
    assert vocab_counts("not a nack")[4] == 0
    assert vocab_counts("This is a security concern and dangerous")[0] == 1
    assert vocab_counts("This is a security concern and dangerous")[5] == 1


def test_rolling_window_drops_reviews_older_than_the_trail():
    window = 100.0
    reviews = [(1.0, "a")] * 5 + [(150.0, "b")] * 5
    flags, first, top, _when = walk_rolling(
        reviews,
        [50.0, 160.0],
        ["a", "a"],
        top_n=1,
        window_sec=window,
    )
    assert flags[0] is True
    assert flags[1] is False
    assert top == ["b"]
    assert first["a"] == 50.0
    assert first["b"] == 160.0


def test_mantel_haenszel_pools_stratum_risk_differences():
    # equal strata: 8/10 vs 4/10, twice
    rd = mantel_haenszel_rd([(10, 8, 10, 4), (10, 8, 10, 4)])
    assert rd is not None
    assert abs(rd - 0.4) < 1e-9
    odd = mantel_haenszel_or([(10, 8, 10, 2)])
    assert odd is not None and odd > 1


def test_logistic_irls_recovers_a_positive_group_coefficient():
    rng = np.random.default_rng(0)
    group = np.array([0.0, 1.0] * 200)
    latent = -0.4 + 1.2 * group
    prob = 1 / (1 + np.exp(-latent))
    y = rng.random(group.size) < prob
    x_mat = np.column_stack([np.ones(group.size), group])
    beta = logistic_irls(x_mat, y.astype(float))
    assert beta is not None
    assert beta[1] > 0.5


def test_negligible_effect_flag():
    a = np.array([0.0, 1.0, 0.0, 1.0])
    b = np.array([1.0, 0.0, 1.0, 0.0])
    assert cohens_d(a, b) == 0.0
    assert effect_flag(0.19) == "negligible effect size regardless of p-value"
    assert effect_flag(0.2) == "small"
    assert effect_flag(None) == "effect size unavailable"
