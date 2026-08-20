#!/usr/bin/env python3
"""Owner Assurance v2: derive the current Foundation work pointer truthfully.

This is a thin wrapper over the Auditor-reviewed v1 safety logic. Candidate only;
the generated view is never a second canonical authority.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from multiverse_owner_assurance_view_v1 import (
    AssuranceError,
    _classifications,
    _find_pr,
    _load,
    build_view as build_view_v1,
)


LEGACY_FOCUS_LINE = "- **今進める場所:** PR #16 Foundation Audit（全体監査）"


def build_view(lifecycle: Dict[str, Any], operational: Dict[str, Any], safe_mode: Dict[str, Any]) -> str:
    op = operational.get("operational_state")
    if not isinstance(op, dict):
        raise AssuranceError("MISSING_OPERATIONAL_STATE_FOR_CURRENT_FOCUS")

    active_pr = op.get("active_foundation_remediation_pr")
    if not isinstance(active_pr, int) or isinstance(active_pr, bool) or active_pr <= 0:
        raise AssuranceError("MALFORMED_ACTIVE_FOUNDATION_REMEDIATION_PR")

    items = lifecycle.get("open_items")
    if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
        raise AssuranceError("MALFORMED_OPEN_ITEMS_FOR_CURRENT_FOCUS")
    active_item = _find_pr(items, active_pr)
    if "ACTIVE" not in _classifications(active_item):
        raise AssuranceError("ACTIVE_FOUNDATION_POINTER_TARGET_NOT_ACTIVE")
    title = active_item.get("title")
    if not isinstance(title, str) or not title.strip():
        raise AssuranceError("ACTIVE_FOUNDATION_POINTER_TITLE_MISSING")

    text = build_view_v1(lifecycle, operational, safe_mode)
    if text.count(LEGACY_FOCUS_LINE) != 1:
        raise AssuranceError("LEGACY_OWNER_FOCUS_LINE_UNEXPECTED")

    current_focus_line = f"- **今進める場所:** PR #{active_pr} {title.strip()}"
    return text.replace(LEGACY_FOCUS_LINE, current_focus_line, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Owner Assurance v2 candidate")
    parser.add_argument("--lifecycle", required=True)
    parser.add_argument("--operational", required=True)
    parser.add_argument("--safe-mode", required=True)
    args = parser.parse_args()
    try:
        text = build_view(_load(Path(args.lifecycle)), _load(Path(args.operational)), _load(Path(args.safe_mode)))
    except AssuranceError as exc:
        print(f"OWNER_ASSURANCE_V2_FAIL_CLOSED:{exc}")
        return 42
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
