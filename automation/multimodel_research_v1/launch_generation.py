from __future__ import annotations

import re
from typing import Any

from automation.multimodel_research_v1.catalog_freshness import (
    build_catalog_freshness_receipt,
    catalog_freshness_sha256,
)
from automation.multimodel_research_v1.model import require, sha256_json
from automation.multimodel_research_v1.provider_catalog import (
    validate_provider_catalog,
)

LAUNCH_GENERATION_SCHEMA = (
    "MULTIVERSE_PHASE_B_CURRENT_CANONICAL_LAUNCH_GENERATION_v1"
)

CANONICAL_MAIN = "6ab0ecb54a4fadeae5cb0e508318ba65749be3e9"
CANONICAL_TREE = "ebfc09b16482cf7522f725ca678c49fa8a5dc4dc"
CANONICAL_MULTIMODEL_SUBTREE = (
    "4c161005b9b3dcd6597e5be9fcaf756e19049555"
)
REVIEWED_PR = 285
REVIEWED_HEAD = "efb5e45f5a82a87ba213516f7f5d2579a176a235"
REVIEWED_TREE = "ebfc09b16482cf7522f725ca678c49fa8a5dc4dc"
REVIEWED_MULTIMODEL_SUBTREE = (
    "4c161005b9b3dcd6597e5be9fcaf756e19049555"
)
REVIEWED_LAB_BUILD = 57
REVIEWED_LAB_COMMENT = 5611542648
REVIEWED_T1_COMMENT = 5611550128
REVIEWED_AUDITOR_BUILD = 1299
REVIEWED_AUDITOR_COMMENT = 5615177103
REVIEWED_T2_COMMENT = 5615179680
REVIEWED_TECHNICAL_COMPLETION_COMMENT = 5615205875
REVIEWED_TEST_COUNT = 478
PREDECESSOR_CANDIDATE_SEAL_BLOB = (
    "ac4352caead5bbfb3c02658262830407beacec8e"
)

CATALOG_SNAPSHOT_ID = "provider-model-catalog-20260910"
CATALOG_SNAPSHOT_BLOB = "6ba85c23bbe666baf204d29ae2145b510a164528"
CATALOG_SNAPSHOT_SHA256 = (
    "a5ef9478eec64e505fbd734999240174be9f209634b4341ac39fe1c54d640e33"
)
SOURCE_OBSERVED_AT = "2026-09-10T11:31:00Z"
CHECKED_AT = "2026-09-10T11:35:00Z"
RECORDED_AT = "2026-09-10T11:35:05Z"

LAUNCH_GENERATION_KEYS = {
    "schema",
    "launch_generation_id",
    "source_observed_at",
    "checked_at",
    "recorded_at",
    "canonical_main",
    "canonical_tree",
    "canonical_multimodel_subtree",
    "reviewed_pr",
    "reviewed_head",
    "reviewed_tree",
    "reviewed_multimodel_subtree",
    "reviewed_lab_build",
    "reviewed_lab_comment",
    "reviewed_t1_comment",
    "reviewed_auditor_build",
    "reviewed_auditor_comment",
    "reviewed_t2_comment",
    "reviewed_technical_completion_comment",
    "reviewed_test_count",
    "predecessor_candidate_seal_blob",
    "predecessor_seal_is_historical_only",
    "provider_catalog_snapshot_id",
    "provider_catalog_snapshot_blob",
    "provider_catalog_snapshot_sha256",
    "catalog_freshness_sha256",
    "catalog_age_seconds",
    "catalog_max_age_seconds",
    "provider_call_authorized",
    "credential_authorized",
    "spend_authorized",
    "live_execution_performed",
    "protected_data_effect",
    "live_business_effect",
    "adoption_authority",
    "runtime",
}


def _git_sha1(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{40}", value)),
        code,
    )
    return value


def _sha256(value: Any, code: str) -> str:
    require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
        code,
    )
    return value


def _expected(snapshot: dict[str, Any]) -> dict[str, Any]:
    validate_provider_catalog(snapshot)
    require(
        snapshot["snapshot_id"] == CATALOG_SNAPSHOT_ID,
        "LAUNCH_GENERATION_CATALOG_ID_MISMATCH",
    )
    require(
        snapshot["observed_at"] == SOURCE_OBSERVED_AT,
        "LAUNCH_GENERATION_CATALOG_OBSERVED_AT_MISMATCH",
    )
    require(
        sha256_json(snapshot) == CATALOG_SNAPSHOT_SHA256,
        "LAUNCH_GENERATION_CATALOG_SHA256_MISMATCH",
    )
    freshness = build_catalog_freshness_receipt(
        snapshot,
        checked_at=CHECKED_AT,
    )
    return {
        "schema": LAUNCH_GENERATION_SCHEMA,
        "launch_generation_id":
            "phase-b-current-canonical-launch-generation-20260910-001",
        "source_observed_at": SOURCE_OBSERVED_AT,
        "checked_at": CHECKED_AT,
        "recorded_at": RECORDED_AT,
        "canonical_main": CANONICAL_MAIN,
        "canonical_tree": CANONICAL_TREE,
        "canonical_multimodel_subtree":
            CANONICAL_MULTIMODEL_SUBTREE,
        "reviewed_pr": REVIEWED_PR,
        "reviewed_head": REVIEWED_HEAD,
        "reviewed_tree": REVIEWED_TREE,
        "reviewed_multimodel_subtree":
            REVIEWED_MULTIMODEL_SUBTREE,
        "reviewed_lab_build": REVIEWED_LAB_BUILD,
        "reviewed_lab_comment": REVIEWED_LAB_COMMENT,
        "reviewed_t1_comment": REVIEWED_T1_COMMENT,
        "reviewed_auditor_build": REVIEWED_AUDITOR_BUILD,
        "reviewed_auditor_comment": REVIEWED_AUDITOR_COMMENT,
        "reviewed_t2_comment": REVIEWED_T2_COMMENT,
        "reviewed_technical_completion_comment":
            REVIEWED_TECHNICAL_COMPLETION_COMMENT,
        "reviewed_test_count": REVIEWED_TEST_COUNT,
        "predecessor_candidate_seal_blob":
            PREDECESSOR_CANDIDATE_SEAL_BLOB,
        "predecessor_seal_is_historical_only": True,
        "provider_catalog_snapshot_id": CATALOG_SNAPSHOT_ID,
        "provider_catalog_snapshot_blob": CATALOG_SNAPSHOT_BLOB,
        "provider_catalog_snapshot_sha256":
            CATALOG_SNAPSHOT_SHA256,
        "catalog_freshness_sha256":
            catalog_freshness_sha256(snapshot, freshness),
        "catalog_age_seconds": freshness["age_seconds"],
        "catalog_max_age_seconds": freshness["max_age_seconds"],
        "provider_call_authorized": False,
        "credential_authorized": False,
        "spend_authorized": False,
        "live_execution_performed": False,
        "protected_data_effect": False,
        "live_business_effect": False,
        "adoption_authority": False,
        "runtime": "OFF",
    }


def build_current_canonical_launch_generation(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    generation = _expected(snapshot)
    return validate_current_canonical_launch_generation(
        snapshot,
        generation,
    )


def validate_current_canonical_launch_generation(
    snapshot: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    require(
        isinstance(generation, dict)
        and set(generation) == LAUNCH_GENERATION_KEYS,
        "LAUNCH_GENERATION_SCHEMA_KEYS",
    )
    expected = _expected(snapshot)
    require(
        generation == expected,
        "LAUNCH_GENERATION_EXACT_BINDING_MISMATCH",
    )
    for key in (
        "canonical_main",
        "canonical_tree",
        "canonical_multimodel_subtree",
        "reviewed_head",
        "reviewed_tree",
        "reviewed_multimodel_subtree",
        "predecessor_candidate_seal_blob",
        "provider_catalog_snapshot_blob",
    ):
        _git_sha1(generation[key], f"LAUNCH_GENERATION_GIT_SHA:{key}")
    _sha256(
        generation["provider_catalog_snapshot_sha256"],
        "LAUNCH_GENERATION_CATALOG_SHA256",
    )
    _sha256(
        generation["catalog_freshness_sha256"],
        "LAUNCH_GENERATION_FRESHNESS_SHA256",
    )
    require(
        generation["catalog_age_seconds"]
        <= generation["catalog_max_age_seconds"]
        <= 86400,
        "LAUNCH_GENERATION_CATALOG_NOT_FRESH",
    )
    require(
        generation["predecessor_seal_is_historical_only"] is True,
        "LAUNCH_GENERATION_PREDECESSOR_SEAL_ROLE",
    )
    for key in (
        "provider_call_authorized",
        "credential_authorized",
        "spend_authorized",
        "live_execution_performed",
        "protected_data_effect",
        "live_business_effect",
        "adoption_authority",
    ):
        require(
            generation[key] is False,
            f"LAUNCH_GENERATION_FORBIDDEN_TRUE:{key}",
        )
    require(
        generation["runtime"] == "OFF",
        "LAUNCH_GENERATION_RUNTIME_NOT_OFF",
    )
    return generation


def current_canonical_launch_generation_sha256(
    snapshot: dict[str, Any],
    generation: dict[str, Any],
) -> str:
    validate_current_canonical_launch_generation(
        snapshot,
        generation,
    )
    return sha256_json(generation)
