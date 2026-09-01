#!/usr/bin/env python3
"""Prespecified promotion policy for the minimal MULTIVERSE task router.

This layer exists to keep AUDITOR PASS routing deterministic: the task manifest
must declare before review whether Auditor PASS stops at OWNER_GATE or DONE.
"""
from __future__ import annotations

import json
from typing import Any

from multiverse_task_router_v1 import (
    RouterError,
    next_role_for_state,
    transition as base_transition,
    utc_now,
    validate_manifest,
)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RouterError(code)


def owner_gate_on_auditor_pass(task: dict[str, Any]) -> bool:
    validate_manifest(task)
    value = task["authority"].get("owner_gate_on_auditor_pass")
    require(isinstance(value, bool), "OWNER_GATE_ON_AUDITOR_PASS_NOT_PRESPECIFIED")
    return value


def transition(task: dict[str, Any], event: str, evidence_ref: str | None = None) -> dict[str, Any]:
    """Apply base routing, except AUDITOR_PASS uses prespecified promotion policy."""
    validate_manifest(task)
    if event != "AUDITOR_PASS":
        return base_transition(task, event, evidence_ref)

    require(task["state"] == "AUDIT_REVIEW", f"INVALID_TRANSITION:{task['state']}:{event}")
    target = "OWNER_GATE" if owner_gate_on_auditor_pass(task) else "DONE"

    out = json.loads(json.dumps(task))
    out["previous_state"] = task["state"]
    out["state"] = target
    out["updated_at"] = utc_now()
    if evidence_ref:
        require(isinstance(evidence_ref, str) and evidence_ref, "EVIDENCE_REF")
        out["evidence_refs"].append(evidence_ref)
    out["next_role"] = next_role_for_state(target)
    out["fail_closed"] = False
    out["next_state"] = target
    validate_manifest(out)
    return out
