from __future__ import annotations

import hashlib
import json
import re
from typing import Any

TASK_SCHEMA = "MULTIVERSE_RESEARCH_TASK_v1"
RESULT_SCHEMA = "MULTIVERSE_RESEARCH_RESULT_v1"
AGGREGATE_SCHEMA = "MULTIVERSE_RESEARCH_AGGREGATE_v1"

TASK_KEYS = {
    "schema",
    "task_id",
    "snapshot_id",
    "domain",
    "objective",
    "source_refs",
    "allowed_primitives",
    "constraints",
    "requested_roles",
    "nonauthority",
}

RESULT_KEYS = {
    "schema",
    "task_id",
    "submission_id",
    "snapshot_id",
    "model_identity",
    "status",
    "findings",
    "uncertainty_factors",
    "nonauthority",
}

CONSTRAINT_KEYS = {
    "network_access",
    "max_compute_seconds",
    "max_output_bytes",
    "max_findings",
}

NONAUTHORITY_KEYS = {
    "adoption",
    "merge",
    "main_mutation",
    "ruleset_mutation",
    "workflow_dispatch_rerun",
    "runtime_activation",
    "provider_effect",
    "production",
    "protected_data",
    "live_business_effect",
    "spend",
}

ALLOWED_PRIMITIVES = {
    "SOURCE_REF",
    "SUBTREE_HASH",
    "NORMALIZED_JSON_SHA256",
    "EXACT_LINEAGE",
    "UNITTEST_RESULT",
    "VALIDATOR_RESULT",
    "PUBLIC_EVIDENCE_REF",
    "SYNTHETIC_FIXTURE",
}

RESULT_STATUSES = {
    "COMPLETED",
    "INFRA_FAILURE",
    "UNSUPPORTED",
    "REFUSED",
}

FINDING_KEYS = {
    "finding_id",
    "claim_key",
    "position",
    "severity",
    "assertion",
    "evidence",
    "confidence",
    "uncertainty",
    "recommendation",
    "validation_plan",
}

POSITIONS = {
    "SUPPORT",
    "OPPOSE",
    "UNKNOWN",
}

SEVERITIES = {
    "INFO",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

FORBIDDEN_DYNAMIC_KEYS = {
    "command",
    "shell",
    "script",
    "python",
    "yaml",
    "token",
    "password",
    "credential",
    "private_key",
}


class ResearchContractError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ResearchContractError(code)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _identifier(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", value)),
        code,
    )
    return value


def _text(value: Any, code: str, max_len: int = 20000) -> str:
    require(isinstance(value, str), code)
    require(0 < len(value) <= max_len, code)
    return value


def _nonauthority(value: Any) -> dict[str, bool]:
    require(
        isinstance(value, dict)
        and set(value) == NONAUTHORITY_KEYS,
        "NONAUTHORITY_SCHEMA",
    )
    for key, flag in value.items():
        require(flag is False, f"NONAUTHORITY_NOT_FALSE:{key}")
    return value


def _reject_dynamic_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            low = str(key).lower()
            for fragment in FORBIDDEN_DYNAMIC_KEYS:
                require(
                    fragment not in low,
                    f"FORBIDDEN_DYNAMIC_KEY:{key}",
                )
            _reject_dynamic_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_dynamic_keys(child)


def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(task, dict), "TASK_OBJECT")
    require(set(task) == TASK_KEYS, "TASK_SCHEMA_KEYS")
    require(task["schema"] == TASK_SCHEMA, "TASK_SCHEMA_VERSION")
    _identifier(task["task_id"], "TASK_ID")
    _identifier(task["snapshot_id"], "SNAPSHOT_ID")
    _identifier(task["domain"], "DOMAIN")
    _text(task["objective"], "OBJECTIVE")

    refs = task["source_refs"]
    require(isinstance(refs, list) and bool(refs), "SOURCE_REFS")
    require(len(refs) <= 100, "SOURCE_REFS_LIMIT")
    for item in refs:
        require(
            isinstance(item, dict)
            and set(item) == {"kind", "ref", "sha256"},
            "SOURCE_REF_SCHEMA",
        )
        _identifier(item["kind"], "SOURCE_REF_KIND")
        _text(item["ref"], "SOURCE_REF_REF", 4000)
        digest = item["sha256"]
        require(
            digest is None
            or (
                isinstance(digest, str)
                and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
            ),
            "SOURCE_REF_SHA256",
        )

    primitives = task["allowed_primitives"]
    require(isinstance(primitives, list) and bool(primitives), "ALLOWED_PRIMITIVES")
    require(
        set(primitives).issubset(ALLOWED_PRIMITIVES),
        "UNKNOWN_PRIMITIVE",
    )
    require(
        len(set(primitives)) == len(primitives),
        "DUPLICATE_PRIMITIVE",
    )

    constraints = task["constraints"]
    require(
        isinstance(constraints, dict)
        and set(constraints) == CONSTRAINT_KEYS,
        "CONSTRAINT_SCHEMA",
    )
    require(
        constraints["network_access"] in {"NONE", "PUBLIC_READ_ONLY"},
        "NETWORK_ACCESS",
    )
    require(
        isinstance(constraints["max_compute_seconds"], int)
        and 1 <= constraints["max_compute_seconds"] <= 3600,
        "MAX_COMPUTE_SECONDS",
    )
    require(
        isinstance(constraints["max_output_bytes"], int)
        and 1024 <= constraints["max_output_bytes"] <= 10_000_000,
        "MAX_OUTPUT_BYTES",
    )
    require(
        isinstance(constraints["max_findings"], int)
        and 1 <= constraints["max_findings"] <= 500,
        "MAX_FINDINGS",
    )

    roles = task["requested_roles"]
    require(isinstance(roles, list) and bool(roles), "REQUESTED_ROLES")
    require(len(roles) <= 16, "REQUESTED_ROLES_LIMIT")
    for role in roles:
        _identifier(role, "REQUESTED_ROLE")

    _nonauthority(task["nonauthority"])
    _reject_dynamic_keys(task)
    return task


def validate_result(result: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(result, dict), "RESULT_OBJECT")
    require(set(result) == RESULT_KEYS, "RESULT_SCHEMA_KEYS")
    require(result["schema"] == RESULT_SCHEMA, "RESULT_SCHEMA_VERSION")
    _identifier(result["task_id"], "RESULT_TASK_ID")
    _identifier(result["submission_id"], "SUBMISSION_ID")
    _identifier(result["snapshot_id"], "RESULT_SNAPSHOT_ID")

    identity = result["model_identity"]
    require(
        isinstance(identity, dict)
        and set(identity) == {"provider", "model", "role"},
        "MODEL_IDENTITY_SCHEMA",
    )
    for key in ("provider", "model", "role"):
        _identifier(identity[key], f"MODEL_IDENTITY_{key.upper()}")

    require(result["status"] in RESULT_STATUSES, "RESULT_STATUS")

    findings = result["findings"]
    require(isinstance(findings, list), "FINDINGS_LIST")
    require(len(findings) <= 500, "FINDINGS_LIMIT")

    if result["status"] == "COMPLETED":
        require(bool(findings), "COMPLETED_REQUIRES_FINDING")
    else:
        require(findings == [], "NONCOMPLETED_FINDINGS_MUST_BE_EMPTY")

    finding_ids: set[str] = set()

    for finding in findings:
        require(
            isinstance(finding, dict)
            and set(finding) == FINDING_KEYS,
            "FINDING_SCHEMA",
        )

        finding_id = _identifier(
            finding["finding_id"],
            "FINDING_ID",
        )
        require(
            finding_id not in finding_ids,
            "DUPLICATE_FINDING_ID",
        )
        finding_ids.add(finding_id)

        _identifier(finding["claim_key"], "CLAIM_KEY")
        require(finding["position"] in POSITIONS, "FINDING_POSITION")
        require(finding["severity"] in SEVERITIES, "FINDING_SEVERITY")
        _text(finding["assertion"], "FINDING_ASSERTION")
        require(
            isinstance(finding["confidence"], (int, float))
            and not isinstance(finding["confidence"], bool)
            and 0.0 <= float(finding["confidence"]) <= 1.0,
            "FINDING_CONFIDENCE",
        )
        _text(finding["uncertainty"], "FINDING_UNCERTAINTY")
        _text(finding["recommendation"], "FINDING_RECOMMENDATION")
        _text(finding["validation_plan"], "FINDING_VALIDATION_PLAN")

        evidence = finding["evidence"]
        require(
            isinstance(evidence, dict)
            and set(evidence) == {"primitive", "ref", "sha256"},
            "FINDING_EVIDENCE_SCHEMA",
        )
        require(
            evidence["primitive"] in ALLOWED_PRIMITIVES,
            "FINDING_EVIDENCE_PRIMITIVE",
        )
        _text(evidence["ref"], "FINDING_EVIDENCE_REF", 4000)
        digest = evidence["sha256"]
        require(
            digest is None
            or (
                isinstance(digest, str)
                and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
            ),
            "FINDING_EVIDENCE_SHA256",
        )

    uncertainty_factors = result["uncertainty_factors"]
    require(
        isinstance(uncertainty_factors, list),
        "UNCERTAINTY_FACTORS",
    )
    require(
        len(uncertainty_factors) <= 100,
        "UNCERTAINTY_FACTORS_LIMIT",
    )
    for item in uncertainty_factors:
        _text(item, "UNCERTAINTY_FACTOR", 4000)

    _nonauthority(result["nonauthority"])
    _reject_dynamic_keys(result)
    return result


def result_content_digest(result: dict[str, Any]) -> str:
    validate_result(result)
    content = dict(result)
    content.pop("submission_id", None)
    return sha256_json(content)
