#!/usr/bin/env python3
"""Inventory GitHub Actions trigger semantics without executing any target workflow.

NEXT_VERSION_CANDIDATE audit utility. It reads YAML as text and reports top-level
`on:` events conservatively. Unknown/malformed trigger syntax is surfaced as UNKNOWN,
never treated as manual-only.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

ON_RE = re.compile(r"^(?:['\"]?on['\"]?):\s*(.*?)\s*$")
EVENT_RE = re.compile(r"^\s{2}([A-Za-z0-9_-]+):(?:\s|$)")

MANUAL_EVENTS = {"workflow_dispatch"}
CALLABLE_EVENTS = {"workflow_call"}
AUTO_EVENTS = {
    "push", "pull_request", "pull_request_target", "schedule", "workflow_run",
    "repository_dispatch", "issues", "issue_comment", "discussion", "discussion_comment",
    "release", "create", "delete", "fork", "gollum", "page_build", "public", "status",
    "watch", "check_run", "check_suite", "deployment", "deployment_status", "merge_group",
}

SENSITIVE_NAME_TOKENS = (
    "keirin", "keirinjp", "tamano", "shadow250", "sim100", "stage7", "dev2000",
    "all-market", "nextgen", "universe", "settlement", "result", "payout",
)


def _inline_events(value: str) -> List[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        return [x.strip().strip("'\"") for x in value[1:-1].split(",") if x.strip()]
    return [value.strip().strip("'\"")]


def parse_events(text: str) -> Dict[str, object]:
    lines = text.splitlines()
    start = None
    inline = ""
    for i, line in enumerate(lines):
        if line.startswith((" ", "\t")):
            continue
        m = ON_RE.match(line)
        if m:
            start = i
            inline = m.group(1)
            break
    if start is None:
        return {"events": [], "parse_status": "NO_TOP_LEVEL_ON_FOUND"}
    events = _inline_events(inline)
    if not events:
        for line in lines[start + 1:]:
            if line and not line.startswith((" ", "\t", "#")):
                break
            m = EVENT_RE.match(line)
            if m:
                events.append(m.group(1))
    events = sorted(set(events))
    return {"events": events, "parse_status": "PASS" if events else "ON_FOUND_NO_EVENTS"}


def classify(events: List[str], parse_status: str) -> str:
    if parse_status != "PASS" or not events:
        return "UNKNOWN_FAIL_CLOSED"
    unknown = [x for x in events if x not in MANUAL_EVENTS | CALLABLE_EVENTS | AUTO_EVENTS]
    if unknown:
        return "UNKNOWN_FAIL_CLOSED"
    if any(x in AUTO_EVENTS for x in events):
        return "AUTO_TRIGGER_PRESENT"
    if any(x in CALLABLE_EVENTS for x in events):
        return "CALLABLE_NOT_STANDALONE_MANUAL"
    return "MANUAL_ONLY"


def scan(root: Path) -> Dict[str, object]:
    files = sorted([*root.glob("*.yml"), *root.glob("*.yaml")])
    rows = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        parsed = parse_events(text)
        events = parsed["events"]
        classification = classify(events, parsed["parse_status"])
        lower = path.name.lower()
        rows.append({
            "path": path.as_posix(),
            "events": events,
            "parse_status": parsed["parse_status"],
            "trigger_class": classification,
            "keirin_sensitive_name": any(tok in lower for tok in SENSITIVE_NAME_TOKENS),
        })
    sensitive = [r for r in rows if r["keirin_sensitive_name"]]
    auto_sensitive = [r for r in sensitive if r["trigger_class"] == "AUTO_TRIGGER_PRESENT"]
    unknown_sensitive = [r for r in sensitive if r["trigger_class"] == "UNKNOWN_FAIL_CLOSED"]
    return {
        "record": "MULTIVERSE_WORKFLOW_TRIGGER_INVENTORY_v1",
        "workflow_count": len(rows),
        "sensitive_name_count": len(sensitive),
        "sensitive_auto_trigger_count": len(auto_sensitive),
        "sensitive_unknown_trigger_count": len(unknown_sensitive),
        "rows": rows,
        "scientific_execution_performed": False,
        "result_payout_accessed": False,
        "holdout_accessed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".github/workflows")
    p.add_argument("--output")
    args = p.parse_args()
    result = scan(Path(args.root))
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    print(
        "WORKFLOW_TRIGGER_INVENTORY_PASS",
        f"workflows={result['workflow_count']}",
        f"sensitive_auto={result['sensitive_auto_trigger_count']}",
        f"sensitive_unknown={result['sensitive_unknown_trigger_count']}",
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
