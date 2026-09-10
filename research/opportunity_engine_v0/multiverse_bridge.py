from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS, validate_task

BRIDGE_SCHEMA = "MULTIVERSE_OPPORTUNITY_REVIEW_PACKET_v1"
DEFAULT_ROLES = (
    "competitor_challenge",
    "economics_challenge",
    "execution_risk_challenge",
)


class OpportunityBridgeError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _utc_z(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpportunityBridgeError("timestamp is required")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as exc:
        raise OpportunityBridgeError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OpportunityBridgeError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _nonauthority() -> dict[str, bool]:
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def _bounded_case_summary(case: dict[str, Any]) -> str:
    summary = canonical_json(case)
    if len(summary) > 12000:
        raise OpportunityBridgeError("opportunity case is too large for bounded review task")
    return summary


def _validate_roles(roles: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(roles)
    if not normalized or len(normalized) > 16:
        raise OpportunityBridgeError("requested roles must contain 1-16 entries")
    if len(set(normalized)) != len(normalized):
        raise OpportunityBridgeError("requested roles must be unique")
    for role in normalized:
        if not isinstance(role, str) or not role.strip():
            raise OpportunityBridgeError("requested role must be non-empty text")
    return normalized


def build_multiverse_review_packet(
    *,
    opportunity_case: dict[str, Any],
    case_ref: str,
    task_id: str,
    snapshot_id: str,
    created_at: str,
    observed_at: str | None = None,
    requested_roles: Iterable[str] = DEFAULT_ROLES,
) -> dict[str, Any]:
    """Freeze one opportunity case into the existing MULTIVERSE research-task contract.

    This bridge does not execute providers or grant authority. It creates a bounded,
    hash-bound review packet that existing MULTIVERSE Core/Vault/Lab/Auditor flows
    can consume later under their own governance.
    """
    if not isinstance(opportunity_case, dict):
        raise OpportunityBridgeError("opportunity_case must be an object")
    if not isinstance(case_ref, str) or not case_ref.strip():
        raise OpportunityBridgeError("case_ref is required")

    frozen_case = copy.deepcopy(opportunity_case)
    case_id = frozen_case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise OpportunityBridgeError("opportunity case requires case_id")

    created_utc = _utc_z(created_at)
    observed_utc = _utc_z(observed_at or created_at)
    if observed_utc > created_utc:
        raise OpportunityBridgeError("observed_at cannot be after created_at")

    roles = _validate_roles(requested_roles)
    case_sha256 = sha256_json(frozen_case)
    summary = _bounded_case_summary(frozen_case)
    objective = (
        "Independently challenge this frozen Opportunity Engine case. "
        "Do not assume its provisional verdict is correct. Attack competitor coverage, "
        "general-AI/incumbent substitution, payer clarity, low/base/high economics, "
        "demand lifetime, leverage assumptions, owner burden, copy exposure, legal/safety "
        "risk, kill conditions, and whether a simpler existing-service solution dominates. "
        "Return evidence-grounded findings only; this task has no adoption, execution, "
        "spend, publication, provider-effect, or Runtime authority.\n\n"
        f"FROZEN_OPPORTUNITY_CASE_SHA256={case_sha256}\n"
        f"FROZEN_OPPORTUNITY_CASE={summary}"
    )

    source_ref = {
        "kind": "OPPORTUNITY_CASE",
        "ref": case_ref.strip(),
        "sha256": case_sha256,
        "observed_at": observed_utc,
    }
    task = {
        "schema": "MULTIVERSE_RESEARCH_TASK_v2",
        "task_id": task_id,
        "snapshot_id": snapshot_id,
        "created_at": created_utc,
        "domain": "opportunity_engine",
        "objective": objective,
        "source_refs": [source_ref],
        "allowed_primitives": ["SOURCE_REF"],
        "constraints": {
            "network_access": "NONE",
            "max_compute_seconds": 180,
            "max_output_bytes": 100000,
            "max_findings": 12,
        },
        "requested_roles": list(roles),
        "nonauthority": _nonauthority(),
        "evidence_manifest": [
            {
                "primitive": "SOURCE_REF",
                "ref": case_ref.strip(),
                "sha256": case_sha256,
                "observed_at": observed_utc,
            }
        ],
    }

    validated_task = validate_task(task)
    packet = {
        "schema": BRIDGE_SCHEMA,
        "case_id": case_id,
        "case_ref": case_ref.strip(),
        "opportunity_case": frozen_case,
        "opportunity_case_sha256": case_sha256,
        "research_task": validated_task,
        "bridge_authority": _nonauthority(),
    }
    packet["packet_sha256"] = sha256_json(packet)
    return packet


def validate_multiverse_review_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "case_id",
        "case_ref",
        "opportunity_case",
        "opportunity_case_sha256",
        "research_task",
        "bridge_authority",
        "packet_sha256",
    }
    if not isinstance(packet, dict) or set(packet) != required:
        raise OpportunityBridgeError("bridge packet schema mismatch")
    if packet["schema"] != BRIDGE_SCHEMA:
        raise OpportunityBridgeError("bridge packet version mismatch")
    if sha256_json(packet["opportunity_case"]) != packet["opportunity_case_sha256"]:
        raise OpportunityBridgeError("opportunity case hash mismatch")
    if packet["case_id"] != packet["opportunity_case"].get("case_id"):
        raise OpportunityBridgeError("case_id mismatch")
    if packet["bridge_authority"] != _nonauthority():
        raise OpportunityBridgeError("bridge cannot grant authority")

    validate_task(packet["research_task"])
    task_ref = packet["research_task"]["source_refs"][0]
    if task_ref["ref"] != packet["case_ref"]:
        raise OpportunityBridgeError("task source ref mismatch")
    if task_ref["sha256"] != packet["opportunity_case_sha256"]:
        raise OpportunityBridgeError("task source hash mismatch")

    expected_packet_hash = packet["packet_sha256"]
    unsigned = dict(packet)
    del unsigned["packet_sha256"]
    if sha256_json(unsigned) != expected_packet_hash:
        raise OpportunityBridgeError("bridge packet hash mismatch")
    return packet
