#!/usr/bin/env python3
"""Selftest for workflow pause coverage audit candidate."""

from __future__ import annotations

import tempfile
from pathlib import Path

from multiverse_workflow_pause_coverage_audit_v1 import inventory


def write(root: Path, name: str, text: str) -> None:
    path = root / ".github" / "workflows" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write(root, "keirin-stress.yml", "on:\n  push:\njobs:\n  run:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo simulate\n")
        write(root, "dev2000-scoring.yml", "on:\n  workflow_dispatch:\njobs:\n  score:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo score\n")
        write(root, "all-market-safe.yml", "on:\n  push:\njobs:\n  run:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python tools/multiverse_pause_guard_v1.py\n")
        write(root, "multiverse-foundation-candidate-ci-v1.yml", "on:\n  pull_request:\njobs:\n  audit:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo audit\n")
        write(root, "mystery.yml", "on:\n  schedule:\n    - cron: '0 0 * * *'\njobs:\n  mystery:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hello\n")

        result = inventory(root, root / ".github" / "workflows")
        by_name = {Path(e["path"]).name: e for e in result["entries"]}
        assert by_name["keirin-stress.yml"]["classification"] == "SCIENTIFIC_CANDIDATE"
        assert by_name["dev2000-scoring.yml"]["classification"] == "SCIENTIFIC_CANDIDATE"
        assert by_name["all-market-safe.yml"]["classification"] == "SCIENTIFIC_CANDIDATE"
        assert by_name["all-market-safe.yml"]["pause_guard_present"] is True
        assert by_name["multiverse-foundation-candidate-ci-v1.yml"]["classification"] == "AUDIT_OR_GOVERNANCE_ONLY"
        assert by_name["mystery.yml"]["classification"] == "UNKNOWN_REVIEW_REQUIRED"
        assert result["counts"]["scientific_candidate"] == 3
        assert result["counts"]["scientific_candidate_with_guard"] == 1
        assert result["counts"]["scientific_candidate_without_guard"] == 2
        assert result["counts"]["unknown_review_required"] == 1
        assert "mystery.yml" in {Path(x).name for x in result["unknown_review_required"]}

    print("MULTIVERSE_WORKFLOW_PAUSE_COVERAGE_AUDIT_SELFTEST_PASS")


if __name__ == "__main__":
    main()
