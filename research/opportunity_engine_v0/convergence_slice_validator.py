from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


_FORBIDDEN_PREFIXES = (
    "automation/review_dispatcher_v1/",
    "automation/multimodel_research_v1/",
)

_FORBIDDEN_TOKENS = (
    "multiverse_bridge",
    "multiverse_result_bridge",
    "provider",
    "credential",
    "runtime",
    "publisher",
    "t2",
    "customer_contribution",
    "customer_value_loop",
    "hundred_user",
    "advisor_",
    "review_",
    "forecast_revision",
)


@dataclass(frozen=True)
class SliceValidation:
    valid: bool
    findings: tuple[str, ...]


def validate_adoption_slice_paths(paths: Iterable[str]) -> SliceValidation:
    """Fail closed if an adoption slice leaks control/live/high-coupling paths.

    This is a repository-only research validator. It grants no review, adoption,
    merge, provider, spend, publication, customer, or Runtime authority.
    """
    findings: list[str] = []
    normalized: list[str] = []

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
        for token in _FORBIDDEN_TOKENS:
            if token in lower:
                findings.append(f"HIGH_COUPLING_PATH_FORBIDDEN:{rendered}:{token}")
                break

    if len(normalized) != len(set(normalized)):
        findings.append("DUPLICATE_PATH")

    return SliceValidation(valid=not findings, findings=tuple(findings))


def slice_a_authority_ceiling() -> dict[str, bool]:
    return {
        "formal_review_authorized": False,
        "canonical_adoption_authorized": False,
        "merge_authorized": False,
        "provider_call_authorized": False,
        "credential_use_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "customer_recruitment_authorized": False,
        "runtime_activation_authorized": False,
    }
