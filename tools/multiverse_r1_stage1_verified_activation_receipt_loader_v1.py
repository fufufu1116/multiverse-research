#!/usr/bin/env python3
"""Verified immutable activation-receipt loader for R1 Stage 1.

Pre-activation only. This module does not create an activation receipt, create
or update any Git ref, provision a ruleset, provision a writer key, create the
runtime branch, issue authorization, or activate Runtime.

It closes the remaining caller-construction gap shared by the audited PR #60
runtime CAS adapter and PR #61/#62 canonical authority adapter by loading one
strict activation receipt from a protected annotated Git tag and returning both
verified anchor objects. All network facts are Fresh Read from github.com via
the GitHub API and fail closed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from multiverse_r1_stage1_canonical_authority_adapter_v1 import (
    ACCEPTED_AUTHORITY_STATUS,
    AUTHORITY_SCOPE,
    TRUSTED_CLOCK_SOURCE,
    CanonicalAuthorityDenied,
    VerifiedCanonicalAuthorityAnchor,
)
from multiverse_r1_stage1_canonical_authority_adapter_v2 import (
    AUTHORITY_MANIFEST_SCHEMA_V2,
    EXPECTED_POLICY,
    EXPECTED_POLICY_DIGEST,
    FRESHNESS_BARRIER_MODE,
    POLICY_GENERATION,
    validate_source_manifest_structure,
)
from multiverse_r1_stage1_github_runtime_cas_v1 import (
    CANONICAL_REPO,
    JOURNAL_RULESET_INCLUDE,
    VerifiedActivationAnchor,
)
from multiverse_r1_stage1_runtime_v1 import (
    MAX_TERMINAL_TASKS,
    MAX_WORKERS,
    RETRY_BUDGET,
    RUNTIME_BRANCH,
    WINDOW_DAYS,
)

ACTIVATION_RECEIPT_SCHEMA = "MULTIVERSE_R1_STAGE1_IMMUTABLE_ACTIVATION_RECEIPT_v1"
ACTIVATION_RECEIPT_STATUS = "ACCEPTED_IMMUTABLE_STAGE1_ACTIVATION_RECEIPT"
ACTIVATION_TAG_NAME = "multiverse-r1-stage1-activation-v1"
ACTIVATION_TAG_REF = f"refs/tags/{ACTIVATION_TAG_NAME}"
AUTHORITY_MANIFEST_PATH = "governance/MULTIVERSE_R1_STAGE1_PRODUCTION_AUTHORITY_ROOT_20260822_v1.json"
OWNER_GATE_COMMENT = 5367308652
PRODUCTION_AUTHORITY_OWNER_GATE_COMMENT = 5374516958
MAX_TASKS_PER_INVOCATION = 10

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

TOP_FIELDS = {
    "schema_version",
    "status",
    "canonical_repo",
    "stage_id",
    "activation_receipt_id",
    "canonical_main",
    "authority_manifest",
    "runtime",
    "infrastructure",
    "activation_window",
    "governance_evidence",
}
AUTHORITY_FIELDS = {
    "commit",
    "path",
    "blob_sha",
    "sha256",
    "status",
    "authority_scope",
    "policy_generation",
    "policy_digest",
    "revocation_generation",
    "safe_mode_generation",
    "trusted_clock_source",
    "freshness_barrier_mode",
}
RUNTIME_FIELDS = {
    "audited_implementation_head",
    "runtime_branch",
    "runtime_genesis",
    "initial_ledger_head",
    "max_concurrent_workers",
    "max_tasks_per_invocation",
    "retry_budget_per_task",
    "max_terminal_tasks",
    "runtime_window_days",
    "auto_resume_authorized",
    "scheduler_authorized",
    "always_on_worker_authorized",
}
INFRA_FIELDS = {
    "journal_ruleset_id",
    "journal_ruleset_updated_at",
    "journal_ruleset_no_bypass_attested",
    "writer_key_id",
    "writer_key_sha256",
    "activation_tag_ref",
}
WINDOW_FIELDS = {"activated_at", "expires_at"}
GOV_FIELDS = {
    "owner_gate_comment",
    "production_authority_owner_gate_comment",
    "final_lab_evidence_ref",
    "final_auditor_evidence_ref",
}


class ActivationReceiptDenied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise ActivationReceiptDenied(code)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _strict_int(value: Any, *, positive: bool = False) -> bool:
    if not isinstance(value, int) or isinstance(value, bool):
        return False
    return value > 0 if positive else value >= 0


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _aware_time(value: Any, code: str) -> datetime:
    if not _nonempty(value):
        _deny(code)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ActivationReceiptDenied(code) from exc
    if dt.tzinfo is None:
        _deny(code)
    return dt.astimezone(timezone.utc)


def _assert_transport_pinned(environ: Mapping[str, str], unix_socket: str) -> None:
    if environ.get("GH_HOST") not in (None, "", "github.com"):
        _deny("ACTIVATION_RECEIPT_GH_HOST_OVERRIDE_PROHIBITED")
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR",
    ):
        if environ.get(key):
            _deny("ACTIVATION_RECEIPT_PROXY_OR_CUSTOM_CA_PROHIBITED")
    if unix_socket.strip():
        _deny("ACTIVATION_RECEIPT_GH_HTTP_UNIX_SOCKET_PROHIBITED")


@dataclass(frozen=True)
class LoadedActivationAnchors:
    runtime: VerifiedActivationAnchor
    authority: VerifiedCanonicalAuthorityAnchor
    trusted_now: datetime
    receipt: dict


class ImmutableActivationReceiptLoader:
    """Read-only verifier for the single Stage-1 activation receipt tag."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            _deny("ACTIVATION_RECEIPT_REPO_NOT_GIT_WORKTREE")
        self._validate_transport()

    def _validate_transport(self) -> None:
        if shutil.which("gh") is None:
            _deny("ACTIVATION_RECEIPT_GH_CLI_REQUIRED")
        proc = subprocess.run(
            ["gh", "config", "list", "--host", "github.com"],
            cwd=str(self.repo_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
        if proc.returncode != 0:
            _deny("ACTIVATION_RECEIPT_GH_CONFIG_QUERY_FAILED")
        values = [
            line.split("=", 1)[1]
            for line in proc.stdout.splitlines()
            if line.startswith("http_unix_socket=") and "=" in line
        ]
        if len(values) != 1:
            _deny("ACTIVATION_RECEIPT_GH_HTTP_UNIX_SOCKET_STATE_AMBIGUOUS")
        _assert_transport_pinned(os.environ, values[0])

    @staticmethod
    def _parse_include_json(text: str) -> tuple[datetime, Any]:
        header, sep, body = text.replace("\r\n", "\n").partition("\n\n")
        if not sep:
            _deny("ACTIVATION_RECEIPT_API_HEADERS_OR_BODY_MISSING")
        lines = [line for line in header.splitlines() if line]
        if not lines or not lines[0].startswith("HTTP/"):
            _deny("ACTIVATION_RECEIPT_API_STATUS_MISSING")
        parts = lines[0].split()
        if len(parts) < 2 or parts[1] != "200":
            _deny("ACTIVATION_RECEIPT_API_NON_200")
        dates = [
            line.split(":", 1)[1].strip()
            for line in lines[1:]
            if line.lower().startswith("date:")
        ]
        if len(dates) != 1:
            _deny("ACTIVATION_RECEIPT_TRUSTED_DATE_MISSING_OR_AMBIGUOUS")
        from email.utils import parsedate_to_datetime
        try:
            trusted_now = parsedate_to_datetime(dates[0])
        except Exception as exc:
            raise ActivationReceiptDenied("ACTIVATION_RECEIPT_TRUSTED_DATE_INVALID") from exc
        if trusted_now.tzinfo is None:
            _deny("ACTIVATION_RECEIPT_TRUSTED_DATE_NOT_AWARE")
        try:
            payload = json.loads(body)
        except Exception as exc:
            raise ActivationReceiptDenied("ACTIVATION_RECEIPT_API_JSON_INVALID") from exc
        return trusted_now.astimezone(timezone.utc), payload

    def _api(self, endpoint: str) -> tuple[datetime, Any]:
        self._validate_transport()
        proc = subprocess.run(
            [
                "gh", "api", "--hostname", "github.com", "--include",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                endpoint,
            ],
            cwd=str(self.repo_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
        if proc.returncode != 0:
            raise ActivationReceiptDenied(
                "ACTIVATION_RECEIPT_GITHUB_API_UNAVAILABLE:" + proc.stderr.strip()[:200]
            )
        return self._parse_include_json(proc.stdout)

    def _fresh_main(self) -> tuple[str, datetime]:
        now, payload = self._api(f"/repos/{CANONICAL_REPO}/branches/main")
        commit = payload.get("commit") if isinstance(payload, dict) else None
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(sha, str) or not _HEX40.fullmatch(sha):
            _deny("ACTIVATION_RECEIPT_CANONICAL_MAIN_UNAVAILABLE")
        return sha, now

    def _load_tag_message(self) -> tuple[str, str]:
        _, ref_payload = self._api(
            f"/repos/{CANONICAL_REPO}/git/ref/tags/{ACTIVATION_TAG_NAME}"
        )
        if not isinstance(ref_payload, dict) or ref_payload.get("ref") != ACTIVATION_TAG_REF:
            _deny("ACTIVATION_RECEIPT_TAG_REF_MISMATCH")
        obj = ref_payload.get("object")
        if not isinstance(obj, dict) or obj.get("type") != "tag":
            _deny("ACTIVATION_RECEIPT_MUST_USE_ANNOTATED_TAG")
        tag_sha = obj.get("sha")
        if not isinstance(tag_sha, str) or not _HEX40.fullmatch(tag_sha):
            _deny("ACTIVATION_RECEIPT_TAG_OBJECT_SHA_INVALID")

        _, tag_payload = self._api(f"/repos/{CANONICAL_REPO}/git/tags/{tag_sha}")
        if not isinstance(tag_payload, dict) or tag_payload.get("tag") != ACTIVATION_TAG_NAME:
            _deny("ACTIVATION_RECEIPT_TAG_OBJECT_IDENTITY_MISMATCH")
        target = tag_payload.get("object")
        if not isinstance(target, dict) or target.get("type") != "commit":
            _deny("ACTIVATION_RECEIPT_TAG_TARGET_MUST_BE_COMMIT")
        target_sha = target.get("sha")
        if not isinstance(target_sha, str) or not _HEX40.fullmatch(target_sha):
            _deny("ACTIVATION_RECEIPT_TAG_TARGET_SHA_INVALID")
        message = tag_payload.get("message")
        if not isinstance(message, str) or not message:
            _deny("ACTIVATION_RECEIPT_TAG_MESSAGE_MISSING")
        return target_sha, message

    @staticmethod
    def _ruleset_is_strict(detail: Any, *, receipt: Mapping[str, Any]) -> bool:
        if not isinstance(detail, dict):
            return False
        infra = receipt["infrastructure"]
        if detail.get("id") != infra["journal_ruleset_id"]:
            return False
        if detail.get("updated_at") != infra["journal_ruleset_updated_at"]:
            return False
        if detail.get("target") != "tag":
            return False
        if detail.get("enforcement") not in {"active", "enabled", "always"}:
            return False
        if detail.get("bypass_actors") != []:
            return False
        conditions = detail.get("conditions")
        if not isinstance(conditions, dict):
            return False
        ref_name = conditions.get("ref_name")
        if not isinstance(ref_name, dict):
            return False
        includes = ref_name.get("include")
        excludes = ref_name.get("exclude")
        if not isinstance(includes, list):
            return False
        if JOURNAL_RULESET_INCLUDE not in includes or ACTIVATION_TAG_REF not in includes:
            return False
        if not isinstance(excludes, list) or excludes:
            return False
        rules = detail.get("rules")
        if not isinstance(rules, list):
            return False
        types = {rule.get("type") for rule in rules if isinstance(rule, dict)}
        if not {"deletion", "update", "non_fast_forward"}.issubset(types):
            return False
        if "creation" in types:
            return False
        return True

    def _validate_receipt(self, value: Any, *, target_main: str, trusted_now: datetime) -> dict:
        if not isinstance(value, dict) or set(value) != TOP_FIELDS:
            _deny("ACTIVATION_RECEIPT_SCHEMA")
        if value["schema_version"] != ACTIVATION_RECEIPT_SCHEMA:
            _deny("ACTIVATION_RECEIPT_SCHEMA_IDENTITY")
        if value["status"] != ACTIVATION_RECEIPT_STATUS:
            _deny("ACTIVATION_RECEIPT_STATUS")
        if value["canonical_repo"] != CANONICAL_REPO:
            _deny("ACTIVATION_RECEIPT_REPO_IDENTITY")
        if value["stage_id"] != AUTHORITY_SCOPE:
            _deny("ACTIVATION_RECEIPT_STAGE_IDENTITY")
        if not _nonempty(value["activation_receipt_id"]):
            _deny("ACTIVATION_RECEIPT_ID_MISSING")
        if value["canonical_main"] != target_main or not _HEX40.fullmatch(value["canonical_main"]):
            _deny("ACTIVATION_RECEIPT_CANONICAL_MAIN_MISMATCH")

        authority = value["authority_manifest"]
        runtime = value["runtime"]
        infra = value["infrastructure"]
        window = value["activation_window"]
        gov = value["governance_evidence"]
        if not isinstance(authority, dict) or set(authority) != AUTHORITY_FIELDS:
            _deny("ACTIVATION_RECEIPT_AUTHORITY_SCHEMA")
        if not isinstance(runtime, dict) or set(runtime) != RUNTIME_FIELDS:
            _deny("ACTIVATION_RECEIPT_RUNTIME_SCHEMA")
        if not isinstance(infra, dict) or set(infra) != INFRA_FIELDS:
            _deny("ACTIVATION_RECEIPT_INFRA_SCHEMA")
        if not isinstance(window, dict) or set(window) != WINDOW_FIELDS:
            _deny("ACTIVATION_RECEIPT_WINDOW_SCHEMA")
        if not isinstance(gov, dict) or set(gov) != GOV_FIELDS:
            _deny("ACTIVATION_RECEIPT_GOVERNANCE_SCHEMA")

        if authority["commit"] != value["canonical_main"] or not _HEX40.fullmatch(authority["commit"]):
            _deny("ACTIVATION_RECEIPT_AUTHORITY_COMMIT")
        if authority["path"] != AUTHORITY_MANIFEST_PATH:
            _deny("ACTIVATION_RECEIPT_AUTHORITY_PATH")
        if not _HEX40.fullmatch(authority["blob_sha"]) or not _HEX64.fullmatch(authority["sha256"]):
            _deny("ACTIVATION_RECEIPT_AUTHORITY_DIGEST")
        if authority["status"] != ACCEPTED_AUTHORITY_STATUS:
            _deny("ACTIVATION_RECEIPT_AUTHORITY_STATUS")
        if authority["authority_scope"] != AUTHORITY_SCOPE:
            _deny("ACTIVATION_RECEIPT_AUTHORITY_SCOPE")
        if authority["policy_generation"] != POLICY_GENERATION:
            _deny("ACTIVATION_RECEIPT_POLICY_GENERATION")
        if authority["policy_digest"] != EXPECTED_POLICY_DIGEST:
            _deny("ACTIVATION_RECEIPT_POLICY_DIGEST")
        if not _strict_int(authority["revocation_generation"], positive=True):
            _deny("ACTIVATION_RECEIPT_REVOCATION_GENERATION")
        if not _strict_int(authority["safe_mode_generation"], positive=True):
            _deny("ACTIVATION_RECEIPT_SAFE_MODE_GENERATION")
        if authority["trusted_clock_source"] != TRUSTED_CLOCK_SOURCE:
            _deny("ACTIVATION_RECEIPT_TRUSTED_CLOCK_SOURCE")
        if authority["freshness_barrier_mode"] != FRESHNESS_BARRIER_MODE:
            _deny("ACTIVATION_RECEIPT_FRESHNESS_BARRIER")

        for field in ("audited_implementation_head", "runtime_genesis", "initial_ledger_head"):
            if not isinstance(runtime[field], str) or not _HEX40.fullmatch(runtime[field]):
                _deny("ACTIVATION_RECEIPT_RUNTIME_SHA")
        if runtime["runtime_branch"] != RUNTIME_BRANCH:
            _deny("ACTIVATION_RECEIPT_RUNTIME_BRANCH")
        if runtime["runtime_genesis"] != value["canonical_main"]:
            _deny("ACTIVATION_RECEIPT_RUNTIME_GENESIS_MUST_BE_CANONICAL_MAIN")
        if runtime["max_concurrent_workers"] != MAX_WORKERS:
            _deny("ACTIVATION_RECEIPT_WORKER_CEILING")
        if runtime["max_tasks_per_invocation"] != MAX_TASKS_PER_INVOCATION:
            _deny("ACTIVATION_RECEIPT_INVOCATION_CEILING")
        if runtime["retry_budget_per_task"] != RETRY_BUDGET:
            _deny("ACTIVATION_RECEIPT_RETRY_BUDGET")
        if runtime["max_terminal_tasks"] != MAX_TERMINAL_TASKS:
            _deny("ACTIVATION_RECEIPT_TERMINAL_CEILING")
        if runtime["runtime_window_days"] != WINDOW_DAYS:
            _deny("ACTIVATION_RECEIPT_RUNTIME_WINDOW")
        if runtime["auto_resume_authorized"] is not False:
            _deny("ACTIVATION_RECEIPT_AUTO_RESUME")
        if runtime["scheduler_authorized"] is not False or runtime["always_on_worker_authorized"] is not False:
            _deny("ACTIVATION_RECEIPT_SCHEDULER_OR_ALWAYS_ON")

        if not _strict_int(infra["journal_ruleset_id"], positive=True):
            _deny("ACTIVATION_RECEIPT_RULESET_ID")
        ruleset_updated_at = _aware_time(infra["journal_ruleset_updated_at"], "ACTIVATION_RECEIPT_RULESET_UPDATED_AT")
        if infra["journal_ruleset_no_bypass_attested"] is not True:
            _deny("ACTIVATION_RECEIPT_RULESET_NO_BYPASS")
        if not _nonempty(infra["writer_key_id"]) or not _HEX64.fullmatch(infra["writer_key_sha256"]):
            _deny("ACTIVATION_RECEIPT_WRITER_KEY_IDENTITY")
        if infra["activation_tag_ref"] != ACTIVATION_TAG_REF:
            _deny("ACTIVATION_RECEIPT_TAG_BINDING")

        activated_at = _aware_time(window["activated_at"], "ACTIVATION_RECEIPT_ACTIVATED_AT")
        expires_at = _aware_time(window["expires_at"], "ACTIVATION_RECEIPT_EXPIRES_AT")
        if ruleset_updated_at > activated_at:
            _deny("ACTIVATION_RECEIPT_RULESET_NEWER_THAN_ACTIVATION")
        if expires_at <= activated_at:
            _deny("ACTIVATION_RECEIPT_WINDOW_ORDER")
        if expires_at - activated_at > timedelta(days=WINDOW_DAYS):
            _deny("ACTIVATION_RECEIPT_WINDOW_EXCEEDS_STAGE1")
        if trusted_now < activated_at or trusted_now >= expires_at:
            _deny("ACTIVATION_RECEIPT_OUTSIDE_TRUSTED_WINDOW")

        if gov["owner_gate_comment"] != OWNER_GATE_COMMENT:
            _deny("ACTIVATION_RECEIPT_OWNER_GATE")
        if gov["production_authority_owner_gate_comment"] != PRODUCTION_AUTHORITY_OWNER_GATE_COMMENT:
            _deny("ACTIVATION_RECEIPT_PRODUCTION_AUTHORITY_GATE")
        if not _nonempty(gov["final_lab_evidence_ref"]) or not _nonempty(gov["final_auditor_evidence_ref"]):
            _deny("ACTIVATION_RECEIPT_FINAL_REVIEW_EVIDENCE")
        return json.loads(_canonical_json(value))

    def _load_authority_manifest(self, receipt: Mapping[str, Any]) -> tuple[dict, str]:
        authority = receipt["authority_manifest"]
        _, payload = self._api(
            f"/repos/{CANONICAL_REPO}/contents/{authority['path']}?ref={authority['commit']}"
        )
        if not isinstance(payload, dict) or payload.get("type") != "file":
            _deny("ACTIVATION_RECEIPT_MANIFEST_RESPONSE")
        if payload.get("sha") != authority["blob_sha"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_BLOB_DRIFT")
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            _deny("ACTIVATION_RECEIPT_MANIFEST_ENCODING")
        try:
            raw = base64.b64decode("".join(payload["content"].split()), validate=True)
            text = raw.decode("utf-8")
        except Exception as exc:
            raise ActivationReceiptDenied("ACTIVATION_RECEIPT_MANIFEST_DECODE") from exc
        digest = hashlib.sha256(raw).hexdigest()
        if digest != authority["sha256"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_SHA256_DRIFT")
        try:
            manifest_raw = json.loads(text)
        except Exception as exc:
            raise ActivationReceiptDenied("ACTIVATION_RECEIPT_MANIFEST_JSON") from exc
        try:
            manifest = validate_source_manifest_structure(manifest_raw)
        except CanonicalAuthorityDenied as exc:
            raise ActivationReceiptDenied("ACTIVATION_RECEIPT_MANIFEST_INVALID:" + str(exc)) from exc

        if not manifest["bundles"] or manifest["safe_mode_active"] is not False:
            _deny("ACTIVATION_RECEIPT_REQUIRES_POPULATED_SAFE_MODE_OFF_MANIFEST")
        if manifest["status"] != authority["status"] or manifest["authority_scope"] != authority["authority_scope"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_STATUS_OR_SCOPE_DRIFT")
        if manifest["policy_generation"] != authority["policy_generation"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_POLICY_GENERATION_DRIFT")
        if manifest["policy_digest"] != authority["policy_digest"] or manifest["policy"] != EXPECTED_POLICY:
            _deny("ACTIVATION_RECEIPT_MANIFEST_POLICY_DRIFT")
        if manifest["revocation_generation"] != authority["revocation_generation"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_REVOCATION_DRIFT")
        if manifest["safe_mode_generation"] != authority["safe_mode_generation"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_SAFE_MODE_GENERATION_DRIFT")
        if manifest["trusted_clock_source"] != authority["trusted_clock_source"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_CLOCK_DRIFT")
        if manifest["freshness_barrier_mode"] != authority["freshness_barrier_mode"]:
            _deny("ACTIVATION_RECEIPT_MANIFEST_FRESHNESS_DRIFT")
        return manifest, digest

    @staticmethod
    def _min_decision_expiry(manifest: Mapping[str, Any]) -> datetime:
        expiries: list[datetime] = []
        for bundle in manifest["bundles"]:
            decisions = [bundle["enqueue_decision"], *bundle["operation_decisions"].values()]
            for decision in decisions:
                expiries.append(
                    _aware_time(decision.get("expires_at"), "ACTIVATION_RECEIPT_DECISION_EXPIRY")
                )
        if not expiries:
            _deny("ACTIVATION_RECEIPT_DECISION_EXPIRY_MISSING")
        return min(expiries)

    def load(self) -> LoadedActivationAnchors:
        main_before, _ = self._fresh_main()
        tag_target, message = self._load_tag_message()
        if tag_target != main_before:
            _deny("ACTIVATION_RECEIPT_TAG_TARGET_NOT_CURRENT_MAIN")
        try:
            receipt_raw = json.loads(message)
        except Exception as exc:
            raise ActivationReceiptDenied("ACTIVATION_RECEIPT_TAG_MESSAGE_JSON") from exc
        canonical_message = _canonical_json(receipt_raw)
        if message != canonical_message:
            _deny("ACTIVATION_RECEIPT_TAG_MESSAGE_NOT_CANONICAL_JSON")

        _, now_after_tag = self._fresh_main()
        receipt = self._validate_receipt(
            receipt_raw, target_main=main_before, trusted_now=now_after_tag
        )

        _, ruleset = self._api(
            f"/repos/{CANONICAL_REPO}/rulesets/{receipt['infrastructure']['journal_ruleset_id']}"
        )
        if not self._ruleset_is_strict(ruleset, receipt=receipt):
            _deny("ACTIVATION_RECEIPT_IMMUTABLE_TAG_AND_JOURNAL_RULESET_MISSING")

        _, runtime_ref = self._api(
            f"/repos/{CANONICAL_REPO}/git/ref/heads/{RUNTIME_BRANCH}"
        )
        obj = runtime_ref.get("object") if isinstance(runtime_ref, dict) else None
        if not isinstance(obj, dict) or obj.get("type") != "commit":
            _deny("ACTIVATION_RECEIPT_RUNTIME_REF_INVALID")
        if obj.get("sha") != receipt["runtime"]["initial_ledger_head"]:
            _deny("ACTIVATION_RECEIPT_RUNTIME_INITIAL_HEAD_DRIFT")

        manifest, _ = self._load_authority_manifest(receipt)
        expires_at = _aware_time(
            receipt["activation_window"]["expires_at"],
            "ACTIVATION_RECEIPT_EXPIRES_AT",
        )
        if expires_at > self._min_decision_expiry(manifest):
            _deny("ACTIVATION_RECEIPT_WINDOW_EXCEEDS_AUTHORITY_DECISION_EXPIRY")

        main_after, trusted_now = self._fresh_main()
        if main_after != main_before:
            _deny("ACTIVATION_RECEIPT_CANONICAL_MAIN_DRIFT")

        receipt_sha256 = hashlib.sha256(canonical_message.encode("utf-8")).hexdigest()
        runtime = receipt["runtime"]
        infra = receipt["infrastructure"]
        authority = receipt["authority_manifest"]
        window = receipt["activation_window"]

        runtime_anchor = VerifiedActivationAnchor(
            activation_receipt_id=receipt["activation_receipt_id"],
            canonical_main=receipt["canonical_main"],
            audited_implementation_head=runtime["audited_implementation_head"],
            runtime_branch=runtime["runtime_branch"],
            runtime_genesis=runtime["runtime_genesis"],
            initial_ledger_head=runtime["initial_ledger_head"],
            activated_at=window["activated_at"],
            max_concurrent_workers=runtime["max_concurrent_workers"],
            max_terminal_tasks=runtime["max_terminal_tasks"],
            runtime_window_days=runtime["runtime_window_days"],
            retry_budget_per_task=runtime["retry_budget_per_task"],
            auto_resume_authorized=runtime["auto_resume_authorized"],
            receipt_ref=ACTIVATION_TAG_REF,
            receipt_sha256=receipt_sha256,
            journal_ruleset_id=infra["journal_ruleset_id"],
            journal_ruleset_updated_at=infra["journal_ruleset_updated_at"],
            journal_ruleset_no_bypass_attested=True,
            writer_key_id=infra["writer_key_id"],
            writer_key_sha256=infra["writer_key_sha256"],
            verified_from_immutable_activation_receipt=True,
        )
        runtime_anchor.validate()

        authority_anchor = VerifiedCanonicalAuthorityAnchor(
            activation_receipt_ref=ACTIVATION_TAG_REF,
            activation_receipt_sha256=receipt_sha256,
            canonical_main=receipt["canonical_main"],
            authority_manifest_commit=authority["commit"],
            authority_manifest_path=authority["path"],
            authority_manifest_blob_sha=authority["blob_sha"],
            authority_manifest_sha256=authority["sha256"],
            authority_manifest_status=authority["status"],
            authority_scope=authority["authority_scope"],
            policy_generation=authority["policy_generation"],
            policy_digest=authority["policy_digest"],
            revocation_generation=authority["revocation_generation"],
            safe_mode_generation=authority["safe_mode_generation"],
            trusted_clock_source=authority["trusted_clock_source"],
            canonical_main_is_complete_authority_freshness_barrier=True,
            verified_from_immutable_activation_receipt=True,
        )
        authority_anchor.validate()

        return LoadedActivationAnchors(
            runtime=runtime_anchor,
            authority=authority_anchor,
            trusted_now=trusted_now,
            receipt=receipt,
        )


def _sample_manifest(*, expires_at: str) -> dict:
    """Minimal populated v2 manifest for selftest only."""
    def decision(did: str, op: str) -> dict:
        return {
            "authorization_decision_id": did,
            "policy_generation": POLICY_GENERATION,
            "policy_digest": EXPECTED_POLICY_DIGEST,
            "actor_role": "EXECUTION",
            "actor_instance": "stage1-worker-1" if op != "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK" else "stage1-router-1",
            "operation": op,
            "target": RUNTIME_BRANCH if op == "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK" else "task:selftest",
            "permission_class_requested": "P1_REVERSIBLE_INTERNAL_WRITE",
            "permission_ceiling": "P1_REVERSIBLE_INTERNAL_WRITE",
            "scope": {
                "operation": op,
                "target": RUNTIME_BRANCH if op == "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK" else "task:selftest",
                "data_exposure_scope": "GITHUB_INTERNAL_SOURCE_AUDIT_ADMIN_METADATA_ONLY" if op == "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK" else "INTERNAL_R1_STATE_ONLY",
            },
            "data_exposure_scope": "GITHUB_INTERNAL_SOURCE_AUDIT_ADMIN_METADATA_ONLY" if op == "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK" else "INTERNAL_R1_STATE_ONLY",
            "issued_at": "2026-08-22T00:00:00+00:00",
            "expires_at": expires_at,
            "grant_ref": "grant-selftest",
            "owner_gate_ref": None,
            "revocation_generation_seen": 2,
            "safe_mode_generation_seen": 2,
            "decision": "ALLOW",
            "reason_codes": ["SELFTEST"],
            "evidence_refs": ["selftest://receipt-loader"],
        }

    enqueue = decision("auth-selftest-enqueue", "R1_STAGE1_ENQUEUE_SOURCE_AUDIT_ADMIN_TASK")
    ops = {
        "checkpoint": decision("auth-selftest-checkpoint", "R1_TASK_CHECKPOINT"),
        "commit": decision("auth-selftest-commit", "R1_SOURCE_REVIEW_COMMIT"),
        "failure": decision("auth-selftest-failure", "R1_TASK_RECORD_FAILURE"),
        "inspect": decision("auth-selftest-inspect", "R1_SOURCE_CACHE_INSPECT_OR_STAGE"),
        "lease": decision("auth-selftest-lease", "R1_TASK_ACQUIRE_LEASE"),
    }
    payload_digest = hashlib.sha256(
        _canonical_json({"enqueue": enqueue, "operations": ops}).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": AUTHORITY_MANIFEST_SCHEMA_V2,
        "status": ACCEPTED_AUTHORITY_STATUS,
        "canonical_authority": True,
        "authority_scope": AUTHORITY_SCOPE,
        "policy_generation": POLICY_GENERATION,
        "policy": EXPECTED_POLICY,
        "policy_digest": EXPECTED_POLICY_DIGEST,
        "revocation_generation": 2,
        "safe_mode_generation": 2,
        "safe_mode_active": False,
        "valid_grant_refs": ["grant-selftest"],
        "trusted_clock_source": TRUSTED_CLOCK_SOURCE,
        "freshness_barrier_mode": FRESHNESS_BARRIER_MODE,
        "external_authority_state_refs": [],
        "bundles": [{
            "bundle_id": "bundle-selftest",
            "envelope_digest": "1" * 64,
            "enqueue_actor_role": "EXECUTION",
            "enqueue_actor_instance": "stage1-router-1",
            "worker_actor_role": "EXECUTION",
            "worker_actor_instance": "stage1-worker-1",
            "enqueue_decision": enqueue,
            "operation_decisions": ops,
            "decision_payload_digest": payload_digest,
        }],
    }


def selftest() -> None:
    main = "a" * 40
    manifest = _sample_manifest(expires_at="2026-08-29T00:00:00+00:00")
    manifest_raw = _canonical_json(manifest).encode("utf-8")
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    manifest_blob = "b" * 40
    initial_head = "c" * 40
    ruleset_id = 123
    ruleset_updated = "2026-08-22T00:00:00Z"
    receipt = {
        "schema_version": ACTIVATION_RECEIPT_SCHEMA,
        "status": ACTIVATION_RECEIPT_STATUS,
        "canonical_repo": CANONICAL_REPO,
        "stage_id": AUTHORITY_SCOPE,
        "activation_receipt_id": "activation-selftest-v1",
        "canonical_main": main,
        "authority_manifest": {
            "commit": main,
            "path": AUTHORITY_MANIFEST_PATH,
            "blob_sha": manifest_blob,
            "sha256": manifest_sha,
            "status": ACCEPTED_AUTHORITY_STATUS,
            "authority_scope": AUTHORITY_SCOPE,
            "policy_generation": POLICY_GENERATION,
            "policy_digest": EXPECTED_POLICY_DIGEST,
            "revocation_generation": 2,
            "safe_mode_generation": 2,
            "trusted_clock_source": TRUSTED_CLOCK_SOURCE,
            "freshness_barrier_mode": FRESHNESS_BARRIER_MODE,
        },
        "runtime": {
            "audited_implementation_head": "d" * 40,
            "runtime_branch": RUNTIME_BRANCH,
            "runtime_genesis": main,
            "initial_ledger_head": initial_head,
            "max_concurrent_workers": MAX_WORKERS,
            "max_tasks_per_invocation": MAX_TASKS_PER_INVOCATION,
            "retry_budget_per_task": RETRY_BUDGET,
            "max_terminal_tasks": MAX_TERMINAL_TASKS,
            "runtime_window_days": WINDOW_DAYS,
            "auto_resume_authorized": False,
            "scheduler_authorized": False,
            "always_on_worker_authorized": False,
        },
        "infrastructure": {
            "journal_ruleset_id": ruleset_id,
            "journal_ruleset_updated_at": ruleset_updated,
            "journal_ruleset_no_bypass_attested": True,
            "writer_key_id": "stage1-writer-key-selftest",
            "writer_key_sha256": "e" * 64,
            "activation_tag_ref": ACTIVATION_TAG_REF,
        },
        "activation_window": {
            "activated_at": "2026-08-22T00:10:00+00:00",
            "expires_at": "2026-08-29T00:00:00+00:00",
        },
        "governance_evidence": {
            "owner_gate_comment": OWNER_GATE_COMMENT,
            "production_authority_owner_gate_comment": PRODUCTION_AUTHORITY_OWNER_GATE_COMMENT,
            "final_lab_evidence_ref": "selftest://lab",
            "final_auditor_evidence_ref": "selftest://auditor",
        },
    }
    message = _canonical_json(receipt)
    ruleset = {
        "id": ruleset_id,
        "updated_at": ruleset_updated,
        "target": "tag",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": [JOURNAL_RULESET_INCLUDE, ACTIVATION_TAG_REF],
                "exclude": [],
            }
        },
        "rules": [
            {"type": "deletion"},
            {"type": "update"},
            {"type": "non_fast_forward"},
        ],
    }
    manifest_b64 = base64.b64encode(manifest_raw).decode("ascii")

    class FakeLoader(ImmutableActivationReceiptLoader):
        def __init__(self):
            self.repo_root = Path(".")

        def _validate_transport(self) -> None:
            return None

        def _api(self, endpoint: str) -> tuple[datetime, Any]:
            now = datetime(2026, 8, 22, 0, 20, tzinfo=timezone.utc)
            if endpoint.endswith("/branches/main"):
                return now, {"commit": {"sha": main}}
            if endpoint.endswith(f"/git/ref/tags/{ACTIVATION_TAG_NAME}"):
                return now, {
                    "ref": ACTIVATION_TAG_REF,
                    "object": {"type": "tag", "sha": "f" * 40},
                }
            if endpoint.endswith("/git/tags/" + "f" * 40):
                return now, {
                    "tag": ACTIVATION_TAG_NAME,
                    "object": {"type": "commit", "sha": main},
                    "message": message,
                }
            if endpoint.endswith(f"/rulesets/{ruleset_id}"):
                return now, ruleset
            if endpoint.endswith(f"/git/ref/heads/{RUNTIME_BRANCH}"):
                return now, {"object": {"type": "commit", "sha": initial_head}}
            if "/contents/" in endpoint:
                return now, {
                    "type": "file",
                    "sha": manifest_blob,
                    "encoding": "base64",
                    "content": manifest_b64,
                }
            raise AssertionError(endpoint)

    loaded = FakeLoader().load()
    assert loaded.runtime.verified_from_immutable_activation_receipt is True
    assert loaded.authority.verified_from_immutable_activation_receipt is True
    assert loaded.runtime.receipt_ref == ACTIVATION_TAG_REF
    assert loaded.authority.activation_receipt_ref == ACTIVATION_TAG_REF
    print("ACTIVATION_RECEIPT_LOADER_DUAL_ANCHOR_PASS")

    bad_ruleset = json.loads(json.dumps(ruleset))
    bad_ruleset["bypass_actors"] = [{"actor_id": 1}]
    assert ImmutableActivationReceiptLoader._ruleset_is_strict(bad_ruleset, receipt=receipt) is False
    print("ACTIVATION_RECEIPT_LOADER_BYPASS_REJECTED")

    bad_ruleset = json.loads(json.dumps(ruleset))
    bad_ruleset["conditions"]["ref_name"]["include"] = [JOURNAL_RULESET_INCLUDE]
    assert ImmutableActivationReceiptLoader._ruleset_is_strict(bad_ruleset, receipt=receipt) is False
    print("ACTIVATION_RECEIPT_LOADER_UNPROTECTED_RECEIPT_TAG_REJECTED")

    bad_receipt = json.loads(message)
    bad_receipt["runtime"]["max_terminal_tasks"] = MAX_TERMINAL_TASKS + 1
    try:
        FakeLoader()._validate_receipt(
            bad_receipt,
            target_main=main,
            trusted_now=datetime(2026, 8, 22, 0, 20, tzinfo=timezone.utc),
        )
    except ActivationReceiptDenied as exc:
        assert str(exc) == "ACTIVATION_RECEIPT_TERMINAL_CEILING"
    else:
        raise AssertionError("widened terminal ceiling must fail")
    print("ACTIVATION_RECEIPT_LOADER_CEILING_DRIFT_REJECTED")

    try:
        FakeLoader()._validate_receipt(
            receipt,
            target_main=main,
            trusted_now=datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc),
        )
    except ActivationReceiptDenied as exc:
        assert str(exc) == "ACTIVATION_RECEIPT_OUTSIDE_TRUSTED_WINDOW"
    else:
        raise AssertionError("expired receipt must fail")
    print("ACTIVATION_RECEIPT_LOADER_TRUSTED_EXPIRY_REJECTED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    parser.error("preactivation module: only --selftest is exposed")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
