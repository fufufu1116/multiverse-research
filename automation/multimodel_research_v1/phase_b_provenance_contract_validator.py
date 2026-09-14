from __future__ import annotations

import copy
import json
from pathlib import Path

from automation.multimodel_research_v1.model import sha256_json
from automation.multimodel_research_v1.phase_b_provenance_contract import (
    ASSIGNMENT_SCHEMA,
    RECEIPT_SCHEMA,
    RESULT_SCHEMA_V2,
    receipt_authenticates_external_provider,
    validate_assignment,
    validate_execution_receipt,
    validate_result_v2,
)

ROOT = Path(__file__).resolve().parent

NONAUTHORITY = {
    "adoption": False,
    "merge": False,
    "main_mutation": False,
    "ruleset_mutation": False,
    "workflow_dispatch_rerun": False,
    "runtime_activation": False,
    "provider_effect": False,
    "production": False,
    "protected_data": False,
    "live_business_effect": False,
    "spend": False,
}


def _fixture() -> tuple[dict, dict, dict, dict]:
    task = {
        "schema": "MULTIVERSE_RESEARCH_TASK_v2",
        "task_id": "task-provenance-validator-001",
        "snapshot_id": "snapshot-provenance-validator-001",
        "created_at": "2026-09-15T00:00:00Z",
        "domain": "MULTIMODEL_RESEARCH",
        "objective": "Repository-only provenance validator fixture.",
        "source_refs": [{
            "kind": "PUBLIC_DOC",
            "ref": "https://example.invalid/evidence",
            "sha256": "1" * 64,
            "observed_at": "2026-09-14T23:59:00Z",
        }],
        "allowed_primitives": ["PUBLIC_EVIDENCE_REF"],
        "constraints": {
            "network_access": "PUBLIC_READ_ONLY",
            "max_compute_seconds": 120,
            "max_output_bytes": 100000,
            "max_findings": 8,
        },
        "requested_roles": ["RESEARCHER"],
        "nonauthority": copy.deepcopy(NONAUTHORITY),
        "evidence_manifest": [{
            "primitive": "PUBLIC_EVIDENCE_REF",
            "ref": "https://example.invalid/evidence",
            "sha256": "1" * 64,
            "observed_at": "2026-09-14T23:59:00Z",
        }],
    }
    assignment = {
        "schema": ASSIGNMENT_SCHEMA,
        "assignment_id": "assignment-provenance-validator-001",
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "target": {"provider": "SYNTHETIC_PROVIDER", "model": "synthetic-model"},
        "requested_role": "RESEARCHER",
        "adapter_sha256": "2" * 64,
        "execution_mode": "SYNTHETIC_OFFLINE",
        "research_network_access": "NONE",
        "provider_transport": "DISABLED",
        "limits": {"max_compute_seconds": 60, "max_output_bytes": 50000},
        "attestation_required": False,
        "nonauthority": copy.deepcopy(NONAUTHORITY),
    }
    result = {
        "schema": RESULT_SCHEMA_V2,
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "assignment_sha256": sha256_json(assignment),
        "submission_id": "submission-provenance-validator-001",
        "snapshot_id": task["snapshot_id"],
        "produced_at": "2026-09-15T00:02:00Z",
        "model_identity": {"provider": "SYNTHETIC_PROVIDER", "model": "synthetic-model", "role": "RESEARCHER"},
        "status": "COMPLETED",
        "findings": [{
            "finding_id": "finding-provenance-validator-001",
            "claim_key": "claim-provenance-validator-001",
            "position": "SUPPORT",
            "severity": "INFO",
            "assertion": "Exact assignment provenance is preserved.",
            "evidence": {"primitive": "PUBLIC_EVIDENCE_REF", "ref": "https://example.invalid/evidence", "sha256": "1" * 64},
            "confidence": 0.8,
            "uncertainty": "Synthetic only.",
            "recommendation": "Keep authority separate.",
            "validation_plan": "Run repository-only tests.",
        }],
        "uncertainty_factors": ["synthetic-only"],
        "nonauthority": copy.deepcopy(NONAUTHORITY),
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "task_id": task["task_id"],
        "task_sha256": sha256_json(task),
        "assignment_sha256": sha256_json(assignment),
        "submission_id": result["submission_id"],
        "adapter_sha256": assignment["adapter_sha256"],
        "execution_mode": "SYNTHETIC_OFFLINE",
        "request_started_at": "2026-09-15T00:01:00Z",
        "response_received_at": "2026-09-15T00:02:00Z",
        "provider_reference_id": None,
        "observed_provider": "SYNTHETIC_PROVIDER",
        "observed_model": "synthetic-model",
        "provider_response_sha256": "3" * 64,
        "result_sha256": sha256_json(result),
        "attestation_state": "SYNTHETIC_OFFLINE",
        "nonauthority": copy.deepcopy(NONAUTHORITY),
    }
    return task, assignment, result, receipt


def validate() -> dict:
    findings: list[str] = []
    checks: dict[str, str] = {}

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks[name] = "PASS" if ok else "FIX_REQUIRED"
        if not ok:
            findings.append(f"{name}:{detail}")

    try:
        task, assignment, result, receipt = _fixture()
        validate_assignment(task, assignment)
        validate_result_v2(task, assignment, result)
        validate_execution_receipt(task, assignment, result, receipt)
        record("synthetic_chain", True)
        record("synthetic_not_external_attested", not receipt_authenticates_external_provider(receipt))
        record("all_nonauthority_false", all(v is False for v in assignment["nonauthority"].values()) and all(v is False for v in result["nonauthority"].values()) and all(v is False for v in receipt["nonauthority"].values()))
    except Exception as exc:
        record("synthetic_chain", False, repr(exc))

    source = (ROOT / "phase_b_provenance_contract.py").read_text().lower()
    for marker in ("requests.", "httpx.", "aiohttp.", "urllib.request", ".interactions.create(", ".messages.create("):
        record(f"no_provider_execution:{marker}", marker not in source, marker)

    return {
        "schema": "MULTIVERSE_PHASE_B_PROVENANCE_CONTRACT_VALIDATOR_v1",
        "verdict": "PASS" if not findings else "FIX_REQUIRED",
        "findings": findings,
        "checks": checks,
        "provider_call_authorized": False,
        "provider_credentials": False,
        "spend_authorized": False,
        "live_effect": False,
        "runtime": "OFF",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
