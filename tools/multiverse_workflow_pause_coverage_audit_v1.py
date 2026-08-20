#!/usr/bin/env python3
"""Inventory workflow pause-guard coverage without declaring unknown workflows safe.

Candidate audit tool only. Standard-library implementation so it can run in GitHub Actions
without adding dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCIENTIFIC_FILENAME_MARKERS = (
    "all-market",
    "dev2000",
    "keirin",
    "digital-twin",
    "digital_twin",
    "reality",
    "stress",
    "settlement",
    "prediction",
    "ticket",
    "price-ev",
    "holdout",
)

SCIENTIFIC_CONTENT_MARKERS = (
    "DEV2000",
    "ECON_HOLDOUT",
    "RESULT",
    "PAYOUT",
    "settlement",
    "prediction",
    "simulate",
    "simulation",
    "digital_twin",
    "top3",
    "ticket",
    "odds",
    "scoring",
)

AUDIT_FILENAME_MARKERS = (
    "multiverse-foundation-candidate-ci",
    "audit",
    "recovery",
    "bootstrap",
)

GUARD_MARKERS = (
    "multiverse_pause_guard_v1.py",
    "MULTIVERSE_PAUSE_GUARD",
)

YAML_SUFFIXES = {".yml", ".yaml"}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _contains_any(text: str, markers: Iterable[str]) -> List[str]:
    low = text.lower()
    return sorted({m for m in markers if m.lower() in low})


def _looks_like_workflow(text: str) -> bool:
    # Do not need a full YAML parser for inventory. Require at least jobs + an event-ish key.
    return bool(re.search(r"(?m)^\s*jobs\s*:", text)) and bool(re.search(r"(?m)^\s*on\s*:", text))


def classify(path: Path, root: Path) -> Dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    name = path.name.lower()
    text = _read_text(path)

    filename_science = [m for m in SCIENTIFIC_FILENAME_MARKERS if m in name]
    content_science = _contains_any(text, SCIENTIFIC_CONTENT_MARKERS)
    audit_name = [m for m in AUDIT_FILENAME_MARKERS if m in name]
    guard_hits = _contains_any(text, GUARD_MARKERS)

    if not _looks_like_workflow(text):
        classification = "UNKNOWN_REVIEW_REQUIRED"
        reason = "YAML_FILE_NOT_CONFIRMED_AS_WORKFLOW_BY_MINIMAL_SHAPE_CHECK"
    elif filename_science or content_science:
        classification = "SCIENTIFIC_CANDIDATE"
        reason = "SCIENTIFIC_MARKER_PRESENT"
    elif audit_name:
        classification = "AUDIT_OR_GOVERNANCE_ONLY"
        reason = "AUDIT_GOVERNANCE_FILENAME_MARKER_AND_NO_SCIENCE_MARKER"
    else:
        classification = "UNKNOWN_REVIEW_REQUIRED"
        reason = "NO_SUFFICIENT_MARKER_TO_CALL_SCIENTIFIC_OR_AUDIT_ONLY"

    return {
        "path": rel,
        "classification": classification,
        "reason": reason,
        "filename_science_markers": filename_science,
        "content_science_markers": content_science,
        "audit_filename_markers": audit_name,
        "pause_guard_markers": guard_hits,
        "pause_guard_present": bool(guard_hits),
        "automatic_triggers_detected": {
            "push": bool(re.search(r"(?m)^\s*push\s*:", text)),
            "pull_request": bool(re.search(r"(?m)^\s*pull_request\s*:", text)),
            "schedule": bool(re.search(r"(?m)^\s*schedule\s*:", text)),
            "workflow_dispatch": "workflow_dispatch" in text,
        },
    }


def inventory(root: Path, workflow_dir: Path) -> Dict[str, Any]:
    if not workflow_dir.exists() or not workflow_dir.is_dir():
        raise RuntimeError("WORKFLOW_DIRECTORY_MISSING")

    paths = sorted(
        p for p in workflow_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in YAML_SUFFIXES
    )
    entries = [classify(p, root) for p in paths]

    counts = {
        "total_workflow_yaml": len(entries),
        "scientific_candidate": sum(e["classification"] == "SCIENTIFIC_CANDIDATE" for e in entries),
        "audit_or_governance_only": sum(e["classification"] == "AUDIT_OR_GOVERNANCE_ONLY" for e in entries),
        "unknown_review_required": sum(e["classification"] == "UNKNOWN_REVIEW_REQUIRED" for e in entries),
        "scientific_candidate_with_guard": sum(
            e["classification"] == "SCIENTIFIC_CANDIDATE" and e["pause_guard_present"] for e in entries
        ),
        "scientific_candidate_without_guard": sum(
            e["classification"] == "SCIENTIFIC_CANDIDATE" and not e["pause_guard_present"] for e in entries
        ),
    }

    uncovered = [e["path"] for e in entries if e["classification"] == "SCIENTIFIC_CANDIDATE" and not e["pause_guard_present"]]
    unknown = [e["path"] for e in entries if e["classification"] == "UNKNOWN_REVIEW_REQUIRED"]

    return {
        "record": "MULTIVERSE_WORKFLOW_PAUSE_COVERAGE_AUDIT_V1",
        "status": "CANDIDATE_INVENTORY_NOT_AUTHORIZATION_DECISION",
        "counts": counts,
        "uncovered_scientific_candidates": uncovered,
        "unknown_review_required": unknown,
        "entries": entries,
        "interpretation_rule": "UNKNOWN_REVIEW_REQUIRED is not safe/exempt. SCIENTIFIC_CANDIDATE_WITHOUT_GUARD is an integration gap candidate requiring review/remediation before a workflow-wide pause guarantee.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit workflow pause-guard coverage")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--workflow-dir", default=".github/workflows")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    workflow_dir = (root / args.workflow_dir).resolve()
    try:
        result = inventory(root, workflow_dir)
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": str(exc)}, sort_keys=True))
        return 42

    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output == "-":
        print(payload, end="")
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
