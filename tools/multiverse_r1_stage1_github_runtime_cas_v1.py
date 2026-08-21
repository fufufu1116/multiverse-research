#!/usr/bin/env python3
"""Concrete GitHub runtime-ledger CAS adapter for R1 Stage 1.

Pre-activation only. This module does not issue authorization decisions, does
not create the production runtime branch, and does not activate Stage 1.

Production use is fail-closed unless all of the following hold:
- every effective fetch/push origin URL is the canonical repository and Git URL
  rewrite configuration is absent;
- an externally verified immutable activation anchor matches the runtime ledger;
- an active GitHub tag ruleset protects the Stage-1 journal namespace against
  deletion, update, and force-push with no bypass actors;
- canonical main is Fresh Read immediately before every remote mutation;
- every runtime mutation uses expected-old-head CAS and a journal-first commit.
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
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from multiverse_r1_stage1_runtime_v1 import (
    MAX_TERMINAL_TASKS,
    MAX_WORKERS,
    RETRY_BUDGET,
    RUNTIME_BRANCH,
    WINDOW_DAYS,
    RemoteSnapshot,
    Stage1Denied,
    Stage1Tamper,
    claim_control,
    empty_control,
    record_terminal_receipt,
    release_control,
    validate_control,
    validate_write_path,
)
from multiverse_r1_state_v1 import StaleState, empty_state, validate_state

CANONICAL_REPO = "fufufu1116/multiverse-research"
REMOTE_NAME = "origin"
RUNTIME_REF = f"refs/heads/{RUNTIME_BRANCH}"
STATE_PATH = "runtime/r1_source_audit_stage1/exceptions/control_plane/runtime_ledger.json"
LEDGER_SCHEMA = "MULTIVERSE_R1_STAGE1_GITHUB_RUNTIME_LEDGER_v2"
LEDGER_FIELDS = {"schema_version", "sequence", "control", "r1_state"}
JOURNAL_TAG_PREFIX = "multiverse-r1-stage1-ledger-v1"
JOURNAL_RULESET_INCLUDE = f"refs/tags/{JOURNAL_TAG_PREFIX}-*"
MAX_SEQUENCE = 1_000_000

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_JOURNAL_RE = re.compile(
    rf"^refs/tags/{re.escape(JOURNAL_TAG_PREFIX)}-([0-9a-f]{{16}})-s([0-9]{{8}})-t([0-9]{{8}})$"
)


def _deny(code: str, exc=Stage1Denied):
    raise exc(code)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _activation_key(control: Mapping[str, Any]) -> str:
    validate_control(control)
    raw = control["activation_receipt_id"].encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _validate_ledger_payload(payload: Any) -> None:
    if not isinstance(payload, dict) or set(payload) != LEDGER_FIELDS:
        _deny("GITHUB_RUNTIME_LEDGER_SCHEMA", Stage1Tamper)
    if payload["schema_version"] != LEDGER_SCHEMA:
        _deny("GITHUB_RUNTIME_LEDGER_IDENTITY", Stage1Tamper)
    sequence = payload["sequence"]
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not (0 <= sequence <= MAX_SEQUENCE):
        _deny("GITHUB_RUNTIME_LEDGER_SEQUENCE", Stage1Tamper)
    validate_control(payload["control"])
    state = copy.deepcopy(payload["r1_state"])
    validate_state(state)


@dataclass(frozen=True)
class VerifiedActivationAnchor:
    """Identity facts read from a separately reviewed immutable activation receipt.

    This adapter never mints this object from runtime state. The activation path
    must supply it only after independently verifying the immutable receipt.
    """

    activation_receipt_id: str
    canonical_main: str
    audited_implementation_head: str
    runtime_branch: str
    runtime_genesis: str
    activated_at: str
    max_concurrent_workers: int
    max_terminal_tasks: int
    runtime_window_days: int
    retry_budget_per_task: int
    auto_resume_authorized: bool
    receipt_ref: str
    receipt_sha256: str
    journal_ruleset_id: int
    journal_ruleset_updated_at: str
    journal_ruleset_no_bypass_attested: bool
    verified_from_immutable_activation_receipt: bool

    def validate(self) -> None:
        if not self.verified_from_immutable_activation_receipt:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_UNVERIFIED", Stage1Tamper)
        if not self.activation_receipt_id or not self.receipt_ref:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_IDENTITY_MISSING", Stage1Tamper)
        for value in (self.canonical_main, self.audited_implementation_head, self.runtime_genesis):
            if not _HEX40.fullmatch(value):
                _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_SHA_INVALID", Stage1Tamper)
        if not _HEX64.fullmatch(self.receipt_sha256):
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_DIGEST_INVALID", Stage1Tamper)
        if not isinstance(self.journal_ruleset_id, int) or isinstance(self.journal_ruleset_id, bool) or self.journal_ruleset_id <= 0:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_RULESET_ID", Stage1Tamper)
        if not self.journal_ruleset_no_bypass_attested:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_RULESET_BYPASS_ATTESTATION", Stage1Tamper)
        try:
            ruleset_dt = datetime.fromisoformat(self.journal_ruleset_updated_at.replace("Z", "+00:00"))
        except Exception as exc:
            raise Stage1Tamper("GITHUB_RUNTIME_ACTIVATION_ANCHOR_RULESET_TIME_INVALID") from exc
        if ruleset_dt.tzinfo is None:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_RULESET_TIME_NOT_AWARE", Stage1Tamper)
        if self.runtime_branch != RUNTIME_BRANCH:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_BRANCH_MISMATCH", Stage1Tamper)
        try:
            dt = datetime.fromisoformat(self.activated_at.replace("Z", "+00:00"))
        except Exception as exc:
            raise Stage1Tamper("GITHUB_RUNTIME_ACTIVATION_ANCHOR_TIME_INVALID") from exc
        if dt.tzinfo is None:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_TIME_NOT_AWARE", Stage1Tamper)
        if self.max_concurrent_workers != MAX_WORKERS:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_WORKER_CEILING", Stage1Tamper)
        if self.max_terminal_tasks != MAX_TERMINAL_TASKS:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_TERMINAL_CEILING", Stage1Tamper)
        if self.runtime_window_days != WINDOW_DAYS:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_WINDOW_CEILING", Stage1Tamper)
        if self.retry_budget_per_task != RETRY_BUDGET:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_RETRY_BUDGET", Stage1Tamper)
        if self.auto_resume_authorized is not False:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_AUTO_RESUME", Stage1Tamper)


@dataclass(frozen=True)
class _InternalSnapshot:
    public: RemoteSnapshot
    sequence: int
    payload: dict


class GitHubRuntimeCASLedger:
    """Concrete production GitHub CAS ledger. No authorization issuance."""

    def __init__(self, repo_root: Path | str, *, activation_anchor: VerifiedActivationAnchor):
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            _deny("GITHUB_RUNTIME_REPO_NOT_GIT_WORKTREE")
        validate_write_path(RUNTIME_BRANCH, STATE_PATH)
        if not isinstance(activation_anchor, VerifiedActivationAnchor):
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_TYPE", Stage1Tamper)
        activation_anchor.validate()
        self.activation_anchor = activation_anchor
        self._validate_origin()
        self._verify_repository_journal_protection()

    def _git(
        self,
        *args: str,
        input_text: Optional[str] = None,
        check: bool = True,
        env: Optional[Mapping[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        proc = subprocess.run(
            ["git", "-C", str(self.repo_root), *args],
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=merged_env,
        )
        if check and proc.returncode != 0:
            raise Stage1Denied(
                "GITHUB_RUNTIME_GIT_COMMAND_FAILED:"
                + " ".join(args[:3])
                + ":"
                + proc.stderr.strip()[:240]
            )
        return proc

    @staticmethod
    def _accepted_origin_urls() -> set[str]:
        return {
            f"https://github.com/{CANONICAL_REPO}",
            f"https://github.com/{CANONICAL_REPO}.git",
            f"git@github.com:{CANONICAL_REPO}.git",
            f"ssh://git@github.com/{CANONICAL_REPO}.git",
        }

    @classmethod
    def _assert_canonical_origin_urls(cls, fetch_urls: list[str], push_urls: list[str]) -> None:
        accepted = cls._accepted_origin_urls()
        if not fetch_urls or not push_urls:
            _deny("GITHUB_RUNTIME_ORIGIN_URL_MISSING", Stage1Tamper)
        if any(url not in accepted for url in fetch_urls):
            _deny("GITHUB_RUNTIME_FETCH_ORIGIN_IDENTITY_MISMATCH", Stage1Tamper)
        if any(url not in accepted for url in push_urls):
            _deny("GITHUB_RUNTIME_PUSH_ORIGIN_IDENTITY_MISMATCH", Stage1Tamper)

    @staticmethod
    def _assert_no_url_rewrite_config(config_rows: str) -> None:
        if any(line.strip() for line in config_rows.splitlines()):
            _deny("GITHUB_RUNTIME_URL_REWRITE_CONFIG_PROHIBITED", Stage1Tamper)

    def _validate_origin(self) -> None:
        fetch_urls = [x.strip() for x in self._git("remote", "get-url", "--all", REMOTE_NAME).stdout.splitlines() if x.strip()]
        push_urls = [x.strip() for x in self._git("remote", "get-url", "--push", "--all", REMOTE_NAME).stdout.splitlines() if x.strip()]
        self._assert_canonical_origin_urls(fetch_urls, push_urls)
        configs = self._git("config", "--show-origin", "--list", check=False)
        if configs.returncode != 0:
            _deny("GITHUB_RUNTIME_URL_REWRITE_CONFIG_QUERY_FAILED", Stage1Tamper)
        rewrite_rows = []
        for line in configs.stdout.splitlines():
            lower = line.lower()
            if "url." in lower and (".insteadof=" in lower or ".pushinsteadof=" in lower):
                rewrite_rows.append(line)
        self._assert_no_url_rewrite_config("\n".join(rewrite_rows))

    def _gh_api_json(self, endpoint: str) -> Any:
        if shutil.which("gh") is None:
            _deny("GITHUB_RUNTIME_GH_CLI_REQUIRED_FOR_RULESET_VERIFY", Stage1Tamper)
        proc = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github+json", endpoint],
            cwd=str(self.repo_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise Stage1Tamper("GITHUB_RUNTIME_RULESET_API_UNAVAILABLE:" + proc.stderr.strip()[:200])
        try:
            return json.loads(proc.stdout)
        except Exception as exc:
            raise Stage1Tamper("GITHUB_RUNTIME_RULESET_API_JSON_INVALID") from exc

    @staticmethod
    def _ruleset_is_strict_journal_protection(detail: Mapping[str, Any]) -> bool:
        if not isinstance(detail, dict):
            return False
        if detail.get("target") != "tag":
            return False
        if detail.get("enforcement") not in {"active", "enabled", "always"}:
            return False
        conditions = detail.get("conditions")
        if not isinstance(conditions, dict):
            return False
        ref_name = conditions.get("ref_name")
        if not isinstance(ref_name, dict):
            return False
        includes = ref_name.get("include")
        excludes = ref_name.get("exclude")
        if not isinstance(includes, list) or JOURNAL_RULESET_INCLUDE not in includes:
            return False
        if not isinstance(excludes, list) or excludes:
            return False
        rules = detail.get("rules")
        if not isinstance(rules, list):
            return False
        types = {rule.get("type") for rule in rules if isinstance(rule, dict)}
        if not {"deletion", "update", "non_fast_forward"}.issubset(types) or "creation" in types:
            return False
        if "bypass_actors" in detail and detail.get("bypass_actors") != []:
            return False
        return True

    def _verify_repository_journal_protection(self) -> None:
        a = self.activation_anchor
        detail = self._gh_api_json(f"/repos/{CANONICAL_REPO}/rulesets/{a.journal_ruleset_id}")
        if not self._ruleset_is_strict_journal_protection(detail):
            _deny("GITHUB_RUNTIME_IMMUTABLE_JOURNAL_RULESET_MISSING", Stage1Tamper)
        if detail.get("id") != a.journal_ruleset_id:
            _deny("GITHUB_RUNTIME_JOURNAL_RULESET_ID_DRIFT", Stage1Tamper)
        if detail.get("updated_at") != a.journal_ruleset_updated_at:
            _deny("GITHUB_RUNTIME_JOURNAL_RULESET_VERSION_DRIFT", Stage1Tamper)
        if not a.journal_ruleset_no_bypass_attested:
            _deny("GITHUB_RUNTIME_JOURNAL_RULESET_BYPASS_UNATTESTED", Stage1Tamper)

    def _assert_activation_anchor(self, control: Mapping[str, Any], current_main: str) -> None:
        validate_control(control)
        a = self.activation_anchor
        a.validate()
        expected = {
            "activation_receipt_id": a.activation_receipt_id,
            "canonical_main": a.canonical_main,
            "audited_implementation_head": a.audited_implementation_head,
            "runtime_branch": a.runtime_branch,
            "runtime_genesis": a.runtime_genesis,
            "activated_at": a.activated_at,
        }
        for field, value in expected.items():
            if control[field] != value:
                _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_MISMATCH", Stage1Tamper)
        if current_main != a.canonical_main:
            _deny("GITHUB_RUNTIME_ACTIVATION_ANCHOR_STALE_MAIN", StaleState)

    def _remote_ref(self, ref: str) -> Optional[str]:
        self._validate_origin()
        proc = self._git("ls-remote", "--refs", REMOTE_NAME, ref)
        rows = [line.split("\t", 1) for line in proc.stdout.splitlines() if line.strip()]
        exact = [sha for sha, name in rows if name == ref]
        if not exact:
            return None
        if len(exact) != 1 or not _HEX40.fullmatch(exact[0]):
            _deny("GITHUB_RUNTIME_REMOTE_REF_AMBIGUOUS", Stage1Tamper)
        return exact[0]

    def _fresh_main(self) -> str:
        main = self._remote_ref("refs/heads/main")
        if main is None:
            _deny("GITHUB_RUNTIME_CANONICAL_MAIN_MISSING", StaleState)
        return main

    def _assert_main_unchanged(self, expected_main: str) -> None:
        if self._fresh_main() != expected_main:
            _deny("GITHUB_RUNTIME_MID_MUTATION_MAIN_DRIFT", StaleState)

    def _fetch_runtime_head(self, expected: Optional[str] = None) -> str:
        actual = self._remote_ref(RUNTIME_REF)
        if actual is None:
            _deny("GITHUB_RUNTIME_BRANCH_MISSING")
        if expected is not None and actual != expected:
            _deny("GITHUB_RUNTIME_EXPECTED_OLD_HEAD_MISMATCH", Stage1Tamper)
        self._git("fetch", "--no-tags", REMOTE_NAME, RUNTIME_REF)
        fetched = self._git("rev-parse", "FETCH_HEAD").stdout.strip()
        if fetched != actual:
            _deny("GITHUB_RUNTIME_FETCH_HEAD_MISMATCH", Stage1Tamper)
        return actual

    def _runtime_payload(self, head: str) -> dict:
        proc = self._git("show", f"{head}:{STATE_PATH}", check=False)
        if proc.returncode != 0:
            _deny("GITHUB_RUNTIME_LEDGER_FILE_MISSING", Stage1Tamper)
        try:
            payload = json.loads(proc.stdout)
        except Exception as exc:
            raise Stage1Tamper("GITHUB_RUNTIME_LEDGER_JSON_INVALID") from exc
        _validate_ledger_payload(payload)
        return payload

    def _assert_runtime_history_paths(self, genesis: str, head: str) -> None:
        if not _HEX40.fullmatch(genesis) or not _HEX40.fullmatch(head):
            _deny("GITHUB_RUNTIME_HISTORY_SHA_INVALID", Stage1Tamper)
        anc = self._git("merge-base", "--is-ancestor", genesis, head, check=False)
        if anc.returncode != 0:
            _deny("GITHUB_RUNTIME_GENESIS_ANCESTRY_TAMPER", Stage1Tamper)
        touched = self._git("log", "--format=", "--name-only", f"{genesis}..{head}").stdout.splitlines()
        for path in sorted({p.strip() for p in touched if p.strip()}):
            validate_write_path(RUNTIME_BRANCH, path)

    def _journal_entries(self, control: Mapping[str, Any]) -> list[tuple[int, int, str, str]]:
        key = _activation_key(control)
        glob = f"refs/tags/{JOURNAL_TAG_PREFIX}-{key}-s*-t*"
        proc = self._git("ls-remote", "--refs", REMOTE_NAME, glob)
        out: list[tuple[int, int, str, str]] = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            sha, ref = line.split("\t", 1)
            match = _JOURNAL_RE.fullmatch(ref)
            if not match or match.group(1) != key or not _HEX40.fullmatch(sha):
                _deny("GITHUB_RUNTIME_JOURNAL_IDENTITY", Stage1Tamper)
            out.append((int(match.group(2)), int(match.group(3)), sha, ref))
        out.sort()
        for i, (seq, _, _, _) in enumerate(out, start=1):
            if seq != i:
                _deny("GITHUB_RUNTIME_JOURNAL_SEQUENCE_GAP", Stage1Tamper)
        return out

    def _verify_journal(self, *, control: Mapping[str, Any], sequence: int, head: str) -> int:
        entries = self._journal_entries(control)
        if sequence == 0:
            if entries:
                _deny("GITHUB_RUNTIME_JOURNAL_AHEAD_OF_LEDGER", Stage1Tamper)
            if control["terminal_count"] != 0:
                _deny("GITHUB_RUNTIME_TERMINAL_WITHOUT_JOURNAL", Stage1Tamper)
            return 0
        if len(entries) != sequence:
            _deny("GITHUB_RUNTIME_JOURNAL_LEDGER_SEQUENCE_MISMATCH", Stage1Tamper)
        last_seq, _, _, last_ref = entries[-1]
        if last_seq != sequence:
            _deny("GITHUB_RUNTIME_JOURNAL_LAST_SEQUENCE_MISMATCH", Stage1Tamper)
        self._git("fetch", "--no-tags", REMOTE_NAME, last_ref)
        target = self._git("rev-parse", "FETCH_HEAD^{}").stdout.strip()
        if target != head:
            _deny("GITHUB_RUNTIME_HISTORY_REWRITE_OR_ROLLBACK", Stage1Tamper)
        high_water = max(terminal for _, terminal, _, _ in entries)
        if high_water != control["terminal_count"]:
            _deny("GITHUB_RUNTIME_TERMINAL_HIGH_WATER_MISMATCH", Stage1Tamper)
        return high_water

    def _load_internal(self, expected_head: Optional[str] = None) -> _InternalSnapshot:
        self._verify_repository_journal_protection()
        current_main = self._fresh_main()
        head = self._fetch_runtime_head(expected_head)
        payload = self._runtime_payload(head)
        control = payload["control"]
        self._assert_activation_anchor(control, current_main)
        if control["canonical_main"] != current_main:
            _deny("GITHUB_RUNTIME_STALE_CANONICAL_MAIN", StaleState)
        genesis = control["runtime_genesis"]
        self._assert_runtime_history_paths(genesis, head)
        high_water = self._verify_journal(control=control, sequence=payload["sequence"], head=head)
        snapshot = RemoteSnapshot(
            remote_head=head,
            canonical_main=current_main,
            runtime_genesis=genesis,
            genesis_is_ancestor=True,
            high_water_count=high_water,
            control=copy.deepcopy(control),
            r1_state=copy.deepcopy(payload["r1_state"]),
        )
        return _InternalSnapshot(public=snapshot, sequence=payload["sequence"], payload=payload)

    def load_snapshot(self) -> RemoteSnapshot:
        return self._load_internal().public

    @staticmethod
    def _assert_control_identity_preserved(old: Mapping[str, Any], new: Mapping[str, Any]) -> None:
        validate_control(old)
        validate_control(new)
        immutable = (
            "schema_version", "stage_id", "activation_receipt_id", "canonical_main",
            "audited_implementation_head", "runtime_branch", "runtime_genesis", "activated_at",
        )
        for field in immutable:
            if old[field] != new[field]:
                _deny("GITHUB_RUNTIME_CONTROL_IDENTITY_MUTATION", Stage1Tamper)
        old_ids = list(old["counted_receipt_ids"])
        new_ids = list(new["counted_receipt_ids"])
        if new_ids[: len(old_ids)] != old_ids:
            _deny("GITHUB_RUNTIME_COUNTED_RECEIPT_HISTORY_REWRITE", Stage1Tamper)
        if new["terminal_count"] < old["terminal_count"]:
            _deny("GITHUB_RUNTIME_TERMINAL_COUNT_ROLLBACK", Stage1Tamper)
        if old["paused"] and not new["paused"]:
            _deny("GITHUB_RUNTIME_AUTO_RESUME_DENIED", Stage1Tamper)

    def _build_commit(self, *, expected_head: str, payload: Mapping[str, Any], message: str) -> str:
        _validate_ledger_payload(payload)
        serialized = json.dumps(payload, sort_keys=True, indent=2) + "\n"
        with tempfile.TemporaryDirectory() as td:
            index = str(Path(td) / "index")
            env = {"GIT_INDEX_FILE": index}
            self._git("read-tree", expected_head, env=env)
            blob = self._git("hash-object", "-w", "--stdin", input_text=serialized).stdout.strip()
            if not _HEX40.fullmatch(blob):
                _deny("GITHUB_RUNTIME_BLOB_CREATE_FAILED")
            self._git("update-index", "--add", "--cacheinfo", f"100644,{blob},{STATE_PATH}", env=env)
            tree = self._git("write-tree", env=env).stdout.strip()
        commit = self._git(
            "-c", "user.name=Multiverse Stage1 Control Plane",
            "-c", "user.email=multiverse-stage1-control-plane@example.invalid",
            "commit-tree", tree, "-p", expected_head, "-m", message,
        ).stdout.strip()
        if not _HEX40.fullmatch(commit):
            _deny("GITHUB_RUNTIME_COMMIT_CREATE_FAILED")
        if self._git("merge-base", "--is-ancestor", expected_head, commit, check=False).returncode != 0:
            _deny("GITHUB_RUNTIME_NON_FAST_FORWARD_COMMIT", Stage1Tamper)
        return commit

    def _after_journal_claim_for_test_only(self) -> None:
        return None

    def _claim_journal_then_branch(self, *, old: _InternalSnapshot, new_payload: Mapping[str, Any], message: str) -> RemoteSnapshot:
        new_sequence = old.sequence + 1
        if new_sequence > MAX_SEQUENCE:
            _deny("GITHUB_RUNTIME_SEQUENCE_CEILING")
        payload = copy.deepcopy(dict(new_payload))
        payload["sequence"] = new_sequence
        _validate_ledger_payload(payload)
        self._assert_activation_anchor(payload["control"], old.public.canonical_main)
        new_commit = self._build_commit(expected_head=old.public.remote_head, payload=payload, message=message)

        control = payload["control"]
        key = _activation_key(control)
        terminal = control["terminal_count"]
        tag_ref = f"refs/tags/{JOURNAL_TAG_PREFIX}-{key}-s{new_sequence:08d}-t{terminal:08d}"
        if self._remote_ref(tag_ref) is not None:
            _deny("GITHUB_RUNTIME_JOURNAL_SEQUENCE_ALREADY_CLAIMED", Stage1Tamper)

        self._validate_origin()
        self._verify_repository_journal_protection()
        self._assert_main_unchanged(control["canonical_main"])
        journal_push = self._git(
            "push", REMOTE_NAME, f"{new_commit}:{tag_ref}", f"--force-with-lease={tag_ref}:", check=False
        )
        if journal_push.returncode != 0:
            _deny("GITHUB_RUNTIME_JOURNAL_CAS_FAILED", Stage1Tamper)

        self._after_journal_claim_for_test_only()

        self._validate_origin()
        self._verify_repository_journal_protection()
        self._assert_main_unchanged(control["canonical_main"])
        branch_push = self._git(
            "push", REMOTE_NAME, f"{new_commit}:{RUNTIME_REF}",
            f"--force-with-lease={RUNTIME_REF}:{old.public.remote_head}", check=False,
        )
        if branch_push.returncode != 0:
            _deny("GITHUB_RUNTIME_BRANCH_CAS_FAILED_JOURNAL_LEFT_FOR_REPAIR", Stage1Tamper)
        if self._remote_ref(RUNTIME_REF) != new_commit:
            _deny("GITHUB_RUNTIME_POST_PUSH_HEAD_MISMATCH", Stage1Tamper)
        return self._load_internal(expected_head=new_commit).public

    def claim_invocation(self, *, expected_remote_head: str, claim_id: str, claimed_control: Mapping[str, Any]) -> RemoteSnapshot:
        old = self._load_internal(expected_head=expected_remote_head)
        self._assert_control_identity_preserved(old.public.control, claimed_control)
        if claimed_control["invocation_claim_id"] != claim_id:
            _deny("GITHUB_RUNTIME_CLAIM_OWNER_MISMATCH", Stage1Tamper)
        if claimed_control["invocation_claim_expires_at"] is None:
            _deny("GITHUB_RUNTIME_CLAIM_EXPIRY_MISSING", Stage1Tamper)
        payload = copy.deepcopy(old.payload)
        payload["control"] = copy.deepcopy(dict(claimed_control))
        return self._claim_journal_then_branch(old=old, new_payload=payload, message=f"Stage1 claim {claim_id}")

    def persist_r1_state(self, *, expected_remote_head: str, claim_id: str, r1_state: Mapping[str, Any]) -> RemoteSnapshot:
        old = self._load_internal(expected_head=expected_remote_head)
        if old.public.control["invocation_claim_id"] != claim_id:
            _deny("GITHUB_RUNTIME_STALE_NONOWNER_PERSIST", Stage1Tamper)
        state = copy.deepcopy(dict(r1_state))
        validate_state(state)
        payload = copy.deepcopy(old.payload)
        payload["r1_state"] = state
        return self._claim_journal_then_branch(old=old, new_payload=payload, message=f"Stage1 persist R1 state {claim_id}")

    def release_invocation(self, *, expected_remote_head: str, claim_id: str, released_control: Mapping[str, Any]) -> RemoteSnapshot:
        old = self._load_internal(expected_head=expected_remote_head)
        if old.public.control["invocation_claim_id"] != claim_id:
            _deny("GITHUB_RUNTIME_STALE_NONOWNER_RELEASE", Stage1Tamper)
        self._assert_control_identity_preserved(old.public.control, released_control)
        if released_control["invocation_claim_id"] is not None or released_control["invocation_claim_expires_at"] is not None:
            _deny("GITHUB_RUNTIME_RELEASE_DID_NOT_CLEAR_CLAIM", Stage1Tamper)
        payload = copy.deepcopy(old.payload)
        payload["control"] = copy.deepcopy(dict(released_control))
        return self._claim_journal_then_branch(old=old, new_payload=payload, message=f"Stage1 release {claim_id}")


def _run_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", "-C", str(cwd), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


def _install_selftest_journal_protection_hook(bare: Path) -> None:
    hook = bare / "hooks" / "pre-receive"
    hook.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        "zero=0000000000000000000000000000000000000000\n"
        "while read old new ref; do\n"
        f"  case \"$ref\" in refs/tags/{JOURNAL_TAG_PREFIX}-*)\n"
        "    if [ \"$old\" != \"$zero\" ]; then echo protected-journal-update-denied >&2; exit 1; fi;;\n"
        "  esac\n"
        "done\n"
    )
    hook.chmod(0o755)


def _setup_selftest_repo(root: Path, suffix: str) -> tuple[Path, Path, str, str, VerifiedActivationAnchor]:
    bare = root / f"remote-{suffix}.git"
    work = root / f"work-{suffix}"
    _run_git(root, "init", "--bare", str(bare))
    _install_selftest_journal_protection_hook(bare)
    _run_git(root, "clone", str(bare), str(work))
    _run_git(work, "config", "user.name", "Stage1 Selftest")
    _run_git(work, "config", "user.email", "stage1-selftest@example.invalid")
    (work / "README.md").write_text("stage1 adapter selftest\n")
    _run_git(work, "add", "README.md")
    _run_git(work, "commit", "-m", "selftest main")
    _run_git(work, "branch", "-M", "main")
    _run_git(work, "push", "-u", "origin", "main")
    main = _run_git(work, "rev-parse", "HEAD").stdout.strip()

    activated_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc).isoformat()
    receipt_id = f"selftest-activation-{suffix}"
    audited_head = "a" * 40
    anchor = VerifiedActivationAnchor(
        activation_receipt_id=receipt_id,
        canonical_main=main,
        audited_implementation_head=audited_head,
        runtime_branch=RUNTIME_BRANCH,
        runtime_genesis=main,
        activated_at=activated_at,
        max_concurrent_workers=MAX_WORKERS,
        max_terminal_tasks=MAX_TERMINAL_TASKS,
        runtime_window_days=WINDOW_DAYS,
        retry_budget_per_task=RETRY_BUDGET,
        auto_resume_authorized=False,
        receipt_ref=f"selftest://{suffix}",
        receipt_sha256=hashlib.sha256(f"selftest-{suffix}".encode()).hexdigest(),
        journal_ruleset_id=424242,
        journal_ruleset_updated_at="2026-08-21T12:00:00+00:00",
        journal_ruleset_no_bypass_attested=True,
        verified_from_immutable_activation_receipt=True,
    )

    _run_git(work, "checkout", "-b", RUNTIME_BRANCH, main)
    control = empty_control(
        activation_receipt_id=receipt_id,
        canonical_main=main,
        audited_implementation_head=audited_head,
        runtime_genesis=main,
        activated_at=datetime.fromisoformat(activated_at),
    )
    payload = {"schema_version": LEDGER_SCHEMA, "sequence": 0, "control": control, "r1_state": empty_state()}
    path = work / STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    _run_git(work, "add", STATE_PATH)
    _run_git(work, "commit", "-m", "selftest runtime genesis state")
    _run_git(work, "push", "-u", "origin", RUNTIME_BRANCH)
    head = _run_git(work, "rev-parse", "HEAD").stdout.strip()
    _run_git(work, "checkout", "main")
    return work, bare, main, head, anchor


def selftest() -> None:
    class LocalBareLedger(GitHubRuntimeCASLedger):
        """Function-local only: cannot be imported as a production bypass."""

        def _validate_origin(self) -> None:
            url = self._git("remote", "get-url", REMOTE_NAME).stdout.strip()
            if not url:
                _deny("SELFTEST_REMOTE_MISSING")

        def _verify_repository_journal_protection(self) -> None:
            return None

    class CrashAfterJournalLedger(LocalBareLedger):
        def _after_journal_claim_for_test_only(self) -> None:
            raise RuntimeError("SELFTEST_INJECTED_JOURNAL_FIRST_CRASH")

    class MainDriftAfterJournalLedger(LocalBareLedger):
        def _after_journal_claim_for_test_only(self) -> None:
            self._git("checkout", "main")
            p = self.repo_root / "drift.txt"
            p.write_text("main drift\n")
            self._git("add", "drift.txt")
            self._git("-c", "user.name=Stage1 Selftest", "-c", "user.email=stage1-selftest@example.invalid", "commit", "-m", "selftest main drift")
            self._git("push", REMOTE_NAME, "main")

    accepted = sorted(GitHubRuntimeCASLedger._accepted_origin_urls())
    GitHubRuntimeCASLedger._assert_canonical_origin_urls([accepted[0]], [accepted[1]])
    try:
        GitHubRuntimeCASLedger._assert_canonical_origin_urls([accepted[0]], ["/tmp/evil.git"])
        raise AssertionError("pushurl redirect unexpectedly accepted")
    except Stage1Tamper:
        pass
    try:
        GitHubRuntimeCASLedger._assert_no_url_rewrite_config("file:/tmp/.gitconfig url.x.pushInsteadOf evil")
        raise AssertionError("pushInsteadOf unexpectedly accepted")
    except Stage1Tamper:
        pass
    print("GITHUB_RUNTIME_FETCH_AND_PUSH_ORIGIN_BINDING_PASS")

    good_ruleset = {
        "id": 424242, "updated_at": "2026-08-21T12:00:00+00:00",
        "target": "tag", "enforcement": "active", "bypass_actors": [],
        "conditions": {"ref_name": {"include": [JOURNAL_RULESET_INCLUDE], "exclude": []}},
        "rules": [{"type": "deletion"}, {"type": "update"}, {"type": "non_fast_forward"}],
    }
    assert GitHubRuntimeCASLedger._ruleset_is_strict_journal_protection(good_ruleset)
    bad_ruleset = copy.deepcopy(good_ruleset)
    bad_ruleset["rules"] = [{"type": "deletion"}]
    assert not GitHubRuntimeCASLedger._ruleset_is_strict_journal_protection(bad_ruleset)
    bad_bypass = copy.deepcopy(good_ruleset)
    bad_bypass["bypass_actors"] = [{"actor_type": "RepositoryRole", "actor_id": 5}]
    assert not GitHubRuntimeCASLedger._ruleset_is_strict_journal_protection(bad_bypass)
    print("GITHUB_RUNTIME_IMMUTABLE_JOURNAL_RULESET_VALIDATION_PASS")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        work, _, _, initial_head, anchor = _setup_selftest_repo(root, "cas")
        a = LocalBareLedger(work, activation_anchor=anchor)
        b = LocalBareLedger(work, activation_anchor=anchor)
        snap_a = a.load_snapshot()
        snap_b = b.load_snapshot()
        assert snap_a.remote_head == snap_b.remote_head == initial_head
        claimed_control = claim_control(snap_a.control, claim_id="claim-a", trusted_now=datetime(2026, 8, 21, 12, 1, tzinfo=timezone.utc))
        claimed = a.claim_invocation(expected_remote_head=snap_a.remote_head, claim_id="claim-a", claimed_control=claimed_control)
        try:
            b.claim_invocation(
                expected_remote_head=snap_b.remote_head,
                claim_id="claim-b",
                claimed_control=claim_control(snap_b.control, claim_id="claim-b", trusted_now=datetime(2026, 8, 21, 12, 1, tzinfo=timezone.utc)),
            )
            raise AssertionError("stale second claim unexpectedly succeeded")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_EXPECTED_OLD_HEAD_CAS_PASS")

        try:
            a.persist_r1_state(expected_remote_head=claimed.remote_head, claim_id="not-owner", r1_state=claimed.r1_state)
            raise AssertionError("nonowner persist unexpectedly succeeded")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_STALE_NONOWNER_REJECTED")

        persisted = a.persist_r1_state(expected_remote_head=claimed.remote_head, claim_id="claim-a", r1_state=claimed.r1_state)
        terminal_control = record_terminal_receipt(persisted.control, "receipt-selftest-1")
        released_control = release_control(terminal_control, claim_id="claim-a")
        released = a.release_invocation(expected_remote_head=persisted.remote_head, claim_id="claim-a", released_control=released_control)
        assert released.control["terminal_count"] == released.high_water_count == 1
        print("GITHUB_RUNTIME_APPEND_ONLY_JOURNAL_HIGH_WATER_PASS")

        key = _activation_key(released.control)
        journal_refs = _run_git(work, "ls-remote", "--refs", "origin", f"refs/tags/{JOURNAL_TAG_PREFIX}-{key}-*").stdout.splitlines()
        latest_ref = sorted(line.split("\t", 1)[1] for line in journal_refs)[-1]
        delete = _run_git(work, "push", "origin", f":{latest_ref}", check=False)
        assert delete.returncode != 0
        rollback = _run_git(work, "push", "origin", f"{initial_head}:{RUNTIME_REF}", "--force", check=False)
        assert rollback.returncode == 0
        try:
            a.load_snapshot()
            raise AssertionError("rollback after denied journal deletion unexpectedly accepted")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_JOURNAL_DELETION_PLUS_ROLLBACK_BLOCKED")

        work2, _, _, _, anchor2 = _setup_selftest_repo(root, "crash")
        crash_ledger = CrashAfterJournalLedger(work2, activation_anchor=anchor2)
        s2 = crash_ledger.load_snapshot()
        c2 = claim_control(s2.control, claim_id="crash-claim", trusted_now=datetime(2026, 8, 21, 12, 1, tzinfo=timezone.utc))
        try:
            crash_ledger.claim_invocation(expected_remote_head=s2.remote_head, claim_id="crash-claim", claimed_control=c2)
            raise AssertionError("journal-first crash not injected")
        except RuntimeError as exc:
            assert "SELFTEST_INJECTED_JOURNAL_FIRST_CRASH" in str(exc)
        try:
            LocalBareLedger(work2, activation_anchor=anchor2).load_snapshot()
            raise AssertionError("journal-ahead crash state unexpectedly accepted")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_JOURNAL_FIRST_CRASH_FAIL_CLOSED_PASS")

        work3, _, _, original3, anchor3 = _setup_selftest_repo(root, "maindrift")
        drift_ledger = MainDriftAfterJournalLedger(work3, activation_anchor=anchor3)
        s3 = drift_ledger.load_snapshot()
        c3 = claim_control(s3.control, claim_id="drift-claim", trusted_now=datetime(2026, 8, 21, 12, 1, tzinfo=timezone.utc))
        try:
            drift_ledger.claim_invocation(expected_remote_head=s3.remote_head, claim_id="drift-claim", claimed_control=c3)
            raise AssertionError("mid-mutation main drift unexpectedly accepted")
        except StaleState:
            pass
        assert _run_git(work3, "ls-remote", "--refs", "origin", RUNTIME_REF).stdout.split("\t", 1)[0] == original3
        print("GITHUB_RUNTIME_MID_MUTATION_MAIN_DRIFT_DENIED")

        work4, _, _, head4, anchor4 = _setup_selftest_repo(root, "rekey")
        l4 = LocalBareLedger(work4, activation_anchor=anchor4)
        s4 = l4.load_snapshot()
        tampered = copy.deepcopy(s4.control)
        tampered["activation_receipt_id"] = "attacker-new-activation"
        payload4 = {"schema_version": LEDGER_SCHEMA, "sequence": 0, "control": tampered, "r1_state": s4.r1_state}
        forged = l4._build_commit(expected_head=head4, payload=payload4, message="selftest activation rekey")
        _run_git(work4, "push", "origin", f"{forged}:{RUNTIME_REF}", "--force")
        try:
            l4.load_snapshot()
            raise AssertionError("activation rekey unexpectedly accepted")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_ACTIVATION_REKEY_REJECTED_BY_EXTERNAL_ANCHOR")

        work5, _, _, _, anchor5 = _setup_selftest_repo(root, "paths")
        ledger5 = LocalBareLedger(work5, activation_anchor=anchor5)
        ledger5.load_snapshot()
        _run_git(work5, "fetch", "origin", RUNTIME_REF)
        _run_git(work5, "checkout", "-B", "tamper", "FETCH_HEAD")
        forbidden = work5 / "governance" / "FORBIDDEN_RUNTIME_WRITE.txt"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text("not allowed\n")
        _run_git(work5, "add", "governance/FORBIDDEN_RUNTIME_WRITE.txt")
        _run_git(work5, "commit", "-m", "forbidden runtime drift")
        forbidden.unlink()
        _run_git(work5, "add", "-u")
        _run_git(work5, "commit", "-m", "revert forbidden runtime drift")
        tampered_head = _run_git(work5, "rev-parse", "HEAD").stdout.strip()
        _run_git(work5, "push", "origin", f"{tampered_head}:{RUNTIME_REF}")
        try:
            ledger5.load_snapshot()
            raise AssertionError("reverted forbidden path drift unexpectedly accepted")
        except Stage1Denied:
            pass
        print("GITHUB_RUNTIME_FORBIDDEN_PATH_HISTORY_DRIFT_REJECTED")

    assert "LocalBareLedger" not in globals()
    print("GITHUB_RUNTIME_TEST_ONLY_ORIGIN_BYPASS_FUNCTION_LOCAL_PASS")
    print("GITHUB_RUNTIME_CAS_ADAPTER_SELFTEST_PASS")
    print("PRODUCTION_RUNTIME_BRANCH_CREATED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")
    print("AUTHORIZATION_DECISION_ISSUANCE_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    parser.error("pre-activation library only; use --selftest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
