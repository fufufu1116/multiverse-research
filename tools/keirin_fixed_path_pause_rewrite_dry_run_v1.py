#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

EXPECTED_INPUT_BLOB = "248616ba6e8e671d044793ff82bbec2a04804611"
NEW_UPDATED_JST = "2026-08-21T00:42:00+09:00"
NEW_STATUS = "PAUSED_POST_FOUNDATION_ACCEPTANCE_AWAITING_SEPARATE_SCIENTIFIC_EXECUTION_AUTHORIZATION"
NEW_NEXT_GATE = "SEPARATE_SCIENTIFIC_EXECUTION_AUTHORIZATION_REQUIRED_BEFORE_ANY_KEIRIN_SCIENTIFIC_EXECUTION"


def git_blob_sha(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def build_rewrite(original: dict) -> dict:
    if not original.get("status", "").startswith("ACTIVE_RESEARCH_"):
        raise RuntimeError("legacy status drift: expected ACTIVE_RESEARCH_ prefix")
    if original.get("updated_jst") != "2026-08-20T00:29:00+09:00":
        raise RuntimeError("legacy updated_jst drift")

    rewritten = copy.deepcopy(original)
    rewritten["updated_jst"] = NEW_UPDATED_JST
    rewritten["status"] = NEW_STATUS
    rewritten["effective_scientific_execution_control"] = {
        "state_generation_context": 11,
        "keirin_science": "PAUSED",
        "scientific_execution_allowed": False,
        "scientific_resume_allowed": False,
        "separate_scientific_execution_authorization_required": True,
        "foundation_acceptance_is_not_scientific_authorization": True,
        "zero_history_orientation_is_not_scientific_authorization": True,
        "latest_legitimate_completed_scientific_checkpoint": {
            "pr": 14,
            "exact_lab_reviewed_scientific_head": "e70bda39a5d3ce585af4e028b35106b859871bd9",
            "evidence_class": "SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY",
            "real_world_edge_or_roi_evidence": False,
        },
        "pr15": {
            "status": "QUARANTINED_NOT_ADMITTED",
            "metrics_may_be_inspected_for_resume_selection": False,
        },
    }
    rewritten["pre_pause_next_gate_historical"] = original["next_gate"]
    rewritten["pre_pause_next_exact_actions_historical"] = copy.deepcopy(original["next_exact_actions"])
    rewritten["next_gate"] = NEW_NEXT_GATE
    rewritten["next_exact_actions"] = [
        "Maintain Keirin scientific execution PAUSED until a separate Scientific Execution Authorization Gate is validly satisfied.",
        "Treat Foundation acceptance and Zero-History orientation as non-authorizing for Keirin scientific execution.",
        "Keep PR #15 QUARANTINED_NOT_ADMITTED and do not inspect its metrics for resume selection.",
        "Keep ECON_HOLDOUT1000 SEALED and RESULT/PAYOUT UNAUTHORIZED.",
        "Do not use DEV2000 C for new-lineage rescue or same-lineage B/C rescue tuning.",
        "Do not open untouched validation, promote a model, contact an external provider, or use real money.",
        "Preserve PR #14 as the latest legitimate completed scientific checkpoint; synthetic engineering evidence is not real-world edge or ROI evidence.",
        "Await independent Lab determination before any fixed-path canonical rewrite or further acceptance action.",
    ]
    return rewritten


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run a fail-closed Keirin fixed-path pause rewrite")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    src = Path(args.input).resolve()
    dst = Path(args.output).resolve()
    if src == dst:
        raise SystemExit("REFUSE_IN_PLACE_WRITE")

    raw = src.read_bytes()
    actual_blob = git_blob_sha(raw)
    if actual_blob != EXPECTED_INPUT_BLOB:
        raise SystemExit(f"STALE_LEGACY_BLOB expected={EXPECTED_INPUT_BLOB} actual={actual_blob}")

    original = json.loads(raw.decode("utf-8"))
    rewritten = build_rewrite(original)
    dst.write_text(json.dumps(rewritten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("KEIRIN_FIXED_PATH_PAUSE_REWRITE_DRY_RUN_PASS")
    print(f"INPUT_BLOB={actual_blob}")
    print("ACTUAL_FIXED_PATH_MODIFIED=false")
    print("SCIENTIFIC_EXECUTION_PERFORMED=false")
    print("SCIENTIFIC_RESUME_ALLOWED=false")
    print("RESULT_PAYOUT_ACCESSED=false")
    print("HOLDOUT_ACCESSED=false")
    print("PR15_QUARANTINED_METRICS_INSPECTED=false")


if __name__ == "__main__":
    main()
