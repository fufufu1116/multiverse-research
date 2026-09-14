#!/usr/bin/env python3
"""Fixture runner for materiality_diff_engine_v1.py. Research-only, local/offline."""
from __future__ import annotations

import json
from pathlib import Path

from materiality_diff_engine_v1 import classify

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "materiality_diff_fixtures_v1.json"


def main() -> None:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    base = data["base"]
    passed = 0

    for case in data["cases"]:
        after = dict(base)
        after.update(case.get("patch", {}))
        result = classify(base, after)

        assert result["status"] == case["expected_status"], (
            case["id"], result["status"], case["expected_status"]
        )
        assert result["human_review_required"] is case["expected_human_review"], (
            case["id"], result["human_review_required"], case["expected_human_review"]
        )

        expected_category = case.get("expected_category")
        if expected_category:
            assert any(c["category"] == expected_category for c in result["changes"]), (
                case["id"], expected_category, result["changes"]
            )
        passed += 1

    print(f"FIXTURE_TEST_PASS_{passed}_OF_{len(data['cases'])}")


if __name__ == "__main__":
    main()
