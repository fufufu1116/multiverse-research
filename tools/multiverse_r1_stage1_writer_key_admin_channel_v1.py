#!/usr/bin/env python3
"""Read-only iPhone Codespaces administration boundary for R1 Stage-1 Phase C.

Candidate implementation only. This module exposes authentication/fresh-read
and local-cleanup operations. It intentionally exposes no GitHub mutation API.
All future Phase-C mutations are constructed inside the zero-argument
provisioner production path from reviewed literals and internally derived data.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import quote

CANONICAL_REPO = "fufufu1116/multiverse-research"
EXPECTED_LOGIN = "fufufu1116"
ENVIRONMENT_NAME = "multiverse-r1-stage1-writer-key-v1"
FENCE_REF = "refs/tags/multiverse-r1-stage1-writer-provision-fence-v1"
FENCE_SHORT = "tags/multiverse-r1-stage1-writer-provision-fence-v1"
WRITER_PREFIX = "MULTIVERSE_R1_STAGE1_WRITER_KEY_"
RULESET_NAME = "multiverse-r1-stage1-journal-activation-protection-v1"
JOURNAL_INCLUDE = "refs/tags/multiverse-r1-stage1-ledger-v1-*"
ACTIVATION_INCLUDE = "refs/tags/multiverse-r1-stage1-activation-v1"
RULESET_ID = 21227261
RULESET_UPDATED_AT = "2026-08-23T06:39:18.750Z"
EXPECTED_EFFECTIVE_OAUTH_SCOPES = {"repo", "read:org", "gist"}
EXPECTED_GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
SESSION_STATE_DIR = "/dev/shm/multiverse-r1-stage1-phase-c-session-state"
API_VERSION = "2022-11-28"
MAX_PAGES = 100
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_SESSION_ID = re.compile(r"^[0-9a-f]{32}$")


class Denied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise Denied(code)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )


def _assert_env_clean() -> str:
    if os.environ.get("CODESPACES") != "true":
        _deny("PHASE_C_CODESPACES_REQUIRED")
    name = os.environ.get("CODESPACE_NAME", "")
    if not name:
        _deny("PHASE_C_CODESPACE_NAME_REQUIRED")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        if os.environ.get(key):
            _deny("PHASE_C_ENVIRONMENT_TOKEN_PROHIBITED:" + key)
    if os.environ.get("GH_HOST") not in (None, "", "github.com"):
        _deny("PHASE_C_GH_HOST_OVERRIDE_PROHIBITED")
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG",
    ):
        if os.environ.get(key):
            _deny("PHASE_C_PROXY_CA_OR_DEBUG_PROHIBITED:" + key)
    return name


def _assert_no_swap() -> None:
    try:
        rows = [x for x in pathlib.Path("/proc/swaps").read_text().splitlines() if x.strip()]
    except Exception as exc:
        raise Denied("PHASE_C_SWAP_STATE_UNREADABLE") from exc
    if len(rows) != 1 or not rows[0].lower().startswith("filename"):
        _deny("PHASE_C_ACTIVE_SWAP_PROHIBITED")


def _assert_memory_dir(path: str, *, require_empty: bool = False, create: bool = False) -> pathlib.Path:
    p = pathlib.Path(path)
    if create and not os.path.lexists(path):
        os.mkdir(path, 0o700)
    try:
        st = os.lstat(p)
    except FileNotFoundError as exc:
        raise Denied("PHASE_C_MEMORY_DIR_MISSING") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        _deny("PHASE_C_MEMORY_DIR_IDENTITY")
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
        _deny("PHASE_C_MEMORY_DIR_PERMISSIONS")
    fs = _run(["stat", "-f", "-c", "%T", path])
    if fs.returncode != 0 or fs.stdout.strip() not in {"tmpfs", "ramfs"}:
        _deny("PHASE_C_MEMORY_DIR_NOT_MEMORY_FILESYSTEM")
    _assert_no_swap()
    count = 0
    for root, dirs, files in os.walk(p, topdown=True, followlinks=False):
        base = pathlib.Path(root)
        count += len(dirs) + len(files)
        for name in dirs:
            s = os.lstat(base / name)
            if stat.S_ISLNK(s.st_mode) or not stat.S_ISDIR(s.st_mode):
                _deny("PHASE_C_MEMORY_DIR_CHILD_IDENTITY")
            if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) != 0o700:
                _deny("PHASE_C_MEMORY_DIR_CHILD_PERMISSIONS")
        for name in files:
            s = os.lstat(base / name)
            if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
                _deny("PHASE_C_MEMORY_FILE_IDENTITY")
            if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) & 0o177:
                _deny("PHASE_C_MEMORY_FILE_PERMISSIONS")
    if require_empty and count:
        _deny("PHASE_C_PREAUTH_MEMORY_DIR_NOT_EMPTY")
    return p


def _assert_local_gh_config_safe() -> None:
    proc = _run(["gh", "config", "list", "--host", "github.com"])
    if proc.returncode != 0:
        _deny("PHASE_C_GH_CONFIG_QUERY_FAILED")
    sockets = [
        row.split("=", 1)[1].strip()
        for row in proc.stdout.splitlines()
        if row.startswith("http_unix_socket=") and "=" in row
    ]
    if len(sockets) != 1 or sockets[0]:
        _deny("PHASE_C_GH_HTTP_UNIX_SOCKET_PROHIBITED_OR_AMBIGUOUS")


def preauth_storage_proof() -> dict[str, Any]:
    name = _assert_env_clean()
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        _deny("PHASE_C_GH_CONFIG_DIR_NOT_PINNED")
    _assert_memory_dir(EXPECTED_GH_CONFIG_DIR, require_empty=True)
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_PREAUTH_PROOF_v1",
        "status": "PHASE_C_PREAUTH_STORAGE_VERIFIED",
        "codespace_name": name,
        "gh_config_dir": EXPECTED_GH_CONFIG_DIR,
        "active_swap_absent": True,
        "credential_material_accessed": False,
        "production_mutation_performed": False,
        "runtime_activation_performed": False,
    }


def _parse_included_response(text: str) -> tuple[int, dict[str, str], Any]:
    header, sep, body = text.replace("\r\n", "\n").partition("\n\n")
    if not sep:
        _deny("PHASE_C_API_RESPONSE_HEADERS_MISSING")
    lines = [x for x in header.splitlines() if x]
    if not lines or not lines[0].startswith("HTTP/"):
        _deny("PHASE_C_API_HTTP_STATUS_MISSING")
    try:
        status = int(lines[0].split()[1])
    except Exception as exc:
        raise Denied("PHASE_C_API_HTTP_STATUS_INVALID") from exc
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().lower()
        if key in headers:
            _deny("PHASE_C_API_DUPLICATE_HEADER:" + key)
        headers[key] = v.strip()
    raw = body.strip()
    if not raw:
        payload: Any = None
    else:
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise Denied("PHASE_C_API_JSON_INVALID") from exc
    return status, headers, payload


def _environment_path() -> str:
    return f"/repos/{CANONICAL_REPO}/environments/{quote(ENVIRONMENT_NAME, safe='')}"


def _repo_secret_list_base() -> str:
    return f"/repos/{CANONICAL_REPO}/actions/secrets"


def _env_secret_list_base() -> str:
    return _environment_path() + "/secrets"


def _env_policy_list_base() -> str:
    return _environment_path() + "/deployment-branch-policies"


def _env_public_key_path() -> str:
    return _environment_path() + "/secrets/public-key"


def _paged(base: str, page: int) -> str:
    if not isinstance(page, int) or isinstance(page, bool) or not (1 <= page <= MAX_PAGES):
        _deny("PHASE_C_API_PAGE_INVALID")
    return f"{base}?per_page=100&page={page}"


@dataclass(frozen=True)
class ApiResult:
    status: int
    headers: Mapping[str, str]
    payload: Any


class PhaseCAdminChannel:
    """Read-only authenticated channel. No public GitHub mutation primitive exists."""

    _FIXED_READ_ENDPOINTS = {
        "user": "/user",
        "repo": f"/repos/{CANONICAL_REPO}",
        "main": f"/repos/{CANONICAL_REPO}/git/ref/heads/main",
        "fence": f"/repos/{CANONICAL_REPO}/git/ref/{FENCE_SHORT}",
        "ruleset": f"/repos/{CANONICAL_REPO}/rulesets/{RULESET_ID}",
        "environment": _environment_path(),
        "environment_public_key": _env_public_key_path(),
    }

    def __init__(self) -> None:
        self.assert_transport_ready()

    def assert_transport_ready(self) -> None:
        _assert_env_clean()
        if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
            _deny("PHASE_C_GH_CONFIG_DIR_NOT_PINNED")
        _assert_memory_dir(EXPECTED_GH_CONFIG_DIR)
        if shutil.which("gh") is None:
            _deny("PHASE_C_GH_CLI_REQUIRED")
        _assert_local_gh_config_safe()

    def _read_fixed(self, kind: str, *, page: Optional[int] = None) -> ApiResult:
        self.assert_transport_ready()
        if kind in self._FIXED_READ_ENDPOINTS:
            if page is not None:
                _deny("PHASE_C_READ_PAGE_NOT_ALLOWED_FOR_FIXED_ENDPOINT")
            endpoint = self._FIXED_READ_ENDPOINTS[kind]
        elif kind == "repository_secret_names":
            if page is None:
                _deny("PHASE_C_READ_PAGE_REQUIRED")
            endpoint = _paged(_repo_secret_list_base(), page)
        elif kind == "environment_secret_names":
            if page is None:
                _deny("PHASE_C_READ_PAGE_REQUIRED")
            endpoint = _paged(_env_secret_list_base(), page)
        elif kind == "environment_policies":
            if page is None:
                _deny("PHASE_C_READ_PAGE_REQUIRED")
            endpoint = _paged(_env_policy_list_base(), page)
        else:
            _deny("PHASE_C_READ_KIND_NOT_ALLOWLISTED")
        cmd = [
            "gh", "api", "--hostname", "github.com", "--include",
            "-H", "Accept: application/vnd.github+json",
            "-H", f"X-GitHub-Api-Version: {API_VERSION}",
            "--method", "GET", endpoint,
        ]
        proc = _run(cmd)
        if not proc.stdout.strip():
            _deny("PHASE_C_GITHUB_API_NO_RESPONSE")
        status, headers, body = _parse_included_response(proc.stdout)
        return ApiResult(status=status, headers=headers, payload=body)

    def verify_identity_and_scope(self) -> list[str]:
        result = self._read_fixed("user")
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_USER_API_FAILED")
        if result.payload.get("login") != EXPECTED_LOGIN:
            _deny("PHASE_C_GITHUB_LOGIN_MISMATCH")
        raw = result.headers.get("x-oauth-scopes")
        if raw is None:
            _deny("PHASE_C_OAUTH_SCOPE_HEADER_MISSING")
        scopes = {x.strip() for x in raw.split(",") if x.strip()}
        if scopes != EXPECTED_EFFECTIVE_OAUTH_SCOPES:
            _deny("PHASE_C_OAUTH_SCOPE_SET_NOT_EXACT")
        repo = self._read_fixed("repo")
        permissions = repo.payload.get("permissions") if repo.status == 200 and isinstance(repo.payload, dict) else None
        if not isinstance(permissions, dict) or permissions.get("admin") is not True:
            _deny("PHASE_C_REPOSITORY_ADMIN_REQUIRED")
        return sorted(scopes)

    def fresh_main(self) -> str:
        result = self._read_fixed("main")
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_MAIN_READ_FAILED")
        obj = result.payload.get("object")
        sha = obj.get("sha") if isinstance(obj, dict) else None
        if not isinstance(sha, str) or not _HEX40.fullmatch(sha):
            _deny("PHASE_C_MAIN_SHA_INVALID")
        return sha

    def fence(self) -> Optional[str]:
        result = self._read_fixed("fence")
        if result.status == 404:
            return None
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_FENCE_READ_FAILED")
        obj = result.payload.get("object")
        sha = obj.get("sha") if isinstance(obj, dict) else None
        if not isinstance(sha, str) or not _HEX40.fullmatch(sha):
            _deny("PHASE_C_FENCE_SHA_INVALID")
        return sha

    def verify_ruleset(self) -> dict[str, Any]:
        result = self._read_fixed("ruleset")
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_RULESET_READ_FAILED")
        detail = result.payload
        if detail.get("id") != RULESET_ID or detail.get("updated_at") != RULESET_UPDATED_AT:
            _deny("PHASE_C_RULESET_BINDING_DRIFT")
        if detail.get("name") != RULESET_NAME or detail.get("target") != "tag" or detail.get("enforcement") != "active":
            _deny("PHASE_C_RULESET_IDENTITY_OR_ENFORCEMENT_DRIFT")
        if detail.get("bypass_actors") != []:
            _deny("PHASE_C_RULESET_BYPASS_DRIFT")
        if detail.get("source_type") not in (None, "Repository") or detail.get("source") not in (None, CANONICAL_REPO):
            _deny("PHASE_C_RULESET_SOURCE_DRIFT")
        cond = detail.get("conditions")
        if not isinstance(cond, dict) or set(cond) != {"ref_name"}:
            _deny("PHASE_C_RULESET_CONDITIONS_DRIFT")
        ref = cond.get("ref_name")
        if not isinstance(ref, dict) or set(ref) != {"include", "exclude"}:
            _deny("PHASE_C_RULESET_REF_CONDITION_INVALID")
        includes, excludes = ref.get("include"), ref.get("exclude")
        if not isinstance(includes, list) or len(includes) != 2 or set(includes) != {JOURNAL_INCLUDE, ACTIVATION_INCLUDE}:
            _deny("PHASE_C_RULESET_INCLUDE_DRIFT")
        if excludes != []:
            _deny("PHASE_C_RULESET_EXCLUDE_DRIFT")
        rules = detail.get("rules")
        if not isinstance(rules, list) or len(rules) != 3:
            _deny("PHASE_C_RULESET_RULES_DRIFT")
        types = []
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("type") not in {"deletion", "update", "non_fast_forward"}:
                _deny("PHASE_C_RULESET_RULES_DRIFT")
            extras = set(rule) - {"type"}
            if extras and any(rule.get(key) not in (None, {}, False) for key in extras):
                _deny("PHASE_C_RULESET_RULE_PARAMETERS_DRIFT")
            types.append(rule["type"])
        if set(types) != {"deletion", "update", "non_fast_forward"}:
            _deny("PHASE_C_RULESET_RULES_DRIFT")
        return {"id": RULESET_ID, "updated_at": RULESET_UPDATED_AT, "no_bypass": True, "creation_rule_absent": True}

    def probe_environment(self) -> ApiResult:
        return self._read_fixed("environment")

    def environment(self) -> Mapping[str, Any]:
        result = self.probe_environment()
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_ENVIRONMENT_READ_FAILED")
        return result.payload

    def _paged_rows(self, kind: str, field: str) -> list[Mapping[str, Any]]:
        out: list[Mapping[str, Any]] = []
        declared_total: Optional[int] = None
        for page in range(1, MAX_PAGES + 1):
            result = self._read_fixed(kind, page=page)
            if result.status != 200 or not isinstance(result.payload, dict):
                _deny("PHASE_C_PAGED_INVENTORY_FAILED")
            rows = result.payload.get(field)
            total = result.payload.get("total_count")
            if not isinstance(rows, list) or not isinstance(total, int) or isinstance(total, bool) or total < 0:
                _deny("PHASE_C_PAGED_INVENTORY_SCHEMA")
            if declared_total is None:
                declared_total = total
            elif total != declared_total:
                _deny("PHASE_C_PAGED_INVENTORY_TOTAL_DRIFT")
            for row in rows:
                if not isinstance(row, dict):
                    _deny("PHASE_C_PAGED_INVENTORY_ENTRY_INVALID")
                out.append(row)
            if len(rows) < 100:
                break
        else:
            _deny("PHASE_C_PAGED_INVENTORY_UNBOUNDED")
        if declared_total is None or len(out) != declared_total:
            _deny("PHASE_C_PAGED_INVENTORY_INCOMPLETE")
        return out

    def policies(self) -> list[Mapping[str, Any]]:
        return self._paged_rows("environment_policies", "branch_policies")

    def secret_names(self) -> tuple[set[str], set[str]]:
        def names(kind: str) -> set[str]:
            rows = self._paged_rows(kind, "secrets")
            out: set[str] = set()
            for row in rows:
                name = row.get("name")
                if not isinstance(name, str) or not name or name in out:
                    _deny("PHASE_C_SECRET_INVENTORY_NAME_INVALID_OR_DUPLICATE")
                out.add(name)
            return out
        return names("repository_secret_names"), names("environment_secret_names")

    def public_key(self) -> tuple[str, str]:
        result = self._read_fixed("environment_public_key")
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_ENVIRONMENT_PUBLIC_KEY_FAILED")
        key_id, key = result.payload.get("key_id"), result.payload.get("key")
        if not isinstance(key_id, str) or not key_id or not isinstance(key, str) or not key:
            _deny("PHASE_C_ENVIRONMENT_PUBLIC_KEY_INVALID")
        return key_id, key


def _consume_session_marker(session_id: str) -> dict[str, Any]:
    if not _SESSION_ID.fullmatch(session_id):
        _deny("PHASE_C_SESSION_ID_INVALID")
    root = _assert_memory_dir(SESSION_STATE_DIR)
    path = root / (session_id + ".json")
    try:
        before = os.lstat(path)
    except FileNotFoundError as exc:
        raise Denied("PHASE_C_SESSION_MARKER_MISSING") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        _deny("PHASE_C_SESSION_MARKER_IDENTITY")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _deny("PHASE_C_SESSION_MARKER_RACE")
        payload = json.load(handle)
    if not isinstance(payload, dict) or payload.get("session_id") != session_id:
        _deny("PHASE_C_SESSION_MARKER_CONTENT")
    if payload.get("codespace_name") != os.environ.get("CODESPACE_NAME"):
        _deny("PHASE_C_SESSION_CODESPACE_BINDING")
    path.unlink()
    return payload


def cleanup_local_credentials(session_id: str) -> dict[str, Any]:
    name = _assert_env_clean()
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        _deny("PHASE_C_GH_CONFIG_DIR_NOT_PINNED")
    cfg = _assert_memory_dir(EXPECTED_GH_CONFIG_DIR)
    marker = _consume_session_marker(session_id)
    logout = _run(["gh", "auth", "logout", "--hostname", "github.com"])
    if logout.returncode not in {0, 1}:
        _deny("PHASE_C_LOCAL_LOGOUT_FAILED")
    for child in list(cfg.iterdir()):
        if child.is_symlink():
            _deny("PHASE_C_CLEANUP_SYMLINK_PROHIBITED")
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    _assert_memory_dir(EXPECTED_GH_CONFIG_DIR, require_empty=True)
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_LOCAL_CLEANUP_PROOF_v1",
        "status": "PHASE_C_LOCAL_CREDENTIAL_COPY_DESTROYED",
        "codespace_name": name,
        "session_id": session_id,
        "origin_session_bound": marker.get("session_id") == session_id,
        "origin_session_marker_consumed": True,
        "gh_auth_logout_semantics": "LOCAL_CONFIGURATION_REMOVAL_ONLY_NOT_SERVER_REVOCATION",
        "memory_backed_credential_directory_empty": True,
        "codespace_deletion_still_required": True,
        "runtime_activation_performed": False,
    }


def selftest() -> None:
    forbidden = {"api", "create_fence", "configure_locked_environment", "put_encrypted_secret"}
    assert not forbidden.intersection(set(dir(PhaseCAdminChannel)))
    assert EXPECTED_EFFECTIVE_OAUTH_SCOPES == {"repo", "read:org", "gist"}
    assert PhaseCAdminChannel._FIXED_READ_ENDPOINTS["fence"].endswith(FENCE_SHORT)
    print("PHASE_C_ADMIN_CHANNEL_READ_ONLY_SURFACE_SELFTEST_PASS")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preauth", action="store_true")
    mode.add_argument("--cleanup", metavar="SESSION_ID")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.preauth:
        print(json.dumps(preauth_storage_proof(), sort_keys=True))
    elif args.cleanup:
        print(json.dumps(cleanup_local_credentials(args.cleanup), sort_keys=True))
    else:
        selftest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
