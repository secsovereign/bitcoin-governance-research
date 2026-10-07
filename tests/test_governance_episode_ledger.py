"""Governance episode ledger schema: Intelligence-filled cells, no inferred objections, no identity store."""

from __future__ import annotations

import json

from src.utils.paths import get_analysis_dir, get_findings_dir

NACK_ALLOWED = {"unknown", "yes", "no", "partial"}
CONTEXT_ALLOWED = {"process", "technical", "ambiguous"}
CITE_SOURCES = {"github", "irc", "mail", "delving", "bips"}
EPISODE_IDS = {
    "blocksize-2015",
    "taproot-activation",
    "op-return-2024",
    "dandelion-pr13947",
    "utxo-commitments",
    "erlay",
    "bip-editor-dashjr",
    "kernel-extraction",
}
STALL_IDS = {
    "dandelion-pr13947",
    "utxo-commitments",
    "erlay",
    "wallet-node-split",
    "stratum-v2-native",
}
PHRASES = {
    "not the right venue",
    "work on Core first",
    "rough consensus",
    "off-list",
    "too risky",
    "needs more review",
    "breaks existing behavior",
}
EPISODE_KEYS = {
    "episode_id",
    "proposal",
    "venue",
    "technical_objections",
    "process_objections",
    "outcome",
    "corpus_cites",
    "existing_findings",
    "github_anchors",
}
STALL_KEYS = {
    "proposal",
    "episode_id",
    "first_proposed",
    "last_activity",
    "stated_reason_for_stall",
    "nack_exists",
    "nack_source",
    "corpus_cites",
    "existing_findings",
}
IDENTITY_STORE_KEYS = {
    "aliases",
    "email_aliases",
    "name_aliases",
    "nick_aliases",
    "display_names",
    "merge_key_holders",
    "person_role",
}
CONTRIBUTOR_KEYS = {
    "canonical_key",
    "github_handle",
    "episodes_involved",
    "episode_roles",
    "corpus_cites",
}
ROLES = {
    "technical-objector",
    "process-objector",
    "merger",
    "reviewer",
    "redirector",
}


def _load() -> dict:
    findings = get_findings_dir() / "data" / "governance_episode_ledger.json"
    analysis = get_analysis_dir() / "findings" / "data" / "governance_episode_ledger.json"
    left = json.loads(findings.read_text(encoding="utf-8"))
    right = json.loads(analysis.read_text(encoding="utf-8"))
    assert left == right
    return left


def _assert_cites(cites: list) -> None:
    for c in cites:
        assert c["source"] in CITE_SOURCES
        assert c["passage_id"]
        assert c["when"]


def test_pin_forbids_inference():
    pin = _load()["pin"].lower()
    assert "btcdecoded" in pin
    assert "not an identity store" in pin
    assert "not corpus_cites" in pin or "not substitutes" in pin


def test_required_episode_keys():
    data = _load()
    eps = data["episodes"]
    assert {e["episode_id"] for e in eps} == EPISODE_IDS
    for row in eps:
        assert EPISODE_KEYS <= set(row)
        assert "objection_source" not in row
        _assert_cites(row["corpus_cites"])
        for obj in row["technical_objections"] + row["process_objections"]:
            assert obj["cite"]
            assert obj["text"]
            assert obj["source"] in CITE_SOURCES


def test_kernel_is_child_of_wallet_node():
    kernel = next(e for e in _load()["episodes"] if e["episode_id"] == "kernel-extraction")
    assert kernel["parent_episode"] == "wallet-node-split"


def test_known_github_anchors_only():
    by_id = {e["episode_id"]: e for e in _load()["episodes"]}
    assert "bitcoin/bitcoin#13947" in by_id["dandelion-pr13947"]["github_anchors"]
    assert "bitcoin/bitcoin#21515" in by_id["erlay"]["github_anchors"]
    assert by_id["blocksize-2015"]["existing_findings"] == ["governance_timeline.json"]
    for row in by_id.values():
        for anchor in row["github_anchors"]:
            assert "/" in anchor and "#" in anchor


def test_agreement_stalls_no_full_rbf():
    stalls = _load()["agreement_stalls"]
    assert {s["episode_id"] for s in stalls} == STALL_IDS
    for row in stalls:
        assert STALL_KEYS <= set(row)
        assert row["nack_exists"] in NACK_ALLOWED
        if row["nack_exists"] == "yes":
            assert row["nack_source"]
            assert row["episode_id"] == "stratum-v2-native"
        else:
            assert row["nack_exists"] == "unknown"
        _assert_cites(row["corpus_cites"])
        label = f"{row['proposal']} {row['episode_id']}".lower()
        assert "full-rbf" not in label and "fullrbf" not in label and "mempoolfullrbf" not in label


def test_phrases_counts_stay_null():
    phrases = _load()["phrases"]
    assert {p["phrase"] for p in phrases} == PHRASES
    for row in phrases:
        assert row["context_type"] in CONTEXT_ALLOWED
        assert row["count"] is None
        _assert_cites(row["corpus_cites"])
        for eid in row["episode_ids"]:
            assert eid in EPISODE_IDS or eid in STALL_IDS


def test_contributors_join_not_identity():
    data = _load()
    assert data["contributor_schema"] == [
        "canonical_key",
        "github_handle",
        "episodes_involved",
        "episode_roles",
        "corpus_cites",
    ]
    assert "canonical_key" in data["contributor_schema"]
    for key in IDENTITY_STORE_KEYS:
        assert key not in data
        assert key not in data["contributor_schema"]
        for row in data["contributors"]:
            assert key not in row
    for row in data["contributors"]:
        assert CONTRIBUTOR_KEYS <= set(row)
        assert row["canonical_key"]
        assert row["episodes_involved"]
        assert set(row["episode_roles"]) <= ROLES
        _assert_cites(row["corpus_cites"])
        assert "thecharlatan" not in row["github_handle"].lower() or row["github_handle"] != "sedited"


def test_nack_exists_enum():
    data = _load()
    assert set(data["nack_exists_enum"]) == NACK_ALLOWED


def test_no_stalled_proposals_md_collision():
    findings = get_findings_dir()
    assert not (findings / "STALLED_PROPOSALS.md").exists()
    assert (findings / "data" / "governance_episode_ledger.json").exists()


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("ok", _name)
