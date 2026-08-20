#!/usr/bin/env python3
"""Generate a compact Owner Assurance view from derived governance state.

Candidate only. The generated view is never a second canonical authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


class AssuranceError(RuntimeError):
    pass


def _load(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssuranceError(f"MISSING_INPUT:{path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError(f"UNREADABLE_OR_MALFORMED_INPUT:{path}") from exc
    if not isinstance(value, dict):
        raise AssuranceError(f"MALFORMED_ROOT:{path}")
    return value


def _classifications(item: Dict[str, Any]) -> set[str]:
    value = item.get("classification", [])
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise AssuranceError("MALFORMED_LIFECYCLE_CLASSIFICATION")
    return set(value)


def _find_pr(items: Iterable[Dict[str, Any]], pr: int) -> Dict[str, Any]:
    found = [x for x in items if x.get("pr") == pr]
    if len(found) != 1:
        raise AssuranceError(f"PR_{pr}_COUNT_{len(found)}")
    return found[0]


def build_view(lifecycle: Dict[str, Any], operational: Dict[str, Any], safe_mode: Dict[str, Any]) -> str:
    if lifecycle.get("registry_is_authoritative") is not False:
        raise AssuranceError("LIFECYCLE_REGISTRY_MUST_REMAIN_NONAUTHORITATIVE")
    if safe_mode.get("canonical_authority") is not False:
        raise AssuranceError("SAFE_MODE_CANDIDATE_MUST_REMAIN_NONCANONICAL")

    main_a = lifecycle.get("canonical_main_observed")
    main_b = operational.get("canonical_main_observed")
    if not isinstance(main_a, str) or main_a != main_b:
        raise AssuranceError("CANONICAL_MAIN_OBSERVATION_MISMATCH")

    op = operational.get("operational_state")
    sm = safe_mode.get("safe_mode")
    if not isinstance(op, dict) or not isinstance(sm, dict):
        raise AssuranceError("MISSING_OPERATIONAL_OR_SAFE_MODE_STATE")
    if not isinstance(sm.get("active"), bool):
        raise AssuranceError("MALFORMED_SAFE_MODE_ACTIVE")

    paused = op.get("keirin_research") == "PAUSED_FOR_MULTIVERSE_ZERO_BASE_FOUNDATION_AUDIT"
    if sm.get("active") != paused:
        raise AssuranceError("PAUSE_STATE_MISMATCH")
    if paused and op.get("new_scientific_execution_allowed") is not False:
        raise AssuranceError("PAUSE_WITH_SCIENTIFIC_EXECUTION_ALLOWED")

    items = lifecycle.get("open_items")
    if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
        raise AssuranceError("MALFORMED_OPEN_ITEMS")

    pr14 = _find_pr(items, 14)
    pr15 = _find_pr(items, 15)
    pr16 = _find_pr(items, 16)
    if "LAB_PASS" not in _classifications(pr14):
        raise AssuranceError("PR14_NOT_LAB_PASS_IN_REGISTRY")
    if "PAUSED" not in _classifications(pr15) or "QUARANTINED" not in _classifications(pr15):
        raise AssuranceError("PR15_PAUSE_QUARANTINE_MISSING")
    if "ACTIVE" not in _classifications(pr16):
        raise AssuranceError("PR16_NOT_ACTIVE_FOUNDATION_AUDIT")

    f1 = lifecycle.get("global_scientific_firewall")
    f2 = operational.get("scientific_firewall_preserved")
    if not isinstance(f1, dict) or not isinstance(f2, dict):
        raise AssuranceError("MISSING_FIREWALL_STATE")
    field_map = {
        "ECON_HOLDOUT1000": ("ECON_HOLDOUT1000", "SEALED", "SEALED"),
        "RESULT_PAYOUT": ("RESULT_PAYOUT", "UNAUTHORIZED", "UNAUTHORIZED"),
        "UNTOUCHED_VALIDATION": ("new_untouched_validation_opened", "CLOSED", False),
        "MODEL_PROMOTION": ("model_promotion", "PROHIBITED", "PROHIBITED"),
        "REAL_MONEY_WAGERING": ("real_money_wagering", "OUT_OF_SCOPE", "OUT_OF_SCOPE"),
    }
    for lifecycle_key, (operational_key, expected_left, expected_right) in field_map.items():
        left = f1.get(lifecycle_key)
        right = f2.get(operational_key)
        if left != expected_left or right != expected_right:
            raise AssuranceError(f"FIREWALL_MISMATCH:{lifecycle_key}:{left}:{right}")

    pending_review = []
    expired = []
    acceptance_pending = []
    for item in items:
        classes = _classifications(item)
        if "UNREVIEWED" in classes:
            pending_review.append(item.get("pr"))
        if "EXPIRED_CANDIDATE" in classes:
            expired.append(item.get("pr"))
        if "ACCEPTANCE_PENDING" in classes:
            acceptance_pending.append(item.get("pr"))

    state_word = "PAUSED（科学実験停止中）" if paused else "ACTIVE（実行可否は別Gate確認）"
    owner_action = op.get("owner_action_now", "UNKNOWN")
    if owner_action != "NONE":
        owner_line = f"要確認: {owner_action}"
    else:
        owner_line = "なし"

    lines = [
        "# Multiverse — Owner Assurance（主向け安心表示）",
        "",
        "> Generated view candidate. 正本ではなく、下記state/registryから作る表示。",
        "",
        f"- **競輪研究:** {state_word}",
        "- **今進める場所:** PR #16 Foundation Audit（全体監査）",
        "- **最後に完了した科学Checkpoint:** PR #14 / Lab PASS / Synthetic engineering only（仮想世界の開発証拠のみ）",
        "- **停止中の子作業:** PR #15 / QUARANTINED（隔離） / metricsは再開経路選択に使わない",
        f"- **未レビューPR:** {pending_review or 'なし'}",
        f"- **期限切れ候補PR:** {expired or 'なし'}",
        f"- **Lab PASS後の受理待ちPR:** {acceptance_pending or 'なし'}",
        "- **ECON_HOLDOUT1000:** SEALED（封印）",
        "- **RESULT/PAYOUT:** UNAUTHORIZED（未許可）",
        "- **Untouched Validation:** CLOSED（未開封）",
        "- **Model Promotion:** PROHIBITED（昇格禁止）",
        f"- **主が今やること:** {owner_line}",
        "",
        f"Evidence main observed: `{main_a}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Owner Assurance view candidate")
    parser.add_argument("--lifecycle", required=True)
    parser.add_argument("--operational", required=True)
    parser.add_argument("--safe-mode", required=True)
    args = parser.parse_args()
    try:
        text = build_view(_load(Path(args.lifecycle)), _load(Path(args.operational)), _load(Path(args.safe_mode)))
    except AssuranceError as exc:
        print(f"OWNER_ASSURANCE_FAIL_CLOSED:{exc}")
        return 42
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
