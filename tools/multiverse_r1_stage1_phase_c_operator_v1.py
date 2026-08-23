#!/usr/bin/env python3
"""Frozen iPhone Codespaces Phase-C operator sequence."""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, subprocess
from typing import Any
from multiverse_r1_stage1_writer_key_admin_channel_v1 import (
    EXPECTED_GH_CONFIG_DIR, Denied, _assert_env_clean, _assert_memory_dir,
    cleanup_local_credentials,
)
from multiverse_r1_stage1_phase_c_guarded_execution_v1 import (
    AUTHORIZED_CANONICAL_MAIN, apply_once, live_preflight,
)
LOGIN_COMMAND = [
    "gh", "auth", "login", "--hostname", "github.com",
    "--git-protocol", "https", "--web", "--scopes", "repo",
]

def _deny(code: str) -> None:
    raise Denied(code)

def _pin_runtime_env() -> None:
    if os.environ.get("GH_CONFIG_DIR") not in (None, "", EXPECTED_GH_CONFIG_DIR):
        _deny("PHASE_C_GH_CONFIG_DIR_OVERRIDE_PROHIBITED")
    os.environ["GH_CONFIG_DIR"] = EXPECTED_GH_CONFIG_DIR
    _assert_env_clean()

def _purge_preauth_credentials_best_effort() -> None:
    os.environ["GH_CONFIG_DIR"] = EXPECTED_GH_CONFIG_DIR
    subprocess.run(
        ["gh", "auth", "logout", "--hostname", "github.com"],
        text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
    )
    path = pathlib.Path(EXPECTED_GH_CONFIG_DIR)
    if path.exists() and not path.is_symlink():
        for child in list(path.iterdir()):
            if child.is_symlink():
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

def login_and_live_preflight() -> dict[str, Any]:
    _pin_runtime_env()
    _assert_memory_dir(EXPECTED_GH_CONFIG_DIR, create=True, require_empty=True)
    login = subprocess.run(LOGIN_COMMAND, env=os.environ.copy())
    if login.returncode != 0:
        _purge_preauth_credentials_best_effort()
        _deny("PHASE_C_BROWSER_OAUTH_LOGIN_FAILED")
    try:
        result = live_preflight()
    except Exception:
        _purge_preauth_credentials_best_effort()
        raise
    result = dict(result)
    result["operator_login_command"] = "gh auth login --hostname github.com --git-protocol https --web --scopes repo"
    result["gh_config_dir"] = EXPECTED_GH_CONFIG_DIR
    result["authorized_canonical_main"] = AUTHORIZED_CANONICAL_MAIN
    result["local_credentials_retained_for_single_guarded_apply"] = True
    return result

def guarded_apply() -> dict[str, Any]:
    _pin_runtime_env()
    return apply_once()

def guarded_cleanup(session_id: str) -> dict[str, Any]:
    _pin_runtime_env()
    return cleanup_local_credentials(session_id)

def selftest() -> None:
    assert LOGIN_COMMAND == [
        "gh", "auth", "login", "--hostname", "github.com",
        "--git-protocol", "https", "--web", "--scopes", "repo",
    ]
    assert AUTHORIZED_CANONICAL_MAIN == "ff07e5ee02fa84405eb2fc89cfdbff1d26267cc9"
    print("PHASE_C_FROZEN_OPERATOR_SELFTEST_PASS")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")

def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--login-preflight", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--cleanup", metavar="SESSION_ID")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.login_preflight:
            result = login_and_live_preflight()
        elif args.apply:
            result = guarded_apply()
        elif args.cleanup:
            result = guarded_cleanup(args.cleanup)
        else:
            selftest()
            return 0
    except Denied as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_FROZEN_OPERATOR_RESULT_v1",
            "status": "DENIED_FAIL_CLOSED", "reason": str(exc),
            "blind_retry_authorized": False, "runtime_activation_performed": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
