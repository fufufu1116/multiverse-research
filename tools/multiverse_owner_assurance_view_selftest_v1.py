#!/usr/bin/env python3
"""Selftest for Owner Assurance view generator candidate."""

from __future__ import annotations

import copy

from multiverse_owner_assurance_view_v1 import AssuranceError, build_view


LIFECYCLE = {
    "registry_is_authoritative": False,
    "canonical_main_observed": "819afb723c8f14000757b2e53b6664d71ab01227",
    "open_items": [
        {"pr": 11, "classification": ["UNREVIEWED", "EXPIRED_CANDIDATE"]},
        {"pr": 12, "classification": ["LAB_PASS", "ACCEPTANCE_PENDING", "PAUSED"]},
        {"pr": 14, "classification": ["LAB_PASS", "PAUSED"]},
        {"pr": 15, "classification": ["PAUSED", "QUARANTINED"]},
        {"pr": 16, "classification": ["ACTIVE", "FOUNDATION_AUDIT"]}
    ],
    "global_scientific_firewall": {
        "ECON_HOLDOUT1000": "SEALED",
        "RESULT_PAYOUT": "UNAUTHORIZED",
        "UNTOUCHED_VALIDATION": "CLOSED",
        "MODEL_PROMOTION": "PROHIBITED",
        "REAL_MONEY_WAGERING": "OUT_OF_SCOPE"
    }
}

OPERATIONAL = {
    "canonical_main_observed": "819afb723c8f14000757b2e53b6664d71ab01227",
    "operational_state": {
        "keirin_research": "PAUSED_FOR_MULTIVERSE_ZERO_BASE_FOUNDATION_AUDIT",
        "new_scientific_execution_allowed": False,
        "owner_action_now": "NONE"
    },
    "scientific_firewall_preserved": {
        "ECON_HOLDOUT1000": "SEALED",
        "RESULT_PAYOUT": "UNAUTHORIZED",
        "new_untouched_validation_opened": False,
        "model_promotion": "PROHIBITED",
        "real_money_wagering": "OUT_OF_SCOPE"
    }
}

SAFE_MODE = {
    "canonical_authority": False,
    "safe_mode": {
        "active": True,
        "scope": ["KEIRIN_SCIENTIFIC_EXECUTION"]
    }
}


def must_fail(lifecycle: dict, operational: dict, safe_mode: dict, label: str) -> None:
    try:
        build_view(lifecycle, operational, safe_mode)
    except AssuranceError:
        return
    raise AssertionError(f"expected fail-closed: {label}")


def main() -> None:
    text = build_view(LIFECYCLE, OPERATIONAL, SAFE_MODE)
    assert "PAUSED（科学実験停止中）" in text
    assert "PR #14 / Lab PASS" in text
    assert "PR #15 / QUARANTINED" in text
    assert "未レビューPR:** [11]" in text
    assert "期限切れ候補PR:** [11]" in text
    assert "Lab PASS後の受理待ちPR:** [12]" in text
    assert "主が今やること:** なし" in text

    bad = copy.deepcopy(LIFECYCLE)
    bad["registry_is_authoritative"] = True
    must_fail(bad, OPERATIONAL, SAFE_MODE, "registry became authoritative")

    bad_op = copy.deepcopy(OPERATIONAL)
    bad_op["canonical_main_observed"] = "0" * 40
    must_fail(LIFECYCLE, bad_op, SAFE_MODE, "main observation mismatch")

    bad_safe = copy.deepcopy(SAFE_MODE)
    bad_safe["safe_mode"]["active"] = False
    must_fail(LIFECYCLE, OPERATIONAL, bad_safe, "pause state mismatch")

    bad_op2 = copy.deepcopy(OPERATIONAL)
    bad_op2["operational_state"]["new_scientific_execution_allowed"] = True
    must_fail(LIFECYCLE, bad_op2, SAFE_MODE, "pause with science allowed")

    bad_lifecycle = copy.deepcopy(LIFECYCLE)
    for item in bad_lifecycle["open_items"]:
        if item["pr"] == 15:
            item["classification"] = ["PAUSED"]
    must_fail(bad_lifecycle, OPERATIONAL, SAFE_MODE, "quarantine marker missing")

    bad_fw = copy.deepcopy(OPERATIONAL)
    bad_fw["scientific_firewall_preserved"]["RESULT_PAYOUT"] = "AUTHORIZED"
    must_fail(LIFECYCLE, bad_fw, SAFE_MODE, "firewall mismatch")

    print("MULTIVERSE_OWNER_ASSURANCE_VIEW_SELFTEST_PASS")


if __name__ == "__main__":
    main()
