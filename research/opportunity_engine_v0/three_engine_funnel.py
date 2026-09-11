from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PersonalizationTier(str, Enum):
    CONTEXTUAL = "CONTEXTUAL"
    FIRST_PARTY_HISTORY = "FIRST_PARTY_HISTORY"
    PERMISSION_GATED_CROSS_CONTEXT = "PERMISSION_GATED_CROSS_CONTEXT"


@dataclass(frozen=True)
class ThreeEngineSurface:
    domain: str
    branded_content_strength: int
    repeat_intent: int
    shareable_output_strength: int
    exclusive_owned_utility: int
    first_party_state_value: int
    monetization_fit: int
    platform_dependency_risk: int
    policy_fragility: int

    def __post_init__(self) -> None:
        if not self.domain.strip():
            raise ValueError("domain is required")
        for name in (
            "branded_content_strength",
            "repeat_intent",
            "shareable_output_strength",
            "exclusive_owned_utility",
            "first_party_state_value",
            "monetization_fit",
            "platform_dependency_risk",
            "policy_fragility",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def score_three_engine_surface(surface: ThreeEngineSurface) -> dict[str, object]:
    """Rank a domain for the clean attack/defense/personalization loop.

    This is a hypothesis score for research prioritization, not evidence of demand,
    conversion, retention, or profit. Platform and policy dependence are penalties.
    """
    positive = (
        surface.branded_content_strength * 4
        + surface.repeat_intent * 5
        + surface.shareable_output_strength * 4
        + surface.exclusive_owned_utility * 6
        + surface.first_party_state_value * 5
        + surface.monetization_fit * 4
    )
    penalty = surface.platform_dependency_risk * 4 + surface.policy_fragility * 5
    score = max(0, min(100, positive - penalty))

    blockers: list[str] = []
    if surface.exclusive_owned_utility < 3:
        blockers.append("OWNED_UTILITY_TOO_WEAK")
    if surface.repeat_intent < 3:
        blockers.append("REPEAT_INTENT_TOO_WEAK")
    if surface.policy_fragility >= 4:
        blockers.append("POLICY_FRAGILITY_HIGH")
    if surface.platform_dependency_risk >= 5:
        blockers.append("PLATFORM_DEPENDENCY_EXTREME")

    if blockers:
        posture = "RESEARCH_OR_REDESIGN"
    elif score >= 65:
        posture = "PRIORITY_RESEARCH_CANDIDATE"
    elif score >= 45:
        posture = "SECONDARY_RESEARCH_CANDIDATE"
    else:
        posture = "LOW_PRIORITY"

    return {
        "domain": surface.domain,
        "score": score,
        "posture": posture,
        "blockers": blockers,
        "score_is_hypothesis_only": True,
        "live_execution_authorized": False,
        "spend_authorized": False,
        "adoption_authorized": False,
    }


def build_clean_funnel(*, personalization_tier: PersonalizationTier, tracking_permission: bool) -> dict[str, object]:
    """Return the platform-neutral funnel while enforcing permission boundaries."""
    if not isinstance(personalization_tier, PersonalizationTier):
        raise ValueError("personalization_tier must be PersonalizationTier")
    if not isinstance(tracking_permission, bool):
        raise ValueError("tracking_permission must be boolean")

    if personalization_tier == PersonalizationTier.PERMISSION_GATED_CROSS_CONTEXT and not tracking_permission:
        return {
            "decision": "BLOCK_CROSS_CONTEXT_PERSONALIZATION",
            "reason": "TRACKING_PERMISSION_REQUIRED",
            "fallback_tier": PersonalizationTier.FIRST_PARTY_HISTORY.value,
            "live_execution_authorized": False,
        }

    stages = (
        "BRANDED_DISCOVERY_CONTENT",
        "SOCIAL_DISCOVERY_OR_REPOST",
        "SOURCE_OR_UTILITY_CUE",
        "DEEP_LINK_TO_OWNED_UTILITY",
        "IMMEDIATE_USEFUL_ACTION",
        "SAVE_STATE_OR_PROGRESS",
        "NEXT_USEFUL_RECOMMENDATION",
        "PREMIUM_VALUE_AT_RECURRING_FRICTION",
        "SHAREABLE_USER_OUTPUT",
        "EXTERNAL_REDISCOVERY",
    )
    metrics = (
        "qualified_view_to_owned_visit",
        "owned_visit_to_first_value",
        "first_value_to_saved_state",
        "saved_state_to_7d_return",
        "return_to_premium_exposure",
        "premium_exposure_to_paid_conversion",
        "active_user_to_share",
        "share_to_new_owned_visit",
        "repeat_loop_rate",
    )
    return {
        "decision": "CLEAN_FUNNEL_DEFINED",
        "personalization_tier": personalization_tier.value,
        "stages": stages,
        "metrics": metrics,
        "principles": (
            "value_before account friction where practical",
            "premium prompt at recurring friction, not artificial obstruction",
            "clear price renewal and cancellation",
            "no covert cross-site profiling",
            "no assumption that visible promotional watermarking is platform-safe",
        ),
        "live_execution_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "adoption_authorized": False,
    }
