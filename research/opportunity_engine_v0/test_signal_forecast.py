import unittest

from research.opportunity_engine_v0.forecast_ledger import (
    ForecastCard,
    ForecastOutcome,
    ForecastSettlement,
    forecast_commitment,
    settle_forecast,
)
from research.opportunity_engine_v0.signals import (
    EvidenceRef,
    SignalObservation,
    SignalType,
    evidence_quality,
)


class SignalTests(unittest.TestCase):
    def test_signal_requires_evidence(self):
        with self.assertRaises(ValueError):
            SignalObservation(
                signal_id="s1",
                title="candidate",
                signal_type=SignalType.SEARCH,
                market="JP",
                observed_at="2026-09-11T00:00:00+09:00",
                strength=4,
                purchase_intent_hint=3,
                evidence=(),
            )

    def test_multi_source_with_primary_scores_high(self):
        signal = SignalObservation(
            signal_id="s2",
            title="candidate",
            signal_type=SignalType.RULE_CHANGE,
            market="JP",
            observed_at="2026-09-11T00:00:00+09:00",
            strength=4,
            purchase_intent_hint=4,
            evidence=(
                EvidenceRef("official", "official://notice", "2026-09-11", True),
                EvidenceRef("search", "search://trend", "2026-09-11"),
                EvidenceRef("news", "news://coverage", "2026-09-11"),
            ),
        )
        self.assertEqual(evidence_quality(signal), 5)


class ForecastLedgerTests(unittest.TestCase):
    def _card(self):
        return ForecastCard(
            forecast_id="f1",
            candidate_name="synthetic",
            created_at="2026-09-11T01:00:00+09:00",
            source_signal_ids=("s1", "s2"),
            predicted_peak_start="2026-09-15",
            predicted_peak_end="2026-09-20",
            expected_demand_life_days=30,
            predicted_competitor_arrival_days=10,
            predicted_ai_or_incumbent_absorption_days=45,
            predicted_next_actions=("awareness", "search", "purchase", "competition"),
            monetization_hypothesis="affiliate",
            kill_condition="exit after 40% demand decline",
            confidence=3,
        )

    def test_forecast_is_committed_before_settlement(self):
        card = self._card()
        commitment = forecast_commitment(card)
        result = settle_forecast(
            card=card,
            expected_commitment=commitment,
            settlement=ForecastSettlement(
                forecast_id="f1",
                settled_at="2026-10-20T00:00:00+09:00",
                outcome=ForecastOutcome.WIN,
                observed_profit_yen=50000,
            ),
        )
        self.assertEqual(result["outcome"], "WIN")
        self.assertEqual(result["commitment"], commitment)

    def test_changed_forecast_fails_commitment_check(self):
        card = self._card()
        commitment = forecast_commitment(card)
        changed = ForecastCard(**{**card.__dict__, "confidence": 5})
        with self.assertRaises(ValueError):
            settle_forecast(
                card=changed,
                expected_commitment=commitment,
                settlement=ForecastSettlement(
                    forecast_id="f1",
                    settled_at="2026-10-20T00:00:00+09:00",
                    outcome=ForecastOutcome.WIN,
                ),
            )

    def test_forecast_requires_three_to_seven_steps(self):
        with self.assertRaises(ValueError):
            ForecastCard(
                forecast_id="f2",
                candidate_name="bad",
                created_at="2026-09-11T01:00:00+09:00",
                source_signal_ids=("s1",),
                predicted_peak_start="2026-09-15",
                predicted_peak_end="2026-09-20",
                expected_demand_life_days=10,
                predicted_competitor_arrival_days=3,
                predicted_ai_or_incumbent_absorption_days=7,
                predicted_next_actions=("one", "two"),
                monetization_hypothesis="ads",
                kill_condition="stop",
                confidence=2,
            )


if __name__ == "__main__":
    unittest.main()
