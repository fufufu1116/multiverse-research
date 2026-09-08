from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
    build_pilot_freshness_binding,
)
from automation.multimodel_research_v1.dual_provider_fanout import (
    build_dual_provider_fanout_rehearsal,
    dual_provider_fanout_rehearsal_sha256,
)
from automation.multimodel_research_v1.dual_provider_research import (
    build_dual_provider_offline_research,
    dual_provider_offline_research_sha256,
)
from automation.multimodel_research_v1.launch_evidence import (
    build_provider_launch_evidence,
)
from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.pilot_dry_run import (
    build_first_provider_pilot_dry_run,
)
from automation.multimodel_research_v1.pilot_matrix import (
    build_provider_pilot_matrix,
)
from automation.multimodel_research_v1.pilot_roundtrip import (
    build_provider_pilot_roundtrip,
)
from automation.multimodel_research_v1.pre_execution_bundle import (
    build_provider_pre_execution_bundle,
)
from automation.multimodel_research_v1.rehearsal_convergence import (
    build_provider_rehearsal_convergence,
)
from automation.multimodel_research_v1.time_attestation import (
    build_catalog_freshness_time_binding,
)

FEDERATION_SCHEMA = "MULTIVERSE_DUAL_PROVIDER_FEDERATION_REHEARSAL_v1"

PRELIVE_HEAD = "d354bfa274b1f6a4ba116fbfa27356ce01979677"
PRELIVE_SEAL_BLOB = "89d17c2978749da8bd4e146c06ed16ce0fa8730e"
CHECKED_AT = "2026-09-08T11:30:00Z"

FEDERATION_KEYS = {
    "schema",
    "rehearsal_id",
    "provider_count",
    "provider_model_count",
    "prelive_candidate_head",
    "prelive_candidate_seal_blob",
    "checked_at",
    "gemini_model_id",
    "claude_model_id",
    "provider_neutral_prompt_sha256",
    "gemini_matrix_sha256",
    "claude_matrix_sha256",
    "gemini_rehearsal_sha256",
    "claude_rehearsal_sha256",
    "dual_provider_fanout_sha256",
    "dual_provider_research_sha256",
    "full_batch_complete",
    "missing_provider_fails_complete",
    "disagreement_detected",
    "agreement_not_mislabeled_divergent",
    "mechanical_falsification_route_preserved",
    "repository_evidence_aligned",
    "synthetic_only",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_provider_execution",
    "adoption_authority",
    "runtime",
}


def _time_attestation() -> dict[str, Any]:
    return {
        "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
        "attestation_id": "dual-provider-control-time-001",
        "source": "CONTROL_RUNTIME_CLOCK",
        "source_ref": "control-runtime-clock-dual-provider-001",
        "source_observation_sha256": "c" * 64,
        "attested_at": CHECKED_AT,
        "recorded_at": "2026-09-08T11:30:05Z",
        "prelive_candidate_head": PRELIVE_HEAD,
        "prelive_candidate_seal_blob": PRELIVE_SEAL_BLOB,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }


def _provider_rehearsal(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    provider: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = build_first_provider_pilot_dry_run(
        snapshot,
        provider,
        prelive_candidate_head=PRELIVE_HEAD,
        prelive_candidate_seal_blob=PRELIVE_SEAL_BLOB,
    )
    freshness = build_catalog_freshness_receipt(
        snapshot,
        checked_at=CHECKED_AT,
    )
    pilot_binding = build_pilot_freshness_binding(
        snapshot,
        plan,
        freshness,
    )
    attestation = _time_attestation()
    time_binding = build_catalog_freshness_time_binding(
        snapshot,
        freshness,
        attestation,
    )
    bundle = build_provider_pre_execution_bundle(
        snapshot,
        plan,
        freshness,
        pilot_binding,
        attestation,
        time_binding,
    )
    matrix = build_provider_pilot_matrix(
        task,
        snapshot,
        provider,
        response_schema,
    )
    launch = build_provider_launch_evidence(
        task,
        snapshot,
        response_schema,
        matrix,
        plan,
        freshness,
        pilot_binding,
        attestation,
        time_binding,
        bundle,
    )
    roundtrip = build_provider_pilot_roundtrip(
        task,
        snapshot,
        provider,
        response_schema,
    )
    rehearsal = build_provider_rehearsal_convergence(
        task,
        snapshot,
        response_schema,
        matrix,
        plan,
        freshness,
        pilot_binding,
        attestation,
        time_binding,
        bundle,
        launch,
        roundtrip,
    )
    return matrix, rehearsal



def _validate_record_envelope(record: dict[str, Any]) -> None:
    require(
        isinstance(record, dict) and set(record) == FEDERATION_KEYS,
        "FEDERATION_SCHEMA_KEYS",
    )
    require(
        record["schema"] == FEDERATION_SCHEMA,
        "FEDERATION_SCHEMA_VERSION",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_provider_execution",
        "adoption_authority",
    ):
        require(
            record[key] is False,
            f"FEDERATION_FORBIDDEN_TRUE:{key}",
        )
    require(record["runtime"] == "OFF", "FEDERATION_RUNTIME_NOT_OFF")

def build_dual_provider_federation_rehearsal(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    gemini_matrix, gemini_rehearsal = _provider_rehearsal(
        task,
        snapshot,
        response_schema,
        "GOOGLE_GEMINI",
    )
    claude_matrix, claude_rehearsal = _provider_rehearsal(
        task,
        snapshot,
        response_schema,
        "ANTHROPIC_CLAUDE",
    )
    fanout = build_dual_provider_fanout_rehearsal(
        task,
        snapshot,
        response_schema,
    )
    research = build_dual_provider_offline_research(
        task,
        snapshot,
        response_schema,
    )

    require(
        gemini_rehearsal["prelive_candidate_head"]
        == claude_rehearsal["prelive_candidate_head"]
        == PRELIVE_HEAD,
        "FEDERATION_PRELIVE_HEAD_MISMATCH",
    )
    require(
        gemini_rehearsal["prelive_candidate_seal_blob"]
        == claude_rehearsal["prelive_candidate_seal_blob"]
        == PRELIVE_SEAL_BLOB,
        "FEDERATION_PRELIVE_SEAL_MISMATCH",
    )
    require(
        gemini_rehearsal["checked_at"]
        == claude_rehearsal["checked_at"]
        == CHECKED_AT,
        "FEDERATION_CHECKED_AT_MISMATCH",
    )
    require(
        gemini_rehearsal["model_id"]
        == fanout["gemini_model_id"]
        == research["gemini_model_id"],
        "FEDERATION_GEMINI_MODEL_MISMATCH",
    )
    require(
        claude_rehearsal["model_id"]
        == fanout["claude_model_id"]
        == research["claude_model_id"],
        "FEDERATION_CLAUDE_MODEL_MISMATCH",
    )
    require(
        gemini_rehearsal["pilot_matrix_sha256"]
        == fanout["gemini_matrix_sha256"]
        == research["gemini_matrix_sha256"],
        "FEDERATION_GEMINI_MATRIX_MISMATCH",
    )
    require(
        claude_rehearsal["pilot_matrix_sha256"]
        == fanout["claude_matrix_sha256"]
        == research["claude_matrix_sha256"],
        "FEDERATION_CLAUDE_MATRIX_MISMATCH",
    )
    require(
        fanout["provider_neutral_prompt_sha256"]
        == research["provider_neutral_prompt_sha256"],
        "FEDERATION_PROMPT_SHA256_MISMATCH",
    )
    require(
        fanout["full_all_planned_completed"] is True,
        "FEDERATION_FULL_BATCH_NOT_COMPLETE",
    )
    require(
        fanout["missing_demo_all_planned_completed"] is False,
        "FEDERATION_MISSING_PROVIDER_ACCEPTED",
    )
    require(
        research["cross_provider_divergence"] is True,
        "FEDERATION_DISAGREEMENT_NOT_DETECTED",
    )
    require(
        research["agreement_cross_provider_divergence"] is False,
        "FEDERATION_AGREEMENT_MISLABELED",
    )
    require(
        research["required_next_action"]
        == "MECHANICAL_FALSIFICATION_TASK",
        "FEDERATION_FALSIFICATION_ROUTE",
    )

    record = {
        "schema": FEDERATION_SCHEMA,
        "rehearsal_id": "dual-provider-federation-rehearsal-001",
        "provider_count": 2,
        "provider_model_count": 2,
        "prelive_candidate_head": PRELIVE_HEAD,
        "prelive_candidate_seal_blob": PRELIVE_SEAL_BLOB,
        "checked_at": CHECKED_AT,
        "gemini_model_id": gemini_matrix["assignment"]["target_model"],
        "claude_model_id": claude_matrix["assignment"]["target_model"],
        "provider_neutral_prompt_sha256":
            fanout["provider_neutral_prompt_sha256"],
        "gemini_matrix_sha256":
            gemini_rehearsal["pilot_matrix_sha256"],
        "claude_matrix_sha256":
            claude_rehearsal["pilot_matrix_sha256"],
        "provider_neutral_prompt_sha256":
            fanout["provider_neutral_prompt_sha256"],
        "gemini_matrix_sha256":
            gemini_rehearsal["pilot_matrix_sha256"],
        "claude_matrix_sha256":
            claude_rehearsal["pilot_matrix_sha256"],
        "gemini_rehearsal_sha256": sha256_json(gemini_rehearsal),
        "claude_rehearsal_sha256": sha256_json(claude_rehearsal),
        "dual_provider_fanout_sha256":
            dual_provider_fanout_rehearsal_sha256(
                task,
                snapshot,
                response_schema,
                fanout,
            ),
        "dual_provider_research_sha256":
            dual_provider_offline_research_sha256(
                task,
                snapshot,
                response_schema,
                research,
            ),
        "full_batch_complete": True,
        "missing_provider_fails_complete": True,
        "disagreement_detected": True,
        "agreement_not_mislabeled_divergent": True,
        "mechanical_falsification_route_preserved": True,
        "repository_evidence_aligned": True,
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }
    _validate_record_envelope(record)
    return record


def validate_dual_provider_federation_rehearsal(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    _validate_record_envelope(record)
    expected = build_dual_provider_federation_rehearsal_unchecked(
        task,
        snapshot,
        response_schema,
    )
    require(record == expected, "FEDERATION_EXACT_MISMATCH")
    return record


def build_dual_provider_federation_rehearsal_unchecked(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    gemini_matrix, gemini_rehearsal = _provider_rehearsal(
        task, snapshot, response_schema, "GOOGLE_GEMINI"
    )
    claude_matrix, claude_rehearsal = _provider_rehearsal(
        task, snapshot, response_schema, "ANTHROPIC_CLAUDE"
    )
    fanout = build_dual_provider_fanout_rehearsal(
        task, snapshot, response_schema
    )
    research = build_dual_provider_offline_research(
        task, snapshot, response_schema
    )
    return {
        "schema": FEDERATION_SCHEMA,
        "rehearsal_id": "dual-provider-federation-rehearsal-001",
        "provider_count": 2,
        "provider_model_count": 2,
        "prelive_candidate_head": PRELIVE_HEAD,
        "prelive_candidate_seal_blob": PRELIVE_SEAL_BLOB,
        "checked_at": CHECKED_AT,
        "gemini_model_id": gemini_matrix["assignment"]["target_model"],
        "claude_model_id": claude_matrix["assignment"]["target_model"],
        "gemini_rehearsal_sha256": sha256_json(gemini_rehearsal),
        "claude_rehearsal_sha256": sha256_json(claude_rehearsal),
        "dual_provider_fanout_sha256":
            dual_provider_fanout_rehearsal_sha256(
                task, snapshot, response_schema, fanout
            ),
        "dual_provider_research_sha256":
            dual_provider_offline_research_sha256(
                task, snapshot, response_schema, research
            ),
        "full_batch_complete":
            fanout["full_all_planned_completed"],
        "missing_provider_fails_complete":
            not fanout["missing_demo_all_planned_completed"],
        "disagreement_detected":
            research["cross_provider_divergence"],
        "agreement_not_mislabeled_divergent":
            not research["agreement_cross_provider_divergence"],
        "mechanical_falsification_route_preserved":
            research["required_next_action"]
            == "MECHANICAL_FALSIFICATION_TASK",
        "repository_evidence_aligned": True,
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


def dual_provider_federation_rehearsal_sha256(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    record: dict[str, Any],
) -> str:
    validate_dual_provider_federation_rehearsal(
        task,
        snapshot,
        response_schema,
        record,
    )
    return sha256_json(record)
