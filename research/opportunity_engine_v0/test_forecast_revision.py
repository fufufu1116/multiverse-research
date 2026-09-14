import unittest

from research.opportunity_engine_v0.forecast_ledger import ForecastCard, forecast_commitment
from research.opportunity_engine_v0.forecast_revision import ExternalChange, assess_forecast_revision_need, bind_successor_forecast


class ForecastRevisionTests(unittest.TestCase):
    def card(self, forecast_id="f-1", confidence=3):
        return ForecastCard(
            forecast_id=forecast_id,
            candidate_name="example",
            created_at="2026-09-11T00:00:00Z",
            source_signal_ids=("s-1",),
            predicted_peak_start="2026-09-20",
            predicted_peak_end="2026-10-20",
            expected_demand_life_days=90,
            predicted_competitor_arrival_days=30,
            predicted_ai_or_incumbent_absorption_days=120,
            predicted_next_actions=("research", "test", "measure"),
            monetization_hypothesis="subscription",
            kill_condition="economics fail",
            confidence=confidence,
        )

    def change(self, materiality=4):
        return ExternalChange(
            change_id="chg-1",
            observed_at="2026-09-12T00:00:00Z",
            change_type="PLATFORM_POLICY",
            evidence_refs=("official-policy-1",),
            materiality=materiality,
        )

    def test_material_change_requires_fresh_research_not_forecast_mutation(self):
        card = self.card()
        result = assess_forecast_revision_need(
            current_card=card,
            current_commitment=forecast_commitment(card),
            change=self.change(4),
            shock_verdict="HOLD",
        )
        self.assertEqual(result["decision"], "FRESH_RESEARCH_REQUIRED")
        self.assertFalse(result["old_forecast_mutation_authorized"])
        self.assertTrue(result["new_forecast_must_use_new_id"])

    def test_adaptation_verdict_triggers_research_even_at_lower_materiality(self):
        card = self.card()
        result = assess_forecast_revision_need(
            current_card=card,
            current_commitment=forecast_commitment(card),
            change=self.change(2),
            shock_verdict="ADAPT",
        )
        self.assertEqual(result["decision"], "FRESH_RESEARCH_REQUIRED")

    def test_small_nonadaptive_change_keeps_current_forecast(self):
        card = self.card()
        result = assess_forecast_revision_need(
            current_card=card,
            current_commitment=forecast_commitment(card),
            change=self.change(1),
            shock_verdict="HOLD",
        )
        self.assertEqual(result["decision"], "KEEP_CURRENT")

    def test_rejected_adaptation_does_not_create_positive_revision_path(self):
        card = self.card()
        result = assess_forecast_revision_need(
            current_card=card,
            current_commitment=forecast_commitment(card),
            change=self.change(5),
            shock_verdict="REJECT",
        )
        self.assertEqual(result["decision"], "REJECT_ADAPTATION")
        self.assertFalse(result["automatic_execution_authorized"])

    def test_tampered_prior_forecast_fails_closed(self):
        card = self.card()
        with self.assertRaises(ValueError):
            assess_forecast_revision_need(
                current_card=card,
                current_commitment="bad",
                change=self.change(),
                shock_verdict="ADAPT",
            )

    def test_successor_is_bound_without_replacing_prior(self):
        prior = self.card("f-1")
        successor = self.card("f-2", confidence=4)
        result = bind_successor_forecast(
            prior_card=prior,
            prior_commitment=forecast_commitment(prior),
            successor_card=successor,
            triggering_change_id="chg-1",
        )
        self.assertEqual(result["prior_forecast_id"], "f-1")
        self.assertEqual(result["successor_forecast_id"], "f-2")
        self.assertTrue(result["prior_forecast_preserved"])

    def test_successor_cannot_reuse_prior_id(self):
        prior = self.card("f-1")
        with self.assertRaises(ValueError):
            bind_successor_forecast(
                prior_card=prior,
                prior_commitment=forecast_commitment(prior),
                successor_card=self.card("f-1", confidence=4),
                triggering_change_id="chg-1",
            )


if __name__ == "__main__":
    unittest.main()
