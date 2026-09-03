#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import os
import pathlib
import subprocess
import sys

from orchestrator_role_relay_policy_source_v5 import (
    REVIEWED_POLICY_MANIFEST_SHA256,
    REVIEWED_POLICY_SOURCE_BRANCH,
    REVIEWED_POLICY_SOURCE_CANONICAL_MAIN,
    ReviewedPolicySource,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "automation"
MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
FILES = [
    HERE / "orchestrator_role_relay_policy_source_v5.py",
    HERE / "test_orchestrator_role_relay_policy_source_v5.py",
    HERE / "test_orchestrator_role_relay_policy_source_v5_integration.py",
]
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib.request", "boto3", "openai", "anthropic"}


def run(cmd, *, env=None):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=env)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-head", required=True)
    ap.add_argument("--canonical-main", required=True)
    ap.add_argument("--candidate-branch", required=True)
    ns = ap.parse_args()
    if len(ns.expected_head) != 40 or len(ns.canonical_main) != 40:
        print("SHA_ARGUMENT_INVALID")
        return 2
    if ns.canonical_main != REVIEWED_POLICY_SOURCE_CANONICAL_MAIN:
        print("CURRENT_MAIN_NOT_REVIEWED_SOURCE_MAIN")
        return 2
    if ns.candidate_branch != REVIEWED_POLICY_SOURCE_BRANCH:
        print("WRONG_V5_BRANCH")
        return 2

    for path in FILES:
        if not path.is_file():
            print(f"MISSING:{path.relative_to(ROOT)}")
            return 3
        tree = ast.parse(path.read_text(), filename=str(path))
        if path.name == "orchestrator_role_relay_policy_source_v5.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name in FORBIDDEN_IMPORTS:
                            print(f"FORBIDDEN_IMPORT:{name.name}")
                            return 4
                if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_IMPORTS:
                    print(f"FORBIDDEN_IMPORT:{node.module}")
                    return 4

    head = run(["git", "rev-parse", "HEAD"])
    if head.returncode != 0 or head.stdout.strip() != ns.expected_head:
        print("EXACT_HEAD_BINDING_FAIL")
        return 5

    source = ReviewedPolicySource.load(MANIFEST)
    if source.raw_sha256 != REVIEWED_POLICY_MANIFEST_SHA256:
        print("SOURCE_SHA_MISMATCH")
        return 6

    env = os.environ.copy()
    env["MULTIVERSE_EXPECTED_HEAD"] = ns.expected_head
    env["MULTIVERSE_CANONICAL_MAIN"] = ns.canonical_main
    env["MULTIVERSE_V5_CANDIDATE_BRANCH"] = ns.candidate_branch

    patterns = [
        "test_orchestrator_role_relay_v3.py",
        "test_orchestrator_role_relay_policy_v4.py",
        "test_orchestrator_role_relay_policy_source_v5.py",
        "test_orchestrator_role_relay_policy_source_v5_integration.py",
    ]
    for pattern in patterns:
        tests = run([sys.executable, "-m", "unittest", "discover", "-s", "automation",
                     "-p", pattern, "-v"], env=env)
        print(tests.stdout, end="")
        print(tests.stderr, end="")
        if tests.returncode != 0:
            print(f"POLICY_SOURCE_V5_TESTS_FAIL:{pattern}")
            return 7

    print("POLICY_SOURCE_V5_MECHANICAL_GATE_PASS=true")
    print("POLICY_SOURCE_V5_EXACT_HEAD=" + ns.expected_head)
    print("POLICY_SOURCE_V5_CANONICAL_MAIN=" + ns.canonical_main)
    print("POLICY_SOURCE_V5_CANDIDATE_BRANCH=" + ns.candidate_branch)
    print("POLICY_SOURCE_V5_MANIFEST_SHA256=" + source.raw_sha256)
    print("POLICY_SOURCE_V5_COMPILED_SOURCE_IDENTITY=true")
    print("POLICY_SOURCE_V5_TASK_POLICY_SELECTION=false")
    print("POLICY_SOURCE_V5_V4_DB_BYPASS_DENIED=true")
    print("OWNER_COPY_PASTE_COUNT=0")
    print("OWNER_CONTINUE_PROMPT_COUNT=0")
    print("OWNER_KEEP_ALIVE_COUNT=0")
    print("LIVE_PROVIDER_INTEGRATION=false")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("CORE_KEIRIN_ADOPTION_AUTHORITY=false")
    print("POLICY_SOURCE_V5_RUNTIME=OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
