from __future__ import annotations

from typing import Any

from automation.multimodel_research_v1.execution_prep import (
    live_execution_prep_sha256,
    validate_live_execution_prep,
)
from automation.multimodel_research_v1.model import (
    require,
    sha256_json,
)
from automation.multimodel_research_v1.smoke_profile import (
    live_smoke_profile_sha256,
)
from automation.multimodel_research_v1.transport_binding import (
    transport_binding_sha256,
)

READINESS_SCHEMA = "MULTIVERSE_LIVE_PROVIDER_READINESS_REPORT_v1"

READINESS_KEYS = {
    "schema",
    "provider",
    "readiness_state",
    "repository_contract_ready",
    "smoke_profile_sha256",
    "transport_binding_sha256",
    "execution_prep_sha256",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "runtime",
    "adoption_authority",
}


def build_live_provider_readiness_report(
    *,
    task: dict[str, Any],
    assignments: list[dict[str, Any]],
    fanout_plan: dict[str, Any],
    assignment: dict[str, Any],
    model_target_policy: dict[str, Any],
    capability_policy: dict[str, Any],
    prompt: dict[str, Any],
    request_envelope: dict[str, Any],
    smoke_profile: dict[str, Any],
    response_schema: dict[str, Any],
    render: dict[str, Any],
    execution_prep: dict[str, Any],
) -> dict[str, Any]:
    validate_live_execution_prep(
        task=task,
        assignments=assignments,
        fanout_plan=fanout_plan,
        assignment=assignment,
        model_target_policy=model_target_policy,
        capability_policy=capability_policy,
        prompt=prompt,
        request_envelope=request_envelope,
        smoke_profile=smoke_profile,
        response_schema=response_schema,
        render=render,
        prep=execution_prep,
    )

    report = {
        "schema": READINESS_SCHEMA,
        "provider": execution_prep["provider"],
        "readiness_state":
            "READY_FOR_SEPARATE_PROVIDER_AUTHORITY",
        "repository_contract_ready": True,
        "smoke_profile_sha256":
            live_smoke_profile_sha256(
                task,
                assignments,
                fanout_plan,
                assignment,
                model_target_policy,
                capability_policy,
                prompt,
                request_envelope,
                smoke_profile,
            ),
        "transport_binding_sha256":
            transport_binding_sha256(
                task,
                assignment,
                model_target_policy,
                capability_policy,
                prompt,
                request_envelope,
                response_schema,
                render,
            ),
        "execution_prep_sha256":
            live_execution_prep_sha256(
                task=task,
                assignments=assignments,
                fanout_plan=fanout_plan,
                assignment=assignment,
                model_target_policy=model_target_policy,
                capability_policy=capability_policy,
                prompt=prompt,
                request_envelope=request_envelope,
                smoke_profile=smoke_profile,
                response_schema=response_schema,
                render=render,
                prep=execution_prep,
            ),
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "runtime": "OFF",
        "adoption_authority": False,
    }
    require(
        set(report) == READINESS_KEYS,
        "READINESS_SCHEMA_KEYS",
    )
    return report


def validate_live_provider_readiness_report(
    report: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(report, dict)
        and set(report) == READINESS_KEYS,
        "READINESS_SCHEMA_KEYS",
    )
    require(
        report["schema"] == READINESS_SCHEMA,
        "READINESS_SCHEMA_VERSION",
    )
    require(
        report["readiness_state"]
        == "READY_FOR_SEPARATE_PROVIDER_AUTHORITY",
        "READINESS_STATE",
    )
    require(
        report["repository_contract_ready"] is True,
        "READINESS_REPOSITORY_NOT_READY",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
        "adoption_authority",
    ):
        require(
            report[key] is False,
            f"READINESS_FORBIDDEN_TRUE:{key}",
        )
    require(
        report["runtime"] == "OFF",
        "READINESS_RUNTIME_NOT_OFF",
    )
    return report


def live_provider_readiness_sha256(**kwargs: Any) -> str:
    report = build_live_provider_readiness_report(**kwargs)
    validate_live_provider_readiness_report(report)
    return sha256_json(report)
