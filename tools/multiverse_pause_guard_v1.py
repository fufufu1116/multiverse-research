#!/usr/bin/env python3
"""Fail-closed candidate pause guard for governed Multiverse execution.

This is a NEXT_VERSION_CANDIDATE implementation used by PR #16 for audit/testing.
It does not change accepted policy or canonical authority by itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

ALLOW = "ALLOW"
DENY = "DENY"
EXIT_ALLOW = 0
EXIT_DENY = 42

KNOWN_OPERATIONS = {
    "SCIENTIFIC_EXECUTION",
    "PROTECTED_DATA_OPEN",
    "MODEL_PROMOTION",
    "EXTERNAL_PROVIDER_CONTACT",
    "AUDIT_READ",
    "RECOVERY_READ_VERIFY",
    "EVIDENCE_PRESERVATION",
    "REVERSIBLE_CONTAINMENT",
}

ALWAYS_DENY = {
    "PROTECTED_DATA_OPEN",
    "MODEL_PROMOTION",
    "EXTERNAL_PROVIDER_CONTACT",
}

ESSENTIAL_SAFE_MODE_ALLOW = {
    "AUDIT_READ",
    "RECOVERY_READ_VERIFY",
    "EVIDENCE_PRESERVATION",
    "REVERSIBLE_CONTAINMENT",
}


def _deny(reason: str, *, generation: Optional[int] = None) -> Dict[str, Any]:
    return {
        "decision": DENY,
        "reason_code": reason,
        "safe_mode_generation_seen": generation,
    }


def _allow(reason: str, *, generation: Optional[int] = None) -> Dict[str, Any]:
    return {
        "decision": ALLOW,
        "reason_code": reason,
        "safe_mode_generation_seen": generation,
    }


def evaluate_state(
    state: Dict[str, Any],
    *,
    domain: str,
    operation: str,
    expected_generation: Optional[int] = None,
) -> Dict[str, Any]:
    """Evaluate one execution attempt against a parsed safe-mode state."""
    if operation not in KNOWN_OPERATIONS:
        return _deny("UNKNOWN_OPERATION_DENY")
    if not isinstance(domain, str) or not domain.strip():
        return _deny("MISSING_OR_INVALID_DOMAIN_DENY")

    generation = state.get("candidate_generation")
    if not isinstance(generation, int) or generation < 0:
        return _deny("MALFORMED_GENERATION_DENY")
    if expected_generation is not None and generation != expected_generation:
        return _deny("STALE_EXPECTED_GENERATION_DENY", generation=generation)

    safe_mode = state.get("safe_mode")
    if not isinstance(safe_mode, dict):
        return _deny("MALFORMED_SAFE_MODE_DENY", generation=generation)
    active = safe_mode.get("active")
    scope = safe_mode.get("scope")
    if not isinstance(active, bool) or not isinstance(scope, list) or not all(isinstance(x, str) for x in scope):
        return _deny("MALFORMED_SAFE_MODE_DENY", generation=generation)

    if operation in ALWAYS_DENY:
        return _deny(f"{operation}_DENIED_BY_POLICY", generation=generation)

    if active:
        if operation in ESSENTIAL_SAFE_MODE_ALLOW:
            return _allow("SAFE_MODE_ESSENTIAL_OPERATION_ALLOWED", generation=generation)
        if operation == "SCIENTIFIC_EXECUTION":
            scope_key = f"{domain.strip().upper()}_SCIENTIFIC_EXECUTION"
            if scope_key in scope or "ALL_SCIENTIFIC_EXECUTION" in scope:
                return _deny("OWNER_PAUSE_SCOPE_DENY", generation=generation)
            return _allow("SAFE_MODE_ACTIVE_BUT_DOMAIN_OUTSIDE_PAUSE_SCOPE", generation=generation)
        return _deny("SAFE_MODE_DEFAULT_DENY", generation=generation)

    if operation == "SCIENTIFIC_EXECUTION":
        return _allow("SAFE_MODE_INACTIVE_SCIENTIFIC_EXECUTION_NOT_BLOCKED_BY_THIS_GUARD", generation=generation)
    if operation in ESSENTIAL_SAFE_MODE_ALLOW:
        return _allow("SAFE_MODE_INACTIVE_OPERATION_ALLOWED", generation=generation)
    return _deny("DEFAULT_FAIL_CLOSED_DENY", generation=generation)


def evaluate_file(
    path: Path,
    *,
    domain: str,
    operation: str,
    expected_generation: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
    except FileNotFoundError:
        return _deny("MISSING_STATE_DENY")
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _deny("UNREADABLE_OR_MALFORMED_STATE_DENY")
    if not isinstance(state, dict):
        return _deny("MALFORMED_STATE_ROOT_DENY")
    return evaluate_state(
        state,
        domain=domain,
        operation=operation,
        expected_generation=expected_generation,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed Multiverse pause guard candidate")
    parser.add_argument("--state", required=True, help="Path to safe-mode state JSON")
    parser.add_argument("--domain", required=True, help="Execution domain, e.g. KEIRIN")
    parser.add_argument("--operation", required=True, help="Governed operation class")
    parser.add_argument("--expected-generation", type=int, default=None)
    args = parser.parse_args()

    result = evaluate_file(
        Path(args.state),
        domain=args.domain,
        operation=args.operation,
        expected_generation=args.expected_generation,
    )
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return EXIT_ALLOW if result["decision"] == ALLOW else EXIT_DENY


if __name__ == "__main__":
    raise SystemExit(main())
