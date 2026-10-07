"""The four pass reports may only say what the stored estimates support."""

import json
from pathlib import Path

from scripts.reporting.pass_validation import trajectory_rows, validate_all

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "findings" / "data"


def _load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_all_methodology_checks_hold():
    result = validate_all(
        _load("rsd_ingroup_analysis.json"),
        _load("rsd_ingroup_analysis_v2.json"),
        _load("commons_dynamics_analysis.json"),
        _load("first_year_signal_analysis.json"),
    )
    failed = [row["claim"] for row in result["checks"] if row["status"] != "holds"]
    assert failed == []
    assert result["n_checks"] >= 12


def test_confirmed_commons_effects_are_e_ids_only():
    result = validate_all(
        _load("rsd_ingroup_analysis.json"),
        _load("rsd_ingroup_analysis_v2.json"),
        _load("commons_dynamics_analysis.json"),
        _load("first_year_signal_analysis.json"),
    )
    ids = [row["id"] for row in result["confirmed_effects"]]
    assert ids
    assert all(str(item).startswith("E") for item in ids)
    assert not any(str(item).startswith("T") for item in ids)


def test_first_year_irc_rate_is_not_a_lead_contrast_and_reciprocity_d_is_flagged():
    rows = {row["id"]: row for row in trajectory_rows(_load("first_year_signal_analysis.json"))}
    assert rows["S1"]["usable"] is False
    assert "Do not cite" in rows["S1"]["note"]
    assert rows["S4"]["usable"] is True
    assert "small-cell" in rows["S4"]["note"]
    assert rows["S3_count"]["usable"] is False
    assert rows["T1b"]["usable"] is True
    assert "outlier" in rows["T1b"]["note"]
    assert rows["T1c"]["usable"] is False
