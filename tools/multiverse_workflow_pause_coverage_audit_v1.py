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

# Stronger content markers only. Ordinary words like RESULT/PAYOUT are deliberately
# excluded because governance/audit workflows may mention them while proving firewalls.
SCIENTIFIC_CONTENT_MARKERS = (
    "stage7_settlement",
    "settlement_eval",
    "prediction_lock",
    "synthetic_market_odds",
    "digital_twin_v1.py",
    "c0_c1_n1",
    "top3_architecture",
    "ticket_probability",
    "price_catalog",
    "score_predictions",
    "simulate_race",
)

# Exemption by broad words such as 'audit' or 'recovery' is unsafe. Only an exact,
# already-reviewed governance-only workflow name can be called audit-only here.
AUDIT_EXACT_ALLOWLIST = {
    "multiverse-foundation-candidate-ci-v1.yml",
}

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
    return bool(re.search(r"(?m)^\s*jobs\s*:", text)) and bool(re.search(r"(?m)^\s*on\s*:", text))


def classify(path: Path, root: Path) -> Dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    name = path.name.lower()
    text = _read_text(path)

    filename_science = [m for m in SCIENTIFIC_FILENAME_MARKERS if m in name]
    content_science = _contains_any(text, SCIENTIFIC_CONTENT_MARKERS)
    exact_audit_allowlisted = name in AUDIT_EXACT_ALLOWLIST
    guard_hits = _contains_any(text, GUARD_MARKERS)

    if not _looks_like_workflow(text):
        classification = "UNKNOWN_REVIEW_REQUIRED"
        reason = "YAML_FILE_NOT_CONFIRMED_AS_WORKFLOW_BY_MINIMAL_SHAPE_CHECK"
    elif filename_science:
        classification = "SCIENTIFIC_CANDIDATE"
        reason = "SCIENTIFIC_FILENAME_MARKER_PRESENT"
    elif exact_audit_allowlisted and not content_science:
        classification = "AUDIT_OR_GOVERNANCE_ONLY"
        reason = "EXACT_AUDIT_ALLOWLIST_AND_NO_STRONG_SCIENCE_CONTENT_MARKER"
    elif content_science:
        classification = "SCIENTIFIC_CANDIDATE"
        reason = "STRONG_SCIENCE_CONTENT_MARKER_PRESENT"
    else:
        classification = "UNKNOWN_REVIEW_REQUIRED"
        reason = "NO_SUFFICIENT_EVIDENCE_TO_CALL_SAFE_OR_SCIENTIFIC"

    return {
        "path": rel,
        "classification": classification,
        "reason": reason,
        "filename_science_markers": filename_science,
        "content_science_markers": content_science,
        "exact_audit_allowlisted": exact_audit_allowlisted,
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
        "interpretation_rule": "UNKNOWN_REVIEW_REQUIRED is not safe/exempt. SCIENTIFIC_CANDIDATE without the guard is an integration-gap candidate requiring review/remediation before any workflow-wide pause guarantee.",
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
