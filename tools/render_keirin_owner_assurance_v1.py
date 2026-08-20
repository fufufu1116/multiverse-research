#!/usr/bin/env python3
"""Render a minimal Owner-facing Keirin assurance view from derived state evidence.

NEXT_VERSION_CANDIDATE only. This renderer does not create canonical truth; it renders
from a state-sync candidate and lifecycle registry so the human-facing view is not a
second manually maintained state database.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict

class AssuranceError(RuntimeError):
    pass

def _load(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError(f"UNREADABLE_OR_MALFORMED:{path}") from exc
    if not isinstance(value, dict):
        raise AssuranceError(f"ROOT_NOT_OBJECT:{path}")
    return value

def render(state: Dict[str, Any], lifecycle: Dict[str, Any]) -> str:
    if state.get("status") != "DRAFT_NONCANONICAL_STATE_SYNC_CANDIDATE":
        raise AssuranceError("STATE_STATUS_NOT_EXPECTED_CANDIDATE")
    if lifecycle.get("status") != "DRAFT_NONCANONICAL_AUDIT_EVIDENCE":
        raise AssuranceError("LIFECYCLE_STATUS_NOT_EXPECTED_CANDIDATE")
    if lifecycle.get("registry_is_authoritative") is not False:
        raise AssuranceError("LIFECYCLE_MUST_NOT_BE_SECOND_CANONICAL_AUTHORITY")
    op = state.get("operational_state")
    checkpoint = state.get("latest_legitimate_completed_scientific_checkpoint")
    child = state.get("paused_child_work")
    firewall = state.get("scientific_firewall_preserved")
    gates = state.get("foundation_resume_gate")
    items = lifecycle.get("open_items")
    if not all(isinstance(x, dict) for x in (op, checkpoint, child, firewall)):
        raise AssuranceError("MISSING_REQUIRED_STATE_SECTION")
    if not isinstance(gates, list) or not isinstance(items, list):
        raise AssuranceError("MISSING_GATE_OR_LIFECYCLE_LIST")
    if op.get("new_scientific_execution_allowed") is not False:
        raise AssuranceError("PAUSE_VIEW_REQUIRES_SCIENCE_CLOSED")
    if child.get("post_pause_run_disposition") != "QUARANTINED_NOT_ADMITTED":
        raise AssuranceError("QUARANTINE_DISPOSITION_MISMATCH")
    by_pr = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("pr"), int):
            raise AssuranceError("MALFORMED_LIFECYCLE_ITEM")
        if item["pr"] in by_pr:
            raise AssuranceError("DUPLICATE_PR_IN_LIFECYCLE")
        by_pr[item["pr"]] = item
    for required in (14, 15, 16):
        if required not in by_pr:
            raise AssuranceError(f"MISSING_REQUIRED_PR_{required}")
    lines = [
        "# Multiverse 競輪ver — いまここ（自動生成候補）", "",
        "この表示は正本ではありません。GitHubの正本・exact PR head・review evidenceから作る主向けView候補です。", "",
        "## 一言でいうと", f"**{op.get('keirin_research')}**", "",
        "競輪の新しい科学実験は停止中。Multiverse基盤監査・安全修復だけ進行中です。", "",
        "## 最後に確定している競輪研究地点",
        f"- PR #{checkpoint.get('pr')} — {checkpoint.get('title')}",
        f"- Lab: `{checkpoint.get('lab')}`",
        f"- Auditor: `{checkpoint.get('auditor')}`",
        f"- 証拠の種類: `{checkpoint.get('evidence_class')}`",
        f"- 評価数: `{checkpoint.get('scenario_race_evaluations')}`",
        "- 現実で勝てるモデルの確定ではありません。", "",
        "## 停止中の子作業",
        f"- PR #{child.get('pr')} — {child.get('title')}",
        f"- 自動科学実行: `{child.get('automatic_scientific_execution')}`",
        f"- 停止後に既に走ってしまったrun: `{child.get('post_pause_already_armed_run')}`",
        f"- そのrunの扱い: `{child.get('post_pause_run_disposition')}`",
        "- その結果を見て再開先を選ぶことは禁止。", "",
        "## いま進めてよいもの", "- 監査", "- Recovery（復旧）確認", "- Evidence preservation（証拠保全）", "- Reversible containment（元に戻せる安全対策）", "",
        "## 再開前Gate（通過条件）",
    ]
    lines.extend(f"- `{g}`" for g in gates)
    lines.extend([
        "", "## 保護状態",
        f"- ECON_HOLDOUT1000: `{firewall.get('ECON_HOLDOUT1000')}`",
        f"- RESULT/PAYOUT: `{firewall.get('RESULT_PAYOUT')}`",
        f"- Untouched validation: `{firewall.get('new_untouched_validation_opened')}`",
        f"- Model promotion: `{firewall.get('model_promotion')}`",
        f"- Real-money wagering: `{firewall.get('real_money_wagering')}`", "",
        "## 主がやること", f"**{op.get('owner_action_now')}**", "",
        "## 重要", "このViewは表示専用。再開許可はZero-History Resume Resolverと正式review/gateを別に通す必要があります。", ""
    ])
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--lifecycle", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    try:
        text = render(_load(Path(args.state)), _load(Path(args.lifecycle)))
    except AssuranceError as exc:
        print(f"OWNER_ASSURANCE_RENDER_DENY:{exc}")
        return 42
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
