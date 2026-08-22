#!/usr/bin/env python3
"""iPhone Codespaces gate for the already-approved Stage1 ruleset operator.

DRAFT/review-only. Default is non-mutating rehearsal. Successful apply remains
cleanup-pending and never opens Phase C by itself.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import stat
import subprocess
import sys
from typing import Any, Mapping

CANONICAL_REPO = "fufufu1116/multiverse-research"
EXPECTED_LOGIN = "fufufu1116"
APPROVED_ADMIN_HEAD = "49ab50cfce03e29eedd95d66ee76a41de159940e"
APPROVED_AUDITOR_REVIEW = 4999948431
LAB_RESULT_COMMENT = 5379999637
APPROVED_OPERATOR_PATH = "tools/multiverse_r1_stage1_ruleset_admin_channel_v1.py"
APPROVED_OPERATOR_BLOB = "673501d6c083ee240811156ce5917d34b7a1bee4"
EXPECTED_GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-gh-auth"
SESSION_STATE_DIR = "/dev/shm/multiverse-r1-stage1-codespaces-session-state"
REQUIRED_SCOPE = "repo"
ALLOWED_OAUTH_SCOPES = {"repo", "read:org", "gist", "workflow"}
API_VERSION = "2022-11-28"
_HEX32 = re.compile(r"^[0-9a-f]{32}$")


class Denied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise Denied(code)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())


def _effective_uid() -> int:
    return os.geteuid()


def _codespace_name() -> str:
    value = os.environ.get("CODESPACE_NAME", "")
    if not value:
        _deny("CODESPACES_NAME_REQUIRED_FOR_SESSION_BINDING")
    return value


def _assert_env_clean() -> None:
    if os.environ.get("CODESPACES") != "true":
        _deny("CODESPACES_CHANNEL_REQUIRED")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        if os.environ.get(key):
            _deny("CODESPACES_ENVIRONMENT_TOKEN_PROHIBITED:" + key)
    if os.environ.get("GH_HOST") not in (None, "", "github.com"):
        _deny("CODESPACES_GH_HOST_OVERRIDE_PROHIBITED")
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG",
    ):
        if os.environ.get(key):
            _deny("CODESPACES_PROXY_CA_OR_DEBUG_PROHIBITED:" + key)


def _assert_swap_absent() -> None:
    try:
        lines = [x for x in pathlib.Path("/proc/swaps").read_text().splitlines() if x.strip()]
    except Exception as exc:
        raise Denied("CODESPACES_SWAP_STATE_UNREADABLE") from exc
    if len(lines) != 1 or not lines[0].lower().startswith("filename"):
        _deny("CODESPACES_ACTIVE_SWAP_PROHIBITED")


def _memory_filesystem_type(path: str) -> str:
    probe = _run(["stat", "-f", "-c", "%T", path])
    fs_type = probe.stdout.strip() if probe.returncode == 0 else ""
    if fs_type not in {"tmpfs", "ramfs"}:
        _deny("CODESPACES_AUTH_STORAGE_MUST_BE_MEMORY_FILESYSTEM")
    return fs_type


def _assert_auth_storage_secure(*, require_empty: bool = False) -> str:
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        _deny("CODESPACES_GH_CONFIG_DIR_NOT_PINNED_TO_REVIEWED_MEMORY_PATH")
    cfg = pathlib.Path(EXPECTED_GH_CONFIG_DIR)
    try:
        st = os.lstat(cfg)
    except FileNotFoundError as exc:
        raise Denied("CODESPACES_AUTH_DIR_MISSING") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        _deny("CODESPACES_AUTH_DIR_MUST_BE_REAL_DIRECTORY")
    if st.st_uid != _effective_uid():
        _deny("CODESPACES_AUTH_DIR_OWNER_MISMATCH")
    if stat.S_IMODE(st.st_mode) != 0o700:
        _deny("CODESPACES_AUTH_DIR_MODE_NOT_0700")
    fs_type = _memory_filesystem_type(EXPECTED_GH_CONFIG_DIR)
    _assert_swap_absent()
    entry_count = 0
    for root, dirs, files in os.walk(cfg, topdown=True, followlinks=False):
        base = pathlib.Path(root)
        entry_count += len(dirs) + len(files)
        for name in dirs:
            s = os.lstat(base / name)
            if stat.S_ISLNK(s.st_mode) or not stat.S_ISDIR(s.st_mode):
                _deny("CODESPACES_AUTH_STORAGE_NON_DIRECTORY_ENTRY")
            if s.st_uid != _effective_uid() or stat.S_IMODE(s.st_mode) != 0o700:
                _deny("CODESPACES_AUTH_STORAGE_DIRECTORY_PERMISSIONS")
        for name in files:
            s = os.lstat(base / name)
            if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode):
                _deny("CODESPACES_AUTH_STORAGE_FILE_MUST_BE_REGULAR_NON_SYMLINK")
            if s.st_nlink != 1 or s.st_uid != _effective_uid():
                _deny("CODESPACES_AUTH_STORAGE_FILE_IDENTITY")
            if stat.S_IMODE(s.st_mode) & 0o177:
                _deny("CODESPACES_AUTH_STORAGE_FILE_MODE_TOO_BROAD")
    if require_empty and entry_count:
        _deny("CODESPACES_PREAUTH_AUTH_DIR_MUST_BE_EMPTY")
    return fs_type


def _pre_auth_check() -> dict:
    _assert_env_clean()
    codespace_name = _codespace_name()
    fs_type = _assert_auth_storage_secure(require_empty=True)
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_CODESPACES_PRE_AUTH_PROOF_v1",
        "status": "CODESPACES_PRE_AUTH_STORAGE_VERIFIED",
        "codespace_name": codespace_name,
        "gh_config_dir": EXPECTED_GH_CONFIG_DIR,
        "memory_filesystem_type": fs_type,
        "active_swap_absent": True,
        "auth_directory_empty": True,
        "effective_uid_owner_verified": True,
        "credential_material_accessed": False,
        "phase_c_gate_open": False,
    }


def _assert_local_gh_config_safe() -> None:
    proc = _run(["gh", "config", "list", "--host", "github.com"])
    if proc.returncode != 0:
        _deny("CODESPACES_GH_CONFIG_QUERY_FAILED")
    sockets = [row.split("=", 1)[1].strip() for row in proc.stdout.splitlines()
               if row.startswith("http_unix_socket=") and "=" in row]
    if len(sockets) != 1 or sockets[0]:
        _deny("CODESPACES_GH_HTTP_UNIX_SOCKET_PROHIBITED_OR_AMBIGUOUS")


def _parse_include_json(text: str) -> tuple[Mapping[str, str], Any]:
    header, sep, body = text.replace("\r\n", "\n").partition("\n\n")
    if not sep:
        _deny("CODESPACES_API_HEADERS_OR_BODY_MISSING")
    lines = [line for line in header.splitlines() if line]
    if not lines or not lines[0].startswith("HTTP/") or len(lines[0].split()) < 2:
        _deny("CODESPACES_API_STATUS_MISSING")
    if lines[0].split()[1] != "200":
        _deny("CODESPACES_API_NON_200")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            if key in headers:
                _deny("CODESPACES_API_DUPLICATE_HEADER:" + key)
            headers[key] = value.strip()
    try:
        payload = json.loads(body)
    except Exception as exc:
        raise Denied("CODESPACES_API_JSON_INVALID") from exc
    return headers, payload


def _gh_api_include(endpoint: str) -> tuple[Mapping[str, str], Any]:
    if endpoint not in {"/user", f"/repos/{CANONICAL_REPO}"}:
        _deny("CODESPACES_API_ENDPOINT_NOT_ALLOWLISTED")
    proc = _run([
        "gh", "api", "--hostname", "github.com", "--include",
        "-H", "Accept: application/vnd.github+json",
        "-H", f"X-GitHub-Api-Version: {API_VERSION}", endpoint,
    ])
    if proc.returncode != 0:
        _deny("CODESPACES_GITHUB_API_FAILED")
    return _parse_include_json(proc.stdout)


def _verify_oauth() -> list[str]:
    headers, user = _gh_api_include("/user")
    if not isinstance(user, dict) or user.get("login") != EXPECTED_LOGIN:
        _deny("CODESPACES_GITHUB_LOGIN_MISMATCH")
    raw = headers.get("x-oauth-scopes")
    if raw is None:
        _deny("CODESPACES_BROWSER_OAUTH_SCOPE_HEADER_MISSING")
    scopes = sorted({x.strip() for x in raw.split(",") if x.strip()})
    if REQUIRED_SCOPE not in scopes:
        _deny("CODESPACES_BROWSER_OAUTH_REPO_SCOPE_MISSING")
    if not set(scopes).issubset(ALLOWED_OAUTH_SCOPES):
        _deny("CODESPACES_BROWSER_OAUTH_UNREVIEWED_SCOPE_PRESENT")
    _, repo = _gh_api_include(f"/repos/{CANONICAL_REPO}")
    permissions = repo.get("permissions") if isinstance(repo, dict) else None
    if not isinstance(permissions, dict) or permissions.get("admin") is not True:
        _deny("CODESPACES_REPOSITORY_ADMIN_PERMISSION_REQUIRED")
    return scopes


def _verify_approved_operator() -> None:
    proc = _run(["git", "hash-object", APPROVED_OPERATOR_PATH])
    if proc.returncode != 0 or proc.stdout.strip() != APPROVED_OPERATOR_BLOB:
        _deny("CODESPACES_APPROVED_OPERATOR_BLOB_MISMATCH")
    if _run(["git", "merge-base", "--is-ancestor", APPROVED_ADMIN_HEAD, "HEAD"]).returncode != 0:
        _deny("CODESPACES_APPROVED_ADMIN_HEAD_NOT_ANCESTOR")


def _operator(*, apply: bool) -> dict:
    cmd = [sys.executable, APPROVED_OPERATOR_PATH] + (["--apply"] if apply else [])
    proc = _run(cmd)
    if proc.returncode != 0:
        _deny("CODESPACES_APPROVED_OPERATOR_FAILED")
    try:
        value = json.loads(proc.stdout)
    except Exception as exc:
        raise Denied("CODESPACES_APPROVED_OPERATOR_JSON_INVALID") from exc
    if not isinstance(value, dict):
        _deny("CODESPACES_APPROVED_OPERATOR_RESULT_INVALID")
    allowed = {"DRY_RUN_WOULD_CREATE_EXACT_RULESET", "EXISTING_EXACT_VERIFIED",
               "EXISTING_EXACT_VERIFIED_AFTER_REFRESH", "CREATED_AND_FRESH_VERIFIED"}
    if value.get("status") not in allowed:
        _deny("CODESPACES_APPROVED_OPERATOR_STATUS_UNEXPECTED")
    if apply and value.get("status") not in allowed - {"DRY_RUN_WOULD_CREATE_EXACT_RULESET"}:
        _deny("CODESPACES_APPLY_DID_NOT_PROVISION_OR_VERIFY")
    return value


def _assert_session_state_storage_secure(*, create: bool) -> pathlib.Path:
    root = pathlib.Path(SESSION_STATE_DIR)
    if create and not os.path.lexists(SESSION_STATE_DIR):
        try:
            os.mkdir(SESSION_STATE_DIR, 0o700)
        except FileExistsError:
            pass
    try:
        st = os.lstat(root)
    except FileNotFoundError as exc:
        raise Denied("CODESPACES_SESSION_STATE_DIR_MISSING") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        _deny("CODESPACES_SESSION_STATE_DIR_MUST_BE_REAL_DIRECTORY")
    if st.st_uid != _effective_uid() or stat.S_IMODE(st.st_mode) != 0o700:
        _deny("CODESPACES_SESSION_STATE_DIR_PERMISSIONS")
    _memory_filesystem_type(SESSION_STATE_DIR)
    _assert_swap_absent()
    return root


def _session_marker_path(session_id: str) -> pathlib.Path:
    if not _HEX32.fullmatch(session_id):
        _deny("CODESPACES_CLEANUP_SESSION_ID_INVALID")
    return pathlib.Path(SESSION_STATE_DIR) / (session_id + ".json")


def _create_origin_session_marker(*, apply: bool) -> str:
    root = _assert_session_state_storage_secure(create=True)
    session_id = secrets.token_hex(16)
    path = root / (session_id + ".json")
    payload = {
        "schema_version": "MULTIVERSE_R1_STAGE1_CODESPACES_ORIGIN_SESSION_MARKER_v1",
        "session_id": session_id,
        "codespace_name": _codespace_name(),
        "approved_admin_head": APPROVED_ADMIN_HEAD,
        "approved_operator_blob": APPROVED_OPERATOR_BLOB,
        "mode": "apply" if apply else "rehearsal",
        "gh_config_dir": EXPECTED_GH_CONFIG_DIR,
        "phase_c_gate_open": False,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(_canonical_json(payload))
            handle.flush()
            os.fsync(handle.fileno())
        st = os.lstat(path)
    except Exception as exc:
        try:
            if os.path.lexists(path):
                os.unlink(path)
        except Exception:
            pass
        raise Denied("CODESPACES_ORIGIN_SESSION_MARKER_CREATE_FAILED") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        _deny("CODESPACES_ORIGIN_SESSION_MARKER_IDENTITY")
    if st.st_uid != _effective_uid() or stat.S_IMODE(st.st_mode) != 0o600:
        _deny("CODESPACES_ORIGIN_SESSION_MARKER_PERMISSIONS")
    return session_id


def _consume_origin_session_marker(session_id: str) -> dict:
    _assert_session_state_storage_secure(create=False)
    path = _session_marker_path(session_id)
    try:
        before = os.lstat(path)
    except FileNotFoundError as exc:
        raise Denied("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_MISSING") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        _deny("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_IDENTITY")
    if before.st_uid != _effective_uid() or stat.S_IMODE(before.st_mode) != 0o600:
        _deny("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_PERMISSIONS")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                _deny("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_RACE")
            payload = json.load(handle)
    except Denied:
        raise
    except Exception as exc:
        raise Denied("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_INVALID") from exc
    if not isinstance(payload, dict):
        _deny("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_INVALID")
    expected = {
        "session_id": session_id,
        "codespace_name": _codespace_name(),
        "approved_admin_head": APPROVED_ADMIN_HEAD,
        "approved_operator_blob": APPROVED_OPERATOR_BLOB,
        "gh_config_dir": EXPECTED_GH_CONFIG_DIR,
        "phase_c_gate_open": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            _deny("CODESPACES_CLEANUP_ORIGIN_SESSION_BINDING_MISMATCH:" + key)
    if payload.get("mode") not in {"rehearsal", "apply"}:
        _deny("CODESPACES_CLEANUP_ORIGIN_SESSION_BINDING_MISMATCH:mode")
    try:
        os.unlink(path)
    except Exception as exc:
        raise Denied("CODESPACES_CLEANUP_ORIGIN_SESSION_MARKER_CONSUME_FAILED") from exc
    return payload


def _result(*, apply: bool, scopes: list[str], operator_result: Mapping[str, Any], session_id: str) -> dict:
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_CODESPACES_ADMIN_CHANNEL_RESULT_v3",
        "status": "CODESPACES_APPLY_PENDING_MANDATORY_CLEANUP" if apply
                  else "CODESPACES_IPHONE_REHEARSAL_DRY_RUN_PENDING_CLEANUP",
        "session_id": session_id,
        "canonical_repo": CANONICAL_REPO,
        "approved_admin_head": APPROVED_ADMIN_HEAD,
        "approved_auditor_review": APPROVED_AUDITOR_REVIEW,
        "lab_result_comment": LAB_RESULT_COMMENT,
        "approved_operator_blob": APPROVED_OPERATOR_BLOB,
        "authentication_method": "GH_CLI_WEB_OAUTH_MEMORY_FS_NO_ACTIVE_SWAP",
        "oauth_scopes": scopes,
        "operator_status": operator_result.get("status"),
        "ruleset_id": operator_result.get("ruleset_id"),
        "ruleset_updated_at": operator_result.get("ruleset_updated_at"),
        "credential_material_printed": False,
        "environment_token_used": False,
        "origin_session_marker_created": True,
        "local_cleanup_proof_required": True,
        "codespace_deletion_required": True,
        "durable_github_cleanup_receipt_required": True,
        "phase_c_gate_open": False,
        "runtime_activation_performed": False,
    }


def _cleanup_check(session_id: str) -> dict:
    if not _HEX32.fullmatch(session_id):
        _deny("CODESPACES_CLEANUP_SESSION_ID_INVALID")
    _assert_env_clean()
    codespace_name = _codespace_name()
    if os.environ.get("GH_CONFIG_DIR") not in (None, ""):
        _deny("CODESPACES_CLEANUP_GH_CONFIG_DIR_MUST_BE_UNSET")
    if os.path.lexists(EXPECTED_GH_CONFIG_DIR):
        _deny("CODESPACES_CLEANUP_AUTH_PATH_STILL_EXISTS")
    marker = _consume_origin_session_marker(session_id)
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_CODESPACES_LOCAL_CLEANUP_PROOF_v2",
        "status": "CODESPACES_LOCAL_CREDENTIAL_CLEANUP_VERIFIED",
        "session_id": session_id,
        "codespace_name": codespace_name,
        "origin_session_mode": marker.get("mode"),
        "origin_session_bound": True,
        "origin_codespace_bound": True,
        "origin_session_marker_consumed": True,
        "environment_tokens_absent": True,
        "gh_config_dir_unset": True,
        "auth_path_absent_no_follow": True,
        "codespace_deletion_still_required": True,
        "durable_github_cleanup_receipt_still_required": True,
        "phase_c_gate_open": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--cleanup-check")
    parser.add_argument("--pre-auth-check", action="store_true")
    args = parser.parse_args(argv)
    if sum((bool(args.apply), bool(args.cleanup_check), bool(args.pre_auth_check))) > 1:
        _deny("CODESPACES_ARGUMENT_MODE_CONFLICT")
    if args.pre_auth_check:
        print(_canonical_json(_pre_auth_check()))
        return 0
    if args.cleanup_check:
        print(_canonical_json(_cleanup_check(args.cleanup_check)))
        return 0
    _assert_env_clean()
    _assert_auth_storage_secure()
    _assert_local_gh_config_safe()
    scopes = _verify_oauth()
    _verify_approved_operator()
    session_id = _create_origin_session_marker(apply=args.apply)
    operator_result = _operator(apply=args.apply)
    print(_canonical_json(_result(apply=args.apply, scopes=scopes,
                                  operator_result=operator_result, session_id=session_id)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Denied as exc:
        print(_canonical_json({"status": "DENIED_FAIL_CLOSED", "reason": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
