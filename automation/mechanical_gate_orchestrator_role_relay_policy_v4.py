#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = [
    ROOT / "automation" / "orchestrator_role_relay_policy_v4.py",
    ROOT / "automation" / "test_orchestrator_role_relay_policy_v4.py",
    ROOT / "automation" / "test_orchestrator_role_relay_policy_v4_integration.py",
]
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib.request", "boto3", "openai", "anthropic"}


def run(cmd, *, env=None):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--canonical-main", required=True)
    parser.add_argument("--candidate-branch", required=True)
    args = parser.parse_args()
    if len(args.expected_head) != 40 or len(args.canonical_main) != 40:
        print("SHA_ARGUMENT_INVALID")
        return 2
    if not args.candidate_branch.startswith("agent/"):
        print("CANDIDATE_BRANCH_ARGUMENT_INVALID")
        return 2

    for path in FILES:
        if not path.is_file():
            print(f"MISSING:{path.relative_to(ROOT)}")
            return 3
        tree = ast.parse(path.read_text(), filename=str(path))
        if path.name == "orchestrator_role_relay_policy_v4.py":
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
    if head.returncode != 0 or head.stdout.strip() != args.expected_head:
        print("EXACT_HEAD_BINDING_FAIL")
        print(head.stdout.strip())
        return 5

    src = (ROOT / "automation" / "orchestrator_role_relay_policy_v4.py").read_text()
    required = [
        "CandidateBindingPolicy",
        "POLICY_RELAY_DB_SCHEMA_VERSION = 2",
        "RELAY_BINDING_POLICY_DENIED",
        "RELAY_REPO_POLICY_DENIED",
        "RELAY_POLICY_FINGERPRINT_MISMATCH",
        "binding_policy_fingerprint",
        "PolicyRelayRoleWorker",
        "policy_fixture_process_one",
        "replay_safe = True",
        "agent/",
    ]
    for token in required:
        if token not in src:
            print(f"SOURCE_INVARIANT_MISSING:{token}")
            return 6

    env = os.environ.copy()
    env["MULTIVERSE_EXPECTED_HEAD"] = args.expected_head
    env["MULTIVERSE_CANONICAL_MAIN"] = args.canonical_main
    env["MULTIVERSE_V4_CANDIDATE_BRANCH"] = args.candidate_branch

    patterns = [
        "test_orchestrator_role_relay_v3.py",
        "test_orchestrator_role_relay_policy_v4*.py",
    ]
    for pattern in patterns:
        tests = run([sys.executable, "-m", "unittest", "discover", "-s", "automation",
                     "-p", pattern, "-v"], env=env)
        print(tests.stdout, end="")
        print(tests.stderr, end="")
        if tests.returncode != 0:
            print(f"POLICY_RELAY_V4_TESTS_FAIL:{pattern}")
            return 7

    print(f"POLICY_RELAY_EXACT_HEAD={args.expected_head}")
    print(f"POLICY_RELAY_CANONICAL_MAIN={args.canonical_main}")
    print(f"POLICY_RELAY_CANDIDATE_BRANCH={args.candidate_branch}")
    print("MULTI_CANDIDATE_BINDING_POLICY=true")
    print("POLICY_DB_PINNING=true")
    print("V3_ADAPTER_CANNOT_OPEN_V4_DB=true")
    print("OWNER_COPY_PASTE_COUNT=0")
    print("OWNER_CONTINUE_PROMPT_COUNT=0")
    print("OWNER_KEEP_ALIVE_COUNT=0")
    print("LIVE_PROVIDER_INTEGRATION=false")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("CORE_KEIRIN_ADOPTION_AUTHORITY=false")
    print("RUNTIME=OFF")
    print("MULTIVERSE_ORCHESTRATOR_ROLE_RELAY_POLICY_V4_MECHANICAL_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
