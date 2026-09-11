from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


_FORBIDDEN_PREFIXES = (
    "automation/review_dispatcher_v1/",
    "automation/multimodel_research_v1/",
)

_COMMON_FORBIDDEN_TOKENS = (
    "multiverse_bridge",
    "multiverse_result_bridge",
    "provider_escalation",
    "credential",
    "runtime",
    "publisher",
    "t2",
    "advisor_",
    "review_",
    "owner_gate",
    "mission_continuation",
)

_PROFILE_FORBIDDEN = {
    "A_CORE_DOMAIN": (
        "customer_contribution",
        "customer_value_loop",
        "hundred_user",
        "forecast_revision",
        "forecast_ledger",
        "trend_forecast",
        "trend_retrospective",
    ),
    "B_FORECAST_INTEGRITY": (
        "customer_contribution",
        "customer_value_loop",
        "hundred_user",
        "growth_loop",
    ),
    "C_CUSTOMER_VALUE_HUNDRED_USER": (
        "forecast_revision",
        "forecast_ledger",
        "trend_forecast",
        "trend_retrospective",
    ),
}


@dataclass(frozen=True)
class SliceValidation:
    valid: bool
    findings: tuple[str, ...]


def validate_adoption_slice_paths(paths: Iterable[str], *, profile: str = "A_CORE_DOMAIN") -> SliceValidation:
    """Fail closed if an adoption slice leaks control/live/high-coupling paths.

    Profiles let Slice A/B/C reuse one validator rather than fork validation logic.
    This grants no review, adoption, merge, provider, spend, publication,
    customer, or Runtime authority.
    """
    findings: list[str] = []
    normalized: list[str] = []

    if profile not in _PROFILE_FORBIDDEN:
        return SliceValidation(False, (f"UNKNOWN_PROFILE:{profile}",))

    forbidden_tokens = _COMMON_FORBIDDEN_TOKENS + _PROFILE_FORBIDDEN[profile]

    for raw in paths:
        if not isinstance(raw, str) or not raw.strip():
            findings.append("INVALID_EMPTY_PATH")
            continue
        path = PurePosixPath(raw)
        rendered = path.as_posix()
        normalized.append(rendered)

        if rendered.startswith("/") or ".." in path.parts:
            findings.append(f"UNSAFE_PATH:{rendered}")
            continue
        if not rendered.startswith("research/opportunity_engine_v0/"):
            findings.append(f"OUTSIDE_OPPORTUNITY_ENGINE:{rendered}")
        if any(rendered.startswith(prefix) for prefix in _FORBIDDEN_PREFIXES):
            findings.append(f"CANONICAL_CONTROL_PLANE_FORBIDDEN:{rendered}")

        lower = rendered.lower()
        for token in forbidden_tokens:
            if token in lower:
                findings.append(f"HIGH_COUPLING_PATH_FORBIDDEN:{rendered}:{token}")
                break

    if len(normalized) != len(set(normalized)):
        findings.append("DUPLICATE_PATH")

    return SliceValidation(valid=not findings, findings=tuple(findings))


def slice_authority_ceiling() -> dict[str, bool]:
    return {
        "formal_review_authorized": False,
        "canonical_adoption_authorized": False,
        "merge_authorized": False,
        "provider_call_authorized": False,
        "credential_use_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "customer_recruitment_authorized": False,
        "payment_collection_authorized": False,
        "runtime_activation_authorized": False,
    }


def slice_a_authority_ceiling() -> dict[str, bool]:
    return slice_authority_ceiling()
