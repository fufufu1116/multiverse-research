import unittest

from research.opportunity_engine_v0.market_dynamics import (
    MarketDynamics,
    MarketPattern,
    assess_market_dynamics,
)


class MarketDynamicsTests(unittest.TestCase):
    def test_symbiotic_requires_mutual_value_and_embeddedness(self) -> None:
        result = assess_market_dynamics(
            MarketDynamics(
                transmission=4,
                host_fit=5,
                habituation_immunity=1,
                ai_substitution_immunity=1,
                incumbent_immunity=2,
                mutation_capacity=4,
                recurrence=4,
                network_effect=4,
                embeddedness=5,
                mutual_value=5,
            )
        )
        self.assertEqual(result.pattern, MarketPattern.SYMBIOTIC)
        self.assertTrue(result.eligible)
        self.assertIn("strong_durable_mutual_value", result.reasons)

    def test_harmful_dependence_fails_closed(self) -> None:
        result = assess_market_dynamics(
            MarketDynamics(
                transmission=5,
                host_fit=5,
                habituation_immunity=1,
                ai_substitution_immunity=1,
                incumbent_immunity=1,
                mutation_capacity=5,
                recurrence=5,
                network_effect=5,
                embeddedness=5,
                mutual_value=2,
                harmful_dependence_risk=5,
            )
        )
        self.assertFalse(result.eligible)
        self.assertIn("harmful_dependence_risk_high", result.reasons)

    def test_deceptive_retention_fails_closed(self) -> None:
        result = assess_market_dynamics(
            MarketDynamics(
                transmission=4,
                host_fit=4,
                habituation_immunity=2,
                ai_substitution_immunity=2,
                incumbent_immunity=2,
                mutation_capacity=3,
                recurrence=3,
                network_effect=3,
                embeddedness=4,
                mutual_value=3,
                deceptive_retention_required=True,
            )
        )
        self.assertFalse(result.eligible)
        self.assertIn("deceptive_retention_required", result.reasons)

    def test_high_immunity_pressure_is_explicit(self) -> None:
        result = assess_market_dynamics(
            MarketDynamics(
                transmission=5,
                host_fit=4,
                habituation_immunity=5,
                ai_substitution_immunity=5,
                incumbent_immunity=4,
                mutation_capacity=2,
                recurrence=1,
                network_effect=4,
                embeddedness=1,
                mutual_value=2,
            )
        )
        self.assertGreaterEqual(result.immunity_pressure, 4)
        self.assertIn("high_immunity_pressure", result.reasons)

    def test_event_triggered_delayed_market_can_be_latent(self) -> None:
        result = assess_market_dynamics(
            MarketDynamics(
                transmission=2,
                host_fit=4,
                habituation_immunity=2,
                ai_substitution_immunity=2,
                incumbent_immunity=2,
                mutation_capacity=3,
                recurrence=2,
                network_effect=1,
                embeddedness=1,
                mutual_value=3,
                latency_days=30,
                event_triggered=True,
            )
        )
        self.assertEqual(result.pattern, MarketPattern.LATENT)

    def test_recurring_nonembedded_market_is_seasonal(self) -> None:
        result = assess_market_dynamics(
            MarketDynamics(
                transmission=3,
                host_fit=4,
                habituation_immunity=2,
                ai_substitution_immunity=2,
                incumbent_immunity=2,
                mutation_capacity=3,
                recurrence=5,
                network_effect=2,
                embeddedness=2,
                mutual_value=4,
            )
        )
        self.assertEqual(result.pattern, MarketPattern.SEASONAL)


if __name__ == "__main__":
    unittest.main()
