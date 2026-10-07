"""Unit checks for pass 5 gap closure. They do not load the pull-request corpus."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from scripts.analysis.first_year_signal_test import primary_subsystem, subsystem_of
from scripts.analysis.gap_closure_test import (
    apply_family_q,
    classify_false_negative_timeline,
    classify_subsystem_capacity,
    largest_decline,
    shannon_entropy,
    structure_gap,
    two_year_cohort,
)


def test_subsystem_mapping():
    assert subsystem_of("src/consensus/tx_check.cpp") == "consensus"
    assert subsystem_of("src/validation.cpp") == "consensus"
    assert subsystem_of("src/script/interpreter.cpp") == "consensus"
    assert subsystem_of("src/wallet/wallet.cpp") == "wallet"
    assert subsystem_of("src/net.cpp") == "p2p"
    assert subsystem_of("src/net_processing.cpp") == "p2p"
    assert subsystem_of("src/rpc/server.cpp") == "rpc"
    assert subsystem_of("src/qt/walletview.cpp") == "gui"
    assert subsystem_of("src/test/util_tests.cpp") == "test"
    assert subsystem_of("test/functional/wallet.py") == "test"
    assert subsystem_of("doc/release-notes.md") == "docs"
    assert subsystem_of("build-aux/m4/bitcoin_find_bdb48.m4") == "build"
    assert subsystem_of("src/node/blockstorage.cpp") == "core"
    assert primary_subsystem(["src/wallet/a.cpp", "src/wallet/b.cpp", "src/node/c.cpp"]) == "wallet"
    assert primary_subsystem(["src/wallet/a.cpp", "src/node/c.cpp"]) == "core"


def test_largest_decline_picks_the_biggest_drop():
    scores = {2010: 1.0, 2011: 0.2, 2012: 0.5, 2014: 0.1}
    found = largest_decline(scores)
    assert found["year"] == 2011
    assert found["score"] == 0.2
    assert found["score_year_before"] == 1.0
    assert found["score_year_after"] == 0.5
    assert largest_decline({2010: 1.0})["status"] == "DATA UNAVAILABLE"


def test_false_negative_classes():
    assert classify_false_negative_timeline(0.01, False, 0.1) == "STRUCTURAL"
    assert classify_false_negative_timeline(0.02, True, 0.10) == "DRIFT"
    assert classify_false_negative_timeline(0.02, True, 0.40) == "MIXED"
    assert classify_false_negative_timeline(-0.02, True, 0.1) == "STRUCTURAL"
    assert two_year_cohort(2011) == (2010, "2010-2011")
    assert two_year_cohort(2018) == (2018, "2018-2019")


def test_subsystem_capacity_classes():
    assert classify_subsystem_capacity(True, True, 0.04, 0.01) == "SUBSYSTEM CAPACITY"
    assert classify_subsystem_capacity(True, True, 0.04, 0.03) == "PARTIAL"
    assert classify_subsystem_capacity(True, False, 0.04, 0.01) == "NOT SUBSYSTEM CAPACITY"
    assert classify_subsystem_capacity(True, True, 0.04, 0.05) == "NOT SUBSYSTEM CAPACITY"
    assert classify_subsystem_capacity(False, True, 0.04, 0.01) == "NOT SUBSYSTEM CAPACITY"


def test_entropy_falls_when_concentrated():
    spread = shannon_entropy([10, 10, 10, 10])
    piled = shannon_entropy([37, 1, 1, 1])
    assert spread > piled


def test_missing_reviews_are_unavailable():
    info = {
        "has_reviews": False,
        "has_comment_authors": False,
        "has_comment_text": False,
        "has_participants": False,
        "has_meeting_list": False,
    }
    for effect_id in (
        "E2_reciprocity_excess",
        "E3_log_hours_to_next_same_direction_top5_minus_other",
        "E5_log_participants_on_log_days",
        "E7_first_tone_on_merge_given_later_tone",
        "E9_listed_on_log_days_to_merge",
        "E12_ingroup_on_no_peer_response",
    ):
        reason = structure_gap(effect_id, info)
        assert reason is not None
        assert reason.startswith("DATA UNAVAILABLE")


def test_bh_includes_a_pass5_test():
    prior = [{"id": "pass1.a", "p": 0.2, "in_bh_family": True, "source": "pass1"}]
    current = [{"id": "false_negative_rate_year_slope", "p": 0.001, "in_bh_family": True, "source": "pass5"}]
    family = apply_family_q(prior, [], [], current)
    assert len(family) == 2
    assert current[0]["q"] is not None
    assert current[0]["q"] < prior[0]["q"]


def test_low_power_spearman_flag():
    from scripts.analysis.gap_closure_test import spearman_with_ci

    rng = np.random.default_rng(7)
    x = np.arange(12, dtype=float)
    y = x + rng.normal(0, 0.1, 12)
    fit = spearman_with_ci(x, y, rng, 50)
    assert fit["low_power"] is True
    assert fit["n"] == 12
    assert fit["estimate"] is not None
    assert fit["ci95"] is not None


def test_gap_report_uses_the_pass5_results():
    import json
    from scripts.reporting.generate_from_templates import ctx_commons, ctx_gap, ctx_trajectory
    from scripts.reporting.pass_validation import validate_all
    from scripts.reporting.template_engine import render_file
    from scripts.reporting.generate_from_templates import TEMPLATES

    data = project_root / "findings" / "data"
    gap = json.loads((data / "gap_closure_analysis.json").read_text())
    text = render_file(TEMPLATES / "GAP_CLOSURE.md.tpl", ctx_gap(gap))
    assert "{{" not in text
    assert "{%" not in text
    assert "STRUCTURAL" in text
    assert "NOT SUBSYSTEM CAPACITY" in text
    assert "P6 conflict resolution" in text
    assert "DATA UNAVAILABLE" in text
    assert "LOW POWER" in text
    p1 = json.loads((data / "rsd_ingroup_analysis.json").read_text())
    p2 = json.loads((data / "rsd_ingroup_analysis_v2.json").read_text())
    p3 = json.loads((data / "commons_dynamics_analysis.json").read_text())
    p4 = json.loads((data / "first_year_signal_analysis.json").read_text())
    bundle = validate_all(p1, p2, p3, p4)
    commons = render_file(TEMPLATES / "COMMONS_MECHANISMS.md.tpl", ctx_commons(p3, bundle["confirmed_effects"], gap))
    trajectory = render_file(
        TEMPLATES / "FIRST_YEAR_TRAJECTORY.md.tpl",
        ctx_trajectory(p4, bundle["trajectory_rows"], gap),
    )
    assert "q=0.005" in commons or "q=0.003" in commons
    assert "DATA UNAVAILABLE" in commons
    assert "0.014" in trajectory
    assert "STRUCTURAL" in trajectory
    assert "percentage points per year" in trajectory


if __name__ == "__main__":
    test_subsystem_mapping()
    test_largest_decline_picks_the_biggest_drop()
    test_false_negative_classes()
    test_subsystem_capacity_classes()
    test_entropy_falls_when_concentrated()
    test_missing_reviews_are_unavailable()
    test_bh_includes_a_pass5_test()
    test_low_power_spearman_flag()
    test_gap_report_uses_the_pass5_results()
    print("gap closure tests passed")
