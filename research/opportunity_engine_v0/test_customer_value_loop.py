import unittest

from research.opportunity_engine_v0.customer_value_loop import (
    CustomerValueReturn,
    ValueReturnDecision,
    assess_customer_value_return,
)


class CustomerValueLoopTests(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            utility_gain=5,
            learning_gain=4,
            saved_money_or_time=5,
            identity_or_expression_gain=3,
            community_or_status_gain=2,
            portable_asset_gain=5,
            transparency=5,
            manipulation_risk=0,
            artificial_lock_in=0,
            seller_subsidy_cost=1,
        )
        data.update(overrides)
        return CustomerValueReturn(**data)

    def test_strong_transparent_value_loop_can_be_candidate(self):
        out = assess_customer_value_return(self.base())
        self.assertEqual(out["decision"], ValueReturnDecision.VALUE_LOOP_CANDIDATE.value)
        self.assertGreaterEqual(out["score"], 60)

    def test_manipulation_forces_redesign(self):
        out = assess_customer_value_return(self.base(manipulation_risk=3))
        self.assertEqual(out["decision"], ValueReturnDecision.REDESIGN.value)
        self.assertIn("MANIPULATION_RISK_TOO_HIGH", out["blockers"])

    def test_artificial_lock_in_forces_redesign(self):
        out = assess_customer_value_return(self.base(artificial_lock_in=4))
        self.assertEqual(out["decision"], ValueReturnDecision.REDESIGN.value)
        self.assertIn("ARTIFICIAL_LOCK_IN_TOO_HIGH", out["blockers"])

    def test_low_transparency_forces_redesign(self):
        out = assess_customer_value_return(self.base(transparency=2))
        self.assertEqual(out["decision"], ValueReturnDecision.REDESIGN.value)
        self.assertIn("VALUE_EXCHANGE_NOT_TRANSPARENT", out["blockers"])

    def test_no_strong_nonproduct_value_forces_redesign(self):
        out = assess_customer_value_return(self.base(
            utility_gain=2,
            learning_gain=2,
            saved_money_or_time=2,
            portable_asset_gain=2,
        ))
        self.assertEqual(out["decision"], ValueReturnDecision.REDESIGN.value)
        self.assertIn("NO_STRONG_CUSTOMER_VALUE_BEYOND_PRODUCT", out["blockers"])

    def test_value_loop_never_grants_live_authority(self):
        out = assess_customer_value_return(self.base())
        for key in (
            "automatic_execution_authorized",
            "spend_authorized",
            "publication_authorized",
            "adoption_authorized",
            "runtime_activation_authorized",
        ):
            self.assertFalse(out[key])


if __name__ == "__main__":
    unittest.main()
