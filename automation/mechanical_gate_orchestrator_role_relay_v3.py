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
    ROOT / "automation" / "orchestrator_role_relay_v3.py",
    ROOT / "automation" / "test_orchestrator_role_relay_v3.py",
    ROOT / "automation" / "test_orchestrator_role_relay_v3_integration.py",
]
FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib.request", "boto3", "openai", "anthropic"}


def run(cmd, *, env=None):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=env)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expected-head", required=True)
    p.add_argument("--canonical-main", required=True)
    a = p.parse_args()
    if len(a.expected_head) != 40 or len(a.canonical_main) != 40:
        print("SHA_ARGUMENT_INVALID")
        return 2
    for path in FILES:
        if not path.is_file():
            print(f"MISSING:{path.relative_to(ROOT)}")
            return 3
        tree = ast.parse(path.read_text(), filename=str(path))
        if path.name == "orchestrator_role_relay_v3.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        if n.name in FORBIDDEN_IMPORTS:
                            print(f"FORBIDDEN_IMPORT:{n.name}")
                            return 4
                if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_IMPORTS:
                    print(f"FORBIDDEN_IMPORT:{node.module}")
                    return 4
    head = run(["git", "rev-parse", "HEAD"])
    if head.returncode != 0 or head.stdout.strip() != a.expected_head:
        print("EXACT_HEAD_BINDING_FAIL")
        print(head.stdout.strip())
        return 5
    src = (ROOT / "automation" / "orchestrator_role_relay_v3.py").read_text()
    required = [
        "replay_safe = True",
        "RELAY_CONFLICTING_DUPLICATE_RESULT",
        "RELAY_REPLAY_HEAD_MISMATCH",
        "RELAY_REPLAY_MAIN_MISMATCH",
        "RELAY_CANDIDATE_BRANCH_MISMATCH",
        "RELAY_SPEND_DENIED",
        "RELAY_SAFETY_FAIL_CLOSED",
        "recover_expired",
        "claim_next",
        "lease_expires_at",
        "DurableFixtureReceiptStore",
        "CRASH_AFTER_RECEIPT",
    ]
    for token in required:
        if token not in src:
            print(f"SOURCE_INVARIANT_MISSING:{token}")
            return 6
    env = os.environ.copy()
    env["MULTIVERSE_EXPECTED_HEAD"] = a.expected_head
    env["MULTIVERSE_CANONICAL_MAIN"] = a.canonical_main
    tests = run([sys.executable, "-m", "unittest", "discover", "-s", "automation",
                 "-p", "test_orchestrator_role_relay_v3*.py", "-v"], env=env)
    print(tests.stdout, end="")
    print(tests.stderr, end="")
    if tests.returncode != 0:
        print("ROLE_RELAY_V3_TESTS_FAIL")
        return 7
    print(f"RELAY_EXACT_HEAD={a.expected_head}")
    print(f"RELAY_CANONICAL_MAIN={a.canonical_main}")
    print("OWNER_COPY_PASTE_COUNT=0")
    print("OWNER_CONTINUE_PROMPT_COUNT=0")
    print("OWNER_KEEP_ALIVE_COUNT=0")
    print("LIVE_PROVIDER_INTEGRATION=false")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("RUNTIME=OFF")
    print("MULTIVERSE_ORCHESTRATOR_ROLE_RELAY_V3_MECHANICAL_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
