#!/usr/bin/env python3
"""Selftest for Owner Assurance v2 current-focus truthfulness."""

from __future__ import annotations

import copy

from multiverse_owner_assurance_view_v1 import AssuranceError
from multiverse_owner_assurance_view_selftest_v1 import LIFECYCLE, OPERATIONAL, SAFE_MODE
from multiverse_owner_assurance_view_v2 import build_view


def must_fail(lifecycle: dict, operational: dict, safe_mode: dict, label: str) -> None:
    try:
        build_view(lifecycle, operational, safe_mode)
    except AssuranceError:
        return
    raise AssertionError(f"expected fail-closed: {label}")


def fixtures() -> tuple[dict, dict, dict]:
    lifecycle = copy.deepcopy(LIFECYCLE)
    lifecycle["open_items"].append({
        "pr": 22,
        "title": "Foundation Lab remediation candidate v1",
        "classification": ["ACTIVE", "NONCANONICAL"],
    })
    operational = copy.deepcopy(OPERATIONAL)
    operational["operational_state"]["active_foundation_remediation_pr"] = 22
    return lifecycle, operational, copy.deepcopy(SAFE_MODE)


def main() -> None:
    lifecycle, operational, safe_mode = fixtures()
    text = build_view(lifecycle, operational, safe_mode)
    assert "今進める場所:** PR #22 Foundation Lab remediation candidate v1" in text
    assert "今進める場所:** PR #16 Foundation Audit（全体監査）" not in text
    assert "PAUSED（科学実験停止中）" in text
    assert "ECON_HOLDOUT1000:** SEALED" in text
    assert "RESULT/PAYOUT:** UNAUTHORIZED" in text

    bad = copy.deepcopy(operational)
    bad["operational_state"].pop("active_foundation_remediation_pr")
    must_fail(lifecycle, bad, safe_mode, "active pointer missing")

    bad = copy.deepcopy(operational)
    bad["operational_state"]["active_foundation_remediation_pr"] = 999
    must_fail(lifecycle, bad, safe_mode, "active pointer target missing")

    bad_lifecycle = copy.deepcopy(lifecycle)
    for item in bad_lifecycle["open_items"]:
        if item.get("pr") == 22:
            item["classification"] = ["NONCANONICAL"]
    must_fail(bad_lifecycle, operational, safe_mode, "pointer target not ACTIVE")

    bad_lifecycle = copy.deepcopy(lifecycle)
    for item in bad_lifecycle["open_items"]:
        if item.get("pr") == 22:
            item["title"] = ""
    must_fail(bad_lifecycle, operational, safe_mode, "pointer target title missing")

    print("MULTIVERSE_OWNER_ASSURANCE_VIEW_V2_SELFTEST_PASS")
    print("OWNER_FOCUS_PR=22")
    print("SCIENTIFIC_EXECUTION_PERFORMED=false")
    print("SCIENTIFIC_RESUME_ALLOWED=false")


if __name__ == "__main__":
    main()
