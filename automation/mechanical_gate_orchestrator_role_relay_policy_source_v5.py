#!/usr/bin/env python3
import argparse
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

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST = HERE / "MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"


def run(*args):
    subprocess.run([sys.executable, "-m", "unittest", *args], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-head", required=True)
    ap.add_argument("--canonical-main", required=True)
    ap.add_argument("--candidate-branch", required=True)
    ns = ap.parse_args()
    if len(ns.expected_head) != 40:
        raise SystemExit("BAD_EXPECTED_HEAD")
    if ns.canonical_main != REVIEWED_POLICY_SOURCE_CANONICAL_MAIN:
        raise SystemExit("CURRENT_MAIN_NOT_REVIEWED_SOURCE_MAIN")
    if ns.candidate_branch != REVIEWED_POLICY_SOURCE_BRANCH:
        raise SystemExit("WRONG_V5_BRANCH")
    source = ReviewedPolicySource.load(MANIFEST)
    if source.raw_sha256 != REVIEWED_POLICY_MANIFEST_SHA256:
        raise SystemExit("SOURCE_SHA_MISMATCH")
    os.environ["MULTIVERSE_EXPECTED_HEAD"] = ns.expected_head
    os.environ["MULTIVERSE_CANONICAL_MAIN"] = ns.canonical_main
    os.environ["MULTIVERSE_V5_CANDIDATE_BRANCH"] = ns.candidate_branch
    run("automation.test_orchestrator_role_relay_v3",
        "automation.test_orchestrator_role_relay_policy_v4",
        "automation.test_orchestrator_role_relay_policy_source_v5")
    run("automation.test_orchestrator_role_relay_policy_source_v5_integration")
    print("POLICY_SOURCE_V5_MECHANICAL_GATE_PASS=true")
    print("POLICY_SOURCE_V5_EXACT_HEAD=" + ns.expected_head)
    print("POLICY_SOURCE_V5_CANONICAL_MAIN=" + ns.canonical_main)
    print("POLICY_SOURCE_V5_CANDIDATE_BRANCH=" + ns.candidate_branch)
    print("POLICY_SOURCE_V5_MANIFEST_SHA256=" + source.raw_sha256)
    print("POLICY_SOURCE_V5_COMPILED_SOURCE_IDENTITY=true")
    print("POLICY_SOURCE_V5_TASK_POLICY_SELECTION=false")
    print("POLICY_SOURCE_V5_V4_DB_BYPASS_DENIED=true")
    print("POLICY_SOURCE_V5_RUNTIME=OFF")


if __name__ == "__main__":
    main()
