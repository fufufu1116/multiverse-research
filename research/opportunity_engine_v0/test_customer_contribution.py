import unittest

from research.opportunity_engine_v0.customer_contribution import (
    ContributionDecision,
    ContributionLoop,
    assess_contribution_loop,
)


class CustomerContributionTests(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            customer_value_score=4,
            contribution_usefulness=4,
            contribution_verifiability=4,
            consent_clarity=5,
            reward_transparency=5,
            portability=4,
            abuse_risk=1,
            manipulation_risk=0,
            estimated_reward_cost_per_user=1.0,
            estimated_incremental_value_per_user=3.0,
        )
        data.update(overrides)
        return ContributionLoop(**data)

    def test_clean_positive_economics_is_testable_not_authorized(self):
        out = assess_contribution_loop(self.base())
        self.assertEqual(out["decision"], ContributionDecision.TESTABLE.value)
        self.assertFalse(out["automatic_execution_authorized"])
        self.assertFalse(out["spend_authorized"])

    def test_manipulation_rejects(self):
        out = assess_contribution_loop(self.base(manipulation_risk=3))
        self.assertEqual(out["decision"], ContributionDecision.REJECT.value)

    def test_unclear_consent_rejects(self):
        out = assess_contribution_loop(self.base(consent_clarity=2))
        self.assertEqual(out["decision"], ContributionDecision.REJECT.value)

    def test_negative_reward_economics_redesigns(self):
        out = assess_contribution_loop(self.base(
            estimated_reward_cost_per_user=4.0,
            estimated_incremental_value_per_user=1.0,
        ))
        self.assertEqual(out["decision"], ContributionDecision.REDESIGN.value)
        self.assertIn("REWARD_COST_EXCEEDS_ESTIMATED_INCREMENTAL_VALUE", out["reasons"])

    def test_high_abuse_risk_redesigns(self):
        out = assess_contribution_loop(self.base(abuse_risk=4))
        self.assertEqual(out["decision"], ContributionDecision.REDESIGN.value)

    def test_customer_contribution_never_becomes_independent_evidence(self):
        out = assess_contribution_loop(self.base())
        self.assertFalse(out["contribution_counts_as_independent_evidence"])
        self.assertTrue(out["requires_measured_outcome_before_learning"])


if __name__ == "__main__":
    unittest.main()
