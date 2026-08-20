#!/usr/bin/env python3
"""Deterministic zero-history resume resolver candidate.

Separates 'where to orient' from 'permission to resume scientific execution'.
This candidate is noncanonical until reviewed/adopted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

ALLOW = "ALLOW"
DENY = "DENY"

REQUIRED_GATES = {
    "G1_PAUSE_SEMANTICS_FIXED",
    "G2_CURRENT_STATE_SYNCHRONIZED",
    "G3_REVIEW_LIFECYCLE_REGISTRY_EXISTS",
    "G4_ZERO_HISTORY_RESUME_POINTER_DETERMINISTIC",
    "G5_OWNER_ASSURANCE_MINIMAL_VIEW",
}

ACCEPTED_GATE_VALUES = {"PASS", "ACCEPTED", "SATISFIED_BY_STRONGER_EVIDENCE"}


def _result(mode: str, scientific_resume_allowed: bool, reason: str, **extra: Any) -> Dict[str, Any]:
    out = {
        "mode": mode,
        "scientific_resume_allowed": scientific_resume_allowed,
        "decision": ALLOW if scientific_resume_allowed else DENY,
        "reason_code": reason,
    }
    out.update(extra)
    return out


def resolve(pointer: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(pointer, dict):
        return _result("RECOVERY_AMBIGUOUS", False, "MALFORMED_POINTER_ROOT")

    current = pointer.get("current_operational_resolution")
    paused_child = pointer.get("paused_child")
    gates = pointer.get("foundation_gates")
    requirements = pointer.get("resume_permission_requirements")

    if not isinstance(current, dict) or not isinstance(paused_child, dict) or not isinstance(gates, dict) or not isinstance(requirements, list):
        return _result("RECOVERY_AMBIGUOUS", False, "MISSING_REQUIRED_POINTER_SECTION")

    if set(gates) != REQUIRED_GATES:
        return _result("RECOVERY_AMBIGUOUS", False, "FOUNDATION_GATE_SET_MISMATCH")

    if current.get("mode") == "FOUNDATION_AUDIT_CONTINUATION":
        if current.get("scientific_resume_allowed") is not False:
            return _result("RECOVERY_AMBIGUOUS", False, "PAUSE_MODE_PERMISSION_CONTRADICTION")
        pr = current.get("read_first_pr")
        head = current.get("read_first_exact_head")
        if not isinstance(pr, int) or not isinstance(head, str) or len(head) != 40:
            return _result("RECOVERY_AMBIGUOUS", False, "INVALID_FOUNDATION_ORIENTATION_POINTER")
        return _result(
            "FOUNDATION_AUDIT_CONTINUATION",
            False,
            "OWNER_PAUSE_ACTIVE_OR_RESUME_GATES_NOT_ACCEPTED",
            read_first_pr=pr,
            read_first_exact_head=head,
        )

    unresolved_gates = sorted(k for k, v in gates.items() if v not in ACCEPTED_GATE_VALUES)
    if unresolved_gates:
        return _result("FOUNDATION_GATE_INCOMPLETE", False, "G1_G5_NOT_ALL_ACCEPTED", unresolved_gates=unresolved_gates)

    quarantine = paused_child.get("post_pause_run_disposition")
    if quarantine in {None, "QUARANTINED_NOT_ADMITTED", "UNRESOLVED"}:
        return _result("QUARANTINE_DISPOSITION_REQUIRED", False, "PR15_QUARANTINED_RUN_UNRESOLVED")

    explicit = pointer.get("accepted_resume_pointer")
    if not isinstance(explicit, dict):
        return _result("EXPLICIT_RESUME_POINTER_REQUIRED", False, "NO_ACCEPTED_RESUME_POINTER")

    pr = explicit.get("pr")
    head = explicit.get("exact_head")
    gate = explicit.get("next_gate")
    if not isinstance(pr, int) or not isinstance(head, str) or len(head) != 40 or not isinstance(gate, str) or not gate:
        return _result("RECOVERY_AMBIGUOUS", False, "INVALID_ACCEPTED_RESUME_POINTER")

    if explicit.get("scientific_resume_allowed") is not True:
        return _result("EXPLICIT_RESUME_POINTER_PRESENT_BUT_CLOSED", False, "RESUME_POINTER_DOES_NOT_AUTHORIZE_EXECUTION", pr=pr, exact_head=head, next_gate=gate)

    return _result("SCIENTIFIC_RESUME_EXPLICITLY_AUTHORIZED", True, "EXPLICIT_ACCEPTED_RESUME_POINTER", pr=pr, exact_head=head, next_gate=gate)


def resolve_file(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _result("RECOVERY_AMBIGUOUS", False, "MISSING_POINTER_FILE")
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _result("RECOVERY_AMBIGUOUS", False, "UNREADABLE_OR_MALFORMED_POINTER_FILE")
    return resolve(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve Multiverse zero-history continuation safely")
    parser.add_argument("--pointer", required=True)
    args = parser.parse_args()
    result = resolve_file(Path(args.pointer))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["mode"] == "FOUNDATION_AUDIT_CONTINUATION" else (0 if result["scientific_resume_allowed"] else 42)


if __name__ == "__main__":
    raise SystemExit(main())
