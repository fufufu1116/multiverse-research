import unittest

from research.opportunity_engine_v0.provider_escalation import plan_provider_escalation


class ProviderEscalationTests(unittest.TestCase):
    def base(self, **overrides):
        values = {
            "current_provider_count": 1,
            "uncertainty_score": 3,
            "disagreement_score": 2,
            "max_unresolved_severity": "MEDIUM",
            "expected_upside_yen": 100000.0,
            "downside_if_wrong_yen": 50000.0,
            "estimated_next_review_cost_yen": 500.0,
            "max_review_budget_yen": 2000.0,
            "local_falsification_available": False,
            "official_or_deterministic_check_available": False,
            "high_stakes_domain": False,
        }
        values.update(overrides)
        return plan_provider_escalation(**values)

    def test_cross_provider_review_is_recommended_when_material_and_uncertain(self):
        result = self.base()
        self.assertEqual(result["state"], "ADD_ONE_CROSS_PROVIDER_CHALLENGE")
        self.assertFalse(result["provider_call_authorized"])
        self.assertFalse(result["spend_authorized"])

    def test_local_falsification_precedes_paid_provider_when_disagreement_exists(self):
        result = self.base(local_falsification_available=True)
        self.assertEqual(result["state"], "LOCAL_FALSIFICATION_FIRST")

    def test_high_stakes_official_check_precedes_model_escalation(self):
        result = self.base(
            high_stakes_domain=True,
            official_or_deterministic_check_available=True,
        )
        self.assertEqual(result["state"], "PRIMARY_OR_DETERMINISTIC_CHECK_FIRST")

    def test_budget_blocks_paid_escalation(self):
        result = self.base(
            estimated_next_review_cost_yen=5000.0,
            max_review_budget_yen=1000.0,
        )
        self.assertEqual(result["state"], "PAID_ESCALATION_BLOCKED_BY_BUDGET")

    def test_extra_provider_not_added_when_cross_provider_review_is_already_calm(self):
        result = self.base(
            current_provider_count=2,
            uncertainty_score=1,
            disagreement_score=0,
            max_unresolved_severity="LOW",
        )
        self.assertEqual(result["state"], "NO_ADDITIONAL_PROVIDER_NEEDED_YET")

    def test_third_provider_is_reserved_for_real_cross_provider_disagreement(self):
        result = self.base(
            current_provider_count=2,
            uncertainty_score=4,
            disagreement_score=4,
            expected_upside_yen=500000.0,
        )
        self.assertEqual(result["state"], "THIRD_PROVIDER_MAY_BE_WORTH_TESTING")

    def test_small_decision_does_not_justify_paid_review_just_because_budget_exists(self):
        result = self.base(
            expected_upside_yen=1000.0,
            downside_if_wrong_yen=500.0,
            estimated_next_review_cost_yen=500.0,
            max_review_budget_yen=5000.0,
        )
        self.assertEqual(result["state"], "CHEAPER_EVIDENCE_BEFORE_PROVIDER_SPEND")


if __name__ == "__main__":
    unittest.main()
