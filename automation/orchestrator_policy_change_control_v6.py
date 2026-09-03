#!/usr/bin/env python3
"""MULTIVERSE Automation Candidate Lane — policy change-control v6.

v6 adds a deterministic, no-external-effect classifier in front of future policy
rotation. It never applies a policy. A proposed change is classified as:
- NO_CHANGE
- CANDIDATE_REVIEW_REQUIRED for non-widening changes
- OWNER_GATE_REQUIRED for widening or protected-boundary changes

This is Candidate-only change-control evidence, not canonical policy authority.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from orchestrator_mvp_v2 import OrchestratorError, canonical_json, require
from orchestrator_role_relay_policy_v4 import CandidateBindingPolicy
from orchestrator_role_relay_policy_source_v5 import (
    REVIEWED_POLICY_MANIFEST_SHA256,
    ReviewedPolicySource,
)

CHANGE_CONTROL_BASELINE_SCHEMA = "MULTIVERSE_AUTOMATION_POLICY_CHANGE_CONTROL_BASELINE_v6"
CHANGE_CONTROL_DB_SCHEMA_VERSION = 4
CHANGE_CONTROL_BASELINE_BASENAME = "MULTIVERSE_AUTOMATION_POLICY_CHANGE_CONTROL_V6_BASELINE.json"
CHANGE_CONTROL_BASELINE_SHA256 = "0b37c5e962ad915ced8b1b58311d4a67957e33a57e09eef660d7da057bfb6686"
BASE_V5_REVIEWED_HEAD = "e803723309a045086287e613f924a90a880b5a3b"
BASE_V5_LAB_COMMENT_ID = 5523435184
BASE_V5_AUDITOR_COMMENT_ID = 5523829487
BASE_V5_CLOSURE_COMMENT_ID = 5523892150
BASE_CANONICAL_MAIN = "040d37f0a4e426cf2e119706484c90cbb48f0e56"
CANONICAL_REPO = "fufufu1116/multiverse-research"

NO_CHANGE = "NO_CHANGE"
CANDIDATE_REVIEW_REQUIRED = "CANDIDATE_REVIEW_REQUIRED"
OWNER_GATE_REQUIRED = "OWNER_GATE_REQUIRED"

_V5_POLICY_KEYS = {
    "schema_version", "source_branch", "canonical_main", "canonical_repo",
    "candidate_only", "authority", "allowed_bindings", "policy_id",
}
_V5_AUTHORITY_KEYS = {
    "canonical_adoption", "core_adoption", "keirin_adoption", "live_provider",
    "production", "runtime", "spend",
}
_BASELINE_AUTHORITY_KEYS = {
    "canonical_adoption", "core_adoption", "keirin_adoption", "live_provider",
    "main_mutation", "policy_apply", "policy_widen", "production", "runtime",
    "spend", "workflow_dispatch",
}


@dataclass(frozen=True)
class ChangeControlBaseline:
    raw_sha256: str
    canonical_json_text: str
    control_id: str
    canonical_main: str
    base_policy_manifest_sha256: str
    base_policy_id: str
    base_source_branch: str
    base_reviewed_head: str
    lab_comment_id: int
    auditor_comment_id: int
    closure_comment_id: int

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "ChangeControlBaseline":
        p = pathlib.Path(path)
        require(p.name == CHANGE_CONTROL_BASELINE_BASENAME, "CHANGE_CONTROL_BASELINE_BASENAME")
        require(p.exists() and p.is_file() and not p.is_symlink(), "CHANGE_CONTROL_BASELINE_FILE_CLASS")
        raw = p.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == CHANGE_CONTROL_BASELINE_SHA256, "CHANGE_CONTROL_BASELINE_SHA256")
        try:
            text = raw.decode("utf-8")
            doc = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OrchestratorError("CHANGE_CONTROL_BASELINE_JSON") from exc
        require(isinstance(doc, dict), "CHANGE_CONTROL_BASELINE_SHAPE")
        require(text == canonical_json(doc), "CHANGE_CONTROL_BASELINE_NOT_CANONICAL")
        require(doc.get("schema_version") == CHANGE_CONTROL_BASELINE_SCHEMA, "CHANGE_CONTROL_BASELINE_SCHEMA")
        require(doc.get("canonical_repo") == CANONICAL_REPO, "CHANGE_CONTROL_BASELINE_REPO")
        require(doc.get("canonical_main") == BASE_CANONICAL_MAIN, "CHANGE_CONTROL_BASELINE_MAIN")
        require(doc.get("candidate_only") is True, "CHANGE_CONTROL_BASELINE_CANDIDATE_ONLY")
        authority = doc.get("authority")
        require(isinstance(authority, dict) and set(authority) == _BASELINE_AUTHORITY_KEYS,
                "CHANGE_CONTROL_BASELINE_AUTHORITY_KEYS")
        for key in _BASELINE_AUTHORITY_KEYS:
            require(authority.get(key) is False, f"CHANGE_CONTROL_BASELINE_AUTHORITY_DENIED:{key}")
        base = doc.get("base_policy")
        require(isinstance(base, dict), "CHANGE_CONTROL_BASE_POLICY_SHAPE")
        required_base = {
            "manifest_sha256", "policy_id", "source_branch", "reviewed_head",
            "lab_comment_id", "auditor_comment_id", "closure_comment_id",
        }
        require(set(base) == required_base, "CHANGE_CONTROL_BASE_POLICY_KEYS")
        require(base["manifest_sha256"] == REVIEWED_POLICY_MANIFEST_SHA256,
                "CHANGE_CONTROL_BASE_POLICY_SHA")
        require(base["reviewed_head"] == BASE_V5_REVIEWED_HEAD, "CHANGE_CONTROL_BASE_HEAD")
        require(base["lab_comment_id"] == BASE_V5_LAB_COMMENT_ID, "CHANGE_CONTROL_BASE_LAB")
        require(base["auditor_comment_id"] == BASE_V5_AUDITOR_COMMENT_ID, "CHANGE_CONTROL_BASE_AUDITOR")
        require(base["closure_comment_id"] == BASE_V5_CLOSURE_COMMENT_ID, "CHANGE_CONTROL_BASE_CLOSURE")
        control_id = doc.get("control_id")
        require(isinstance(control_id, str) and 1 <= len(control_id) <= 128, "CHANGE_CONTROL_ID")
        return cls(
            digest, text, control_id, doc["canonical_main"],
            base["manifest_sha256"], base["policy_id"], base["source_branch"],
            base["reviewed_head"], base["lab_comment_id"], base["auditor_comment_id"],
            base["closure_comment_id"],
        )

    def verify_base_source(self, source: ReviewedPolicySource) -> None:
        require(isinstance(source, ReviewedPolicySource), "CHANGE_CONTROL_BASE_SOURCE_REQUIRED")
        require(source.raw_sha256 == self.base_policy_manifest_sha256, "CHANGE_CONTROL_BASE_SOURCE_SHA")
        require(source.policy_id == self.base_policy_id, "CHANGE_CONTROL_BASE_SOURCE_POLICY_ID")
        require(source.source_branch == self.base_source_branch, "CHANGE_CONTROL_BASE_SOURCE_BRANCH")
        require(source.canonical_main == self.canonical_main, "CHANGE_CONTROL_BASE_SOURCE_MAIN")


@dataclass(frozen=True)
class PolicyChangeDecision:
    classification: str
    proposed_sha256: str
    reasons: tuple[str, ...]
    may_apply: bool
    may_route_independent_review: bool
    owner_gate_required: bool

    def as_jsonable(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "proposed_sha256": self.proposed_sha256,
            "reasons": list(self.reasons),
            "may_apply": self.may_apply,
            "may_route_independent_review": self.may_route_independent_review,
            "owner_gate_required": self.owner_gate_required,
        }


def _binding_set(doc: dict[str, Any]) -> tuple[frozenset[tuple[str, str]] | None, list[str]]:
    reasons: list[str] = []
    raw = doc.get("allowed_bindings")
    if not isinstance(raw, list) or not raw:
        return None, ["BINDINGS_INVALID_OR_EMPTY"]
    pairs: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"domain", "candidate_branch"}:
            return None, ["BINDING_SHAPE_INVALID"]
        domain, branch = item.get("domain"), item.get("candidate_branch")
        if not isinstance(domain, str) or not isinstance(branch, str):
            return None, ["BINDING_TYPE_INVALID"]
        pairs.append((domain, branch))
    if len(set(pairs)) != len(pairs):
        reasons.append("DUPLICATE_BINDING")
    try:
        CandidateBindingPolicy.exact(doc.get("canonical_repo"), *pairs)
    except Exception:
        return None, sorted(set(reasons + ["BINDING_POLICY_INVALID"]))
    return frozenset(pairs), sorted(set(reasons))


def _source_branch_shape_valid(branch: Any) -> bool:
    if not isinstance(branch, str):
        return False
    try:
        CandidateBindingPolicy.exact(CANONICAL_REPO, ("automation-source", branch))
    except Exception:
        return False
    return True


def classify_policy_change(
    baseline: ChangeControlBaseline,
    base_source: ReviewedPolicySource,
    proposed_policy: dict[str, Any],
) -> PolicyChangeDecision:
    baseline.verify_base_source(base_source)
    if not isinstance(proposed_policy, dict):
        proposed_text = canonical_json({"invalid_proposed_type": type(proposed_policy).__name__})
        return PolicyChangeDecision(
            OWNER_GATE_REQUIRED,
            hashlib.sha256(proposed_text.encode()).hexdigest(),
            ("PROPOSED_POLICY_NOT_OBJECT",), False, False, True,
        )
    proposed_text = canonical_json(proposed_policy)
    proposed_sha = hashlib.sha256(proposed_text.encode()).hexdigest()
    reasons: list[str] = []

    if set(proposed_policy) != _V5_POLICY_KEYS:
        reasons.append("POLICY_KEY_SET_CHANGED")
    if proposed_policy.get("canonical_repo") != CANONICAL_REPO:
        reasons.append("CANONICAL_REPO_CHANGED")
    if proposed_policy.get("canonical_main") != baseline.canonical_main:
        reasons.append("CANONICAL_MAIN_CHANGED")
    if proposed_policy.get("candidate_only") is not True:
        reasons.append("CANDIDATE_ONLY_DISABLED")

    source_branch = proposed_policy.get("source_branch")
    if not _source_branch_shape_valid(source_branch):
        reasons.append("SOURCE_BRANCH_INVALID")
    policy_id = proposed_policy.get("policy_id")
    if not isinstance(policy_id, str) or not (1 <= len(policy_id) <= 128):
        reasons.append("POLICY_ID_INVALID")
    schema_version = proposed_policy.get("schema_version")
    if not isinstance(schema_version, str) or not (1 <= len(schema_version) <= 128):
        reasons.append("SCHEMA_VERSION_INVALID")

    authority = proposed_policy.get("authority")
    if not isinstance(authority, dict) or set(authority) != _V5_AUTHORITY_KEYS:
        reasons.append("AUTHORITY_KEY_SET_CHANGED")
    else:
        for key in sorted(_V5_AUTHORITY_KEYS):
            if authority.get(key) is not False:
                reasons.append(f"AUTHORITY_WIDENED:{key}")

    new_bindings, binding_reasons = _binding_set(proposed_policy)
    reasons.extend(binding_reasons)
    try:
        base_doc = json.loads(base_source.canonical_json_text)
    except json.JSONDecodeError as exc:
        raise OrchestratorError("CHANGE_CONTROL_BASE_SOURCE_JSON_IMPOSSIBLE") from exc
    old_bindings, old_reasons = _binding_set(base_doc)
    require(old_bindings is not None and not old_reasons, "CHANGE_CONTROL_BASE_BINDINGS_INVALID")

    protected = list(reasons)
    if new_bindings is None:
        protected.append("PROPOSED_BINDINGS_UNUSABLE")
    if protected:
        return PolicyChangeDecision(
            OWNER_GATE_REQUIRED, proposed_sha, tuple(sorted(set(protected))),
            False, False, True,
        )

    assert new_bindings is not None
    added = sorted(new_bindings - old_bindings)
    removed = sorted(old_bindings - new_bindings)
    if added:
        return PolicyChangeDecision(
            OWNER_GATE_REQUIRED, proposed_sha,
            tuple(["BINDING_WIDENED"] + [f"ADDED_BINDING:{d}:{b}" for d, b in added]),
            False, False, True,
        )

    identity_changed = any(
        proposed_policy.get(key) != base_doc.get(key)
        for key in ("schema_version", "source_branch", "policy_id")
    )
    if removed or identity_changed:
        detail = []
        if removed:
            detail.append("BINDING_SET_NARROWED")
        if identity_changed:
            detail.append("POLICY_IDENTITY_ROTATED")
        return PolicyChangeDecision(
            CANDIDATE_REVIEW_REQUIRED, proposed_sha, tuple(detail),
            False, True, False,
        )

    return PolicyChangeDecision(NO_CHANGE, proposed_sha, ("EXACT_POLICY_UNCHANGED",), False, False, False)


class PolicyChangeControlStore:
    """Durable idempotent decision journal. It never writes policy or repository state."""

    def __init__(self, path: pathlib.Path | str, baseline: ChangeControlBaseline,
                 base_source: ReviewedPolicySource) -> None:
        baseline.verify_base_source(base_source)
        self.path = str(path)
        self.baseline = baseline
        self.base_source = base_source
        self.conn = sqlite3.connect(self.path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=10000")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self._init_v6()

    def _init_v6(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL)")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS decisions(
                request_id TEXT PRIMARY KEY,
                proposed_sha256 TEXT NOT NULL,
                proposed_json TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )""")
            row = self.conn.execute("SELECT v FROM meta WHERE k='schema'").fetchone()
            if row is None:
                self.conn.execute("INSERT INTO meta(k,v) VALUES('schema',?)",
                                  (str(CHANGE_CONTROL_DB_SCHEMA_VERSION),))
            elif row[0] != str(CHANGE_CONTROL_DB_SCHEMA_VERSION):
                raise OrchestratorError("CHANGE_CONTROL_DB_SCHEMA_VERSION_MISMATCH")
            expected = {
                "change_control_baseline_sha256": self.baseline.raw_sha256,
                "change_control_baseline_json": self.baseline.canonical_json_text,
                "base_policy_source_sha256": self.base_source.raw_sha256,
                "base_policy_source_json": self.base_source.canonical_json_text,
            }
            rows = {r["k"]: r["v"] for r in self.conn.execute(
                "SELECT k,v FROM meta WHERE k IN (" + ",".join("?" for _ in expected) + ")",
                tuple(expected),
            ).fetchall()}
            if not rows:
                for key, value in expected.items():
                    self.conn.execute("INSERT INTO meta(k,v) VALUES(?,?)", (key, value))
            else:
                require(set(rows) == set(expected), "CHANGE_CONTROL_META_PARTIAL")
                for key, value in expected.items():
                    require(rows[key] == value, f"CHANGE_CONTROL_META_MISMATCH:{key}")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def decide(self, request_id: str, proposed_policy: dict[str, Any]) -> dict[str, Any]:
        require(isinstance(request_id, str) and 1 <= len(request_id) <= 128,
                "CHANGE_CONTROL_REQUEST_ID")
        proposed_json = canonical_json(proposed_policy)
        proposed_sha = hashlib.sha256(proposed_json.encode()).hexdigest()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT proposed_sha256,proposed_json,decision_json FROM decisions WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if row is not None:
                require(row["proposed_sha256"] == proposed_sha and row["proposed_json"] == proposed_json,
                        "CHANGE_REQUEST_REPLAY_CONFLICT")
                out = json.loads(row["decision_json"])
                self.conn.commit()
                return out
            decision = classify_policy_change(self.baseline, self.base_source, proposed_policy)
            out = decision.as_jsonable()
            decision_json = canonical_json(out)
            self.conn.execute(
                "INSERT INTO decisions(request_id,proposed_sha256,proposed_json,decision_json,created_at) VALUES(?,?,?,?,?)",
                (request_id, proposed_sha, proposed_json, decision_json, time.time()),
            )
            self.conn.commit()
            return out
        except Exception:
            self.conn.rollback()
            raise

    def close(self) -> None:
        self.conn.close()


class PolicyChangeControlWorker:
    """Replay-safe because it only classifies and journals; it cannot apply policy."""

    replay_safe = True

    def __init__(self, db_path: pathlib.Path | str, baseline_path: pathlib.Path | str,
                 base_policy_manifest_path: pathlib.Path | str) -> None:
        self.db_path = str(db_path)
        self.baseline_path = str(baseline_path)
        self.base_policy_manifest_path = str(base_policy_manifest_path)

    def run(self, request_id: str, proposed_policy: dict[str, Any]) -> dict[str, Any]:
        baseline = ChangeControlBaseline.load(self.baseline_path)
        source = ReviewedPolicySource.load(self.base_policy_manifest_path)
        store = PolicyChangeControlStore(self.db_path, baseline, source)
        try:
            return store.decide(request_id, proposed_policy)
        finally:
            store.close()
