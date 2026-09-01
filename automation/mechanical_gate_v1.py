#!/usr/bin/env python3
"""Mechanical gate for the minimal routing automation candidate lane."""
from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUTO = ROOT / "automation"
RC = 92
EXPECTED = (
    "multiverse_task_router_v1.py",
    "multiverse_fresh_manifest_v1.py",
    "task_manifest_v1.schema.json",
    "test_multiverse_task_router_v1.py",
    "test_multiverse_fresh_manifest_v1.py",
    "README_MINIMAL_ROUTING_SPRINT_V1.md",
)


def fail(code: str) -> None:
    print(f"MULTIVERSE_AUTOMATION_MECHANICAL_GATE_DENIED:{code}", file=sys.stderr)
    raise SystemExit(RC)


def need(text: str, values: tuple[str, ...], code: str) -> None:
    for value in values:
        if value not in text:
            fail(f"{code}:{value}")


def main() -> int:
    for name in EXPECTED:
        p = AUTO / name
        if not p.is_file():
            fail(f"MISSING:{name}")
    for name in ("multiverse_task_router_v1.py", "multiverse_fresh_manifest_v1.py", "test_multiverse_task_router_v1.py", "test_multiverse_fresh_manifest_v1.py"):
        try:
            ast.parse((AUTO / name).read_text(), filename=name)
        except SyntaxError:
            fail(f"PYTHON_SYNTAX:{name}")
    try:
        schema = json.loads((AUTO / "task_manifest_v1.schema.json").read_text())
    except json.JSONDecodeError:
        fail("SCHEMA_JSON")
    retry = schema["properties"]["retry_count"]
    if retry.get("maximum") != 3 or retry.get("minimum") != 0:
        fail("SCHEMA_RETRY_BOUND")
    if schema["properties"]["target_head"].get("pattern") != "^[0-9a-f]{40}$":
        fail("SCHEMA_HEAD_PATTERN")

    router = (AUTO / "multiverse_task_router_v1.py").read_text()
    need(router, (
        'MAX_REMEDIATION_RETRIES = 3',
        '"FAILED_CLOSED"',
        '"OWNER_GATE"',
        '"LAB_PASS"',
        '"AUDITOR_PASS"',
        'VERDICT_FIELD_COUNT',
        'REVIEWED_HEAD_MISMATCH',
        'owner_free_remediation_allowed',
    ), "ROUTER_INVARIANT")
    for forbidden in ("urllib.request", "requests.", "http.client", "subprocess.", "api.github.com"):
        if forbidden in router:
            fail(f"ROUTER_NETWORK_SURFACE:{forbidden}")

    fresh = (AUTO / "multiverse_fresh_manifest_v1.py").read_text()
    need(fresh, (
        'parsed.hostname == "api.github.com"',
        'method="GET"',
        '"TARGET_HEAD_DRIFT"',
        '"git/ref/heads/main"',
        '"pulls/{pr_number}"',
        '"issues/comments/{comment_id}"',
        'body_sha256',
    ), "FRESH_READ_INVARIANT")
    for forbidden in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"', 'Authorization'):
        if forbidden in fresh:
            fail(f"FRESH_READ_WRITE_OR_CREDENTIAL_SURFACE:{forbidden}")

    p = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(AUTO), "-p", "test_multiverse_*_v1.py", "-v"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    if p.returncode != 0:
        fail(f"UNIT_TESTS:rc={p.returncode}")
    print("MULTIVERSE_AUTOMATION_MECHANICAL_GATE_PASS")
    print("OWNER_TOUCH_AUTHORITY_GRANTED=false")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("RUNTIME=OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
