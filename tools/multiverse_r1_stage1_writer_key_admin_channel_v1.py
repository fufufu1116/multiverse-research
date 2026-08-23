#!/usr/bin/env python3
"""Reviewed iPhone Codespaces administration boundary for R1 Stage-1 Phase C.

Candidate implementation only. It exposes a narrow API client used by the
writer-key provisioner and a local cleanup operation. It never prints or reads
secret values from GitHub and it rejects environment-supplied GitHub tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
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
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_WRITER_ID = re.compile(r"^MULTIVERSE_R1_STAGE1_WRITER_KEY_[0-9A-F]{32}$")
_SESSION_ID = re.compile(r"^[0-9a-f]{32}$")


class Denied(RuntimeError):
    pass


def _deny(code: str) -> None:
    raise Denied(code)


def _run(cmd: list[str], *, input_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
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
    normalized = text.replace("\r\n", "\n")
    header, sep, body = normalized.partition("\n\n")
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
    body = body.strip()
    if not body:
        payload: Any = None
    else:
        try:
            payload = json.loads(body)
        except Exception as exc:
            raise Denied("PHASE_C_API_JSON_INVALID") from exc
    return status, headers, payload


def _environment_path() -> str:
    return f"/repos/{CANONICAL_REPO}/environments/{quote(ENVIRONMENT_NAME, safe='')}"


def _repo_secret_list_path() -> str:
    return f"/repos/{CANONICAL_REPO}/actions/secrets?per_page=100"


def _env_secret_list_path() -> str:
    return _environment_path() + "/secrets?per_page=100"


def _env_public_key_path() -> str:
    return _environment_path() + "/secrets/public-key"


def _env_policy_list_path() -> str:
    return _environment_path() + "/deployment-branch-policies?per_page=100"


def _writer_secret_path(writer_key_id: str) -> str:
    if not _WRITER_ID.fullmatch(writer_key_id):
        _deny("PHASE_C_WRITER_KEY_ID_INVALID")
    return _environment_path() + "/secrets/" + writer_key_id


@dataclass(frozen=True)
class ApiResult:
    status: int
    headers: Mapping[str, str]
    payload: Any


class PhaseCAdminChannel:
    """Exact method/endpoint allowlist. No arbitrary endpoint caller input."""

    def __init__(self) -> None:
        _assert_env_clean()
        if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
            _deny("PHASE_C_GH_CONFIG_DIR_NOT_PINNED")
        _assert_memory_dir(EXPECTED_GH_CONFIG_DIR)
        if shutil.which("gh") is None:
            _deny("PHASE_C_GH_CLI_REQUIRED")

    @staticmethod
    def _allowed(method: str, endpoint: str) -> bool:
        fixed = {
            ("GET", "/user"),
            ("GET", f"/repos/{CANONICAL_REPO}"),
            ("GET", f"/repos/{CANONICAL_REPO}/git/ref/heads/main"),
            ("GET", f"/repos/{CANONICAL_REPO}/git/ref/{FENCE_SHORT}"),
            ("GET", f"/repos/{CANONICAL_REPO}/rulesets/{RULESET_ID}"),
            ("GET", _environment_path()),
            ("GET", _repo_secret_list_path()),
            ("GET", _env_secret_list_path()),
            ("GET", _env_public_key_path()),
            ("GET", _env_policy_list_path()),
            ("POST", f"/repos/{CANONICAL_REPO}/git/refs"),
            ("PUT", _environment_path()),
        }
        if (method, endpoint) in fixed:
            return True
        return method == "PUT" and endpoint.startswith(_environment_path() + "/secrets/") and bool(
            _WRITER_ID.fullmatch(endpoint.rsplit("/", 1)[-1])
        )

    def api(self, method: str, endpoint: str, *, payload: Any = None) -> ApiResult:
        if method not in {"GET", "POST", "PUT"} or not self._allowed(method, endpoint):
            _deny("PHASE_C_API_METHOD_OR_ENDPOINT_NOT_ALLOWLISTED")
        cmd = [
            "gh", "api", "--hostname", "github.com", "--include",
            "-H", "Accept: application/vnd.github+json",
            "-H", f"X-GitHub-Api-Version: {API_VERSION}",
            "--method", method, endpoint,
        ]
        input_text = None
        if payload is not None:
            input_text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            cmd += ["--input", "-"]
        proc = _run(cmd, input_text=input_text)
        if not proc.stdout.strip():
            _deny("PHASE_C_GITHUB_API_NO_RESPONSE")
        status, headers, body = _parse_included_response(proc.stdout)
        return ApiResult(status=status, headers=headers, payload=body)

    def verify_identity_and_scope(self) -> list[str]:
        result = self.api("GET", "/user")
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
        repo = self.api("GET", f"/repos/{CANONICAL_REPO}")
        permissions = repo.payload.get("permissions") if repo.status == 200 and isinstance(repo.payload, dict) else None
        if not isinstance(permissions, dict) or permissions.get("admin") is not True:
            _deny("PHASE_C_REPOSITORY_ADMIN_REQUIRED")
        return sorted(scopes)

    def fresh_main(self) -> str:
        result = self.api("GET", f"/repos/{CANONICAL_REPO}/git/ref/heads/main")
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_MAIN_READ_FAILED")
        obj = result.payload.get("object")
        sha = obj.get("sha") if isinstance(obj, dict) else None
        if not isinstance(sha, str) or not _HEX40.fullmatch(sha):
            _deny("PHASE_C_MAIN_SHA_INVALID")
        return sha

    def fence(self) -> Optional[str]:
        result = self.api("GET", f"/repos/{CANONICAL_REPO}/git/ref/{FENCE_SHORT}")
        if result.status == 404:
            return None
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_FENCE_READ_FAILED")
        obj = result.payload.get("object")
        sha = obj.get("sha") if isinstance(obj, dict) else None
        if not isinstance(sha, str) or not _HEX40.fullmatch(sha):
            _deny("PHASE_C_FENCE_SHA_INVALID")
        return sha

    def create_fence(self, target_sha: str) -> int:
        if not _HEX40.fullmatch(target_sha):
            _deny("PHASE_C_FENCE_TARGET_INVALID")
        result = self.api(
            "POST", f"/repos/{CANONICAL_REPO}/git/refs",
            payload={"ref": FENCE_REF, "sha": target_sha},
        )
        return result.status

    def verify_ruleset(self) -> dict[str, Any]:
        result = self.api("GET", f"/repos/{CANONICAL_REPO}/rulesets/{RULESET_ID}")
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
        includes = ref.get("include")
        excludes = ref.get("exclude")
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
        return {
            "id": RULESET_ID,
            "updated_at": RULESET_UPDATED_AT,
            "no_bypass": True,
            "creation_rule_absent": True,
        }

    def configure_locked_environment(self) -> int:
        payload = {
            "wait_timer": 0,
            "prevent_self_review": False,
            "reviewers": [],
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
        }
        return self.api("PUT", _environment_path(), payload=payload).status

    def environment(self) -> Mapping[str, Any]:
        result = self.api("GET", _environment_path())
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_ENVIRONMENT_READ_FAILED")
        return result.payload

    def policies(self) -> list[Mapping[str, Any]]:
        result = self.api("GET", _env_policy_list_path())
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_DEPLOYMENT_POLICY_LIST_FAILED")
        rows = result.payload.get("branch_policies")
        if not isinstance(rows, list):
            _deny("PHASE_C_DEPLOYMENT_POLICY_LIST_INVALID")
        return [x for x in rows if isinstance(x, dict)]

    def secret_names(self) -> tuple[set[str], set[str]]:
        def names(endpoint: str) -> set[str]:
            result = self.api("GET", endpoint)
            if result.status != 200 or not isinstance(result.payload, dict):
                _deny("PHASE_C_SECRET_INVENTORY_FAILED")
            values = result.payload.get("secrets")
            if not isinstance(values, list):
                _deny("PHASE_C_SECRET_INVENTORY_INVALID")
            out = set()
            for row in values:
                if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                    _deny("PHASE_C_SECRET_INVENTORY_ENTRY_INVALID")
                out.add(row["name"])
            return out
        return names(_repo_secret_list_path()), names(_env_secret_list_path())

    def public_key(self) -> tuple[str, str]:
        result = self.api("GET", _env_public_key_path())
        if result.status != 200 or not isinstance(result.payload, dict):
            _deny("PHASE_C_ENVIRONMENT_PUBLIC_KEY_FAILED")
        key_id, key = result.payload.get("key_id"), result.payload.get("key")
        if not isinstance(key_id, str) or not key_id or not isinstance(key, str) or not key:
            _deny("PHASE_C_ENVIRONMENT_PUBLIC_KEY_INVALID")
        return key_id, key

    def put_encrypted_secret(self, writer_key_id: str, *, key_id: str, encrypted_value: str) -> int:
        if not isinstance(key_id, str) or not key_id:
            _deny("PHASE_C_SECRET_KEY_ID_INVALID")
        if not isinstance(encrypted_value, str) or not encrypted_value:
            _deny("PHASE_C_SECRET_CIPHERTEXT_INVALID")
        result = self.api(
            "PUT", _writer_secret_path(writer_key_id),
            payload={"encrypted_value": encrypted_value, "key_id": key_id},
        )
        return result.status


def create_session_marker() -> str:
    root = _assert_memory_dir(SESSION_STATE_DIR, create=True)
    session_id = secrets.token_hex(16)
    path = root / (session_id + ".json")
    payload = {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_ORIGIN_SESSION_MARKER_v1",
        "session_id": session_id,
        "codespace_name": os.environ.get("CODESPACE_NAME"),
        "gh_config_dir": EXPECTED_GH_CONFIG_DIR,
        "mode": "apply",
        "runtime_activation_performed": False,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        _deny("PHASE_C_SESSION_MARKER_IDENTITY")
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o600:
        _deny("PHASE_C_SESSION_MARKER_PERMISSIONS")
    return session_id


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
    # gh auth logout is local configuration removal only, not server-side revocation.
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
    assert EXPECTED_EFFECTIVE_OAUTH_SCOPES == {"repo", "read:org", "gist"}
    assert PhaseCAdminChannel._allowed("GET", f"/repos/{CANONICAL_REPO}/rulesets/{RULESET_ID}")
    assert PhaseCAdminChannel._allowed("POST", f"/repos/{CANONICAL_REPO}/git/refs")
    assert PhaseCAdminChannel._allowed("PUT", _environment_path())
    assert PhaseCAdminChannel._allowed(
        "PUT", _writer_secret_path("MULTIVERSE_R1_STAGE1_WRITER_KEY_" + "A" * 32)
    )
    assert not PhaseCAdminChannel._allowed("DELETE", f"/repos/{CANONICAL_REPO}/git/refs")
    assert not PhaseCAdminChannel._allowed("PATCH", f"/repos/{CANONICAL_REPO}")
    print("PHASE_C_ADMIN_CHANNEL_ENDPOINT_ALLOWLIST_SELFTEST_PASS")
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
