#!/usr/bin/env python3
"""Nonmutating live preflight and detached-checkout binding for R1 Stage-1 Phase C.

This module performs no GitHub mutation and reads no secret value.  The
production provisioner imports ``verified_execution_checkout_head`` so its
first mutation can only target the exact detached, clean reviewed checkout
whose commit still equals Fresh canonical main.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
from typing import Any

from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    CANONICAL_REPO,
    RULESET_ID,
    RULESET_UPDATED_AT,
    Denied,
    PhaseCAdminChannel,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _deny(code: str) -> None:
    raise Denied(code)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def verified_execution_checkout_head() -> str:
    """Return the exact detached, clean commit containing this reviewed tool."""
    top = _run(["git", "rev-parse", "--show-toplevel"])
    if top.returncode != 0 or not top.stdout.strip():
        _deny("PHASE_C_EXECUTION_GIT_TOPLEVEL_UNAVAILABLE")
    try:
        actual_root = pathlib.Path(top.stdout.strip()).resolve(strict=True)
        expected_root = ROOT.resolve(strict=True)
    except Exception as exc:
        raise Denied("PHASE_C_EXECUTION_GIT_ROOT_UNRESOLVED") from exc
    if actual_root != expected_root:
        _deny("PHASE_C_EXECUTION_GIT_ROOT_MISMATCH")

    symbolic = _run(["git", "symbolic-ref", "-q", "HEAD"])
    if symbolic.returncode == 0:
        _deny("PHASE_C_EXECUTION_CHECKOUT_MUST_BE_DETACHED")
    if symbolic.returncode != 1:
        _deny("PHASE_C_EXECUTION_HEAD_STATE_UNREADABLE")

    head_proc = _run(["git", "rev-parse", "--verify", "HEAD^{commit}"])
    head = head_proc.stdout.strip()
    if head_proc.returncode != 0 or not _HEX40.fullmatch(head):
        _deny("PHASE_C_EXECUTION_CHECKOUT_SHA_INVALID")

    status = _run(["git", "status", "--porcelain=v1", "--untracked-files=all"])
    if status.returncode != 0:
        _deny("PHASE_C_EXECUTION_WORKTREE_STATUS_FAILED")
    if status.stdout.strip():
        _deny("PHASE_C_EXECUTION_WORKTREE_NOT_CLEAN")
    return head


def live_preflight() -> dict[str, Any]:
    """Run the complete reviewed nonmutating live pre-apply proof set."""
    checkout = verified_execution_checkout_head()
    channel = PhaseCAdminChannel()
    scopes = channel.verify_identity_and_scope()
    main_sha = channel.fresh_main()
    if main_sha != checkout:
        _deny("PHASE_C_PREFLIGHT_MAIN_NOT_EXACT_EXECUTION_CHECKOUT")

    ruleset = channel.verify_ruleset()
    if channel.fence() is not None:
        _deny("PHASE_C_PREFLIGHT_PROVISION_FENCE_ALREADY_EXISTS")

    environment = channel.probe_environment()
    if environment.status != 404:
        _deny("PHASE_C_PREFLIGHT_ENVIRONMENT_NOT_ABSENT_404")

    try:
        from nacl.public import PublicKey, SealedBox  # type: ignore
    except Exception as exc:
        raise Denied("PHASE_C_PREFLIGHT_PYNACL_REQUIRED_NO_NETWORK_INSTALL") from exc
    if PublicKey is None or SealedBox is None:
        _deny("PHASE_C_PREFLIGHT_PYNACL_IMPORT_INVALID")

    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_PREFLIGHT_v1",
        "status": "PHASE_C_NONMUTATING_PREFLIGHT_PASS",
        "canonical_repo": CANONICAL_REPO,
        "execution_checkout_sha": checkout,
        "fresh_main_sha": main_sha,
        "detached_checkout": True,
        "clean_worktree": True,
        "oauth_effective_scopes": scopes,
        "ruleset_id": ruleset["id"],
        "ruleset_updated_at": ruleset["updated_at"],
        "ruleset_expected_id": RULESET_ID,
        "ruleset_expected_updated_at": RULESET_UPDATED_AT,
        "provision_fence_absent_404": True,
        "environment_absent_404": True,
        "gh_api_include_non_2xx_capture_proven": True,
        "pynacl_publickey_sealedbox_available_without_install": True,
        "secret_value_read": False,
        "production_mutation_performed": False,
        "runtime_activation_performed": False,
    }


def selftest() -> None:
    assert CANONICAL_REPO == "fufufu1116/multiverse-research"
    assert _HEX40.fullmatch("0" * 40)
    print("PHASE_C_EXECUTION_PREFLIGHT_STATIC_SELFTEST_PASS")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        result = None if args.selftest else live_preflight()
        if args.selftest:
            selftest()
        else:
            print(json.dumps(result, sort_keys=True))
    except Denied as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_PREFLIGHT_v1",
            "status": "DENIED_FAIL_CLOSED",
            "reason": str(exc),
            "production_mutation_performed": False,
            "runtime_activation_performed": False,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
