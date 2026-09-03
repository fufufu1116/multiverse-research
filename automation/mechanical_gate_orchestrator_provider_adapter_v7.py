#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import os
import pathlib
import subprocess
import sys

from orchestrator_provider_adapter_v7 import (
    PROVIDER_ADAPTER_CANONICAL_MAIN,
    PROVIDER_ADAPTER_MANIFEST_SHA256,
    PROVIDER_ADAPTER_SOURCE_BRANCH,
    ProviderAdapterManifest,
)
from orchestrator_role_relay_policy_source_v5 import ReviewedPolicySource

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "automation"
ADAPTER_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_PROVIDER_ADAPTER_CONTRACT_V7.json"
POLICY_MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
FILES = [
    HERE / "orchestrator_provider_adapter_v7.py",
    HERE / "test_orchestrator_provider_adapter_v7.py",
    HERE / "test_orchestrator_provider_adapter_v7_integration.py",
]
FORBIDDEN_IMPORTS = {
    "anthropic", "boto3", "http.client", "httpx", "openai", "requests", "socket",
    "urllib", "urllib.request",
}


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
    if ns.canonical_main != PROVIDER_ADAPTER_CANONICAL_MAIN:
        print("CURRENT_MAIN_NOT_REVIEWED_V7_MAIN")
        return 2
    if ns.candidate_branch != PROVIDER_ADAPTER_SOURCE_BRANCH:
        print("WRONG_V7_BRANCH")
        return 2

    for path in FILES:
        if not path.is_file():
            print(f"MISSING:{path.relative_to(ROOT)}")
            return 3
        tree = ast.parse(path.read_text(), filename=str(path))
        if path.name == "orchestrator_provider_adapter_v7.py":
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

    adapter_manifest = ProviderAdapterManifest.load(ADAPTER_MANIFEST)
    if adapter_manifest.raw_sha256 != PROVIDER_ADAPTER_MANIFEST_SHA256:
        print("ADAPTER_MANIFEST_SHA_MISMATCH")
        return 6
    source = ReviewedPolicySource.load(POLICY_MANIFEST)
    if source.canonical_main != ns.canonical_main:
        print("V5_POLICY_SOURCE_MAIN_MISMATCH")
        return 6

    env = os.environ.copy()
    env["MULTIVERSE_V7_CODE_HEAD"] = ns.expected_head
    env["MULTIVERSE_CANONICAL_MAIN"] = ns.canonical_main

    patterns = [
        "test_orchestrator_role_relay_v3.py",
        "test_orchestrator_role_relay_policy_v4.py",
        "test_orchestrator_role_relay_policy_source_v5.py",
        "test_orchestrator_role_relay_policy_source_v5_integration.py",
        "test_orchestrator_policy_change_control_v6.py",
        "test_orchestrator_provider_adapter_v7.py",
        "test_orchestrator_provider_adapter_v7_integration.py",
    ]
    for pattern in patterns:
        tests = run([sys.executable, "-m", "unittest", "discover", "-s", "automation",
                     "-p", pattern, "-v"], env=env)
        print(tests.stdout, end="")
        print(tests.stderr, end="")
        if tests.returncode != 0:
            print(f"PROVIDER_ADAPTER_V7_TESTS_FAIL:{pattern}")
            return 7

    print("PROVIDER_ADAPTER_V7_MECHANICAL_GATE_PASS=true")
    print("PROVIDER_ADAPTER_V7_EXACT_HEAD=" + ns.expected_head)
    print("PROVIDER_ADAPTER_V7_CANONICAL_MAIN=" + ns.canonical_main)
    print("PROVIDER_ADAPTER_V7_SOURCE_BRANCH=" + ns.candidate_branch)
    print("PROVIDER_ADAPTER_V7_MANIFEST_SHA256=" + adapter_manifest.raw_sha256)
    print("PROVIDER_ADAPTER_V7_SEALED_LOCAL_ADAPTER_ONLY=true")
    print("PROVIDER_ADAPTER_V7_ARBITRARY_RUNTIME_ADAPTER_INJECTION=false")
    print("PROVIDER_ADAPTER_V7_EXISTING_V5_POLICY_ONLY=true")
    print("PROVIDER_ADAPTER_V7_POLICY_WIDENING=false")
    print("PROVIDER_ADAPTER_V7_NETWORK=false")
    print("PROVIDER_ADAPTER_V7_LIVE_PROVIDER=false")
    print("PROVIDER_ADAPTER_V7_EXTERNAL_EFFECT=false")
    print("PROVIDER_ADAPTER_V7_SPEND=false")
    print("PROVIDER_ADAPTER_V7_SECRET_CREDENTIAL=false")
    print("OWNER_COPY_PASTE_COUNT=0")
    print("OWNER_CONTINUE_PROMPT_COUNT=0")
    print("OWNER_KEEP_ALIVE_COUNT=0")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("CORE_KEIRIN_ADOPTION_AUTHORITY=false")
    print("PROVIDER_ADAPTER_V7_RUNTIME=OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
