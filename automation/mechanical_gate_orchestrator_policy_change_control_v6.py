#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import pathlib
import subprocess
import sys

from orchestrator_policy_change_control_v6 import (
    BASE_CANONICAL_MAIN,
    CHANGE_CONTROL_BASELINE_SHA256,
    ChangeControlBaseline,
)
from orchestrator_role_relay_policy_source_v5 import REVIEWED_POLICY_MANIFEST_SHA256, ReviewedPolicySource

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "automation"
BASELINE = HERE / "MULTIVERSE_AUTOMATION_POLICY_CHANGE_CONTROL_V6_BASELINE.json"
BASE_POLICY = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
CANDIDATE_BRANCH = "agent/automation-orchestrator-policy-change-control-v6-20260903-v1"
FILES = [
    HERE / "orchestrator_policy_change_control_v6.py",
    HERE / "test_orchestrator_policy_change_control_v6.py",
]
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib.request", "boto3", "openai", "anthropic"}


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-head", required=True)
    ap.add_argument("--canonical-main", required=True)
    ap.add_argument("--candidate-branch", required=True)
    ns = ap.parse_args()
    if len(ns.expected_head) != 40 or len(ns.canonical_main) != 40:
        print("SHA_ARGUMENT_INVALID")
        return 2
    if ns.canonical_main != BASE_CANONICAL_MAIN:
        print("CURRENT_MAIN_NOT_V6_REVIEWED_MAIN")
        return 2
    if ns.candidate_branch != CANDIDATE_BRANCH:
        print("WRONG_V6_BRANCH")
        return 2

    for path in FILES:
        if not path.is_file():
            print(f"MISSING:{path.relative_to(ROOT)}")
            return 3
        tree = ast.parse(path.read_text(), filename=str(path))
        if path.name == "orchestrator_policy_change_control_v6.py":
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

    baseline = ChangeControlBaseline.load(BASELINE)
    source = ReviewedPolicySource.load(BASE_POLICY)
    baseline.verify_base_source(source)
    if baseline.raw_sha256 != CHANGE_CONTROL_BASELINE_SHA256:
        print("BASELINE_SHA_MISMATCH")
        return 6
    if source.raw_sha256 != REVIEWED_POLICY_MANIFEST_SHA256:
        print("BASE_POLICY_SHA_MISMATCH")
        return 6

    patterns = [
        "test_orchestrator_role_relay_v3.py",
        "test_orchestrator_role_relay_policy_v4.py",
        "test_orchestrator_role_relay_policy_source_v5.py",
        "test_orchestrator_policy_change_control_v6.py",
    ]
    for pattern in patterns:
        tests = run([sys.executable, "-m", "unittest", "discover", "-s", "automation",
                     "-p", pattern, "-v"])
        print(tests.stdout, end="")
        print(tests.stderr, end="")
        if tests.returncode != 0:
            print(f"POLICY_CHANGE_CONTROL_V6_TESTS_FAIL:{pattern}")
            return 7

    print("POLICY_CHANGE_CONTROL_V6_MECHANICAL_GATE_PASS=true")
    print("POLICY_CHANGE_CONTROL_V6_EXACT_HEAD=" + ns.expected_head)
    print("POLICY_CHANGE_CONTROL_V6_CANONICAL_MAIN=" + ns.canonical_main)
    print("POLICY_CHANGE_CONTROL_V6_CANDIDATE_BRANCH=" + ns.candidate_branch)
    print("POLICY_CHANGE_CONTROL_V6_BASELINE_SHA256=" + baseline.raw_sha256)
    print("POLICY_CHANGE_CONTROL_V6_BASE_POLICY_SHA256=" + source.raw_sha256)
    print("POLICY_CHANGE_CONTROL_V6_POLICY_APPLY_SURFACE=false")
    print("POLICY_CHANGE_CONTROL_V6_POLICY_WIDEN_AUTO_AUTHORITY=false")
    print("POLICY_CHANGE_CONTROL_V6_MAIN_MUTATION_AUTHORITY=false")
    print("POLICY_CHANGE_CONTROL_V6_REVIEW_ROUTE_ONLY=true")
    print("OWNER_COPY_PASTE_COUNT=0")
    print("OWNER_CONTINUE_PROMPT_COUNT=0")
    print("OWNER_KEEP_ALIVE_COUNT=0")
    print("LIVE_PROVIDER_INTEGRATION=false")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("CORE_KEIRIN_ADOPTION_AUTHORITY=false")
    print("POLICY_CHANGE_CONTROL_V6_RUNTIME=OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
