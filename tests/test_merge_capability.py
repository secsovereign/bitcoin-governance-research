"""Merge keys vs roster vs cannot-merge. Zero as merger is lack of keys."""

from src.utils.maintainers import (
    ROLE_CANNOT_MERGE,
    ROLE_MERGE_KEYS,
    ROLE_ROSTER_WITHOUT_KEYS,
    cannot_merge,
    has_merge_keys,
    load_maintainer_login_set,
    load_merge_capability,
    person_role,
)


def test_capability_pin_and_counts():
    data = load_merge_capability()
    assert "cannot merge" in data["pin"].lower()
    assert data["counts"]["unique_mergers"] == len(data["merge_key_holders"])
    assert data["counts"]["unique_mergers"] >= 20


def test_fanquake_has_merge_keys():
    assert person_role("fanquake") == ROLE_MERGE_KEYS
    assert has_merge_keys("fanquake")
    assert not cannot_merge("fanquake")


def test_jgarzik_has_keys_but_is_not_on_roster():
    assert person_role("jgarzik") == ROLE_MERGE_KEYS
    assert "jgarzik" not in load_maintainer_login_set()


def test_roster_without_keys_is_not_cannot_merge():
    assert person_role("instagibbs") == ROLE_ROSTER_WITHOUT_KEYS
    assert person_role("thecharlatan") == ROLE_ROSTER_WITHOUT_KEYS
    assert not has_merge_keys("instagibbs")
    assert not cannot_merge("instagibbs")


def test_ordinary_reviewer_cannot_merge():
    assert person_role("some-random-reviewer") == ROLE_CANNOT_MERGE
    assert cannot_merge("some-random-reviewer")
    assert not has_merge_keys("some-random-reviewer")
