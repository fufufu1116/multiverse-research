import unittest

from .three_engine_funnel import (
    PersonalizationTier,
    ThreeEngineSurface,
    build_clean_funnel,
    score_three_engine_surface,
)


class ThreeEngineFunnelTests(unittest.TestCase):
    def surface(self, **overrides):
        values = dict(
            domain="recipes",
            branded_content_strength=4,
            repeat_intent=5,
            shareable_output_strength=4,
            exclusive_owned_utility=5,
            first_party_state_value=4,
            monetization_fit=4,
            platform_dependency_risk=2,
            policy_fragility=1,
        )
        values.update(overrides)
        return ThreeEngineSurface(**values)

    def test_strong_domain_becomes_priority_research_candidate(self):
        result = score_three_engine_surface(self.surface())
        self.assertEqual(result["posture"], "PRIORITY_RESEARCH_CANDIDATE")
        self.assertTrue(result["score_is_hypothesis_only"])
        self.assertFalse(result["live_execution_authorized"])

    def test_weak_owned_utility_blocks_priority(self):
        result = score_three_engine_surface(self.surface(exclusive_owned_utility=1))
        self.assertIn("OWNED_UTILITY_TOO_WEAK", result["blockers"])
        self.assertEqual(result["posture"], "RESEARCH_OR_REDESIGN")

    def test_high_policy_fragility_blocks_priority(self):
        result = score_three_engine_surface(self.surface(policy_fragility=4))
        self.assertIn("POLICY_FRAGILITY_HIGH", result["blockers"])

    def test_cross_context_requires_permission(self):
        result = build_clean_funnel(
            personalization_tier=PersonalizationTier.PERMISSION_GATED_CROSS_CONTEXT,
            tracking_permission=False,
        )
        self.assertEqual(result["decision"], "BLOCK_CROSS_CONTEXT_PERSONALIZATION")
        self.assertEqual(result["fallback_tier"], PersonalizationTier.FIRST_PARTY_HISTORY.value)

    def test_first_party_funnel_does_not_require_cross_context_permission(self):
        result = build_clean_funnel(
            personalization_tier=PersonalizationTier.FIRST_PARTY_HISTORY,
            tracking_permission=False,
        )
        self.assertEqual(result["decision"], "CLEAN_FUNNEL_DEFINED")
        self.assertIn("repeat_loop_rate", result["metrics"])
        self.assertFalse(result["adoption_authorized"])

    def test_contextual_funnel_contains_premium_measurement(self):
        result = build_clean_funnel(
            personalization_tier=PersonalizationTier.CONTEXTUAL,
            tracking_permission=False,
        )
        self.assertIn("premium_exposure_to_paid_conversion", result["metrics"])
        self.assertIn("PREMIUM_VALUE_AT_RECURRING_FRICTION", result["stages"])


if __name__ == "__main__":
    unittest.main()
