import unittest

from research.opportunity_engine_v0.hundred_user_general import (
    HundredUserEvidence,
    assess_hundred_user_stage,
    build_first_wedge_spec,
)


class HundredUserGeneralTests(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            users_observed=100,
            first_value_rate=0.50,
            saved_state_rate=0.30,
            return_7d_rate=0.25,
            second_action_rate=0.20,
            share_output_rate=0.10,
            organic_return_path_rate=0.15,
            premium_interest_signal_rate=0.10,
            owner_minutes_per_active_user=8.0,
            general_ai_substitution_rate=0.50,
            policy_or_safety_incidents=0,
        )
        data.update(overrides)
        return HundredUserEvidence(**data)

    def test_exact_research_thresholds_can_reach_next_stage_candidate(self):
        out = assess_hundred_user_stage(self.base())
        self.assertEqual(out["decision"], "NEXT_STAGE_RESEARCH_CANDIDATE")
        self.assertEqual(out["blockers"], [])

    def test_less_than_hundred_users_blocks(self):
        out = assess_hundred_user_stage(self.base(users_observed=99))
        self.assertIn("HUNDRED_USERS_NOT_OBSERVED", out["blockers"])

    def test_weak_value_and_state_block(self):
        out = assess_hundred_user_stage(self.base(first_value_rate=0.49, saved_state_rate=0.29))
        self.assertIn("FIRST_VALUE_TOO_WEAK", out["blockers"])
        self.assertIn("OWNED_STATE_TOO_WEAK", out["blockers"])

    def test_weak_repeat_and_second_action_block(self):
        out = assess_hundred_user_stage(self.base(return_7d_rate=0.24, second_action_rate=0.19))
        self.assertIn("REPEAT_USE_TOO_WEAK", out["blockers"])
        self.assertIn("SECOND_DECISION_TOO_WEAK", out["blockers"])

    def test_weak_organic_return_path_blocks(self):
        out = assess_hundred_user_stage(self.base(organic_return_path_rate=0.14))
        self.assertIn("ORGANIC_RETURN_PATH_TOO_WEAK", out["blockers"])

    def test_generic_ai_substitution_and_owner_burden_block(self):
        out = assess_hundred_user_stage(self.base(
            general_ai_substitution_rate=0.51,
            owner_minutes_per_active_user=8.1,
        ))
        self.assertIn("GENERIC_AI_SUBSTITUTION_TOO_HIGH", out["blockers"])
        self.assertIn("OWNER_BURDEN_TOO_HIGH", out["blockers"])

    def test_policy_or_safety_incident_blocks(self):
        out = assess_hundred_user_stage(self.base(policy_or_safety_incidents=1))
        self.assertIn("POLICY_OR_SAFETY_INCIDENT_REVIEW_REQUIRED", out["blockers"])

    def test_hundred_user_assessment_never_grants_live_authority(self):
        out = assess_hundred_user_stage(self.base())
        for key in (
            "live_test_authorized",
            "recruitment_authorized",
            "publication_authorized",
            "spend_authorized",
            "payment_collection_authorized",
            "runtime_activation_authorized",
            "adoption_authorized",
        ):
            self.assertFalse(out[key])

    def test_first_wedge_is_hypothesis_and_still_owner_gated(self):
        spec = build_first_wedge_spec()
        self.assertEqual(spec["stage"], "HUNDRED_USER_GENERAL")
        self.assertEqual(spec["candidate"], "FASHION_TREND_COMMENTARY_TO_OWNED_WARDROBE_ACTION")
        self.assertFalse(spec["live_execution_authorized"])
        self.assertTrue(spec["owner_gate_still_required_for_live_test"])


if __name__ == "__main__":
    unittest.main()
