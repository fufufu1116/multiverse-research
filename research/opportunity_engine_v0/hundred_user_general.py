from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HundredUserEvidence:
    users_observed: int
    first_value_rate: float
    saved_state_rate: float
    return_7d_rate: float
    second_action_rate: float
    share_output_rate: float
    organic_return_path_rate: float
    premium_interest_signal_rate: float
    owner_minutes_per_active_user: float
    general_ai_substitution_rate: float
    policy_or_safety_incidents: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.users_observed <= 100:
            raise ValueError("users_observed must be between 0 and 100")
        for name in (
            "first_value_rate",
            "saved_state_rate",
            "return_7d_rate",
            "second_action_rate",
            "share_output_rate",
            "organic_return_path_rate",
            "premium_interest_signal_rate",
            "general_ai_substitution_rate",
        ):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.owner_minutes_per_active_user < 0:
            raise ValueError("owner_minutes_per_active_user must be non-negative")
        if self.policy_or_safety_incidents < 0:
            raise ValueError("policy_or_safety_incidents must be non-negative")


def assess_hundred_user_stage(evidence: HundredUserEvidence) -> dict[str, object]:
    """Assess the first-100-user stage without granting live or adoption authority.

    Thresholds here are research defaults for simulation only. A real experiment must
    freeze its own thresholds before recruitment/data collection.
    """
    blockers: list[str] = []

    if evidence.users_observed < 100:
        blockers.append("HUNDRED_USERS_NOT_OBSERVED")
    if evidence.first_value_rate < 0.50:
        blockers.append("FIRST_VALUE_TOO_WEAK")
    if evidence.saved_state_rate < 0.30:
        blockers.append("OWNED_STATE_TOO_WEAK")
    if evidence.return_7d_rate < 0.25:
        blockers.append("REPEAT_USE_TOO_WEAK")
    if evidence.second_action_rate < 0.20:
        blockers.append("SECOND_DECISION_TOO_WEAK")
    if evidence.organic_return_path_rate < 0.15:
        blockers.append("ORGANIC_RETURN_PATH_TOO_WEAK")
    if evidence.general_ai_substitution_rate > 0.50:
        blockers.append("GENERIC_AI_SUBSTITUTION_TOO_HIGH")
    if evidence.owner_minutes_per_active_user > 8:
        blockers.append("OWNER_BURDEN_TOO_HIGH")
    if evidence.policy_or_safety_incidents > 0:
        blockers.append("POLICY_OR_SAFETY_INCIDENT_REVIEW_REQUIRED")

    if blockers:
        decision = "HOLD_OR_ITERATE_HUNDRED_USER_STAGE"
    else:
        decision = "NEXT_STAGE_RESEARCH_CANDIDATE"

    return {
        "decision": decision,
        "blockers": blockers,
        "users_observed": evidence.users_observed,
        "vanity_metrics_cannot_promote": True,
        "thresholds_are_research_defaults_only": True,
        "live_test_authorized": False,
        "recruitment_authorized": False,
        "publication_authorized": False,
        "spend_authorized": False,
        "payment_collection_authorized": False,
        "runtime_activation_authorized": False,
        "adoption_authorized": False,
    }


def build_first_wedge_spec() -> dict[str, object]:
    """Return the current hypothesis leader for the first 100-user wedge."""
    return {
        "stage": "HUNDRED_USER_GENERAL",
        "candidate": "FASHION_TREND_COMMENTARY_TO_OWNED_WARDROBE_ACTION",
        "promise": "Turn one social fashion trend into one actionable look using the user's existing wardrobe/state.",
        "character_role": "taste-led trend verifier, not an omniscient stylist",
        "owned_state": (
            "wardrobe inventory or lightweight wardrobe memory",
            "style preferences and rejected looks",
            "saved outfits",
            "event/context history",
            "previous decisions and outcomes",
        ),
        "first_value": "one usable outfit/decision from existing state",
        "repeat_reason": "less decision friction because prior state is remembered",
        "shareable_output": "user-controlled outfit/result card without required promotional watermarking",
        "premium_boundary": "higher-value recurring planning/history/analysis, never artificial obstruction",
        "anti_commodity_rule": "generic AI recommendation alone is insufficient; value must depend on accumulated user state or execution context",
        "live_execution_authorized": False,
        "owner_gate_still_required_for_live_test": True,
    }
