"""Unit checks for the first-year signal decomposition. No corpus load."""

import numpy as np

from scripts.analysis.first_year_signal_test import (
    apply_family_q,
    block_matrix,
    classify_decomposition,
    is_bugfix,
    is_consensus_path,
    jargon_hit,
    pooled_cohens_d,
    residual_gap,
)


def test_consensus_paths():
    assert is_consensus_path("src/consensus/params.cpp")
    assert is_consensus_path("src/validation.cpp")
    assert is_consensus_path("src/script/interpreter.cpp")
    assert is_consensus_path("src/primitives/transaction.cpp")
    assert not is_consensus_path("src/wallet/wallet.cpp")
    assert not is_consensus_path("src/validation.h")


def test_bugfix_title_and_label_only():
    assert is_bugfix("Fix crash in wallet", [])
    assert is_bugfix("Add a descriptor", ["bug"])
    assert not is_bugfix("Add a descriptor", [])
    assert not is_bugfix("prefix the log line", [])
    assert not is_bugfix("refactor fixture loading", [])


def test_jargon_is_house_terms_not_rebase_or_acknowledge():
    assert jargon_hit("concept ACK")
    assert jargon_hit("approach ACK")
    assert jargon_hit("utACK deadbeef")
    assert jargon_hit("tACK")
    assert jargon_hit("ACK")
    assert jargon_hit("nit: rename this")
    assert not jargon_hit("please rebase")
    assert not jargon_hit("I acknowledge the comment")
    assert not jargon_hit("squash the commits")


def test_pooled_d_drops_a_one_sided_cohort_cell():
    # 2016 has both groups. 2017 is G1 only and must not enter the pooled d.
    values = np.array([0.0, 0.4, 2.0, 2.4, 9.0, 9.5])
    group = np.array([0.0, 0.0, 1.0, 1.0, 1.0, 1.0])
    cohort = np.array([2016, 2016, 2016, 2016, 2017, 2017])
    both = pooled_cohens_d(values[:4], group[:4], cohort[:4])
    with_onesided = pooled_cohens_d(values, group, cohort)
    assert both is not None and both > 1
    assert with_onesided == both


def test_residual_gap_closes_when_t_explains_the_outcome():
    rng = np.random.default_rng(1)
    technical = np.concatenate([
        rng.normal(0.0, 1.0, 20), rng.normal(3.0, 1.0, 20),
        rng.normal(0.0, 1.0, 20), rng.normal(3.0, 1.0, 20),
    ])
    outcome = technical + rng.normal(0.0, 0.05, technical.size)
    cohort = np.array([2016] * 40 + [2017] * 40, dtype=float)
    group = np.array([0.0] * 20 + [1.0] * 20 + [0.0] * 20 + [1.0] * 20)
    rows = [{"year": int(year), "T": float(value)} for year, value in zip(cohort, technical)]
    x_mat, _, names = block_matrix(rows, ["T"])
    assert "T" in names
    raw = pooled_cohens_d(outcome, group, cohort)
    after = residual_gap(outcome, group, cohort, x_mat)
    assert raw is not None and raw > 1
    assert after is not None and abs(after) < 0.05


def test_decision_rules():
    technical = classify_decomposition(0.80, 0.30, 0.70, 0.25)
    assert technical["verdict"] == "technical"
    social = classify_decomposition(0.80, 0.70, 0.30, 0.25)
    assert social["verdict"] == "social"
    both = classify_decomposition(0.80, 0.50, 0.50, 0.10)
    assert both["verdict"] == "both"
    unexplained = classify_decomposition(0.80, 0.50, 0.50, 0.30)
    assert unexplained["verdict"] == "unexplained"
    redundant = classify_decomposition(0.80, 0.20, 0.20, 0.15)
    assert redundant["verdict"] == "redundant"
    assert redundant["technical_rule_matches"] and redundant["social_rule_matches"]
    assert "UNEXPLAINED VARIANCE" in unexplained["text"]
    assert "prior reputation outside the repo" in unexplained["text"]


def test_bh_family_includes_pass4_and_pass3():
    prior = [{"id": "pass1.gap", "p": 0.40, "in_bh_family": True, "source": "pass1"}]
    pass3 = [{"id": "pass3.E5", "p": 0.20, "in_bh_family": True, "source": "pass3"}]
    tests = [
        {"id": "T1c", "p": 0.001, "in_bh_family": True, "source": "pass4"},
        {"id": "gap_raw", "p": 0.001, "in_bh_family": False, "source": "pass4"},
    ]
    family = apply_family_q(prior, pass3, tests)
    ids = {row["id"] for row in family}
    assert "T1c" in ids
    assert "pass3.E5" in ids
    assert "gap_raw" not in ids
    t1 = next(row for row in tests if row["id"] == "T1c")
    assert t1["q"] < 0.05
    assert tests[1]["q"] is None
