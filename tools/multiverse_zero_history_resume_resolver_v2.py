#!/usr/bin/env python3
"""Zero-history orientation resolver v2 candidate.

This resolver is intentionally incapable of authorizing scientific execution.
It only tells a new chat/agent where to orient, then requires Fresh Read of GitHub.
Execution permission belongs to a separate canonical authorization gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

DENY = "DENY"
REQUIRED_GATES = {
    "G1_PAUSE_SEMANTICS_FIXED",
    "G2_CURRENT_STATE_SYNCHRONIZED",
    "G3_REVIEW_LIFECYCLE_REGISTRY_EXISTS",
    "G4_ZERO_HISTORY_RESUME_POINTER_DETERMINISTIC",
    "G5_OWNER_ASSURANCE_MINIMAL_VIEW",
}


def _result(mode: str, reason: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "mode": mode,
        "decision": DENY,
        "scientific_resume_allowed": False,
        "execution_authority": "NONE_ORIENTATION_ONLY",
        "reason_code": reason,
    }
    out.update(extra)
    return out


def resolve(pointer: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pointer, dict):
        return _result("RECOVERY_AMBIGUOUS", "MALFORMED_POINTER_ROOT")
    if pointer.get("canonical_authority") is not False:
        return _result("RECOVERY_AMBIGUOUS", "ORIENTATION_POINTER_MUST_REMAIN_NONCANONICAL")
    if pointer.get("execution_authority") != "NONE_ORIENTATION_ONLY":
        return _result("RECOVERY_AMBIGUOUS", "ORIENTATION_POINTER_EXECUTION_AUTHORITY_CONTRADICTION")

    current = pointer.get("current_operational_resolution")
    paused_child = pointer.get("paused_child")
    gates = pointer.get("foundation_gates")
    requirements = pointer.get("external_execution_authorization_requirements")
    if not isinstance(current, dict) or not isinstance(paused_child, dict) or not isinstance(gates, dict) or not isinstance(requirements, list):
        return _result("RECOVERY_AMBIGUOUS", "MISSING_REQUIRED_POINTER_SECTION")
    if set(gates) != REQUIRED_GATES or not all(isinstance(v, str) for v in gates.values()):
        return _result("RECOVERY_AMBIGUOUS", "FOUNDATION_GATE_SET_MISMATCH")
    if not all(isinstance(x, str) for x in requirements):
        return _result("RECOVERY_AMBIGUOUS", "MALFORMED_EXTERNAL_AUTH_REQUIREMENTS")

    if current.get("scientific_resume_allowed") is not False:
        return _result("RECOVERY_AMBIGUOUS", "EMBEDDED_EXECUTION_AUTHORITY_FORBIDDEN")
    if "accepted_resume_pointer" in pointer:
        return _result("RECOVERY_AMBIGUOUS", "EMBEDDED_ACCEPTED_RESUME_POINTER_FORBIDDEN")

    mode = current.get("mode")
    pr = current.get("read_first_pr")
    anchor = current.get("read_first_anchor_head")
    fresh = current.get("fresh_read_current_pr_head_required")
    if not isinstance(mode, str) or not mode:
        return _result("RECOVERY_AMBIGUOUS", "INVALID_ORIENTATION_MODE")
    if not isinstance(pr, int) or not isinstance(anchor, str) or len(anchor) != 40 or fresh is not True:
        return _result("RECOVERY_AMBIGUOUS", "INVALID_ORIENTATION_TARGET")

    quarantine = paused_child.get("post_pause_run_disposition")
    if not isinstance(quarantine, str) or not quarantine:
        return _result("RECOVERY_AMBIGUOUS", "MALFORMED_QUARANTINE_STATUS")

    reason = "OWNER_PAUSE_FOUNDATION_REMEDIATION_ORIENTATION" if mode == "FOUNDATION_LAB_REMEDIATION_CONTINUATION" else "ORIENTATION_ONLY_EXTERNAL_EXECUTION_GATE_REQUIRED"
    return _result(
        "ORIENTATION_ONLY",
        reason,
        source_mode=mode,
        read_first_pr=pr,
        read_first_anchor_head=anchor,
        fresh_read_current_pr_head_required=True,
        quarantine_status=quarantine,
        gate_statuses=gates,
    )


def resolve_file(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _result("RECOVERY_AMBIGUOUS", "MISSING_POINTER_FILE")
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _result("RECOVERY_AMBIGUOUS", "UNREADABLE_OR_MALFORMED_POINTER_FILE")
    return resolve(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve zero-history orientation only; never authorize science")
    parser.add_argument("--pointer", required=True)
    args = parser.parse_args()
    result = resolve_file(Path(args.pointer))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["mode"] == "ORIENTATION_ONLY" else 42


if __name__ == "__main__":
    raise SystemExit(main())
