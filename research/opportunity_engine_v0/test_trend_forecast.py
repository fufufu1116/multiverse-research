import unittest

from research.opportunity_engine_v0.trend_forecast import (
    TrendForecastPosture,
    TrendSignalSnapshot,
    assess_trend_signal,
)


class TrendForecastTests(unittest.TestCase):
    def base(self, **overrides):
        data = dict(
            candidate_id="candidate-x",
            observed_on="2026-09-11",
            early_community_heat=4,
            creator_adoption_acceleration=4,
            cross_region_spread=4,
            derivative_creation=3,
            search_or_save_intent=4,
            collectibility_or_identity=3,
            repeat_mention_persistence=4,
            mainstream_saturation=1,
            evidence_strength=4,
        )
        data.update(overrides)
        return TrendSignalSnapshot(**data)

    def test_strong_early_signals_can_be_forecast_candidate(self):
        out = assess_trend_signal(self.base())
        self.assertEqual(out["posture"], TrendForecastPosture.FORECAST_CANDIDATE.value)
        self.assertEqual(out["horizons_days"], [30, 90, 180])
        self.assertTrue(out["settlement_required"])

    def test_mainstream_candidate_is_too_late_for_early_call(self):
        out = assess_trend_signal(self.base(mainstream_saturation=4))
        self.assertEqual(out["posture"], TrendForecastPosture.IGNORE.value)
        self.assertIn("ALREADY_TOO_MAINSTREAM_FOR_EARLY_CALL", out["blockers"])

    def test_weak_evidence_prevents_promotion(self):
        out = assess_trend_signal(self.base(evidence_strength=1))
        self.assertNotEqual(out["posture"], TrendForecastPosture.FORECAST_CANDIDATE.value)
        self.assertIn("EVIDENCE_TOO_WEAK", out["blockers"])

    def test_no_propagation_acceleration_prevents_promotion(self):
        out = assess_trend_signal(self.base(creator_adoption_acceleration=1, cross_region_spread=1))
        self.assertIn("NO_PROPAGATION_ACCELERATION", out["blockers"])

    def test_commitment_is_deterministic_for_same_snapshot(self):
        a = assess_trend_signal(self.base())
        b = assess_trend_signal(self.base())
        self.assertEqual(a["forecast_commitment"], b["forecast_commitment"])

    def test_changed_snapshot_changes_commitment(self):
        a = assess_trend_signal(self.base())
        b = assess_trend_signal(self.base(search_or_save_intent=5))
        self.assertNotEqual(a["forecast_commitment"], b["forecast_commitment"])

    def test_no_live_authority(self):
        out = assess_trend_signal(self.base())
        self.assertFalse(out["automatic_execution_authorized"])
        self.assertFalse(out["spend_authorized"])
        self.assertFalse(out["publication_authorized"])
        self.assertFalse(out["adoption_authorized"])
        self.assertFalse(out["runtime_activation_authorized"])

    def test_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.base(early_community_heat=True)


if __name__ == "__main__":
    unittest.main()
