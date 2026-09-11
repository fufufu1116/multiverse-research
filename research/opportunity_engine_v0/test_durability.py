import unittest

from research.opportunity_engine_v0.durability import (
    DemandDurability,
    DurabilityWaveProfile,
    WaveStage,
    evaluate_durability_wave,
)


def profile(**overrides):
    data = dict(
        demand_persistence=5,
        cross_culture_persistence=4,
        recurring_frequency=5,
        interface_independence=5,
        wave_leverage=4,
        wave_evidence_strength=4,
        independent_adoption_signals=4,
        ecosystem_openness=4,
        incumbent_capture_risk=2,
        regulation_volatility=2,
        human_burden=1,
        enduring_need="food/convenience",
        enabling_wave="agents that can discover and transact",
        why_wave_changes_economics="reduces search and checkout friction",
        historical_analogs=("desktop web commerce", "smartphone commerce"),
    )
    data.update(overrides)
    return DurabilityWaveProfile(**data)


class DurabilityWaveTests(unittest.TestCase):
    def test_foundational_need_can_be_distinguished_from_channel(self):
        result = evaluate_durability_wave(profile())
        self.assertEqual(result.durability, DemandDurability.FOUNDATIONAL)
        self.assertIn("NEED_SURVIVES_CHANNEL_CHANGE", result.reasons)

    def test_hype_without_independent_adoption_evidence_stays_speculative(self):
        result = evaluate_durability_wave(
            profile(wave_evidence_strength=5, independent_adoption_signals=1)
        )
        self.assertEqual(result.wave_stage, WaveStage.SPECULATIVE)
        self.assertIn("WAVE_EVIDENCE_TOO_THIN", result.blockers)

    def test_multiple_strong_signals_can_mark_accelerating_wave(self):
        result = evaluate_durability_wave(profile())
        self.assertEqual(result.wave_stage, WaveStage.ACCELERATING)
        self.assertIn("MULTIPLE_STRONG_ADOPTION_SIGNALS", result.reasons)

    def test_old_market_is_not_automatically_attractive_when_human_burden_is_high(self):
        result = evaluate_durability_wave(
            profile(
                enduring_need="social nightlife",
                human_burden=5,
                regulation_volatility=4,
                ecosystem_openness=2,
            )
        )
        self.assertIn("DIRECT_OPERATION_HUMAN_BURDEN_HIGH", result.blockers)
        self.assertIn("REGULATION_VOLATILITY_HIGH", result.blockers)

    def test_incumbent_capture_risk_is_explicit(self):
        result = evaluate_durability_wave(profile(incumbent_capture_risk=5))
        self.assertIn("INCUMBENT_CAPTURE_RISK_HIGH", result.blockers)

    def test_ephemeral_need_is_not_promoted_by_new_technology_alone(self):
        result = evaluate_durability_wave(
            profile(
                demand_persistence=1,
                cross_culture_persistence=1,
                recurring_frequency=1,
                interface_independence=1,
                wave_leverage=5,
                wave_evidence_strength=5,
                independent_adoption_signals=5,
            )
        )
        self.assertEqual(result.durability, DemandDurability.EPHEMERAL)


if __name__ == "__main__":
    unittest.main()
