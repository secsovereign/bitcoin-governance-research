#!/usr/bin/env python3
"""Unit tests for author_prep / substance / engagement scoring (Phase 1 plan)."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.pr_quality import (  # noqa: E402
    AUTHOR_PREP_HIGH,
    author_prep_band,
    author_prep_score,
    contribution_quality_score,
    engagement_score,
    size_substance_score,
    touches_tests,
)


def _pr(**kwargs):
    base = {
        "body": "",
        "files": [],
        "merged": False,
        "complexity": {"total_changes": 0, "files_changed": 0},
        "review_metrics": {"total_reviews": 0},
    }
    base.update(kwargs)
    return base


def test_author_prep_no_review_or_merge_or_loc():
    small = _pr(body="x" * 600, files=[{"filename": "src/foo.cpp"}], complexity={"total_changes": 5})
    huge = _pr(
        body="x" * 600,
        files=[{"filename": "src/foo.cpp"}],
        complexity={"total_changes": 50000},
        review_metrics={"total_reviews": 20},
        merged=True,
    )
    assert author_prep_score(small) == author_prep_score(huge)
    assert author_prep_score(small) == 0.40  # body only


def test_author_prep_tests_and_ceiling():
    p = _pr(
        body="x" * 600,
        files=[{"filename": "src/test/foo_tests.cpp"}],
        review_metrics={"total_reviews": 99},
        merged=True,
        complexity={"total_changes": 99999},
    )
    assert touches_tests(p)
    assert author_prep_score(p) == 0.80
    assert author_prep_score(p) <= 0.80


def test_author_prep_body_bands_monotonic():
    scores = [
        author_prep_score(_pr(body="")),
        author_prep_score(_pr(body="x" * 51)),
        author_prep_score(_pr(body="x" * 201)),
        author_prep_score(_pr(body="x" * 501)),
    ]
    assert scores == sorted(scores)
    assert scores == [0.0, 0.10, 0.25, 0.40]


def test_touches_tests_structured_not_contest():
    assert not touches_tests(_pr(files=[{"filename": "doc/contest_notes.md"}]))
    assert touches_tests(_pr(files=[{"filename": "src/test/util.cpp"}]))
    assert touches_tests(_pr(files=[{"filename": "test/functional/feature_foo.py"}]))


def test_substance_grows_with_size_not_called_quality():
    tiny = _pr(complexity={"total_changes": 10, "files_changed": 1})
    big = _pr(complexity={"total_changes": 2000, "files_changed": 12})
    assert size_substance_score(big) > size_substance_score(tiny)
    assert size_substance_score(tiny) == contribution_quality_score(tiny, include_merged=False)


def test_engagement_uses_reviews_not_merge():
    cold = _pr(review_metrics={"total_reviews": 0}, merged=True, body="x" * 600)
    hot = _pr(review_metrics={"total_reviews": 3}, merged=False)
    assert engagement_score(hot) > engagement_score(cold)


def test_author_prep_band_thresholds():
    assert author_prep_band(0.0) == "none"
    assert author_prep_band(0.50) == "mid_high"
    assert author_prep_band(AUTHOR_PREP_HIGH) == "high"
    assert author_prep_band(0.80) == "high"


def test_path_risk_and_concept_ack():
    from src.utils.pr_quality import consensus_ack_flags, has_nontrivial_test_diff, path_risk_band

    assert path_risk_band(_pr(files=[{"filename": "src/consensus/tx_verify.cpp"}])) == (
        "consensus_sensitive"
    )
    assert path_risk_band(_pr(files=[{"filename": "src/net_processing.cpp"}])) == "networking"
    assert path_risk_band(_pr(files=[{"filename": "doc/README.md"}])) == "other"
    flags = consensus_ack_flags(
        _pr(comments=[{"body": "Concept ACK on the approach"}], reviews=[])
    )
    assert flags["has_concept_or_approach_ack"]
    assert has_nontrivial_test_diff(
        _pr(files=[{"filename": "src/test/foo_tests.cpp", "additions": 25}])
    )
    assert not has_nontrivial_test_diff(
        _pr(files=[{"filename": "src/test/foo_tests.cpp", "additions": 2}])
    )


if __name__ == "__main__":
    test_author_prep_no_review_or_merge_or_loc()
    test_author_prep_tests_and_ceiling()
    test_author_prep_body_bands_monotonic()
    test_touches_tests_structured_not_contest()
    test_substance_grows_with_size_not_called_quality()
    test_engagement_uses_reviews_not_merge()
    test_author_prep_band_thresholds()
    test_path_risk_and_concept_ack()
    print("ok")
