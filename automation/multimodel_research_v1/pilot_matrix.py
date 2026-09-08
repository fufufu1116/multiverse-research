from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from automation.multimodel_research_v1.assignment import (
    assignment_sha256,
    validate_assignment,
)
from automation.multimodel_research_v1.capability import (
    capability_policy_sha256,
    validate_capability_policy,
)
from automation.multimodel_research_v1.claude_adapter import (
    render_claude_messages_request,
)
from automation.multimodel_research_v1.execution_prep import (
    live_execution_prep_sha256,
    validate_live_execution_prep,
)
from automation.multimodel_research_v1.fanout import (
    fanout_plan_sha256,
    validate_fanout_plan,
)
from automation.multimodel_research_v1.gemini_adapter import (
    render_gemini_interactions_v1,
)
from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
    validate_task,
)
from automation.multimodel_research_v1.model_target import (
    model_target_policy_sha256,
    validate_model_target_policy,
)
from automation.multimodel_research_v1.prompting import (
    build_provider_neutral_prompt,
    provider_neutral_prompt_sha256,
)
from automation.multimodel_research_v1.provider_catalog import (
    catalog_entry,
    catalog_entry_sha256,
    validate_first_smoke_candidate,
    validate_provider_catalog,
)
from automation.multimodel_research_v1.readiness import (
    build_live_provider_readiness_report,
    validate_live_provider_readiness_report,
)
from automation.multimodel_research_v1.request_envelope import (
    request_envelope_sha256,
    validate_request_envelope,
)
from automation.multimodel_research_v1.smoke_profile import (
    live_smoke_profile_sha256,
    validate_live_smoke_profile,
)
from automation.multimodel_research_v1.transport_binding import (
    transport_binding_sha256,
    validate_transport_binding,
)

PILOT_MATRIX_SCHEMA = "MULTIVERSE_PROVIDER_PILOT_MATRIX_v1"

PROVIDER_MAP = {
    "GOOGLE_GEMINI": {
        "assignment_provider": "google-gemini",
        "adapter_file": "gemini_adapter.py",
        "transport_policy_ref": "gemini-interactions-v1-stable",
        "credential_handle_ref": "credential-handle-gemini-smoke",
        "allowed_host": "generativelanguage.googleapis.com",
        "allowed_operation": "INTERACTIONS_CREATE_V1",
    },
    "ANTHROPIC_CLAUDE": {
        "assignment_provider": "anthropic-claude",
        "adapter_file": "claude_adapter.py",
        "transport_policy_ref": "claude-messages-v1",
        "credential_handle_ref": "credential-handle-claude-smoke",
        "allowed_host": "api.anthropic.com",
        "allowed_operation": "MESSAGES_CREATE_V1",
    },
}

MATRIX_KEYS = {
    "schema",
    "provider",
    "catalog_entry_sha256",
    "adapter_source_sha256",
    "assignment",
    "fanout_plan",
    "model_target_policy",
    "capability_policy",
    "prompt",
    "render",
    "request_envelope",
    "smoke_profile",
    "execution_prep",
    "readiness_report",
}


def _adapter_source_sha256(provider: str) -> str:
    require(provider in PROVIDER_MAP, "PILOT_PROVIDER")
    path = Path(__file__).with_name(
        PROVIDER_MAP[provider]["adapter_file"]
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render(
    provider: str,
    task: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    if provider == "GOOGLE_GEMINI":
        return render_gemini_interactions_v1(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            response_schema,
        )
    if provider == "ANTHROPIC_CLAUDE":
        return render_claude_messages_request(
            task,
            assignment,
            model_target_policy,
            capability_policy,
            prompt,
            response_schema,
        )
    raise RuntimeError("PILOT_PROVIDER")


def build_provider_pilot_matrix(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    provider: str,
    response_schema: dict[str, Any],
    *,
    requested_role: str = "architecture_challenge",
) -> dict[str, Any]:
    validate_task(task)
    validate_provider_catalog(catalog_snapshot)
    require(provider in PROVIDER_MAP, "PILOT_PROVIDER")
    require(
        requested_role in task["requested_roles"],
        "PILOT_ROLE_NOT_REQUESTED",
    )
    require(
        isinstance(response_schema, dict)
        and bool(response_schema),
        "PILOT_RESPONSE_SCHEMA",
    )

    catalog_candidate = validate_first_smoke_candidate(
        catalog_snapshot,
        provider,
    )
    entry = catalog_entry(catalog_snapshot, provider)
    spec = PROVIDER_MAP[provider]
    created_at = catalog_snapshot["observed_at"]
    adapter_digest = _adapter_source_sha256(provider)

    assignment = {
        "schema": "MULTIVERSE_RESEARCH_ASSIGNMENT_v1",
        "assignment_id": f"pilot-{provider.lower()}-001",
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "created_at": created_at,
        "target_provider": spec["assignment_provider"],
        "target_model": entry["model_id"],
        "requested_role": requested_role,
        "adapter_sha256": adapter_digest,
        "execution_mode": "LIVE_ADVISORY",
        "research_network_access": "NONE",
        "provider_transport_policy_ref":
            spec["transport_policy_ref"],
        "max_compute_seconds": min(
            120,
            task["constraints"]["max_compute_seconds"],
        ),
        "max_output_bytes": min(
            50000,
            task["constraints"]["max_output_bytes"],
        ),
        "attestation_required": True,
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_assignment(task, assignment)

    assignments = [assignment]
    fanout_plan = {
        "schema": "MULTIVERSE_RESEARCH_FANOUT_PLAN_v1",
        "plan_id": f"pilot-fanout-{provider.lower()}-001",
        "task_sha256": sha256_json(task),
        "snapshot_id": task["snapshot_id"],
        "created_at": created_at,
        "assignment_sha256s": [
            assignment_sha256(task, assignment)
        ],
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_fanout_plan(task, assignments, fanout_plan)

    target_policy = {
        "schema": "MULTIVERSE_MODEL_TARGET_POLICY_v1",
        "policy_id": f"pilot-model-target-{provider.lower()}-001",
        "assignment_sha256":
            assignment_sha256(task, assignment),
        "provider": assignment["target_provider"],
        "requested_model_id": assignment["target_model"],
        "model_id_classification":
            entry["classification"],
        "classification_evidence_ref":
            f"{catalog_snapshot['snapshot_id']}:{provider}",
        "classification_evidence_sha256":
            catalog_entry_sha256(
                catalog_snapshot,
                provider,
            ),
        "alias_allowed": False,
        "preview_allowed": False,
        "experimental_allowed": False,
        "resolved_model_id_required": True,
        "stable_provider_api_required": True,
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_model_target_policy(
        task,
        assignment,
        target_policy,
    )

    capability_policy = {
        "schema":
            "MULTIVERSE_PROVIDER_CAPABILITY_POLICY_v1",
        "policy_id":
            f"pilot-capability-{provider.lower()}-001",
        "assignment_sha256":
            assignment_sha256(task, assignment),
        "model_target_policy_sha256":
            model_target_policy_sha256(
                task,
                assignment,
                target_policy,
            ),
        "tools": "NONE",
        "provider_retrieval_search": "NONE",
        "code_execution": "NONE",
        "file_access": "NONE",
        "provider_memory": "NONE",
        "function_calling": "NONE",
        "structured_output": "JSON_ONLY",
        "streaming": False,
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_capability_policy(
        task,
        assignment,
        target_policy,
        capability_policy,
    )

    prompt = build_provider_neutral_prompt(
        task,
        requested_role,
        sha256_json(response_schema),
    )

    render = _render(
        provider,
        task,
        assignment,
        target_policy,
        capability_policy,
        prompt,
        response_schema,
    )

    envelope = {
        "schema": "MULTIVERSE_PROVIDER_REQUEST_ENVELOPE_v1",
        "request_id": f"pilot-request-{provider.lower()}-001",
        "task_sha256": sha256_json(task),
        "assignment_sha256":
            assignment_sha256(task, assignment),
        "model_target_policy_sha256":
            model_target_policy_sha256(
                task,
                assignment,
                target_policy,
            ),
        "capability_policy_sha256":
            capability_policy_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
            ),
        "provider_neutral_prompt_sha256":
            provider_neutral_prompt_sha256(
                task,
                prompt,
            ),
        "provider_transport_policy_ref":
            assignment["provider_transport_policy_ref"],
        "created_at": created_at,
        "objective_classification": "SYNTHETIC",
        "classification_evidence_ref":
            f"synthetic-task:{task['task_id']}",
        "classification_evidence_sha256":
            sha256_json(task["evidence_manifest"]),
        "egress_items": sorted(
            [
                {
                    "primitive": item["primitive"],
                    "ref": item["ref"],
                    "sha256": item["sha256"],
                    "classification": "SYNTHETIC",
                }
                for item in task["evidence_manifest"]
            ],
            key=lambda item: (
                item["primitive"],
                item["ref"],
                item["sha256"],
            ),
        ),
        "outbound_payload_sha256":
            sha256_json(render["body"]),
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_request_envelope(
        task,
        assignment,
        target_policy,
        capability_policy,
        prompt,
        envelope,
    )
    validate_transport_binding(
        task,
        assignment,
        target_policy,
        capability_policy,
        prompt,
        envelope,
        response_schema,
        render,
    )

    smoke = {
        "schema": "MULTIVERSE_LIVE_PROVIDER_SMOKE_PROFILE_v1",
        "profile_id": f"pilot-smoke-{provider.lower()}-001",
        "fanout_plan_sha256":
            fanout_plan_sha256(
                task,
                assignments,
                fanout_plan,
            ),
        "assignment_sha256":
            assignment_sha256(task, assignment),
        "model_target_policy_sha256":
            model_target_policy_sha256(
                task,
                assignment,
                target_policy,
            ),
        "capability_policy_sha256":
            capability_policy_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
            ),
        "request_envelope_sha256":
            request_envelope_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
                prompt,
                envelope,
            ),
        "planned_provider_count": 1,
        "planned_assignment_count": 1,
        "max_attempts_per_assignment": 1,
        "data_ceiling": "SYNTHETIC_ONLY",
        "structured_output": "JSON_ONLY",
        "streaming": False,
        "protected_data": False,
        "live_business_effect": False,
        "runtime_activation": False,
        "adoption_authority": False,
        "nonauthority": dict(task["nonauthority"]),
    }
    validate_live_smoke_profile(
        task,
        assignments,
        fanout_plan,
        assignment,
        target_policy,
        capability_policy,
        prompt,
        envelope,
        smoke,
    )

    prep = {
        "schema": "MULTIVERSE_LIVE_PROVIDER_EXECUTION_PREP_v1",
        "prep_id": f"pilot-prep-{provider.lower()}-001",
        "provider": provider,
        "smoke_profile_sha256":
            live_smoke_profile_sha256(
                task,
                assignments,
                fanout_plan,
                assignment,
                target_policy,
                capability_policy,
                prompt,
                envelope,
                smoke,
            ),
        "transport_binding_sha256":
            transport_binding_sha256(
                task,
                assignment,
                target_policy,
                capability_policy,
                prompt,
                envelope,
                response_schema,
                render,
            ),
        "allowed_host": spec["allowed_host"],
        "allowed_operation": spec["allowed_operation"],
        "network_scope": "PROVIDER_API_ONLY",
        "credential_handle_ref":
            spec["credential_handle_ref"],
        "credential_material_in_repository": False,
        "max_attempts": 1,
        "max_input_tokens": 32768,
        "max_output_tokens": 4096,
        "proposed_max_cost_usd_micros":
            catalog_candidate[
                "estimated_max_cost_usd_micros"
            ],
        "provider_call_authority_required": True,
        "credential_authority_required": True,
        "spend_authority_required": True,
        "runtime_activation": False,
        "live_business_effect": False,
        "protected_data": False,
    }
    validate_live_execution_prep(
        task=task,
        assignments=assignments,
        fanout_plan=fanout_plan,
        assignment=assignment,
        model_target_policy=target_policy,
        capability_policy=capability_policy,
        prompt=prompt,
        request_envelope=envelope,
        smoke_profile=smoke,
        response_schema=response_schema,
        render=render,
        prep=prep,
    )

    readiness = build_live_provider_readiness_report(
        task=task,
        assignments=assignments,
        fanout_plan=fanout_plan,
        assignment=assignment,
        model_target_policy=target_policy,
        capability_policy=capability_policy,
        prompt=prompt,
        request_envelope=envelope,
        smoke_profile=smoke,
        response_schema=response_schema,
        render=render,
        execution_prep=prep,
    )
    validate_live_provider_readiness_report(readiness)

    matrix = {
        "schema": PILOT_MATRIX_SCHEMA,
        "provider": provider,
        "catalog_entry_sha256":
            catalog_entry_sha256(
                catalog_snapshot,
                provider,
            ),
        "adapter_source_sha256": adapter_digest,
        "assignment": assignment,
        "fanout_plan": fanout_plan,
        "model_target_policy": target_policy,
        "capability_policy": capability_policy,
        "prompt": prompt,
        "render": render,
        "request_envelope": envelope,
        "smoke_profile": smoke,
        "execution_prep": prep,
        "readiness_report": readiness,
    }
    require(
        set(matrix) == MATRIX_KEYS,
        "PILOT_MATRIX_SCHEMA_KEYS",
    )
    return matrix


def validate_provider_pilot_matrix(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    matrix: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(matrix, dict)
        and set(matrix) == MATRIX_KEYS,
        "PILOT_MATRIX_SCHEMA_KEYS",
    )
    require(
        matrix["schema"] == PILOT_MATRIX_SCHEMA,
        "PILOT_MATRIX_SCHEMA_VERSION",
    )
    expected = build_provider_pilot_matrix(
        task,
        catalog_snapshot,
        matrix["provider"],
        response_schema,
        requested_role=
            matrix["assignment"]["requested_role"],
    )
    require(
        matrix == expected,
        "PILOT_MATRIX_EXACT_MISMATCH",
    )
    return matrix


def provider_pilot_matrix_sha256(
    task: dict[str, Any],
    catalog_snapshot: dict[str, Any],
    response_schema: dict[str, Any],
    matrix: dict[str, Any],
) -> str:
    validate_provider_pilot_matrix(
        task,
        catalog_snapshot,
        response_schema,
        matrix,
    )
    return sha256_json(matrix)
