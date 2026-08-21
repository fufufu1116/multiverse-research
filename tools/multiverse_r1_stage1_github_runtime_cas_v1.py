#!/usr/bin/env python3
"""Concrete GitHub runtime-ledger CAS adapter for R1 Stage 1.

Pre-activation only. This module does not issue authorization decisions, does
not create the production runtime branch, and does not activate Stage 1.

The adapter turns every runtime-state mutation into:
1. an exact expected-old-head check,
2. a new fast-forward commit,
3. an append-only journal tag claimed with expected-absent force-with-lease,
4. a runtime-branch push with expected-old-head force-with-lease.

The journal tag is pushed *before* the branch. A crash after journal claim but
before branch advance intentionally makes the next load fail closed instead of
silently replaying or rolling back state.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from multiverse_r1_stage1_runtime_v1 import (
    RUNTIME_BRANCH,
    RemoteSnapshot,
    Stage1Denied,
    Stage1Tamper,
    empty_control,
    claim_control,
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
LEDGER_SCHEMA = "MULTIVERSE_R1_STAGE1_GITHUB_RUNTIME_LEDGER_v1"
LEDGER_FIELDS = {"schema_version", "sequence", "control", "r1_state"}
JOURNAL_TAG_PREFIX = "multiverse-r1-stage1-ledger-v1"
MAX_SEQUENCE = 1_000_000

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
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
class _InternalSnapshot:
    public: RemoteSnapshot
    sequence: int
    payload: dict


class GitHubRuntimeCASLedger:
    """Concrete remote Git CAS ledger. No authorization issuance is performed."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            _deny("GITHUB_RUNTIME_REPO_NOT_GIT_WORKTREE")
        validate_write_path(RUNTIME_BRANCH, STATE_PATH)
        self._validate_origin()

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

    def _validate_origin(self) -> None:
        url = self._git("remote", "get-url", REMOTE_NAME).stdout.strip()
        accepted = {
            f"https://github.com/{CANONICAL_REPO}",
            f"https://github.com/{CANONICAL_REPO}.git",
            f"git@github.com:{CANONICAL_REPO}.git",
            f"ssh://git@github.com/{CANONICAL_REPO}.git",
        }
        if url not in accepted:
            _deny("GITHUB_RUNTIME_ORIGIN_IDENTITY_MISMATCH", Stage1Tamper)

    def _remote_ref(self, ref: str) -> Optional[str]:
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
        touched = self._git(
            "log",
            "--format=",
            "--name-only",
            f"{genesis}..{head}",
        ).stdout.splitlines()
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
            if not match:
                _deny("GITHUB_RUNTIME_JOURNAL_REF_MALFORMED", Stage1Tamper)
            if match.group(1) != key or not _HEX40.fullmatch(sha):
                _deny("GITHUB_RUNTIME_JOURNAL_IDENTITY", Stage1Tamper)
            seq = int(match.group(2))
            terminal = int(match.group(3))
            out.append((seq, terminal, sha, ref))
        out.sort()
        for i, (seq, _, _, _) in enumerate(out, start=1):
            if seq != i:
                _deny("GITHUB_RUNTIME_JOURNAL_SEQUENCE_GAP", Stage1Tamper)
        return out

    def _verify_journal(
        self,
        *,
        control: Mapping[str, Any],
        sequence: int,
        head: str,
    ) -> int:
        entries = self._journal_entries(control)
        if sequence == 0:
            if entries:
                _deny("GITHUB_RUNTIME_JOURNAL_AHEAD_OF_LEDGER", Stage1Tamper)
            if control["terminal_count"] != 0:
                _deny("GITHUB_RUNTIME_TERMINAL_WITHOUT_JOURNAL", Stage1Tamper)
            return 0
        if len(entries) != sequence:
            _deny("GITHUB_RUNTIME_JOURNAL_LEDGER_SEQUENCE_MISMATCH", Stage1Tamper)
        last_seq, _, last_object, last_ref = entries[-1]
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
        current_main = self._fresh_main()
        head = self._fetch_runtime_head(expected_head)
        payload = self._runtime_payload(head)
        control = payload["control"]
        if control["canonical_main"] != current_main:
            _deny("GITHUB_RUNTIME_STALE_CANONICAL_MAIN", StaleState)
        genesis = control["runtime_genesis"]
        self._assert_runtime_history_paths(genesis, head)
        high_water = self._verify_journal(
            control=control,
            sequence=payload["sequence"],
            head=head,
        )
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
            "schema_version",
            "stage_id",
            "activation_receipt_id",
            "canonical_main",
            "audited_implementation_head",
            "runtime_branch",
            "runtime_genesis",
            "activated_at",
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
            self._git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{STATE_PATH}",
                env=env,
            )
            tree = self._git("write-tree", env=env).stdout.strip()
        commit = self._git(
            "-c",
            "user.name=Multiverse Stage1 Control Plane",
            "-c",
            "user.email=multiverse-stage1-control-plane@example.invalid",
            "commit-tree",
            tree,
            "-p",
            expected_head,
            "-m",
            message,
        ).stdout.strip()
        if not _HEX40.fullmatch(commit):
            _deny("GITHUB_RUNTIME_COMMIT_CREATE_FAILED")
        ff = self._git("merge-base", "--is-ancestor", expected_head, commit, check=False)
        if ff.returncode != 0:
            _deny("GITHUB_RUNTIME_NON_FAST_FORWARD_COMMIT", Stage1Tamper)
        return commit

    def _claim_journal_then_branch(
        self,
        *,
        old: _InternalSnapshot,
        new_payload: Mapping[str, Any],
        message: str,
    ) -> RemoteSnapshot:
        new_sequence = old.sequence + 1
        if new_sequence > MAX_SEQUENCE:
            _deny("GITHUB_RUNTIME_SEQUENCE_CEILING")
        payload = copy.deepcopy(dict(new_payload))
        payload["sequence"] = new_sequence
        _validate_ledger_payload(payload)
        new_commit = self._build_commit(
            expected_head=old.public.remote_head,
            payload=payload,
            message=message,
        )

        control = payload["control"]
        key = _activation_key(control)
        terminal = control["terminal_count"]
        tag_ref = (
            f"refs/tags/{JOURNAL_TAG_PREFIX}-{key}-"
            f"s{new_sequence:08d}-t{terminal:08d}"
        )
        if self._remote_ref(tag_ref) is not None:
            _deny("GITHUB_RUNTIME_JOURNAL_SEQUENCE_ALREADY_CLAIMED", Stage1Tamper)

        journal_push = self._git(
            "push",
            REMOTE_NAME,
            f"{new_commit}:{tag_ref}",
            f"--force-with-lease={tag_ref}:",
            check=False,
        )
        if journal_push.returncode != 0:
            _deny("GITHUB_RUNTIME_JOURNAL_CAS_FAILED", Stage1Tamper)

        branch_push = self._git(
            "push",
            REMOTE_NAME,
            f"{new_commit}:{RUNTIME_REF}",
            f"--force-with-lease={RUNTIME_REF}:{old.public.remote_head}",
            check=False,
        )
        if branch_push.returncode != 0:
            # Deliberately do not delete the claimed journal tag. Its presence
            # forces the next load to fail closed and prevents silent replay.
            _deny("GITHUB_RUNTIME_BRANCH_CAS_FAILED_JOURNAL_LEFT_FOR_REPAIR", Stage1Tamper)

        if self._remote_ref(RUNTIME_REF) != new_commit:
            _deny("GITHUB_RUNTIME_POST_PUSH_HEAD_MISMATCH", Stage1Tamper)
        return self._load_internal(expected_head=new_commit).public

    def claim_invocation(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        claimed_control: Mapping[str, Any],
    ) -> RemoteSnapshot:
        old = self._load_internal(expected_head=expected_remote_head)
        self._assert_control_identity_preserved(old.public.control, claimed_control)
        if claimed_control["invocation_claim_id"] != claim_id:
            _deny("GITHUB_RUNTIME_CLAIM_OWNER_MISMATCH", Stage1Tamper)
        if claimed_control["invocation_claim_expires_at"] is None:
            _deny("GITHUB_RUNTIME_CLAIM_EXPIRY_MISSING", Stage1Tamper)
        payload = copy.deepcopy(old.payload)
        payload["control"] = copy.deepcopy(dict(claimed_control))
        return self._claim_journal_then_branch(
            old=old,
            new_payload=payload,
            message=f"Stage1 claim {claim_id}",
        )

    def persist_r1_state(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        r1_state: Mapping[str, Any],
    ) -> RemoteSnapshot:
        old = self._load_internal(expected_head=expected_remote_head)
        if old.public.control["invocation_claim_id"] != claim_id:
            _deny("GITHUB_RUNTIME_STALE_NONOWNER_PERSIST", Stage1Tamper)
        state = copy.deepcopy(dict(r1_state))
        validate_state(state)
        payload = copy.deepcopy(old.payload)
        payload["r1_state"] = state
        return self._claim_journal_then_branch(
            old=old,
            new_payload=payload,
            message=f"Stage1 persist R1 state {claim_id}",
        )

    def release_invocation(
        self,
        *,
        expected_remote_head: str,
        claim_id: str,
        released_control: Mapping[str, Any],
    ) -> RemoteSnapshot:
        old = self._load_internal(expected_head=expected_remote_head)
        if old.public.control["invocation_claim_id"] != claim_id:
            _deny("GITHUB_RUNTIME_STALE_NONOWNER_RELEASE", Stage1Tamper)
        self._assert_control_identity_preserved(old.public.control, released_control)
        if (
            released_control["invocation_claim_id"] is not None
            or released_control["invocation_claim_expires_at"] is not None
        ):
            _deny("GITHUB_RUNTIME_RELEASE_DID_NOT_CLEAR_CLAIM", Stage1Tamper)
        payload = copy.deepcopy(old.payload)
        payload["control"] = copy.deepcopy(dict(released_control))
        return self._claim_journal_then_branch(
            old=old,
            new_payload=payload,
            message=f"Stage1 release {claim_id}",
        )


class _SelftestLedger(GitHubRuntimeCASLedger):
    """Local-bare-repo test adapter; production origin validation stays exact."""

    def _validate_origin(self) -> None:
        url = self._git("remote", "get-url", REMOTE_NAME).stdout.strip()
        if not url:
            _deny("SELFTEST_REMOTE_MISSING")


def _run_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


def _setup_selftest_repo(root: Path, suffix: str) -> tuple[Path, str, str]:
    bare = root / f"remote-{suffix}.git"
    work = root / f"work-{suffix}"
    _run_git(root, "init", "--bare", str(bare))
    _run_git(root, "clone", str(bare), str(work))
    _run_git(work, "config", "user.name", "Stage1 Selftest")
    _run_git(work, "config", "user.email", "stage1-selftest@example.invalid")

    (work / "README.md").write_text("stage1 adapter selftest\n")
    _run_git(work, "add", "README.md")
    _run_git(work, "commit", "-m", "selftest main")
    _run_git(work, "branch", "-M", "main")
    _run_git(work, "push", "-u", "origin", "main")
    main = _run_git(work, "rev-parse", "HEAD").stdout.strip()

    _run_git(work, "checkout", "-b", RUNTIME_BRANCH, main)
    control = empty_control(
        activation_receipt_id=f"selftest-activation-{suffix}",
        canonical_main=main,
        audited_implementation_head="a" * 40,
        runtime_genesis=main,
        activated_at=datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
    )
    payload = {
        "schema_version": LEDGER_SCHEMA,
        "sequence": 0,
        "control": control,
        "r1_state": empty_state(),
    }
    path = work / STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    _run_git(work, "add", STATE_PATH)
    _run_git(work, "commit", "-m", "selftest runtime genesis state")
    _run_git(work, "push", "-u", "origin", RUNTIME_BRANCH)
    head = _run_git(work, "rev-parse", "HEAD").stdout.strip()
    _run_git(work, "checkout", "main")
    return work, main, head


def selftest() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        work, _, initial_head = _setup_selftest_repo(root, "cas")
        a = _SelftestLedger(work)
        b = _SelftestLedger(work)
        snap_a = a.load_snapshot()
        snap_b = b.load_snapshot()
        assert snap_a.remote_head == snap_b.remote_head == initial_head
        assert snap_a.high_water_count == 0

        claimed_control = claim_control(
            snap_a.control,
            claim_id="claim-a",
            trusted_now=datetime(2026, 8, 21, 12, 1, tzinfo=timezone.utc),
        )
        claimed = a.claim_invocation(
            expected_remote_head=snap_a.remote_head,
            claim_id="claim-a",
            claimed_control=claimed_control,
        )
        try:
            b.claim_invocation(
                expected_remote_head=snap_b.remote_head,
                claim_id="claim-b",
                claimed_control=claim_control(
                    snap_b.control,
                    claim_id="claim-b",
                    trusted_now=datetime(2026, 8, 21, 12, 1, tzinfo=timezone.utc),
                ),
            )
            raise AssertionError("stale second claim unexpectedly succeeded")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_EXPECTED_OLD_HEAD_CAS_PASS")

        try:
            a.persist_r1_state(
                expected_remote_head=claimed.remote_head,
                claim_id="not-owner",
                r1_state=claimed.r1_state,
            )
            raise AssertionError("nonowner persist unexpectedly succeeded")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_STALE_NONOWNER_REJECTED")

        persisted = a.persist_r1_state(
            expected_remote_head=claimed.remote_head,
            claim_id="claim-a",
            r1_state=claimed.r1_state,
        )
        terminal_control = record_terminal_receipt(persisted.control, "receipt-selftest-1")
        released_control = release_control(terminal_control, claim_id="claim-a")
        released = a.release_invocation(
            expected_remote_head=persisted.remote_head,
            claim_id="claim-a",
            released_control=released_control,
        )
        assert released.control["terminal_count"] == 1
        assert released.high_water_count == 1
        print("GITHUB_RUNTIME_APPEND_ONLY_JOURNAL_HIGH_WATER_PASS")

        # External rollback attempt: adapter itself never performs this.
        rollback = _run_git(
            work,
            "push",
            "origin",
            f"{initial_head}:{RUNTIME_REF}",
            "--force",
            check=False,
        )
        assert rollback.returncode == 0
        try:
            a.load_snapshot()
            raise AssertionError("rollback unexpectedly accepted")
        except Stage1Tamper:
            pass
        print("GITHUB_RUNTIME_ROLLBACK_DETECTED")

        work2, _, _ = _setup_selftest_repo(root, "paths")
        ledger2 = _SelftestLedger(work2)
        safe = ledger2.load_snapshot()
        _run_git(work2, "fetch", "origin", RUNTIME_REF)
        _run_git(work2, "checkout", "-B", "tamper", "FETCH_HEAD")
        forbidden = work2 / "governance" / "FORBIDDEN_RUNTIME_WRITE.txt"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text("not allowed\n")
        _run_git(work2, "add", "governance/FORBIDDEN_RUNTIME_WRITE.txt")
        _run_git(work2, "commit", "-m", "forbidden runtime drift")
        tampered = _run_git(work2, "rev-parse", "HEAD").stdout.strip()
        _run_git(work2, "push", "origin", f"{tampered}:{RUNTIME_REF}")
        try:
            ledger2.load_snapshot()
            raise AssertionError("forbidden path drift unexpectedly accepted")
        except Stage1Denied:
            pass
        print("GITHUB_RUNTIME_FORBIDDEN_PATH_DRIFT_REJECTED")

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
