#!/usr/bin/env python3
"""Read-only Stage-1 canonical authority/decision/trusted-time adapter.

Pre-activation only. This module does not mint decisions, grants, Owner Gates,
revocation/Safe-Mode state, canonical authority, or activation authority. It
only consumes a separately accepted finite authority manifest pinned by a
separately verified immutable activation receipt. Missing/unverifiable inputs
fail closed, so Runtime remains OFF.
"""
from __future__ import annotations

import argparse
import base64
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
    "valid_grant_refs", "trusted_clock_source",
    "canonical_main_is_complete_authority_freshness_barrier", "bundles",
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
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _decision_digest(enqueue: Mapping[str, Any], operations: Mapping[str, Any]) -> str:
    return _sha256_json({"enqueue": enqueue, "operations": operations})


def _safe_manifest_path(path: str) -> str:
    if not _nonempty(path):
        _deny("AUTHORITY_MANIFEST_PATH_MISSING")
    p = PurePosixPath(path)
    if p.is_absolute() or "." in p.parts or ".." in p.parts:
        _deny("AUTHORITY_MANIFEST_PATH_TRAVERSAL")
    normalized = str(p)
    if not normalized.startswith("governance/"):
        _deny("AUTHORITY_MANIFEST_MUST_BE_GOVERNANCE_PATH")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", normalized):
        _deny("AUTHORITY_MANIFEST_PATH_UNSAFE_FOR_API")
    return normalized


def _validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, dict) or set(envelope) != ENQUEUE_FIELDS:
        _deny("AUTHORITY_ENQUEUE_SCHEMA")
    if envelope["schema_version"] != ENQUEUE_SCHEMA or envelope["stage_id"] != STAGE_ID:
        _deny("AUTHORITY_ENQUEUE_IDENTITY")
    for field in ("candidate_id", "docs_hash", "worker_id", "verdict_reason"):
        if not _nonempty(envelope[field]):
            _deny("AUTHORITY_ENQUEUE_STRING")
    refs = envelope["evidence_refs"]
    if not isinstance(refs, list) or not all(_nonempty(x) for x in refs):
        _deny("AUTHORITY_ENQUEUE_EVIDENCE")


@dataclass(frozen=True)
class VerifiedCanonicalAuthorityAnchor:
    """Facts supplied only by a separately reviewed immutable-receipt loader."""

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
    canonical_main_is_complete_authority_freshness_barrier: bool
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
        if self.canonical_main_is_complete_authority_freshness_barrier is not True:
            _deny("AUTHORITY_ANCHOR_MAIN_FRESHNESS_BARRIER_UNVERIFIED")


class CanonicalAuthorityDecisionAdapter:
    """Verification-only adapter; accepted immutable authority remains external."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if __name__ != "__main__":
            exact_v2_definition = (
                cls.__module__ == "multiverse_r1_stage1_canonical_authority_adapter_v2"
                and cls.__name__ == "ProductionAuthorityDecisionAdapter"
                and "__init__" not in cls.__dict__
                and "__new__" not in cls.__dict__
            )
            if not exact_v2_definition:
                raise TypeError(
                    "CanonicalAuthorityDecisionAdapter permits only the audited v2 subclass in production imports"
                )
        super().__init_subclass__(**kwargs)

    def __init__(self, repo_root: Path | str, *, anchor: VerifiedCanonicalAuthorityAnchor):
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            _deny("AUTHORITY_REPO_NOT_GIT_WORKTREE")
        if not isinstance(anchor, VerifiedCanonicalAuthorityAnchor):
            _deny("AUTHORITY_ANCHOR_TYPE")
        anchor.validate()
        if __name__ != "__main__":
            allowed_type = type(self) is CanonicalAuthorityDecisionAdapter
            if not allowed_type:
                try:
                    from multiverse_r1_stage1_canonical_authority_adapter_v2 import (
                        ProductionAuthorityDecisionAdapter as _ProductionAuthorityDecisionAdapter,
                    )
                except Exception as exc:
                    raise CanonicalAuthorityDenied(
                        "AUTHORITY_PRODUCTION_SUBCLASS_IDENTITY_UNAVAILABLE:"
                        + str(exc)[:200]
                    ) from exc
                allowed_type = type(self) is _ProductionAuthorityDecisionAdapter
            if not allowed_type:
                _deny("AUTHORITY_PRODUCTION_SUBCLASS_PROHIBITED")
            try:
                from multiverse_r1_stage1_verified_activation_receipt_loader_v2 import (
                    verify_authority_consumer_anchor,
                )
                anchor = verify_authority_consumer_anchor(self.repo_root, anchor)
            except CanonicalAuthorityDenied:
                raise
            except Exception as exc:
                raise CanonicalAuthorityDenied(
                    "AUTHORITY_PRODUCTION_ANCHOR_PROVENANCE_UNVERIFIED:"
                    + str(exc)[:200]
                ) from exc
        self.anchor = anchor
        self._validate_api_transport()

    @staticmethod
    def _assert_api_transport_pinned(environ: Mapping[str, str], unix_socket: str) -> None:
        if environ.get("GH_HOST") not in (None, "", "github.com"):
            _deny("AUTHORITY_GH_HOST_OVERRIDE_PROHIBITED")
        for key in (
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy",
            "SSL_CERT_FILE", "SSL_CERT_DIR",
        ):
            if environ.get(key):
                _deny("AUTHORITY_API_PROXY_OR_CUSTOM_CA_PROHIBITED")
        if unix_socket.strip():
            _deny("AUTHORITY_GH_HTTP_UNIX_SOCKET_PROHIBITED")

    def _validate_api_transport(self) -> None:
        if shutil.which("gh") is None:
            _deny("AUTHORITY_GH_CLI_REQUIRED")
        proc = subprocess.run(
            ["gh", "config", "list", "--host", "github.com"],
            cwd=str(self.repo_root), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=os.environ.copy(),
        )
        if proc.returncode != 0:
            _deny("AUTHORITY_GH_CONFIG_QUERY_FAILED")
        values = [
            line.split("=", 1)[1] for line in proc.stdout.splitlines()
            if line.startswith("http_unix_socket=") and "=" in line
        ]
        if len(values) != 1:
            _deny("AUTHORITY_GH_HTTP_UNIX_SOCKET_STATE_AMBIGUOUS")
        self._assert_api_transport_pinned(os.environ, values[0])

    @staticmethod
    def _parse_gh_include_json(text: str) -> tuple[datetime, Any]:
        header, sep, body = text.replace("\r\n", "\n").partition("\n\n")
        if not sep:
            _deny("AUTHORITY_GITHUB_API_HEADERS_OR_BODY_MISSING")
        lines = [line for line in header.splitlines() if line]
        if not lines or not lines[0].startswith("HTTP/"):
            _deny("AUTHORITY_GITHUB_API_STATUS_MISSING")
        parts = lines[0].split()
        if len(parts) < 2 or parts[1] != "200":
            _deny("AUTHORITY_GITHUB_API_NON_200")
        dates = [line.split(":", 1)[1].strip() for line in lines[1:] if line.lower().startswith("date:")]
        if len(dates) != 1:
            _deny("AUTHORITY_TRUSTED_CLOCK_DATE_HEADER_MISSING_OR_AMBIGUOUS")
        try:
            trusted_now = parsedate_to_datetime(dates[0])
        except Exception as exc:
            raise CanonicalAuthorityDenied("AUTHORITY_TRUSTED_CLOCK_DATE_HEADER_INVALID") from exc
        if trusted_now.tzinfo is None:
            _deny("AUTHORITY_TRUSTED_CLOCK_NOT_OFFSET_AWARE")
        try:
            payload = json.loads(body)
        except Exception as exc:
            raise CanonicalAuthorityDenied("AUTHORITY_GITHUB_API_JSON_INVALID") from exc
        return trusted_now.astimezone(timezone.utc), payload

    def _api(self, endpoint: str) -> tuple[datetime, Any]:
        self._validate_api_transport()
        proc = subprocess.run(
            [
                "gh", "api", "--hostname", "github.com", "--include",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                endpoint,
            ],
            cwd=str(self.repo_root), text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=os.environ.copy(),
        )
        if proc.returncode != 0:
            raise CanonicalAuthorityDenied("AUTHORITY_GITHUB_API_UNAVAILABLE:" + proc.stderr.strip()[:200])
        return self._parse_gh_include_json(proc.stdout)

    def _fresh_main_and_trusted_now(self) -> tuple[str, datetime]:
        now, payload = self._api(f"/repos/{CANONICAL_REPO}/branches/main")
        commit = payload.get("commit") if isinstance(payload, dict) else None
        main = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(main, str) or not _HEX40.fullmatch(main):
            _deny("AUTHORITY_CANONICAL_MAIN_UNAVAILABLE")
        return main, now

    def _load_manifest_text(self) -> str:
        a = self.anchor
        _, payload = self._api(
            f"/repos/{CANONICAL_REPO}/contents/{a.authority_manifest_path}?ref={a.authority_manifest_commit}"
        )
        if not isinstance(payload, dict) or payload.get("type") != "file":
            _deny("AUTHORITY_MANIFEST_CONTENT_RESPONSE_INVALID")
        if payload.get("sha") != a.authority_manifest_blob_sha:
            _deny("AUTHORITY_MANIFEST_BLOB_MISMATCH")
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            _deny("AUTHORITY_MANIFEST_CONTENT_ENCODING_INVALID")
        try:
            raw = base64.b64decode("".join(payload["content"].split()), validate=True)
            text = raw.decode("utf-8")
        except Exception as exc:
            raise CanonicalAuthorityDenied("AUTHORITY_MANIFEST_CONTENT_DECODE_INVALID") from exc
        if hashlib.sha256(raw).hexdigest() != a.authority_manifest_sha256:
            _deny("AUTHORITY_MANIFEST_CONTENT_DIGEST_MISMATCH")
        return text

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
        if value["canonical_main_is_complete_authority_freshness_barrier"] is not True:
            _deny("AUTHORITY_MANIFEST_MAIN_FRESHNESS_BARRIER_UNVERIFIED")
        grants = value["valid_grant_refs"]
        if not isinstance(grants, list) or not all(_nonempty(x) for x in grants) or len(grants) != len(set(grants)):
            _deny("AUTHORITY_MANIFEST_GRANTS_INVALID")
        bundles = value["bundles"]
        if not isinstance(bundles, list) or not (1 <= len(bundles) <= MAX_AUTHORITY_BUNDLES):
            _deny("AUTHORITY_MANIFEST_BUNDLE_COUNT_INVALID")

        seen_bundle_ids: set[str] = set()
        seen_envelopes: set[str] = set()
        seen_decisions: set[str] = set()
        for bundle in bundles:
            if not isinstance(bundle, dict) or set(bundle) != BUNDLE_FIELDS:
                _deny("AUTHORITY_MANIFEST_BUNDLE_SCHEMA")
            if not _nonempty(bundle["bundle_id"]) or bundle["bundle_id"] in seen_bundle_ids:
                _deny("AUTHORITY_MANIFEST_BUNDLE_ID_INVALID")
            if not _HEX64.fullmatch(bundle["envelope_digest"]) or bundle["envelope_digest"] in seen_envelopes:
                _deny("AUTHORITY_MANIFEST_ENVELOPE_DIGEST_INVALID")
            seen_bundle_ids.add(bundle["bundle_id"])
            seen_envelopes.add(bundle["envelope_digest"])
            for field in ("enqueue_actor_role", "enqueue_actor_instance", "worker_actor_role", "worker_actor_instance"):
                if not _nonempty(bundle[field]):
                    _deny("AUTHORITY_MANIFEST_ACTOR_IDENTITY_INVALID")
            enqueue = bundle["enqueue_decision"]
            operations = bundle["operation_decisions"]
            if not isinstance(enqueue, dict) or not isinstance(operations, dict) or set(operations) != AUTH_KEYS:
                _deny("AUTHORITY_MANIFEST_DECISION_SET_INVALID")
            if bundle["decision_payload_digest"] != _decision_digest(enqueue, operations):
                _deny("AUTHORITY_MANIFEST_DECISION_DIGEST_MISMATCH")
            for decision in [enqueue, *operations.values()]:
                if not isinstance(decision, dict):
                    _deny("AUTHORITY_MANIFEST_OPERATION_DECISION_INVALID")
                did = decision.get("authorization_decision_id")
                if not _nonempty(did) or did in seen_decisions:
                    _deny("AUTHORITY_MANIFEST_DECISION_ID_NOT_UNIQUE")
                seen_decisions.add(did)
                if decision.get("policy_generation") != value["policy_generation"] or decision.get("policy_digest") != value["policy_digest"]:
                    _deny("AUTHORITY_MANIFEST_DECISION_POLICY_IDENTITY_MISMATCH")
                if decision.get("revocation_generation_seen") != value["revocation_generation"]:
                    _deny("AUTHORITY_MANIFEST_DECISION_REVOCATION_GENERATION_MISMATCH")
                if decision.get("safe_mode_generation_seen") != value["safe_mode_generation"]:
                    _deny("AUTHORITY_MANIFEST_DECISION_SAFE_MODE_GENERATION_MISMATCH")
                if decision.get("permission_class_requested") != "P0_READ_PUBLIC_OR_CANONICAL" and decision.get("grant_ref") not in grants:
                    _deny("AUTHORITY_MANIFEST_DECISION_GRANT_NOT_CURRENT")
            if enqueue.get("actor_role") != bundle["enqueue_actor_role"] or enqueue.get("actor_instance") != bundle["enqueue_actor_instance"]:
                _deny("AUTHORITY_MANIFEST_ENQUEUE_ACTOR_MISMATCH")
            for decision in operations.values():
                if decision.get("actor_role") != bundle["worker_actor_role"] or decision.get("actor_instance") != bundle["worker_actor_instance"]:
                    _deny("AUTHORITY_MANIFEST_WORKER_ACTOR_MISMATCH")
        return copy.deepcopy(value)

    def _load_manifest(self) -> dict:
        try:
            value = json.loads(self._load_manifest_text())
        except CanonicalAuthorityDenied:
            raise
        except Exception as exc:
            raise CanonicalAuthorityDenied("AUTHORITY_MANIFEST_JSON_INVALID") from exc
        return self._validate_manifest(value)

    def issue_authorization_bundle(self, *, current_main: str, envelope: Mapping[str, Any]) -> TrustedAuthorizationBundle:
        _validate_envelope(envelope)
        self.anchor.validate()
        pre_main, _ = self._fresh_main_and_trusted_now()
        if current_main != pre_main or current_main != self.anchor.canonical_main:
            _deny("AUTHORITY_CURRENT_MAIN_MISMATCH")
        manifest = self._load_manifest()
        digest = _sha256_json(envelope)
        matches = [b for b in manifest["bundles"] if b["envelope_digest"] == digest]
        if len(matches) != 1:
            _deny("AUTHORITY_ENVELOPE_NOT_PREISSUED_OR_AMBIGUOUS")
        selected = copy.deepcopy(matches[0])
        if envelope["worker_id"] != selected["worker_actor_instance"]:
            _deny("AUTHORITY_WORKER_BINDING_MISMATCH")

        post_main, trusted_now = self._fresh_main_and_trusted_now()
        if post_main != current_main:
            _deny("AUTHORITY_MAIN_DRIFT_DURING_DECISION_LOAD")
        grants = frozenset(manifest["valid_grant_refs"])
        common = dict(
            policy_generation=manifest["policy_generation"],
            policy_digest=manifest["policy_digest"],
            revocation_generation=manifest["revocation_generation"],
            safe_mode_generation=manifest["safe_mode_generation"],
            now=trusted_now,
            valid_grant_refs=grants,
            expected_owner_gate_ref=None,
            safe_mode_active=manifest["safe_mode_active"],
        )
        enqueue_runtime = AuthorizationRuntime(
            actor_role=selected["enqueue_actor_role"],
            actor_instance=selected["enqueue_actor_instance"], **common,
        )
        worker_runtime = AuthorizationRuntime(
            actor_role=selected["worker_actor_role"],
            actor_instance=selected["worker_actor_instance"], **common,
        )
        a = self.anchor
        bundle = TrustedAuthorizationBundle(
            enqueue_decision=copy.deepcopy(selected["enqueue_decision"]),
            operation_decisions=copy.deepcopy(selected["operation_decisions"]),
            enqueue_runtime=enqueue_runtime,
            worker_runtime=worker_runtime,
            canonical_main=current_main,
            provenance_ref=(
                f"git:{a.authority_manifest_commit}:{a.authority_manifest_path}"
                f"#blob={a.authority_manifest_blob_sha}#sha256={a.authority_manifest_sha256}"
            ),
            decision_payload_digest=selected["decision_payload_digest"],
            verified_from_canonical_authority=True,
            decisions_verified_from_canonical_policy=True,
        )
        seal_authorization_bundle(bundle, envelope=envelope, current_main=current_main)
        return bundle


def _task_id(candidate_id: str, docs_hash: str) -> str:
    raw = json.dumps(f"source-review:{candidate_id}:{docs_hash}", separators=(",", ":")).encode()
    return "task-" + hashlib.sha256(raw).hexdigest()[:16]


def _decision(*, did: str, generation: str, digest: str, actor: str, operation: str, target: str, scope: str, grant: str, rev: int, safe: int) -> dict:
    return {
        "authorization_decision_id": did,
        "policy_generation": generation,
        "policy_digest": digest,
        "actor_role": "EXECUTION",
        "actor_instance": actor,
        "operation": operation,
        "target": target,
        "permission_class_requested": "P1_REVERSIBLE_INTERNAL_WRITE",
        "permission_ceiling": "P1_REVERSIBLE_INTERNAL_WRITE",
        "scope": {"operation": operation, "target": target, "data_exposure_scope": scope},
        "data_exposure_scope": scope,
        "issued_at": "2026-08-22T00:00:00+00:00",
        "expires_at": "2026-08-23T00:00:00+00:00",
        "grant_ref": grant,
        "owner_gate_ref": None,
        "revocation_generation_seen": rev,
        "safe_mode_generation_seen": safe,
        "decision": "ALLOW",
        "reason_codes": ["SELFTEST_PREISSUED_CANONICAL_MANIFEST"],
        "evidence_refs": ["selftest://authority"],
    }


def selftest() -> None:
    main = "1" * 40
    generation = "selftest-policy-v1"
    policy_digest = hashlib.sha256(generation.encode()).hexdigest()
    rev, safe = 7, 9
    grant = "grant-selftest-v1"
    envelope = {
        "schema_version": ENQUEUE_SCHEMA,
        "stage_id": STAGE_ID,
        "candidate_id": "candidate-selftest",
        "docs_hash": hashlib.sha256(b"docs").hexdigest(),
        "worker_id": "worker-selftest",
        "requested_final_state": "REVIEWED_NO_ADMISSION",
        "verdict_reason": "selftest",
        "evidence_refs": ["selftest://evidence"],
    }
    task = _task_id(envelope["candidate_id"], envelope["docs_hash"])
    enqueue = _decision(
        did="auth-enqueue", generation=generation, digest=policy_digest,
        actor="router-selftest", operation=ENQUEUE_OPERATION, target=ENQUEUE_TARGET,
        scope=ENQUEUE_SCOPE, grant=grant, rev=rev, safe=safe,
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
            did=f"auth-{key}", generation=generation, digest=policy_digest,
            actor=envelope["worker_id"], operation=op, target=target, scope=scope,
            grant=grant, rev=rev, safe=safe,
        ) for key, (op, target, scope) in specs.items()
    }
    bundle = {
        "bundle_id": "bundle-selftest",
        "envelope_digest": _sha256_json(envelope),
        "enqueue_actor_role": "EXECUTION",
        "enqueue_actor_instance": "router-selftest",
        "worker_actor_role": "EXECUTION",
        "worker_actor_instance": envelope["worker_id"],
        "enqueue_decision": enqueue,
        "operation_decisions": operations,
        "decision_payload_digest": _decision_digest(enqueue, operations),
    }
    manifest = {
        "schema_version": AUTHORITY_MANIFEST_SCHEMA,
        "status": ACCEPTED_AUTHORITY_STATUS,
        "canonical_authority": True,
        "authority_scope": AUTHORITY_SCOPE,
        "canonical_main": main,
        "policy_generation": generation,
        "policy_digest": policy_digest,
        "revocation_generation": rev,
        "safe_mode_generation": safe,
        "safe_mode_active": False,
        "valid_grant_refs": [grant],
        "trusted_clock_source": TRUSTED_CLOCK_SOURCE,
        "canonical_main_is_complete_authority_freshness_barrier": True,
        "bundles": [bundle],
    }
    manifest_text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    anchor = VerifiedCanonicalAuthorityAnchor(
        activation_receipt_ref="selftest://activation",
        activation_receipt_sha256=hashlib.sha256(b"activation").hexdigest(),
        canonical_main=main,
        authority_manifest_commit=main,
        authority_manifest_path="governance/SELFTEST_STAGE1_AUTHORITY.json",
        authority_manifest_blob_sha="2" * 40,
        authority_manifest_sha256=hashlib.sha256(manifest_text.encode()).hexdigest(),
        authority_manifest_status=ACCEPTED_AUTHORITY_STATUS,
        authority_scope=AUTHORITY_SCOPE,
        policy_generation=generation,
        policy_digest=policy_digest,
        revocation_generation=rev,
        safe_mode_generation=safe,
        trusted_clock_source=TRUSTED_CLOCK_SOURCE,
        canonical_main_is_complete_authority_freshness_barrier=True,
        verified_from_immutable_activation_receipt=True,
    )

    class Local(CanonicalAuthorityDecisionAdapter):
        def _validate_api_transport(self) -> None:
            return None
        def _fresh_main_and_trusted_now(self) -> tuple[str, datetime]:
            return main, datetime(2026, 8, 22, 1, 0, tzinfo=timezone.utc)
        def _load_manifest_text(self) -> str:
            return manifest_text

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / ".git").mkdir()
        adapter = Local(root, anchor=anchor)
        result = adapter.issue_authorization_bundle(current_main=main, envelope=envelope)
        assert result.verified_from_canonical_authority is True
        print("CANONICAL_AUTHORITY_PREISSUED_BUNDLE_ACCEPTED")

        bad_envelope = copy.deepcopy(envelope)
        bad_envelope["candidate_id"] = "unissued"
        for label, fn in (
            ("CANONICAL_AUTHORITY_MAIN_DRIFT_FAIL_CLOSED", lambda: adapter.issue_authorization_bundle(current_main="3" * 40, envelope=envelope)),
            ("CANONICAL_AUTHORITY_UNISSUED_ENVELOPE_DENIED", lambda: adapter.issue_authorization_bundle(current_main=main, envelope=bad_envelope)),
        ):
            try:
                fn(); raise AssertionError(label)
            except CanonicalAuthorityDenied:
                print(label)

        bad_anchor = copy.deepcopy(anchor.__dict__)
        bad_anchor["verified_from_immutable_activation_receipt"] = False
        try:
            VerifiedCanonicalAuthorityAnchor(**bad_anchor).validate(); raise AssertionError("anchor")
        except CanonicalAuthorityDenied:
            print("CANONICAL_AUTHORITY_UNVERIFIED_ACTIVATION_ANCHOR_DENIED")

        for status in (
            "CANARY_FIXTURE_ONLY_NOT_PRODUCTION_AUTHORITY",
            "WORKING_NORMATIVE_CANDIDATE_NOT_ACCEPTED",
            "DRAFT_NONCANONICAL_LAB_REMEDIATION_CANDIDATE",
        ):
            bad = copy.deepcopy(manifest); bad["status"] = status
            try:
                adapter._validate_manifest(bad); raise AssertionError(status)
            except CanonicalAuthorityDenied:
                pass
        print("CANARY_AND_NONCANONICAL_AUTHORITY_SOURCES_REJECTED")

        bad = copy.deepcopy(manifest)
        bad["canonical_main_is_complete_authority_freshness_barrier"] = False
        try:
            adapter._validate_manifest(bad); raise AssertionError("freshness")
        except CanonicalAuthorityDenied:
            pass
        dup = copy.deepcopy(manifest)
        second = copy.deepcopy(bundle); second["bundle_id"] = "bundle-two"; second["envelope_digest"] = "f" * 64
        dup["bundles"].append(second)
        try:
            adapter._validate_manifest(dup); raise AssertionError("duplicate decision ids")
        except CanonicalAuthorityDenied:
            pass
        print("AUTHORITY_FRESHNESS_BARRIER_AND_DECISION_UNIQUENESS_FAIL_CLOSED")

        sample = "HTTP/2.0 200 OK\r\ndate: Sat, 22 Aug 2026 01:00:00 GMT\r\ncontent-type: application/json\r\n\r\n{}"
        parsed_now, parsed_body = adapter._parse_gh_include_json(sample)
        assert parsed_now == datetime(2026, 8, 22, 1, 0, tzinfo=timezone.utc) and parsed_body == {}
        for bad_response in (
            "HTTP/2.0 200 OK\n\n{}",
            "HTTP/2.0 200 OK\ndate: bad\n\n{}",
            "HTTP/2.0 500 Error\ndate: Sat, 22 Aug 2026 01:00:00 GMT\n\n{}",
        ):
            try:
                adapter._parse_gh_include_json(bad_response); raise AssertionError("bad api response")
            except CanonicalAuthorityDenied:
                pass
        for env in (
            {"HTTPS_PROXY": "http://127.0.0.1:9"},
            {"GH_HOST": "evil.example"},
            {"SSL_CERT_FILE": "/tmp/evil-ca"},
        ):
            try:
                adapter._assert_api_transport_pinned(env, ""); raise AssertionError("transport")
            except CanonicalAuthorityDenied:
                pass
        try:
            adapter._assert_api_transport_pinned({}, "/tmp/gh.sock"); raise AssertionError("socket")
        except CanonicalAuthorityDenied:
            pass
        print("GITHUB_SERVER_DATE_AND_API_TRANSPORT_FAIL_CLOSED")

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
