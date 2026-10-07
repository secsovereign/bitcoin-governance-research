"""Scoring direction, disjoint measurements, reciprocity, and BH correction."""

import numpy as np

from scripts.analysis.commons_dynamics_test import (
    SCORING_SPEC,
    assert_measurement_sets_disjoint,
    bh_qvalues,
    dnm_accommodation,
    jargon_hit,
    metric_ids,
    normalize_values,
    reciprocity_index,
)


def test_measurement_sets_are_disjoint():
    assert_measurement_sets_disjoint()
    health = metric_ids("C")
    principles = metric_ids("B")
    effects = metric_ids("A")
    assert health and principles and effects
    assert health.isdisjoint(principles)
    assert health.isdisjoint(effects)
    assert principles.isdisjoint(effects)
    assert "H4_gini_merges" in health
    assert "P2a_gini_provision_ratio" in principles
    assert "H4_gini_merges" != "P2a_gini_provision_ratio"


def test_scoring_spec_directions_are_fixed():
    assert SCORING_SPEC["H6_median_days_to_decision"]["direction"] == "lower_better"
    assert SCORING_SPEC["P4a_self_merge_rate"]["direction"] == "lower_better"
    assert SCORING_SPEC["P4c_nonmaintainer_review_share"]["direction"] == "higher_better"
    assert SCORING_SPEC["E1"]["maps"] == ["P1", "P2"]
    assert SCORING_SPEC["E12"]["maps"] == []
    assert SCORING_SPEC["P5a_sanction_events"]["scored"] is False
    assert SCORING_SPEC["H7_exit_rate"]["part"] == "C"
    assert SCORING_SPEC["P6c_exit_channels"]["part"] == "B"


def test_lower_better_flips_the_scale():
    scaled = normalize_values([1.0, 3.0, None], higher_better=False)
    assert scaled[0] == 1.0
    assert scaled[1] == 0.0
    assert scaled[2] is None


def test_benjamini_hochberg_orders_q_above_p():
    q = bh_qvalues([0.001, 0.04, 0.2])
    assert q[0] <= q[1] <= q[2]
    assert q[0] >= 0.001
    assert q[2] <= 1


def test_reciprocity_requires_the_reverse_inside_the_window():
    day = 86400.0
    reviewer = np.array([0, 1])
    author = np.array([1, 0])
    # The earlier review is reciprocated; the later one's reverse is already in the past.
    assert reciprocity_index(reviewer, author, np.array([0.0, 10 * day])) == 0.5
    assert reciprocity_index(reviewer, author, np.array([0.0, 40 * day])) == 0.0


def test_jargon_matches_house_terms_not_acknowledge():
    assert jargon_hit("concept ACK")
    assert jargon_hit("please rebase and squash")
    assert jargon_hit("utACK")
    assert not jargon_hit("I acknowledge the point")


def test_accommodation_is_higher_when_the_speaker_mirrors():
    partner = np.array([[1, 0], [1, 0], [0, 1], [0, 1]], dtype=bool)
    speaker = np.array([[1, 0], [1, 0], [0, 0], [0, 0]], dtype=bool)
    mirrored = dnm_accommodation(partner, speaker)
    speaker_off = np.array([[0, 1], [0, 1], [1, 0], [1, 0]], dtype=bool)
    opposed = dnm_accommodation(partner, speaker_off)
    assert mirrored is not None and opposed is not None
    assert mirrored > opposed
