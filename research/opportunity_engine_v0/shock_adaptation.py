from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ShockVerdict(str, Enum):
    REJECT = "REJECT"
    HOLD = "HOLD"
    ADAPT = "ADAPT"
    CONSTRAINT_INVERSION = "CONSTRAINT_INVERSION"


@dataclass(frozen=True)
class ShockAdaptationProfile:
    old_model_dependency: int
    compliance_confidence: int
    resilience_gain: int
    cashflow_quality_gain: int
    owner_burden_reduction: int
    distribution_gain: int
    trust_gain: int
    reusable_asset_gain: int
    setup_cost_yen: int
    setup_days: int
    vendor_lock_in: int
    legal_risk: int
    preseed_readiness: int
    evasion_or_jurisdiction_escape: bool = False
    harmful_exploitation: bool = False
    deceptive: bool = False

    def __post_init__(self) -> None:
        for name in (
            "old_model_dependency",
            "compliance_confidence",
            "resilience_gain",
            "cashflow_quality_gain",
            "owner_burden_reduction",
            "distribution_gain",
            "trust_gain",
            "reusable_asset_gain",
            "vendor_lock_in",
            "legal_risk",
            "preseed_readiness",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 5:
                raise ValueError(f"{name} must be an integer from 0 to 5")
        if not isinstance(self.setup_cost_yen, int) or self.setup_cost_yen < 0:
            raise ValueError("setup_cost_yen must be a nonnegative integer")
        if not isinstance(self.setup_days, int) or self.setup_days < 0:
            raise ValueError("setup_days must be a nonnegative integer")


def assess_shock_adaptation(profile: ShockAdaptationProfile) -> dict[str, object]:
    """Assess whether an external shock can force a compliant improvement in the business system.

    Regulation/platform/technology shocks are treated as selection pressure, never as a license
    to evade jurisdiction or move harmful conduct to another channel. Constraint inversion means
    the replacement structure is both more compliant/resilient and economically stronger on at
    least one important dimension. It is a research classification, not execution authority.
    """
    if (
        profile.evasion_or_jurisdiction_escape
        or profile.harmful_exploitation
        or profile.deceptive
        or profile.legal_risk >= 4
    ):
        return {
            "verdict": ShockVerdict.REJECT.value,
            "score": 0,
            "reasons": ("ILLEGAL_UNSAFE_OR_EVASIVE_ADAPTATION",),
            "automatic_execution_authorized": False,
        }

    raw = (
        profile.resilience_gain * 5
        + profile.cashflow_quality_gain * 4
        + profile.owner_burden_reduction * 3
        + profile.distribution_gain * 3
        + profile.trust_gain * 3
        + profile.reusable_asset_gain * 4
        + profile.preseed_readiness * 3
        + profile.compliance_confidence * 5
        - profile.vendor_lock_in * 3
        - profile.legal_risk * 5
        - min(profile.setup_cost_yen / 1000.0, 10)
        - profile.setup_days
    )
    score = max(0, min(100, round(raw)))

    inversion = (
        profile.old_model_dependency >= 4
        and profile.resilience_gain >= 4
        and profile.compliance_confidence >= 4
        and (
            profile.cashflow_quality_gain >= 3
            or profile.distribution_gain >= 3
            or profile.trust_gain >= 3
        )
    )

    if inversion and score >= 55:
        verdict = ShockVerdict.CONSTRAINT_INVERSION
        reasons = ("FRAGILE_OLD_MECHANISM_REMOVED", "COMPLIANT_REPLACEMENT_STRONGER", "SHOCK_CREATED_FORCED_UPGRADE")
    elif score >= 45:
        verdict = ShockVerdict.ADAPT
        reasons = ("ADAPTATION_HAS_POSITIVE_RESILIENCE_VALUE",)
    else:
        verdict = ShockVerdict.HOLD
        reasons = ("ADAPTATION_NOT_YET_STRONG_ENOUGH",)

    return {
        "verdict": verdict.value,
        "score": score,
        "reasons": reasons,
        "automatic_execution_authorized": False,
        "note": "Shock adaptation is only positive when the replacement is compliant, non-deceptive, and independently useful; moving regulated harm to a new channel is never treated as innovation.",
    }
