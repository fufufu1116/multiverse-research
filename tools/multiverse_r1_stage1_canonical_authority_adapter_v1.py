#!/usr/bin/env python3
"""Read-only canonical authorization/decision/trusted-time adapter for Stage 1.

Pre-activation candidate only. This module NEVER mints authorization decisions,
grants, Owner Gates, revocation state, Safe Mode state, or canonical authority.
It can consume only a separately accepted, immutable authority manifest that is
pinned by a separately verified activation receipt. If that source/receipt is
missing or unverifiable, construction/use fails closed and Runtime stays OFF.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from multiverse_r1_auth_v1 import AuthorizationRuntime
from multiverse_r1_stage1_runtime_v1 import (
    AUTH_KEYS,
    ENQUEUE_FIELDS,
    ENQUEUE_OPERATION,
    ENQUEUE_SCHEMA,
    ENQUEUE_SCOPE,
    ENQUEUE_TARGET,
    STAGE_ID,
    TrustedAuthorizationBundle,
    seal_authorization_bundle,
)

CANONICAL_REPO = "fufufu1116/multiverse-research"
REMOTE_NAME = "origin"
AUTHORITY_MANIFEST_SCHEMA = "MULTIVERSE_R1_STAGE1_CANONICAL_AUTHORITY_MANIFEST_v1"
ACCEPTED_AUTHORITY_STATUS = "ACCEPTED_CANONICAL_STAGE1_AUTHORITY_SNAPSHOT"
AUTHORITY_SCOPE = "R1_LIMITED_INTERNAL_RUNTIME_STAGE1"
TRUSTED_CLOCK_SOURCE = "GITHUB_API_SERVER_DATE_HEADER"
MAX_AUTHORITY_BUNDLES = 25

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_FIELDS = {
    "schema_version", "status", "canonical_authority", "authority_scope",
    "canonical_main", "policy_generation", "policy_digest",
    "revocation_generation", "safe_mode_generation", "safe_mode_active",
    "valid_grant_refs", "trusted_clock_source", "bundles",
}
BUNDLE_FIELDS = {
    "bundle_id", "envelope_digest", "enqueue_actor_role",
    "enqueue_actor_instance", "worker_actor_role", "worker_actor_instance",
    "enqueue_decision", "operation_decisions", "decision_payload_digest",
}


class CanonicalAuthorityDenied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise CanonicalAuthorityDenied(code)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _envelope_digest(envelope: Mapping[str, Any]) -> str:
    return _sha256_json(envelope)


def _decision_digest(enqueue_decision: Mapping[str, Any], operation_decisions: Mapping[str, Any]) -> str:
    return _sha256_json({"enqueue": enqueue_decision, "operations": operation_decisions})


def _safe_manifest_path(path: str) -> str:
    if not _nonempty(path):
        _deny("AUTHORITY_MANIFEST_PATH_MISSING")
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        _deny("AUTHORITY_MANIFEST_PATH_TRAVERSAL")
    normalized = str(p)
    if not normalized.startswith("governance/"):
        _deny("AUTHORITY_MANIFEST_MUST_BE_GOVERNANCE_PATH")
    return normalized


def _validate_envelope_shape(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, dict) or set(envelope) != ENQUEUE_FIELDS:
        _deny("AUTHORITY_ENQUEUE_SCHEMA")
    if envelope["schema_version"] != ENQUEUE_SCHEMA or envelope["stage_id"] != STAGE_ID:
        _deny("AUTHORITY_ENQUEUE_IDENTITY")
    for field in ("candidate_id", "docs_hash", "worker_id", "verdict_reason"):
        if not _nonempty(envelope[field]):
            _deny("AUTHORITY_ENQUEUE_STRING")
    if not isinstance(envelope["evidence_refs"], list) or not all(_nonempty(x) for x in envelope["evidence_refs"]):
        _deny("AUTHORITY_ENQUEUE_EVIDENCE")


@dataclass(frozen=True)
class VerifiedCanonicalAuthorityAnchor:
    """Facts loaded from a separately reviewed immutable activation receipt.

    The boolean below is not itself a production receipt verifier. A separate,
    independently reviewed immutable-receipt loader must construct this object.
    """

    activation_receipt_ref: str
    activation_receipt_sha256: str
    canonical_main: str
    authority_manifest_commit: str
    authority_manifest_path: str
    authority_manifest_blob_sha: str
    authority_manifest_sha256: str
    authority_manifest_status: str
    authority_scope: str
    policy_generation: str
    policy_digest: str
    revocation_generation: int
    safe_mode_generation: int
    trusted_clock_source: str
    verified_from_immutable_activation_receipt: bool

    def validate(self) -> None:
        if self.verified_from_immutable_activation_receipt is not True:
            _deny("AUTHORITY_ANCHOR_NOT_FROM_VERIFIED_ACTIVATION_RECEIPT")
        if not _nonempty(self.activation_receipt_ref):
            _deny("AUTHORITY_ANCHOR_RECEIPT_REF_MISSING")
        if not _HEX64.fullmatch(self.activation_receipt_sha256):
            _deny("AUTHORITY_ANCHOR_RECEIPT_DIGEST_INVALID")
        for value in (self.canonical_main, self.authority_manifest_commit, self.authority_manifest_blob_sha):
            if not _HEX40.fullmatch(value):
                _deny("AUTHORITY_ANCHOR_GIT_ID_INVALID")
        if self.authority_manifest_commit != self.canonical_main:
            _deny("AUTHORITY_MANIFEST_MUST_BE_IN_ACTIVATION_CANONICAL_MAIN")
        _safe_manifest_path(self.authority_manifest_path)
        if not _HEX64.fullmatch(self.authority_manifest_sha256):
            _deny("AUTHORITY_MANIFEST_SHA256_INVALID")
        if self.authority_manifest_status != ACCEPTED_AUTHORITY_STATUS:
            _deny("AUTHORITY_ANCHOR_STATUS_NOT_ACCEPTED")
        if self.authority_scope != AUTHORITY_SCOPE:
            _deny("AUTHORITY_ANCHOR_SCOPE_MISMATCH")
        if not _nonempty(self.policy_generation) or not _nonempty(self.policy_digest):
            _deny("AUTHORITY_ANCHOR_POLICY_IDENTITY_MISSING")
        if not _strict_int(self.revocation_generation) or not _strict_int(self.safe_mode_generation):
            _deny("AUTHORITY_ANCHOR_GENERATION_INVALID")
        if self.trusted_clock_source != TRUSTED_CLOCK_SOURCE:
            _deny("AUTHORITY_ANCHOR_TRUSTED_CLOCK_SOURCE_MISMATCH")


class CanonicalAuthorityDecisionAdapter:
    """Consumes accepted immutable decisions; never issues or widens authority."""

    def __init__(self, repo_root: Path | str, *, anchor: VerifiedCanonicalAuthorityAnchor):
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            _deny("AUTHORITY_REPO_NOT_GIT_WORKTREE")
        if not isinstance(anchor, VerifiedCanonicalAuthorityAnchor):
            _deny("AUTHORITY_ANCHOR_TYPE")
        anchor.validate()
        self.anchor = anchor
        self._validate_origin()

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            ["git", "-C", str(self.repo_root), *args], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy(),
        )
        if check and proc.returncode != 0:
            raise CanonicalAuthorityDenied(
                "AUTHORITY_GIT_COMMAND_FAILED:" + " ".join(args[:3]) + ":" + proc.stderr.strip()[:240]
            )
        return proc

    @staticmethod
    def _accepted_origin_urls() -> set[str]:
        return {
            f"https://github.com/{CANONICAL_REPO}",
            f"https://github.com/{CANONICAL_REPO}.git",
        }

    @staticmethod
    def _assert_no_transport_override(config_rows: str, environ: Mapping[str, str]) -> None:
        for key in ("GIT_SSH", "GIT_SSH_COMMAND"):
            if environ.get(key):
                _deny("AUTHORITY_SSH_TRANSPORT_OVERRIDE_PROHIBITED")
        for line in config_rows.splitlines():
            lower = line.lower()
            if "url." in lower and (".insteadof=" in lower or ".pushinsteadof=" in lower):
                _deny("AUTHORITY_GIT_URL_REWRITE_PROHIBITED")
            if "core.sshcommand=" in lower:
                _deny("AUTHORITY_SSH_TRANSPORT_OVERRIDE_PROHIBITED")

    def _validate_origin(self) -> None:
        fetch_urls = [
            x.strip() for x in self._git("remote", "get-url", "--all", REMOTE_NAME).stdout.splitlines()
            if x.strip()
        ]
        accepted = self._accepted_origin_urls()
        if not fetch_urls or any(x not in accepted for x in fetch_urls):
            _deny("AUTHORITY_FETCH_ORIGIN_IDENTITY_MISMATCH")
        configs = self._git("config", "--show-origin", "--list", check=False)
        if configs.returncode != 0:
            _deny("AUTHORITY_GIT_CONFIG_QUERY_FAILED")
        self._assert_no_transport_override(configs.stdout, os.environ)

    def _fresh_main(self) -> str:
        self._validate_origin()
        proc = self._git("ls-remote", "--refs", REMOTE_NAME, "refs/heads/main")
        rows = [line.split("\t", 1) for line in proc.stdout.splitlines() if line.strip()]
        exact = [sha for sha, ref in rows if ref == "refs/heads/main"]
        if len(exact) != 1 or not _HEX40.fullmatch(exact[0]):
            _deny("AUTHORITY_CANONICAL_MAIN_UNAVAILABLE")
        return exact[0]

    def _load_manifest_text(self) -> str:
        a = self.anchor
        self._validate_origin()
        self._git("fetch", "--no-tags", REMOTE_NAME, "refs/heads/main")
        fetched = self._git("rev-parse", "FETCH_HEAD").stdout.strip()
        if fetched != a.authority_manifest_commit:
            _deny("AUTHORITY_MANIFEST_COMMIT_NOT_CURRENT_MAIN")
        blob = self._git("rev-parse", f"{a.authority_manifest_commit}:{a.authority_manifest_path}").stdout.strip()
        if blob != a.authority_manifest_blob_sha:
            _deny("AUTHORITY_MANIFEST_BLOB_MISMATCH")
        shown = self._git("show", f"{a.authority_manifest_commit}:{a.authority_manifest_path}").stdout
        if hashlib.sha256(shown.encode("utf-8")).hexdigest() != a.authority_manifest_sha256:
            _deny("AUTHORITY_MANIFEST_CONTENT_DIGEST_MISMATCH")
        return shown

    @staticmethod
    def _parse_github_date_header(text: str) -> datetime:
        values = [
            line.split(":", 1)[1].strip() for line in text.splitlines()
            if line.lower().startswith("date:")
        ]
        if len(values) != 1:
            _deny("AUTHORITY_TRUSTED_CLOCK_DATE_HEADER_MISSING_OR_AMBIGUOUS")
        try:
            dt = parsedate_to_datetime(values[0])
        except Exception as exc:
            raise CanonicalAuthorityDenied("AUTHORITY_TRUSTED_CLOCK_DATE_HEADER_INVALID") from exc
        if dt.tzinfo is None:
            _deny("AUTHORITY_TRUSTED_CLOCK_NOT_OFFSET_AWARE")
        return dt.astimezone(timezone.utc)

    def _github_trusted_now(self) -> datetime:
        if shutil.which("gh") is None:
            _deny("AUTHORITY_GH_CLI_REQUIRED_FOR_TRUSTED_CLOCK")
        proc = subprocess.run(
            ["gh", "api", "--include", "-H", "Accept: application/vnd.github+json", f"/repos/{CANONICAL_REPO}"],
            cwd=str(self.repo_root), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=os.environ.copy(),
        )
        if proc.returncode != 0:
            raise CanonicalAuthorityDenied(
                "AUTHORITY_GITHUB_TRUSTED_CLOCK_UNAVAILABLE:" + proc.stderr.strip()[:200]
            )
        return self._parse_github_date_header(proc.stdout)

    def _validate_manifest(self, value: Any) -> dict:
        a = self.anchor
        if not isinstance(value, dict) or set(value) != MANIFEST_FIELDS:
            _deny("AUTHORITY_MANIFEST_SCHEMA")
        if value["schema_version"] != AUTHORITY_MANIFEST_SCHEMA:
            _deny("AUTHORITY_MANIFEST_IDENTITY")
        if value["status"] != ACCEPTED_AUTHORITY_STATUS or value["canonical_authority"] is not True:
            _deny("AUTHORITY_MANIFEST_NOT_ACCEPTED_CANONICAL")
        if value["authority_scope"] != AUTHORITY_SCOPE or value["authority_scope"] != a.authority_scope:
            _deny("AUTHORITY_MANIFEST_SCOPE_MISMATCH")
        if value["canonical_main"] != a.canonical_main:
            _deny("AUTHORITY_MANIFEST_CANONICAL_MAIN_MISMATCH")
        if value["policy_generation"] != a.policy_generation or value["policy_digest"] != a.policy_digest:
            _deny("AUTHORITY_MANIFEST_POLICY_IDENTITY_MISMATCH")
        if value["revocation_generation"] != a.revocation_generation:
            _deny("AUTHORITY_MANIFEST_REVOCATION_GENERATION_MISMATCH")
        if value["safe_mode_generation"] != a.safe_mode_generation:
            _deny("AUTHORITY_MANIFEST_SAFE_MODE_GENERATION_MISMATCH")
        if not isinstance(value["safe_mode_active"], bool):
            _deny("AUTHORITY_MANIFEST_SAFE_MODE_INVALID")
        if value["trusted_clock_source"] != TRUSTED_CLOCK_SOURCE:
            _deny("AUTHORITY_MANIFEST_TRUSTED_CLOCK_SOURCE_MISMATCH")
        grants = value["valid_grant_refs"]
        if not isinstance(grants, list) or not all(_nonempty(x) for x in grants) or len(set(grants)) != len(grants):
            _deny("AUTHORITY_MANIFEST_GRANTS_INVALID")
        bundles = value["bundles"]
        if not isinstance(bundles, list) or not (1 <= len(bundles) <= MAX_AUTHORITY_BUNDLES):
            _deny("AUTHORITY_MANIFEST_BUNDLE_COUNT_INVALID")
        seen_ids: set[str] = set()
        seen_envelopes: set[str] = set()
        for bundle in bundles:
            if not isinstance(bundle, dict) or set(bundle) != BUNDLE_FIELDS:
                _deny("AUTHORITY_MANIFEST_BUNDLE_SCHEMA")
            if not _nonempty(bundle["bundle_id"]) or bundle["bundle_id"] in seen_ids:
                _deny("AUTHORITY_MANIFEST_BUNDLE_ID_INVALID")
            if not _HEX64.fullmatch(bundle["envelope_digest"]) or bundle["envelope_digest"] in seen_envelopes:
                _deny("AUTHORITY_MANIFEST_ENVELOPE_DIGEST_INVALID")
            seen_ids.add(bundle["bundle_id"])
            seen_envelopes.add(bundle["envelope_digest"])
            for field in ("enqueue_actor_role", "enqueue_actor_instance", "worker_actor_role", "worker_actor_instance"):
                if not _nonempty(bundle[field]):
                    _deny("AUTHORITY_MANIFEST_ACTOR_IDENTITY_INVALID")
            if not isinstance(bundle["enqueue_decision"], dict):
                _deny("AUTHORITY_MANIFEST_ENQUEUE_DECISION_INVALID")
            operations = bundle["operation_decisions"]
            if not isinstance(operations, dict) or set(operations) != AUTH_KEYS:
                _deny("AUTHORITY_MANIFEST_OPERATION_DECISIONS_INVALID")
            digest = _decision_digest(bundle["enqueue_decision"], operations)
            if bundle["decision_payload_digest"] != digest:
                _deny("AUTHORITY_MANIFEST_DECISION_DIGEST_MISMATCH")
            if bundle["enqueue_decision"].get("actor_role") != bundle["enqueue_actor_role"]:
                _deny("AUTHORITY_MANIFEST_ENQUEUE_ACTOR_ROLE_MISMATCH")
            if bundle["enqueue_decision"].get("actor_instance") != bundle["enqueue_actor_instance"]:
                _deny("AUTHORITY_MANIFEST_ENQUEUE_ACTOR_INSTANCE_MISMATCH")
            for decision in operations.values():
                if not isinstance(decision, dict):
                    _deny("AUTHORITY_MANIFEST_OPERATION_DECISION_INVALID")
                if decision.get("actor_role") != bundle["worker_actor_role"]:
                    _deny("AUTHORITY_MANIFEST_WORKER_ACTOR_ROLE_MISMATCH")
                if decision.get("actor_instance") != bundle["worker_actor_instance"]:
                    _deny("AUTHORITY_MANIFEST_WORKER_ACTOR_INSTANCE_MISMATCH")
        return copy.deepcopy(value)

    def _load_manifest(self) -> dict:
        text = self._load_manifest_text()
        try:
            value = json.loads(text)
        except Exception as exc:
            raise CanonicalAuthorityDenied("AUTHORITY_MANIFEST_JSON_INVALID") from exc
        return self._validate_manifest(value)

    def issue_authorization_bundle(
        self, *, current_main: str, envelope: Mapping[str, Any]
    ) -> TrustedAuthorizationBundle:
        _validate_envelope_shape(envelope)
        a = self.anchor
        a.validate()
        remote_main = self._fresh_main()
        if current_main != remote_main or current_main != a.canonical_main:
            _deny("AUTHORITY_CURRENT_MAIN_MISMATCH")
        manifest = self._load_manifest()
        digest = _envelope_digest(envelope)
        matches = [b for b in manifest["bundles"] if b["envelope_digest"] == digest]
        if len(matches) != 1:
            _deny("AUTHORITY_ENVELOPE_NOT_PREISSUED_OR_AMBIGUOUS")
        selected = copy.deepcopy(matches[0])
        if envelope["worker_id"] != selected["worker_actor_instance"]:
            _deny("AUTHORITY_WORKER_BINDING_MISMATCH")

        trusted_now = self._github_trusted_now()
        if self._fresh_main() != current_main:
            _deny("AUTHORITY_MAIN_DRIFT_DURING_DECISION_LOAD")

        grants = frozenset(manifest["valid_grant_refs"])
        enqueue_runtime = AuthorizationRuntime(
            policy_generation=manifest["policy_generation"],
            policy_digest=manifest["policy_digest"],
            revocation_generation=manifest["revocation_generation"],
            safe_mode_generation=manifest["safe_mode_generation"],
            now=trusted_now,
            actor_role=selected["enqueue_actor_role"],
            actor_instance=selected["enqueue_actor_instance"],
            valid_grant_refs=grants,
            expected_owner_gate_ref=None,
            safe_mode_active=manifest["safe_mode_active"],
        )
        worker_runtime = AuthorizationRuntime(
            policy_generation=manifest["policy_generation"],
            policy_digest=manifest["policy_digest"],
            revocation_generation=manifest["revocation_generation"],
            safe_mode_generation=manifest["safe_mode_generation"],
            now=trusted_now,
            actor_role=selected["worker_actor_role"],
            actor_instance=selected["worker_actor_instance"],
            valid_grant_refs=grants,
            expected_owner_gate_ref=None,
            safe_mode_active=manifest["safe_mode_active"],
        )
        provenance = (
            f"git:{a.authority_manifest_commit}:{a.authority_manifest_path}"
            f"#blob={a.authority_manifest_blob_sha}#sha256={a.authority_manifest_sha256}"
        )
        bundle = TrustedAuthorizationBundle(
            enqueue_decision=copy.deepcopy(selected["enqueue_decision"]),
            operation_decisions=copy.deepcopy(selected["operation_decisions"]),
            enqueue_runtime=enqueue_runtime,
            worker_runtime=worker_runtime,
            canonical_main=current_main,
            provenance_ref=provenance,
            decision_payload_digest=selected["decision_payload_digest"],
            verified_from_canonical_authority=True,
            decisions_verified_from_canonical_policy=True,
        )
        seal_authorization_bundle(bundle, envelope=envelope, current_main=current_main)
        return bundle


def _task_id(candidate_id: str, docs_hash: str) -> str:
    idem = f"source-review:{candidate_id}:{docs_hash}"
    encoded = json.dumps(idem, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "task-" + hashlib.sha256(encoded).hexdigest()[:16]


def _decision(
    *, decision_id: str, policy_generation: str, policy_digest: str,
    actor_role: str, actor_instance: str, operation: str, target: str,
    scope: str, grant_ref: str, revocation_generation: int,
    safe_mode_generation: int,
) -> dict:
    return {
        "authorization_decision_id": decision_id,
        "policy_generation": policy_generation,
        "policy_digest": policy_digest,
        "actor_role": actor_role,
        "actor_instance": actor_instance,
        "operation": operation,
        "target": target,
        "permission_class_requested": "P1_REVERSIBLE_INTERNAL_WRITE",
        "permission_ceiling": "P1_REVERSIBLE_INTERNAL_WRITE",
        "scope": {"operation": operation, "target": target, "data_exposure_scope": scope},
        "data_exposure_scope": scope,
        "issued_at": "2026-08-22T00:00:00+00:00",
        "expires_at": "2026-08-23T00:00:00+00:00",
        "grant_ref": grant_ref,
        "owner_gate_ref": None,
        "revocation_generation_seen": revocation_generation,
        "safe_mode_generation_seen": safe_mode_generation,
        "decision": "ALLOW",
        "reason_codes": ["SELFTEST_PREISSUED_CANONICAL_MANIFEST"],
        "evidence_refs": ["selftest://canonical-authority-manifest"],
    }


def selftest() -> None:
    canonical_main = "1" * 40
    policy_generation = "stage1-selftest-policy-v1"
    policy_digest = hashlib.sha256(b"stage1-selftest-policy-v1").hexdigest()
    revocation_generation = 7
    safe_mode_generation = 9
    grant = "grant-stage1-selftest-v1"
    envelope = {
        "schema_version": ENQUEUE_SCHEMA,
        "stage_id": STAGE_ID,
        "candidate_id": "candidate-selftest-v1",
        "docs_hash": hashlib.sha256(b"selftest-docs").hexdigest(),
        "worker_id": "stage1-selftest-worker",
        "requested_final_state": "REVIEWED_NO_ADMISSION",
        "verdict_reason": "selftest",
        "evidence_refs": ["selftest://evidence"],
    }
    task = _task_id(envelope["candidate_id"], envelope["docs_hash"])
    enqueue = _decision(
        decision_id="auth-selftest-enqueue", policy_generation=policy_generation,
        policy_digest=policy_digest, actor_role="EXECUTION",
        actor_instance="stage1-selftest-router", operation=ENQUEUE_OPERATION,
        target=ENQUEUE_TARGET, scope=ENQUEUE_SCOPE, grant_ref=grant,
        revocation_generation=revocation_generation,
        safe_mode_generation=safe_mode_generation,
    )
    specs = {
        "inspect": ("R1_SOURCE_CACHE_INSPECT_OR_STAGE", f"source-candidate:{envelope['candidate_id']}", "PUBLIC_TERMS_METADATA_ONLY"),
        "lease": ("R1_TASK_ACQUIRE_LEASE", f"task:{task}", "INTERNAL_R1_STATE_ONLY"),
        "checkpoint": ("R1_TASK_CHECKPOINT", f"task:{task}", "INTERNAL_R1_STATE_ONLY"),
        "failure": ("R1_TASK_RECORD_FAILURE", f"task:{task}", "INTERNAL_R1_STATE_ONLY"),
        "commit": ("R1_SOURCE_REVIEW_COMMIT", f"task:{task}", "PUBLIC_TERMS_METADATA_ONLY"),
    }
    operations = {
        key: _decision(
            decision_id=f"auth-selftest-{key}", policy_generation=policy_generation,
            policy_digest=policy_digest, actor_role="EXECUTION",
            actor_instance=envelope["worker_id"], operation=op, target=target,
            scope=scope, grant_ref=grant,
            revocation_generation=revocation_generation,
            safe_mode_generation=safe_mode_generation,
        )
        for key, (op, target, scope) in specs.items()
    }
    manifest = {
        "schema_version": AUTHORITY_MANIFEST_SCHEMA,
        "status": ACCEPTED_AUTHORITY_STATUS,
        "canonical_authority": True,
        "authority_scope": AUTHORITY_SCOPE,
        "canonical_main": canonical_main,
        "policy_generation": policy_generation,
        "policy_digest": policy_digest,
        "revocation_generation": revocation_generation,
        "safe_mode_generation": safe_mode_generation,
        "safe_mode_active": False,
        "valid_grant_refs": [grant],
        "trusted_clock_source": TRUSTED_CLOCK_SOURCE,
        "bundles": [{
            "bundle_id": "bundle-selftest-v1",
            "envelope_digest": _envelope_digest(envelope),
            "enqueue_actor_role": "EXECUTION",
            "enqueue_actor_instance": "stage1-selftest-router",
            "worker_actor_role": "EXECUTION",
            "worker_actor_instance": envelope["worker_id"],
            "enqueue_decision": enqueue,
            "operation_decisions": operations,
            "decision_payload_digest": _decision_digest(enqueue, operations),
        }],
    }
    manifest_text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    manifest_sha256 = hashlib.sha256(manifest_text.encode()).hexdigest()
    anchor = VerifiedCanonicalAuthorityAnchor(
        activation_receipt_ref="selftest://activation-receipt",
        activation_receipt_sha256=hashlib.sha256(b"selftest-activation-receipt").hexdigest(),
        canonical_main=canonical_main,
        authority_manifest_commit=canonical_main,
        authority_manifest_path="governance/SELFTEST_STAGE1_CANONICAL_AUTHORITY.json",
        authority_manifest_blob_sha="2" * 40,
        authority_manifest_sha256=manifest_sha256,
        authority_manifest_status=ACCEPTED_AUTHORITY_STATUS,
        authority_scope=AUTHORITY_SCOPE,
        policy_generation=policy_generation,
        policy_digest=policy_digest,
        revocation_generation=revocation_generation,
        safe_mode_generation=safe_mode_generation,
        trusted_clock_source=TRUSTED_CLOCK_SOURCE,
        verified_from_immutable_activation_receipt=True,
    )

    class LocalAuthorityAdapter(CanonicalAuthorityDecisionAdapter):
        def _validate_origin(self) -> None:
            return None

        def _fresh_main(self) -> str:
            return canonical_main

        def _load_manifest_text(self) -> str:
            if hashlib.sha256(manifest_text.encode()).hexdigest() != self.anchor.authority_manifest_sha256:
                _deny("AUTHORITY_MANIFEST_CONTENT_DIGEST_MISMATCH")
            return manifest_text

        def _github_trusted_now(self) -> datetime:
            return datetime(2026, 8, 22, 1, 0, tzinfo=timezone.utc)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        adapter = LocalAuthorityAdapter(root, anchor=anchor)
        bundle = adapter.issue_authorization_bundle(current_main=canonical_main, envelope=envelope)
        assert bundle.verified_from_canonical_authority is True
        assert bundle.decisions_verified_from_canonical_policy is True
        assert bundle.worker_runtime.now == datetime(2026, 8, 22, 1, 0, tzinfo=timezone.utc)
        print("CANONICAL_AUTHORITY_PREISSUED_BUNDLE_ACCEPTED")

        try:
            adapter.issue_authorization_bundle(current_main="3" * 40, envelope=envelope)
            raise AssertionError("stale main unexpectedly accepted")
        except CanonicalAuthorityDenied:
            pass
        print("CANONICAL_AUTHORITY_MAIN_DRIFT_FAIL_CLOSED")

        unknown = copy.deepcopy(envelope)
        unknown["candidate_id"] = "not-preissued"
        try:
            adapter.issue_authorization_bundle(current_main=canonical_main, envelope=unknown)
            raise AssertionError("unissued envelope unexpectedly accepted")
        except CanonicalAuthorityDenied:
            pass
        print("CANONICAL_AUTHORITY_UNISSUED_ENVELOPE_DENIED")

        bad_anchor = copy.deepcopy(anchor.__dict__)
        bad_anchor["verified_from_immutable_activation_receipt"] = False
        try:
            VerifiedCanonicalAuthorityAnchor(**bad_anchor).validate()
            raise AssertionError("unverified activation anchor unexpectedly accepted")
        except CanonicalAuthorityDenied:
            pass
        print("CANONICAL_AUTHORITY_UNVERIFIED_ACTIVATION_ANCHOR_DENIED")

        for bad_status in (
            "CANARY_FIXTURE_ONLY_NOT_PRODUCTION_AUTHORITY",
            "WORKING_NORMATIVE_CANDIDATE_NOT_ACCEPTED",
            "DRAFT_NONCANONICAL_LAB_REMEDIATION_CANDIDATE",
        ):
            bad = copy.deepcopy(manifest)
            bad["status"] = bad_status
            try:
                adapter._validate_manifest(bad)
                raise AssertionError("nonaccepted authority status unexpectedly accepted")
            except CanonicalAuthorityDenied:
                pass
        print("CANARY_AND_NONCANONICAL_AUTHORITY_SOURCES_REJECTED")

        sample = "HTTP/2 200\r\ndate: Sat, 22 Aug 2026 01:00:00 GMT\r\ncontent-type: application/json\r\n\r\n{}"
        assert adapter._parse_github_date_header(sample) == datetime(2026, 8, 22, 1, 0, tzinfo=timezone.utc)
        for bad_header in (
            "HTTP/2 200\n{}",
            "date: bad-date",
            "date: Sat, 22 Aug 2026 01:00:00 GMT\ndate: Sat, 22 Aug 2026 01:00:01 GMT",
        ):
            try:
                adapter._parse_github_date_header(bad_header)
                raise AssertionError("bad trusted clock header unexpectedly accepted")
            except CanonicalAuthorityDenied:
                pass
        print("GITHUB_SERVER_DATE_TRUSTED_CLOCK_FAIL_CLOSED")

    print("CANONICAL_AUTHORITY_ADAPTER_SELFTEST_PASS")
    print("PRODUCTION_AUTHORITY_MANIFEST_PROVISIONED=false")
    print("AUTHORIZATION_DECISION_MINTING_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    parser.error("pre-activation read-only authority adapter; use --selftest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
