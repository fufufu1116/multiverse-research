#!/usr/bin/env python3
"""Nonmutating, nonsecret GitHub API transport probe for Phase-C diagnosis."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from typing import Any

EXPECTED_GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
API_VERSION = "2022-11-28"


def deny(code: str) -> None:
    raise RuntimeError(code)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())


def assert_clean_boundary() -> None:
    if os.environ.get("CODESPACES") != "true" or not os.environ.get("CODESPACE_NAME"):
        deny("PHASE_C_TRANSPORT_PROBE_CODESPACES_REQUIRED")
    if os.environ.get("GH_CONFIG_DIR") != EXPECTED_GH_CONFIG_DIR:
        deny("PHASE_C_TRANSPORT_PROBE_GH_CONFIG_DIR_NOT_PINNED")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        if os.environ.get(key):
            deny("PHASE_C_TRANSPORT_PROBE_AMBIENT_TOKEN_PROHIBITED:" + key)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "GH_DEBUG", "DEBUG"):
        if os.environ.get(key):
            deny("PHASE_C_TRANSPORT_PROBE_PROXY_CA_OR_DEBUG_PROHIBITED:" + key)
    if shutil.which("gh") is None:
        deny("PHASE_C_TRANSPORT_PROBE_GH_REQUIRED")


def classify_stderr(text: str) -> str:
    s = text.lower()
    if not s.strip():
        return "EMPTY"
    groups = (
        ("AUTH_OR_LOGIN", (r"not logged", r"authenticate", r"authentication", r"oauth", r"login required", r"http 401", r"http 403")),
        ("DNS_OR_NAME_RESOLUTION", (r"no such host", r"name resolution", r"temporary failure in name resolution", r"dns")),
        ("CONNECT_OR_TIMEOUT", (r"connection refused", r"connection reset", r"network is unreachable", r"timed out", r"timeout", r"i/o timeout", r"context deadline")),
        ("TLS_OR_CERTIFICATE", (r"x509", r"certificate", r"tls", r"ssl")),
        ("CLI_USAGE_OR_CONFIG", (r"unknown flag", r"usage:", r"invalid argument", r"required flag", r"configuration", r"config file")),
        ("HTTP_OR_API", (r"bad gateway", r"service unavailable", r"gateway timeout", r"http status", r"api.github.com")),
    )
    for label, patterns in groups:
        if any(re.search(p, s) for p in patterns):
            return label
    return "OTHER_NONEMPTY"


def parse_http_status(stdout: str) -> int | None:
    for line in stdout.replace("\r\n", "\n").splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
            return None
    return None


def probe_user() -> dict[str, Any]:
    assert_clean_boundary()
    cmd = [
        "gh", "api", "--hostname", "github.com", "--include",
        "-H", "Accept: application/vnd.github+json",
        "-H", f"X-GitHub-Api-Version: {API_VERSION}",
        "--method", "GET", "/user",
    ]
    proc = run(cmd)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return {
        "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_GITHUB_API_TRANSPORT_PROBE_v1",
        "status": "PHASE_C_GITHUB_API_TRANSPORT_PROBE_CAPTURE_COMPLETE",
        "endpoint_kind": "user",
        "gh_process_returncode": proc.returncode,
        "stdout_present": bool(stdout.strip()),
        "stdout_length": len(stdout.encode("utf-8")),
        "stderr_present": bool(stderr.strip()),
        "stderr_length": len(stderr.encode("utf-8")),
        "stderr_classification": classify_stderr(stderr),
        "http_status": parse_http_status(stdout),
        "raw_stdout_emitted": False,
        "raw_stderr_emitted": False,
        "credential_material_accessed_by_probe": False,
        "production_apply_invocations": 0,
        "production_mutation_performed": False,
        "runtime_activation_performed": False,
    }


def selftest() -> None:
    cases = {
        "": "EMPTY",
        "authentication required": "AUTH_OR_LOGIN",
        "lookup api.github.com: no such host": "DNS_OR_NAME_RESOLUTION",
        "dial tcp: i/o timeout": "CONNECT_OR_TIMEOUT",
        "x509: certificate signed by unknown authority": "TLS_OR_CERTIFICATE",
        "unknown flag: --wat": "CLI_USAGE_OR_CONFIG",
        "502 Bad Gateway from api.github.com": "HTTP_OR_API",
        "opaque failure": "OTHER_NONEMPTY",
    }
    for sample, expected in cases.items():
        assert classify_stderr(sample) == expected
    assert parse_http_status("HTTP/2.0 200 OK\r\nX: y\r\n\r\n{}") == 200
    assert parse_http_status("") is None
    print("PHASE_C_GITHUB_API_TRANSPORT_PROBE_SELFTEST_PASS")
    print("RAW_STDOUT_EMITTED=false")
    print("RAW_STDERR_EMITTED=false")
    print("PRODUCTION_MUTATION_PERFORMED=false")
    print("RUNTIME_ACTIVATION_PERFORMED=false")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--probe-user", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            selftest()
        else:
            print(json.dumps(probe_user(), sort_keys=True, separators=(",", ":")))
    except Exception as exc:
        print(json.dumps({
            "schema_version": "MULTIVERSE_R1_STAGE1_PHASE_C_GITHUB_API_TRANSPORT_PROBE_v1",
            "status": "PHASE_C_GITHUB_API_TRANSPORT_PROBE_FAILED_CLOSED",
            "reason": str(exc),
            "raw_stdout_emitted": False,
            "raw_stderr_emitted": False,
            "production_apply_invocations": 0,
            "production_mutation_performed": False,
            "runtime_activation_performed": False,
        }, sort_keys=True, separators=(",", ":")))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
