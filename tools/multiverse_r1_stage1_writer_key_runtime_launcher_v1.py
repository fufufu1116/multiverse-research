#!/usr/bin/env python3
"""R1 Stage-1 writer-key Runtime loader/preflight candidate.

This support artifact does not execute a Stage-1 task. It Fresh verifies the
activation receipt, resolves the nonsecret writer-key ID, verifies the exact
secret commitment, constructs canonical Runtime CAS through the hardened
production loader, and performs a read-only snapshot load.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from multiverse_r1_stage1_verified_activation_receipt_loader_v1 import (
    ACTIVATION_TAG_REF,
    ImmutableActivationReceiptLoader,
)
from multiverse_r1_stage1_verified_activation_receipt_loader_v2 import (
    load_verified_stage1_context,
)

WRITER_ID_RE = re.compile(r"^MULTIVERSE_R1_STAGE1_WRITER_KEY_[0-9A-F]{32}$")
STORED_SECRET_RE = re.compile(r"^[A-Za-z0-9_-]{43}=$")
EXACT_ACTIVATION_REF = "refs/tags/multiverse-r1-stage1-activation-v1"
SECRET_ENV = "MULTIVERSE_R1_STAGE1_WRITER_KEY_SECRET"
WRITER_ID_ENV = "MULTIVERSE_R1_STAGE1_WRITER_KEY_ID"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class Denied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise Denied(code)


def _repo_root() -> Path:
    root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    if not (root / ".git").exists():
        _deny("WRITER_LAUNCHER_REPO_NOT_GIT_WORKTREE")
    return root


def _assert_activation_ref() -> str:
    ref = os.environ.get("GITHUB_REF", "")
    sha = os.environ.get("GITHUB_SHA", "")
    if ref != EXACT_ACTIVATION_REF or ACTIVATION_TAG_REF != EXACT_ACTIVATION_REF:
        _deny("WRITER_LAUNCHER_NOT_EXACT_ACTIVATION_TAG_REF")
    if not _HEX40.fullmatch(sha):
        _deny("WRITER_LAUNCHER_GITHUB_SHA_INVALID")
    return sha


def _fresh_activation_product(root: Path):
    # The v1 immutable loader exposes the nonsecret writer-key identity. The
    # secret-bearing path below additionally enters through the hardened v2
    # sole production integration entrypoint before constructing Runtime CAS.
    return ImmutableActivationReceiptLoader(root).load()


def preflight_writer_identity() -> dict[str, Any]:
    root = _repo_root()
    event_sha = _assert_activation_ref()
    loaded = _fresh_activation_product(root)
    writer_key_id = loaded.runtime.writer_key_id
    if not isinstance(writer_key_id, str) or not WRITER_ID_RE.fullmatch(writer_key_id):
        _deny("WRITER_LAUNCHER_RECEIPT_WRITER_ID_OUTSIDE_RESERVED_NAMESPACE")
    if loaded.runtime.canonical_main != event_sha:
        _deny("WRITER_LAUNCHER_TAG_EVENT_SHA_NOT_RECEIPT_CANONICAL_MAIN")
    if loaded.receipt.get("infrastructure", {}).get("activation_tag_ref") != EXACT_ACTIVATION_REF:
        _deny("WRITER_LAUNCHER_RECEIPT_ACTIVATION_TAG_BINDING")
    output = os.environ.get("GITHUB_OUTPUT", "")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("writer_key_id=" + writer_key_id + "\n")
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_WRITER_KEY_RUNTIME_PREFLIGHT_v1",
        "status": "WRITER_KEY_ID_FRESH_VERIFIED",
        "writer_key_id": writer_key_id,
        "canonical_main": loaded.runtime.canonical_main,
        "secret_material_accessed": False,
        "runtime_mutation_performed": False,
        "task_execution_performed": False,
    }


def runtime_loader_preflight() -> dict[str, Any]:
    root = _repo_root()
    event_sha = _assert_activation_ref()
    expected_writer_id = os.environ.get(WRITER_ID_ENV, "")
    secret_text = os.environ.pop(SECRET_ENV, "")
    if not WRITER_ID_RE.fullmatch(expected_writer_id):
        _deny("WRITER_LAUNCHER_DYNAMIC_WRITER_ID_INVALID")
    if not STORED_SECRET_RE.fullmatch(secret_text):
        _deny("WRITER_LAUNCHER_SECRET_ENCODING_INVALID")
    try:
        writer_bytes = secret_text.encode("ascii")
    except Exception as exc:
        raise Denied("WRITER_LAUNCHER_SECRET_NOT_ASCII") from exc

    loaded = _fresh_activation_product(root)
    if loaded.runtime.canonical_main != event_sha:
        _deny("WRITER_LAUNCHER_RECEIPT_MAIN_DRIFT")
    if loaded.runtime.writer_key_id != expected_writer_id:
        _deny("WRITER_LAUNCHER_WRITER_ID_RECEIPT_MISMATCH")
    actual_sha256 = hashlib.sha256(writer_bytes).hexdigest()
    if actual_sha256 != loaded.runtime.writer_key_sha256:
        _deny("WRITER_LAUNCHER_WRITER_SECRET_SHA256_MISMATCH")

    # Hardened canonical production entrypoint. This independently Fresh
    # re-verifies the immutable activation receipt and CAS constructor repeats
    # the writer-key commitment check before retaining key bytes.
    context = load_verified_stage1_context(root)
    ledger = context.build_runtime_ledger(writer_auth_key=writer_bytes)
    snapshot = ledger.load_snapshot()

    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_WRITER_KEY_RUNTIME_PREFLIGHT_v1",
        "status": "CANONICAL_RUNTIME_CAS_READONLY_PREFLIGHT_VERIFIED",
        "writer_key_id": expected_writer_id,
        "writer_key_sha256": actual_sha256,
        "canonical_main": snapshot.canonical_main,
        "runtime_head": snapshot.remote_head,
        "terminal_count": snapshot.control.get("terminal_count"),
        "runtime_mutation_performed": False,
        "task_execution_performed": False,
    }


def selftest() -> None:
    assert WRITER_ID_RE.fullmatch("MULTIVERSE_R1_STAGE1_WRITER_KEY_" + "A" * 32)
    assert STORED_SECRET_RE.fullmatch("A" * 43 + "=")
    assert EXACT_ACTIVATION_REF == ACTIVATION_TAG_REF
    print("WRITER_KEY_RUNTIME_LAUNCHER_STATIC_SELFTEST_PASS")
    print("RUNTIME_MUTATION_PERFORMED=false")
    print("TASK_EXECUTION_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-id", action="store_true")
    mode.add_argument("--runtime-preflight", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.preauth if False else False:  # unreachable guard against accidental mode growth
            raise AssertionError
        if args.preflight_id:
            value = preflight_writer_identity()
        elif args.runtime_preflight:
            value = runtime_loader_preflight()
        else:
            selftest()
            return 0
    except Denied as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_WRITER_KEY_RUNTIME_PREFLIGHT_v1",
            "status": "DENIED_FAIL_CLOSED",
            "reason": str(exc),
            "secret_material_printed": False,
            "runtime_mutation_performed": False,
            "task_execution_performed": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
