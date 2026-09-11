from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LoopVerdict(str, Enum):
    REJECT = "REJECT"
    ONE_WAY_ACQUISITION = "ONE_WAY_ACQUISITION"
    RECIPROCAL_LOOP = "RECIPROCAL_LOOP"
    FLYWHEEL_CANDIDATE = "FLYWHEEL_CANDIDATE"


@dataclass(frozen=True)
class ReciprocalDistributionProfile:
    forward_user_value: int
    return_user_value: int
    attribution_quality: int
    organic_content_creation: int
    repeat_cycle_strength: int
    friction: int
    platform_dependency: int
    legal_policy_risk: int
    deceptive_or_spammy: bool = False
    rights_unclear: bool = False

    def __post_init__(self) -> None:
        for name in (
            "forward_user_value",
            "return_user_value",
            "attribution_quality",
            "organic_content_creation",
            "repeat_cycle_strength",
            "friction",
            "platform_dependency",
            "legal_policy_risk",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")


def assess_reciprocal_distribution(profile: ReciprocalDistributionProfile) -> dict[str, object]:
    """Evaluate whether two surfaces create real reciprocal distribution rather than one-way promotion.

    The mechanism must create independent user value in both directions. Manipulative sharing,
    unclear content rights, and high legal/platform-policy risk fail closed. A flywheel label is
    research-only and never authorizes posting, API calls, ad spend, or publication.
    """
    if profile.deceptive_or_spammy or profile.rights_unclear or profile.legal_policy_risk >= 4:
        return {
            "verdict": LoopVerdict.REJECT.value,
            "score": 0,
            "reasons": ("SAFETY_OR_RIGHTS_BLOCKER",),
            "automatic_execution_authorized": False,
        }

    raw = (
        profile.forward_user_value * 4
        + profile.return_user_value * 4
        + profile.attribution_quality * 2
        + profile.organic_content_creation * 3
        + profile.repeat_cycle_strength * 4
        - profile.friction * 3
        - profile.platform_dependency * 3
        - profile.legal_policy_risk * 4
    )
    score = max(0, min(100, round(raw * 2)))

    if (
        profile.forward_user_value >= 3
        and profile.return_user_value >= 3
        and profile.repeat_cycle_strength >= 4
        and profile.organic_content_creation >= 3
        and score >= 60
    ):
        verdict = LoopVerdict.FLYWHEEL_CANDIDATE
        reasons = ("TWO_WAY_USER_VALUE", "REPEATABLE_RETURN_LOOP", "USER_ACTIVITY_CREATES_DISTRIBUTION")
    elif profile.forward_user_value >= 3 and profile.return_user_value >= 3 and score >= 40:
        verdict = LoopVerdict.RECIPROCAL_LOOP
        reasons = ("TWO_WAY_USER_VALUE",)
    else:
        verdict = LoopVerdict.ONE_WAY_ACQUISITION
        reasons = ("RETURN_LOOP_TOO_WEAK",)

    return {
        "verdict": verdict.value,
        "score": score,
        "reasons": reasons,
        "automatic_execution_authorized": False,
        "note": "Distribution loop assessment only; current platform policy, content rights, attribution, and governed execution remain separate gates.",
    }
