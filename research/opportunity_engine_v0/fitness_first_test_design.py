from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessTestThresholds:
    owned_visit_to_first_value_min: float
    first_value_to_saved_state_min: float
    saved_state_to_7d_return_min: float
    active_user_to_share_min: float
    premium_exposure_to_paid_min: float

    def __post_init__(self) -> None:
        for name in (
            "owned_visit_to_first_value_min",
            "first_value_to_saved_state_min",
            "saved_state_to_7d_return_min",
            "active_user_to_share_min",
            "premium_exposure_to_paid_min",
        ):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= float(value) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


def build_fitness_first_test_plan(*, thresholds: FitnessTestThresholds) -> dict[str, object]:
    """Build a non-live, pre-registered test plan for the three-engine fitness loop.

    The plan freezes the success definition before any publication, spend, provider
    call or live-business effect. Thresholds are hypotheses only until measured.
    """
    return {
        "schema": "OPPORTUNITY_ENGINE_FITNESS_FIRST_TEST_PLAN_v1",
        "domain": "fitness/workouts",
        "test_state": "PRE_LIVE_RESEARCH_ONLY",
        "owned_state_object": {
            "name": "SESSION_PROGRESS_STATE",
            "fields": (
                "completed_session",
                "difficulty_feedback",
                "next_session_intent",
                "streak_or_consistency",
                "personal_best_or_progress_marker",
            ),
            "reason": (
                "The owned product should become more useful after each completed session. "
                "The moat hypothesis is accumulated personal progress and next-action relevance, "
                "not exclusive possession of a workout video."
            ),
        },
        "prototype_funnel": (
            "CHARACTER_LED_WORKOUT_DISCOVERY",
            "DEEP_LINK_TO_EXACT_SESSION",
            "IMMEDIATE_START_WITHOUT_ARTIFICIAL_ACCOUNT_FRICTION",
            "COMPLETE_OR_PARTIAL_SESSION",
            "SAVE_PROGRESS_STATE",
            "USEFUL_NEXT_SESSION_RECOMMENDATION",
            "OPTIONAL_SHAREABLE_PROGRESS_ARTIFACT",
            "RETURN_FOR_NEXT_SESSION",
            "PREMIUM_VALUE_ON_RECURRING_ANALYSIS_OR_PLANNING_NEED",
        ),
        "success_thresholds_frozen_before_live_test": {
            "owned_visit_to_first_value": float(thresholds.owned_visit_to_first_value_min),
            "first_value_to_saved_state": float(thresholds.first_value_to_saved_state_min),
            "saved_state_to_7d_return": float(thresholds.saved_state_to_7d_return_min),
            "active_user_to_share": float(thresholds.active_user_to_share_min),
            "premium_exposure_to_paid": float(thresholds.premium_exposure_to_paid_min),
        },
        "must_measure": (
            "qualified social view to owned visit",
            "owned visit to first useful action",
            "first useful action to saved state",
            "saved state to 7-day return",
            "returning user to second completed session",
            "active user to share",
            "share to new owned visit",
            "premium exposure to paid conversion",
            "owner minutes per active user",
        ),
        "kill_or_redesign_triggers": (
            "users consume content but do not create owned progress state",
            "return behavior depends mainly on external platform reminders",
            "premium value is indistinguishable from general AI coaching",
            "owner workload rises roughly linearly with active users",
            "safety or health-claim boundary cannot be kept narrow",
        ),
        "research_before_owner_gate": (
            "competitor-gap study versus Strava Nike Training Club and general AI",
            "mock the exact owned-state and next-session recommendation UX",
            "define what is deliberately excluded from v0 to avoid device/sensor complexity",
            "freeze measurement and attribution definitions",
        ),
        "provider_call_authorized": False,
        "spend_authorized": False,
        "publication_authorized": False,
        "live_execution_authorized": False,
        "adoption_authorized": False,
        "runtime_activation_authorized": False,
    }
