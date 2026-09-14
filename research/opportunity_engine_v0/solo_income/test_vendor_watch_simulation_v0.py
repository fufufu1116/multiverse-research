#!/usr/bin/env python3
"""Offline end-to-end semantic test for vendor drift watch cases.

Research-only. No network, provider call, publication, monetization or Runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

from materiality_diff_engine_v1 import classify

HERE = Path(__file__).resolve().parent
CASES = HERE / "vendor_watch_simulation_cases_v0.json"


def main() -> None:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    passed = 0

    for case in data["cases"]:
        result = classify(case["before"], case["after"])
        assert result["status"] == case["expected_status"], (
            case["id"], result["status"], case["expected_status"]
        )
        assert any(
            change["category"] == case["expected_category"]
            for change in result["changes"]
        ), (case["id"], case["expected_category"], result["changes"])
        passed += 1
        print(case["id"], "->", result["status"])

    print(f"VENDOR_WATCH_SIMULATION_PASS_{passed}_OF_{len(data['cases'])}")


if __name__ == "__main__":
    main()
