#!/usr/bin/env python3
"""iPhone-compatible Codespaces wrapper for the already-approved Stage1 ruleset operator.

DRAFT / review-only candidate. Default mode is read-only. Actual ruleset mutation
is delegated only to the exact approved PR #69 operator and remains unavailable
until this Codespaces execution channel receives independent Lab and Auditor PASS.

No PAT/token/password is accepted as an argument, stdin value, file input, or
printed output. Authentication is expected to be a GitHub CLI browser-OAuth
credential stored only in an explicitly selected tmpfs GH_CONFIG_DIR.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping

CANONICAL_REPO = "fufufu1116/multiverse-research"
EXPECTED_LOGIN = "fufufu1116"
APPROVED_ADMIN_HEAD = "49ab50cfce03e29eedd95d66ee76a41de159940e"
APPROVED_AUDITOR_REVIEW = 4999948431
APPROVED_OPERATOR_PATH = "tools/multiverse_r1_stage1_ruleset_admin_channel_v1.py"
APPROVED_OPERATOR_BLOB = "673501d6c083ee240811156ce5917d34b7a1bee4"
EXPECTED_GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-gh-auth"
REQUIRED_SCOPE = "repo"
ALLOWED_OAUTH_SCOPES = {"repo", "read:org", "gist", "workflow"}
API_VERSION = "2022-11-28"

_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class Denied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise Denied(code)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _run(cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )


def _assert_environment_before_any_gh() -> None:
    if os.environ.get("CODESPACES") != "true":
        _deny("CODESPACES_CHANNEL_REQUIRED")
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        _deny("CODESPACES_GH_CONFIG_DIR_NOT_PINNED_TO_REVIEWED_TMPFS_PATH")
    for key in (
        "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
    ):
        if os.environ.get(key):
            _deny("CODESPACES_ENVIRONMENT_TOKEN_PROHIBITED:" + key)
    if os.environ.get("GH_HOST") not in (None, "", "github.com"):
        _deny("CODESPACES_GH_HOST_OVERRIDE_PROHIBITED")
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR",
        "GH_DEBUG", "DEBUG",
    ):
        if os.environ.get(key):
            _deny("CODESPACES_PROXY_CA_OR_DEBUG_PROHIBITED:" + key)
    shm = pathlib.Path("/dev/shm")
    cfg = pathlib.Path(EXPECTED_GH_CONFIG_DIR)
    try:
        if not shm.is_dir() or not os.access(shm, os.W_OK):
            _deny("CODESPACES_TMPFS_UNAVAILABLE")
        probe = _run(["stat", "-f", "-c", "%T", "/dev/shm"])
    except FileNotFoundError as exc:
        raise Denied("CODESPACES_TMPFS_PROBE_UNAVAILABLE") from exc
    if probe.returncode != 0 or probe.stdout.strip() not in {"tmpfs", "ramfs"}:
        _deny("CODESPACES_GH_CONFIG_NOT_MEMORY_BACKED")
    try:
        cfg.resolve().relative_to(shm.resolve())
    except Exception as exc:
        raise Denied("CODESPACES_GH_CONFIG_ESCAPES_TMPFS") from exc


def _assert_local_gh_config_safe() -> None:
    proc = _run(["gh", "config", "list", "--host", "github.com"])
    if proc.returncode != 0:
        _deny("CODESPACES_GH_CONFIG_QUERY_FAILED")
    sockets = [
        row.split("=", 1)[1].strip()
        for row in proc.stdout.splitlines()
        if row.startswith("http_unix_socket=") and "=" in row
    ]
    if len(sockets) != 1 or sockets[0]:
        _deny("CODESPACES_GH_HTTP_UNIX_SOCKET_PROHIBITED_OR_AMBIGUOUS")


def _parse_include_json(text: str) -> tuple[Mapping[str, str], Any]:
    header, sep, body = text.replace("\r\n", "\n").partition("\n\n")
    if not sep:
        _deny("CODESPACES_API_HEADERS_OR_BODY_MISSING")
    lines = [line for line in header.splitlines() if line]
    if not lines or not lines[0].startswith("HTTP/"):
        _deny("CODESPACES_API_STATUS_MISSING")
    parts = lines[0].split()
    if len(parts) < 2 or parts[1] != "200":
        _deny("CODESPACES_API_NON_200")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    try:
        payload = json.loads(body)
    except Exception as exc:
        raise Denied("CODESPACES_API_JSON_INVALID") from exc
    return headers, payload


def _gh_api_include(endpoint: str) -> tuple[Mapping[str, str], Any]:
    proc = _run([
        "gh", "api", "--hostname", "github.com", "--include",
        "-H", "Accept: application/vnd.github+json",
        "-H", f"X-GitHub-Api-Version: {API_VERSION}",
        endpoint,
    ])
    if proc.returncode != 0:
        _deny("CODESPACES_GITHUB_API_FAILED")
    return _parse_include_json(proc.stdout)


def _verify_browser_oauth_identity_and_scope() -> list[str]:
    headers, user = _gh_api_include("/user")
    if not isinstance(user, dict) or user.get("login") != EXPECTED_LOGIN:
        _deny("CODESPACES_GITHUB_LOGIN_MISMATCH")
    raw_scopes = headers.get("x-oauth-scopes")
    if raw_scopes is None:
        _deny("CODESPACES_BROWSER_OAUTH_SCOPE_HEADER_MISSING")
    scopes = sorted({item.strip() for item in raw_scopes.split(",") if item.strip()})
    if REQUIRED_SCOPE not in scopes:
        _deny("CODESPACES_BROWSER_OAUTH_REPO_SCOPE_MISSING")
    if not set(scopes).issubset(ALLOWED_OAUTH_SCOPES):
        _deny("CODESPACES_BROWSER_OAUTH_UNREVIEWED_SCOPE_PRESENT")
    _, repo = _gh_api_include(f"/repos/{CANONICAL_REPO}")
    permissions = repo.get("permissions") if isinstance(repo, dict) else None
    if not isinstance(permissions, dict) or permissions.get("admin") is not True:
        _deny("CODESPACES_REPOSITORY_ADMIN_PERMISSION_REQUIRED")
    return scopes


def _verify_approved_operator_blob() -> None:
    proc = _run(["git", "hash-object", APPROVED_OPERATOR_PATH])
    if proc.returncode != 0 or proc.stdout.strip() != APPROVED_OPERATOR_BLOB:
        _deny("CODESPACES_APPROVED_OPERATOR_BLOB_MISMATCH")
    ancestry = _run(["git", "merge-base", "--is-ancestor", APPROVED_ADMIN_HEAD, "HEAD"])
    if ancestry.returncode != 0:
        _deny("CODESPACES_APPROVED_ADMIN_HEAD_NOT_ANCESTOR")


def _run_approved_operator(*, apply: bool) -> dict:
    cmd = [sys.executable, APPROVED_OPERATOR_PATH]
    if apply:
        cmd.append("--apply")
    proc = _run(cmd)
    if proc.returncode != 0:
        reason = proc.stderr.strip()[:240] if proc.stderr else ""
        raise Denied("CODESPACES_APPROVED_OPERATOR_FAILED:" + reason)
    try:
        result = json.loads(proc.stdout)
    except Exception as exc:
        raise Denied("CODESPACES_APPROVED_OPERATOR_JSON_INVALID") from exc
    if not isinstance(result, dict):
        _deny("CODESPACES_APPROVED_OPERATOR_RESULT_INVALID")
    allowed = {
        "DRY_RUN_WOULD_CREATE_EXACT_RULESET",
        "EXISTING_EXACT_VERIFIED",
        "EXISTING_EXACT_VERIFIED_AFTER_REFRESH",
        "CREATED_AND_FRESH_VERIFIED",
    }
    if result.get("status") not in allowed:
        _deny("CODESPACES_APPROVED_OPERATOR_STATUS_UNEXPECTED")
    if apply and result.get("status") not in {
        "EXISTING_EXACT_VERIFIED",
        "EXISTING_EXACT_VERIFIED_AFTER_REFRESH",
        "CREATED_AND_FRESH_VERIFIED",
    }:
        _deny("CODESPACES_APPLY_DID_NOT_PROVISION_OR_VERIFY")
    return result


def _result(status: str, *, scopes: list[str], operator_result: Mapping[str, Any]) -> dict:
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_CODESPACES_ADMIN_CHANNEL_RESULT_v1",
        "status": status,
        "canonical_repo": CANONICAL_REPO,
        "approved_admin_head": APPROVED_ADMIN_HEAD,
        "approved_auditor_review": APPROVED_AUDITOR_REVIEW,
        "approved_operator_blob": APPROVED_OPERATOR_BLOB,
        "execution_environment": "GITHUB_CODESPACES_BROWSER_TERMINAL_IPHONE_COMPATIBLE",
        "authentication_method": "GH_CLI_WEB_OAUTH_TMPFS_ONLY",
        "oauth_scopes": scopes,
        "environment_token_used": False,
        "credential_material_printed": False,
        "credential_material_accepted_as_argument": False,
        "credential_storage": "TMPFS_GH_CONFIG_DIR_DELETE_AFTER_USE",
        "operator_status": operator_result.get("status"),
        "ruleset_id": operator_result.get("ruleset_id"),
        "ruleset_updated_at": operator_result.get("ruleset_updated_at"),
        "runtime_activation_performed": False,
        "writer_key_created": False,
        "runtime_branch_created": False,
        "activation_receipt_created": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    _assert_environment_before_any_gh()
    _assert_local_gh_config_safe()
    scopes = _verify_browser_oauth_identity_and_scope()
    _verify_approved_operator_blob()
    operator_result = _run_approved_operator(apply=args.apply)
    status = "CODESPACES_APPLY_COMPLETE" if args.apply else "CODESPACES_DRY_RUN_COMPLETE"
    print(_canonical_json(_result(status, scopes=scopes, operator_result=operator_result)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Denied as exc:
        print(_canonical_json({"status": "DENIED_FAIL_CLOSED", "reason": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
