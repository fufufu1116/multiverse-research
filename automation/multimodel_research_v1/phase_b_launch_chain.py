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
from automation.multimodel_research_v1.launch_generation import (
    current_canonical_launch_generation_sha256,
    validate_current_canonical_launch_generation,
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
from automation.multimodel_research_v1.pilot_roundtrip_v2 import (
    build_provider_pilot_roundtrip_v2,
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

PHASE_B_LAUNCH_CHAIN_SCHEMA = (
    "MULTIVERSE_PHASE_B_CURRENT_CANONICAL_LAUNCH_CHAIN_v1"
)

PROVIDERS = (
    "GOOGLE_GEMINI",
    "ANTHROPIC_CLAUDE",
)

PROVIDER_RECORD_KEYS = {
    "provider",
    "model_id",
    "launch_generation_sha256",
    "catalog_snapshot_sha256",
    "catalog_freshness_sha256",
    "pilot_dry_run_sha256",
    "pilot_freshness_binding_sha256",
    "time_attestation_sha256",
    "freshness_time_binding_sha256",
    "pre_execution_bundle_sha256",
    "pilot_matrix_sha256",
    "provider_launch_evidence_sha256",
    "pilot_roundtrip_v1_sha256",
    "pilot_roundtrip_v2_sha256",
    "rehearsal_convergence_sha256",
    "prelive_candidate_head",
    "predecessor_candidate_seal_blob",
    "checked_at",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_provider_execution",
    "adoption_authority",
    "runtime",
}

CHAIN_KEYS = {
    "schema",
    "chain_id",
    "launch_generation_sha256",
    "canonical_main",
    "canonical_tree",
    "canonical_multimodel_subtree",
    "reviewed_pr",
    "reviewed_test_count",
    "predecessor_candidate_seal_blob",
    "provider_catalog_snapshot_id",
    "provider_catalog_snapshot_sha256",
    "checked_at",
    "providers",
    "dual_provider_fanout_sha256",
    "dual_provider_research_sha256",
    "full_path_rebound_to_launch_generation",
    "fresh_catalog_bound",
    "historical_seal_predecessor_only",
    "repository_evidence_aligned",
    "synthetic_only",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_provider_execution",
    "protected_data_effect",
    "live_business_effect",
    "adoption_authority",
    "runtime",
}


def _time_attestation(
    generation: dict[str, Any],
    generation_sha256: str,
    provider: str,
) -> dict[str, Any]:
    provider_slug = (
        "google-gemini"
        if provider == "GOOGLE_GEMINI"
        else "anthropic-claude"
    )
    return {
        "schema": "MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1",
        "attestation_id":
            f"phase-b-current-launch-time-{provider_slug}-001",
        "source": "CONTROL_RUNTIME_CLOCK",
        "source_ref":
            f"phase-b-current-launch-generation-{provider_slug}",
        "source_observation_sha256": generation_sha256,
        "attested_at": generation["checked_at"],
        "recorded_at": generation["recorded_at"],
        "prelive_candidate_head": generation["canonical_main"],
        "prelive_candidate_seal_blob":
            generation["predecessor_candidate_seal_blob"],
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
    }


def _provider_chain(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    generation: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    generation_sha = current_canonical_launch_generation_sha256(
        snapshot,
        generation,
    )
    plan = build_first_provider_pilot_dry_run(
        snapshot,
        provider,
        prelive_candidate_head=generation["canonical_main"],
        prelive_candidate_seal_blob=
            generation["predecessor_candidate_seal_blob"],
    )
    freshness = build_catalog_freshness_receipt(
        snapshot,
        checked_at=generation["checked_at"],
    )
    pilot_binding = build_pilot_freshness_binding(
        snapshot,
        plan,
        freshness,
    )
    attestation = _time_attestation(
        generation,
        generation_sha,
        provider,
    )
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
    roundtrip_v1 = build_provider_pilot_roundtrip(
        task,
        snapshot,
        provider,
        response_schema,
    )
    roundtrip_v2 = build_provider_pilot_roundtrip_v2(
        task,
        snapshot,
        provider,
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
        roundtrip_v1,
    )

    require(
        plan["catalog_snapshot_sha256"]
        == bundle["catalog_snapshot_sha256"]
        == sha256_json(snapshot),
        "PHASE_B_CHAIN_CATALOG_GENERATION_MISMATCH",
    )
    require(
        plan["prelive_candidate_head"]
        == bundle["prelive_candidate_head"]
        == launch["prelive_candidate_head"]
        == rehearsal["prelive_candidate_head"]
        == generation["canonical_main"],
        "PHASE_B_CHAIN_MAIN_BINDING_MISMATCH",
    )
    require(
        plan["prelive_candidate_seal_blob"]
        == bundle["prelive_candidate_seal_blob"]
        == launch["prelive_candidate_seal_blob"]
        == rehearsal["prelive_candidate_seal_blob"]
        == generation["predecessor_candidate_seal_blob"],
        "PHASE_B_CHAIN_PREDECESSOR_SEAL_MISMATCH",
    )
    require(
        freshness["checked_at"]
        == time_binding["checked_at"]
        == bundle["checked_at"]
        == launch["checked_at"]
        == rehearsal["checked_at"]
        == generation["checked_at"],
        "PHASE_B_CHAIN_CHECKED_AT_MISMATCH",
    )
    require(
        roundtrip_v1["model_id"]
        == roundtrip_v2["model_id"]
        == launch["model_id"]
        == plan["model_id"],
        "PHASE_B_CHAIN_MODEL_GENERATION_MISMATCH",
    )

    record = {
        "provider": provider,
        "model_id": plan["model_id"],
        "launch_generation_sha256": generation_sha,
        "catalog_snapshot_sha256": sha256_json(snapshot),
        "catalog_freshness_sha256": sha256_json(freshness),
        "pilot_dry_run_sha256": sha256_json(plan),
        "pilot_freshness_binding_sha256": sha256_json(pilot_binding),
        "time_attestation_sha256": sha256_json(attestation),
        "freshness_time_binding_sha256": sha256_json(time_binding),
        "pre_execution_bundle_sha256": sha256_json(bundle),
        "pilot_matrix_sha256": sha256_json(matrix),
        "provider_launch_evidence_sha256": sha256_json(launch),
        "pilot_roundtrip_v1_sha256": sha256_json(roundtrip_v1),
        "pilot_roundtrip_v2_sha256": sha256_json(roundtrip_v2),
        "rehearsal_convergence_sha256": sha256_json(rehearsal),
        "prelive_candidate_head": generation["canonical_main"],
        "predecessor_candidate_seal_blob":
            generation["predecessor_candidate_seal_blob"],
        "checked_at": generation["checked_at"],
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }
    require(
        set(record) == PROVIDER_RECORD_KEYS,
        "PHASE_B_PROVIDER_CHAIN_SCHEMA_KEYS",
    )
    return record


def _build_unchecked(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    validate_current_canonical_launch_generation(
        snapshot,
        generation,
    )
    generation_sha = current_canonical_launch_generation_sha256(
        snapshot,
        generation,
    )
    providers = [
        _provider_chain(
            task,
            snapshot,
            response_schema,
            generation,
            provider,
        )
        for provider in PROVIDERS
    ]
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
    return {
        "schema": PHASE_B_LAUNCH_CHAIN_SCHEMA,
        "chain_id":
            "phase-b-current-canonical-launch-chain-20260910-001",
        "launch_generation_sha256": generation_sha,
        "canonical_main": generation["canonical_main"],
        "canonical_tree": generation["canonical_tree"],
        "canonical_multimodel_subtree":
            generation["canonical_multimodel_subtree"],
        "reviewed_pr": generation["reviewed_pr"],
        "reviewed_test_count": generation["reviewed_test_count"],
        "predecessor_candidate_seal_blob":
            generation["predecessor_candidate_seal_blob"],
        "provider_catalog_snapshot_id":
            generation["provider_catalog_snapshot_id"],
        "provider_catalog_snapshot_sha256": sha256_json(snapshot),
        "checked_at": generation["checked_at"],
        "providers": providers,
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
        "full_path_rebound_to_launch_generation": True,
        "fresh_catalog_bound": True,
        "historical_seal_predecessor_only": True,
        "repository_evidence_aligned": True,
        "synthetic_only": True,
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_provider_execution": False,
        "protected_data_effect": False,
        "live_business_effect": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


def build_phase_b_current_canonical_launch_chain(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    record = _build_unchecked(
        task,
        snapshot,
        response_schema,
        generation,
    )
    return validate_phase_b_current_canonical_launch_chain(
        task,
        snapshot,
        response_schema,
        generation,
        record,
    )


def validate_phase_b_current_canonical_launch_chain(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    generation: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    validate_current_canonical_launch_generation(
        snapshot,
        generation,
    )
    require(
        isinstance(record, dict)
        and set(record) == CHAIN_KEYS,
        "PHASE_B_LAUNCH_CHAIN_SCHEMA_KEYS",
    )
    require(
        record["schema"] == PHASE_B_LAUNCH_CHAIN_SCHEMA,
        "PHASE_B_LAUNCH_CHAIN_SCHEMA_VERSION",
    )
    expected = _build_unchecked(
        task,
        snapshot,
        response_schema,
        generation,
    )
    require(
        record == expected,
        "PHASE_B_LAUNCH_CHAIN_EXACT_MISMATCH",
    )
    require(
        len(record["providers"]) == 2
        and {
            item["provider"]
            for item in record["providers"]
        } == set(PROVIDERS),
        "PHASE_B_LAUNCH_CHAIN_PROVIDER_SET",
    )
    for item in record["providers"]:
        require(
            item["launch_generation_sha256"]
            == record["launch_generation_sha256"],
            "PHASE_B_CHAIN_PROVIDER_GENERATION_MISMATCH",
        )
        require(
            item["catalog_snapshot_sha256"]
            == record["provider_catalog_snapshot_sha256"],
            "PHASE_B_CHAIN_PROVIDER_CATALOG_MISMATCH",
        )
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "live_provider_execution",
            "adoption_authority",
        ):
            require(
                item[key] is False,
                f"PHASE_B_PROVIDER_CHAIN_FORBIDDEN_TRUE:{key}",
            )
        require(
            item["runtime"] == "OFF",
            "PHASE_B_PROVIDER_CHAIN_RUNTIME_NOT_OFF",
        )

    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_provider_execution",
        "protected_data_effect",
        "live_business_effect",
        "adoption_authority",
    ):
        require(
            record[key] is False,
            f"PHASE_B_LAUNCH_CHAIN_FORBIDDEN_TRUE:{key}",
        )
    require(
        record["runtime"] == "OFF",
        "PHASE_B_LAUNCH_CHAIN_RUNTIME_NOT_OFF",
    )
    return record


def phase_b_current_canonical_launch_chain_sha256(
    task: dict[str, Any],
    snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    generation: dict[str, Any],
    record: dict[str, Any],
) -> str:
    validate_phase_b_current_canonical_launch_chain(
        task,
        snapshot,
        response_schema,
        generation,
        record,
    )
    return sha256_json(record)
