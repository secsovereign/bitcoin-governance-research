"""Revealed rough consensus classifiers: NACK is not ACK; rationale vs bare NACK."""

from scripts.analysis.revealed_rough_consensus import (
    classify_text,
    nack_has_rationale,
    pr_consensus_vector,
    window_keys,
)


def test_window_keys_split_at_2016():
    assert window_keys("") == ("all_time",)
    assert window_keys("2015-12-31T23:59:59Z") == ("all_time", "before_2016")
    assert window_keys("2016-01-01T00:00:00Z") == ("all_time", "from_2016")
    assert window_keys("2022-01-01T00:00:00Z") == (
        "all_time",
        "from_2016",
        "from_2022",
    )


def test_nack_hedge_is_not_stance():
    from scripts.analysis.revealed_rough_consensus import nack_is_stance

    assert nack_is_stance("Not a NACK by any means") is False
    assert nack_is_stance("rebased and ready for nack/ack again") is False
    assert nack_is_stance("> NACK this\nI agree actually") is False
    assert nack_is_stance("Concept NACK until there is better rationale.") is True
    flags = classify_text("NACK this is unsafe")
    assert flags["nack"] is True
    assert flags["code_ack"] is False
    assert flags["concept_ack"] is False


def test_concept_ack_is_not_code_ack():
    flags = classify_text("Concept ACK to the goal.")
    assert flags["concept_ack"] is True
    assert flags["code_ack"] is False
    assert flags["nack"] is False


def test_code_ack_needs_commit():
    assert classify_text("ACK aabbccddee")["code_ack"] is True
    assert classify_text("ACK")["code_ack"] is False


def test_bare_nack_has_no_rationale():
    assert nack_has_rationale("NACK") is False
    assert nack_has_rationale("Concept NACK") is False
    assert nack_has_rationale(
        "NACK because this breaks IBD on low-memory nodes and the approach is untested"
    ) is True


def test_self_merge_zero_reviews_is_ack_none():
    vec = pr_consensus_vector(
        {
            "author": "fanquake",
            "merged_by": "fanquake",
            "merged": True,
            "state": "closed",
            "reviews": [],
            "comments": [],
            "files": [],
            "review_metrics": {"total_reviews": 0},
        }
    )
    assert vec["outcome"] == "merged"
    assert vec["self_merge"] is True
    assert vec["ack_source"] == "none"
    assert vec["at_least_one_merge_keys_ack"] is False
    assert vec["review_bucket"] == "zero"


def test_outsider_approved_is_cannot_merge_ack():
    vec = pr_consensus_vector(
        {
            "author": "someone-new",
            "merged_by": "fanquake",
            "merged": True,
            "state": "closed",
            "reviews": [
                {"author": "random-reviewer-xyz", "state": "APPROVED", "body": ""}
            ],
            "comments": [],
            "files": [],
            "review_metrics": {"total_reviews": 1},
        }
    )
    assert vec["ack_source"] == "cannot_merge_only"
    assert vec["has_code_ack"] is True
    assert vec["n_ack_cannot_merge"] == 1
    assert vec["at_least_one_merge_keys_ack"] is False


def test_peer_comments_count_as_observed_discussion():
    vec = pr_consensus_vector(
        {
            "number": 99,
            "author": "alice",
            "merged_by": "fanquake",
            "merged": True,
            "state": "closed",
            "reviews": [],
            "comments": [{"author": "bob", "body": "please rebase"}],
            "files": [],
            "review_metrics": {"total_reviews": 0},
        }
    )
    assert vec["review_bucket"] == "zero"
    assert vec["has_peer_github_comment"] is True
    assert vec["discussion_observed"] is True
    assert vec["github_zero_unobserved"] is False


def test_informal_mention_marks_observed():
    vec = pr_consensus_vector(
        {
            "number": 13947,
            "author": "alice",
            "merged_by": "fanquake",
            "merged": True,
            "reviews": [],
            "comments": [],
            "files": [],
            "review_metrics": {"total_reviews": 0},
        },
        informal_any={13947},
        informal_reviewish=set(),
    )
def test_author_ack_is_excluded():
    vec = pr_consensus_vector(
        {
            "author": "fanquake",
            "merged_by": "fanquake",
            "merged": True,
            "reviews": [{"author": "fanquake", "state": "APPROVED", "body": "ACK abcdef123456"}],
            "comments": [],
            "files": [],
            "review_metrics": {"total_reviews": 1},
        }
    )
    assert vec["ack_source"] == "none"
    assert vec["n_ack_merge_keys"] == 0
