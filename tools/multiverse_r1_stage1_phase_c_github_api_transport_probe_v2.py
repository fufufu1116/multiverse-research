#!/usr/bin/env python3
"""Nonmutating, nonsecret GitHub API transport probe v2 for Phase-C diagnosis."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
from typing import Any

EXPECTED_GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
API_VERSION = "2022-11-28"

FAILURE_REASONS = frozenset({
    "PHASE_C_TRANSPORT_PROBE_CODESPACES_REQUIRED",
    "PHASE_C_TRANSPORT_PROBE_GH_CONFIG_DIR_NOT_PINNED",
    "PHASE_C_TRANSPORT_PROBE_AMBIENT_TOKEN_PROHIBITED",
    "PHASE_C_TRANSPORT_PROBE_GH_HOST_OVERRIDE_PROHIBITED",
    "PHASE_C_TRANSPORT_PROBE_PROXY_CA_OR_DEBUG_PROHIBITED",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_MISSING",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_IDENTITY",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_PERMISSIONS",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_NOT_MEMORY_FILESYSTEM",
    "PHASE_C_TRANSPORT_PROBE_SWAP_STATE_UNREADABLE",
    "PHASE_C_TRANSPORT_PROBE_ACTIVE_SWAP_PROHIBITED",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_CHILD_IDENTITY",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_CHILD_PERMISSIONS",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_FILE_IDENTITY",
    "PHASE_C_TRANSPORT_PROBE_MEMORY_FILE_PERMISSIONS",
    "PHASE_C_TRANSPORT_PROBE_GH_REQUIRED",
    "PHASE_C_TRANSPORT_PROBE_GH_CONFIG_QUERY_FAILED",
    "PHASE_C_TRANSPORT_PROBE_GH_HTTP_UNIX_SOCKET_PROHIBITED_OR_AMBIGUOUS",
    "PHASE_C_TRANSPORT_PROBE_UNEXPECTED_LOCAL_EXCEPTION",
})

class ProbeDenied(RuntimeError):
    def __init__(self, code: str) -> None:
        if code not in FAILURE_REASONS:
            raise ValueError("unregistered probe failure code")
        self.code = code
        super().__init__(code)

def deny(code: str) -> None:
    raise ProbeDenied(code)

def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())

def assert_no_swap() -> None:
    try:
        rows = [x for x in pathlib.Path("/proc/swaps").read_text().splitlines() if x.strip()]
    except Exception:
        deny("PHASE_C_TRANSPORT_PROBE_SWAP_STATE_UNREADABLE")
    if len(rows) != 1 or not rows[0].lower().startswith("filename"):
        deny("PHASE_C_TRANSPORT_PROBE_ACTIVE_SWAP_PROHIBITED")

def assert_memory_dir(path: str) -> None:
    p = pathlib.Path(path)
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        deny("PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_MISSING")
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        deny("PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_IDENTITY")
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
        deny("PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_PERMISSIONS")
    fs = run(["stat", "-f", "-c", "%T", path])
    if fs.returncode != 0 or fs.stdout.strip() not in {"tmpfs", "ramfs"}:
        deny("PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_NOT_MEMORY_FILESYSTEM")
    assert_no_swap()
    for root, dirs, files in os.walk(p, topdown=True, followlinks=False):
        base = pathlib.Path(root)
        for name in dirs:
            s = os.lstat(base / name)
            if stat.S_ISLNK(s.st_mode) or not stat.S_ISDIR(s.st_mode):
                deny("PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_CHILD_IDENTITY")
            if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) != 0o700:
                deny("PHASE_C_TRANSPORT_PROBE_MEMORY_DIR_CHILD_PERMISSIONS")
        for name in files:
            s = os.lstat(base / name)
            if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
                deny("PHASE_C_TRANSPORT_PROBE_MEMORY_FILE_IDENTITY")
            if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) & 0o177:
                deny("PHASE_C_TRANSPORT_PROBE_MEMORY_FILE_PERMISSIONS")

def assert_local_gh_config_safe() -> None:
    proc = run(["gh", "config", "list", "--host", "github.com"])
    if proc.returncode != 0:
        deny("PHASE_C_TRANSPORT_PROBE_GH_CONFIG_QUERY_FAILED")
    sockets = [row.split("=", 1)[1].strip() for row in proc.stdout.splitlines() if row.startswith("http_unix_socket=") and "=" in row]
    if len(sockets) != 1 or sockets[0]:
        deny("PHASE_C_TRANSPORT_PROBE_GH_HTTP_UNIX_SOCKET_PROHIBITED_OR_AMBIGUOUS")

def assert_transport_ready() -> None:
    if os.environ.get("CODESPACES") != "true" or not os.environ.get("CODESPACE_NAME"):
        deny("PHASE_C_TRANSPORT_PROBE_CODESPACES_REQUIRED")
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        deny("PHASE_C_TRANSPORT_PROBE_GH_CONFIG_DIR_NOT_PINNED")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        if os.environ.get(key):
            deny("PHASE_C_TRANSPORT_PROBE_AMBIENT_TOKEN_PROHIBITED")
    if os.environ.get("GH_HOST") not in (None, "", "github.com"):
        deny("PHASE_C_TRANSPORT_PROBE_GH_HOST_OVERRIDE_PROHIBITED")
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG"):
        if os.environ.get(key):
            deny("PHASE_C_TRANSPORT_PROBE_PROXY_CA_OR_DEBUG_PROHIBITED")
    assert_memory_dir(EXPECTED_GH_CONFIG_DIR)
    if shutil.which("gh") is None:
        deny("PHASE_C_TRANSPORT_PROBE_GH_REQUIRED")
    assert_local_gh_config_safe()

def classify_stderr(text: str) -> str:
    s = text.lower()
    if not s.strip(): return "EMPTY"
    groups = (
        ("AUTH_OR_LOGIN", (r"not logged", r"authenticate", r"authentication", r"oauth", r"login required", r"http 401", r"http 403")),
        ("DNS_OR_NAME_RESOLUTION", (r"no such host", r"name resolution", r"temporary failure in name resolution", r"dns")),
        ("CONNECT_OR_TIMEOUT", (r"connection refused", r"connection reset", r"network is unreachable", r"timed out", r"timeout", r"i/o timeout", r"context deadline")),
        ("TLS_OR_CERTIFICATE", (r"x509", r"certificate", r"tls", r"ssl")),
        ("CLI_USAGE_OR_CONFIG", (r"unknown flag", r"usage:", r"invalid argument", r"required flag", r"configuration", r"config file")),
        ("HTTP_OR_API", (r"bad gateway", r"service unavailable", r"gateway timeout", r"http status", r"api.github.com")),
    )
    for label, patterns in groups:
        if any(re.search(p, s) for p in patterns): return label
    return "OTHER_NONEMPTY"

def parse_http_status(stdout: str) -> int | None:
    for line in stdout.replace("\r\n", "\n").splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit(): return int(parts[1])
            return None
    return None

def probe_user() -> dict[str, Any]:
    assert_transport_ready()
    cmd = ["gh", "api", "--hostname", "github.com", "--include", "-H", "Accept: application/vnd.github+json", "-H", f"X-GitHub-Api-Version: {API_VERSION}", "--method", "GET", "/user"]
    proc = run(cmd)
    stdout, stderr = proc.stdout or "", proc.stderr or ""
    return {
        "schema_version":"MULTIVERSE_R1_STAGE1_PHASE_C_GITHUB_API_TRANSPORT_PROBE_v2",
        "status":"PHASE_C_GITHUB_API_TRANSPORT_PROBE_CAPTURE_COMPLETE",
        "endpoint_kind":"user",
        "canonical_transport_ready_equivalent_gate_passed":True,
        "gh_api_user_invocations":1,
        "gh_process_returncode":proc.returncode,
        "stdout_present":bool(stdout.strip()), "stdout_length":len(stdout.encode()),
        "stderr_present":bool(stderr.strip()), "stderr_length":len(stderr.encode()),
        "stderr_classification":classify_stderr(stderr), "http_status":parse_http_status(stdout),
        "raw_stdout_emitted":False, "raw_stderr_emitted":False,
        "python_wrapper_direct_credential_material_read":False,
        "authenticated_gh_child_uses_existing_gh_config":True,
        "production_apply_invocations":0, "production_mutation_performed":False, "runtime_activation_performed":False,
    }

def failure_result(reason: str) -> dict[str, Any]:
    if reason not in FAILURE_REASONS: reason = "PHASE_C_TRANSPORT_PROBE_UNEXPECTED_LOCAL_EXCEPTION"
    return {
        "schema_version":"MULTIVERSE_R1_STAGE1_PHASE_C_GITHUB_API_TRANSPORT_PROBE_v2",
        "status":"PHASE_C_GITHUB_API_TRANSPORT_PROBE_FAILED_CLOSED", "reason":reason,
        "raw_exception_text_emitted":False, "raw_stdout_emitted":False, "raw_stderr_emitted":False,
        "python_wrapper_direct_credential_material_read":False,
        "authenticated_gh_child_uses_existing_gh_config":False,
        "production_apply_invocations":0, "production_mutation_performed":False, "runtime_activation_performed":False,
    }

def selftest() -> None:
    cases={"":"EMPTY","authentication required":"AUTH_OR_LOGIN","lookup api.github.com: no such host":"DNS_OR_NAME_RESOLUTION","dial tcp: i/o timeout":"CONNECT_OR_TIMEOUT","x509: certificate signed by unknown authority":"TLS_OR_CERTIFICATE","unknown flag: --wat":"CLI_USAGE_OR_CONFIG","502 Bad Gateway from api.github.com":"HTTP_OR_API","opaque failure":"OTHER_NONEMPTY"}
    for sample,expected in cases.items(): assert classify_stderr(sample)==expected
    assert parse_http_status("HTTP/2.0 200 OK\r\nX: y\r\n\r\n{}") == 200
    assert parse_http_status("") is None
    assert failure_result("not-allowlisted")["reason"] == "PHASE_C_TRANSPORT_PROBE_UNEXPECTED_LOCAL_EXCEPTION"
    assert all(x.startswith("PHASE_C_TRANSPORT_PROBE_") for x in FAILURE_REASONS)
    print("PHASE_C_GITHUB_API_TRANSPORT_PROBE_V2_SELFTEST_PASS")
    print("RAW_EXCEPTION_TEXT_EMITTED=false")
    print("RAW_STDOUT_EMITTED=false")
    print("RAW_STDERR_EMITTED=false")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")

def main() -> int:
    parser=argparse.ArgumentParser(); mode=parser.add_mutually_exclusive_group(required=True); mode.add_argument("--probe-user",action="store_true"); mode.add_argument("--selftest",action="store_true"); args=parser.parse_args()
    try:
        if args.selftest: selftest()
        else: print(json.dumps(probe_user(),sort_keys=True,separators=(",",":")))
    except ProbeDenied as exc:
        print(json.dumps(failure_result(exc.code),sort_keys=True,separators=(",",":"))); return 2
    except Exception:
        print(json.dumps(failure_result("PHASE_C_TRANSPORT_PROBE_UNEXPECTED_LOCAL_EXCEPTION"),sort_keys=True,separators=(",",":"))); return 2
    return 0

if __name__ == "__main__": raise SystemExit(main())
