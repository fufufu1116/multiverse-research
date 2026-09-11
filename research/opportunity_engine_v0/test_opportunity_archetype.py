import unittest

from research.opportunity_engine_v0.opportunity_archetype import (
    OpportunityArchetype,
    classify_opportunity_archetype,
    ui_label,
)


class OpportunityArchetypeTests(unittest.TestCase):
    def test_short_fast_spike_is_one_hit(self):
        result = classify_opportunity_archetype(
            demand_life_days=30,
            build_days=1,
            payback_days=3,
            spike_concentration_pct=80,
            recurrence_score=0,
            repeatability_score=1,
            durable_asset_score=1,
            exit_trigger_defined=True,
        )
        self.assertEqual(result, OpportunityArchetype.SHORT_WAVE_ONE_HIT)
        self.assertEqual(ui_label(result), "使い切り百人将")

    def test_recurring_short_burst_is_separate(self):
        result = classify_opportunity_archetype(
            demand_life_days=60,
            build_days=10,
            payback_days=20,
            spike_concentration_pct=40,
            recurrence_score=4,
            repeatability_score=2,
            durable_asset_score=2,
            exit_trigger_defined=True,
        )
        self.assertEqual(result, OpportunityArchetype.RECURRING_BURST)

    def test_durable_compounder_needs_repeatability_and_asset(self):
        result = classify_opportunity_archetype(
            demand_life_days=730,
            build_days=30,
            payback_days=60,
            spike_concentration_pct=20,
            recurrence_score=4,
            repeatability_score=4,
            durable_asset_score=4,
            exit_trigger_defined=True,
        )
        self.assertEqual(result, OpportunityArchetype.DURABLE_COMPOUNDER)

    def test_missing_exit_trigger_prevents_one_hit_classification(self):
        result = classify_opportunity_archetype(
            demand_life_days=30,
            build_days=1,
            payback_days=3,
            spike_concentration_pct=80,
            recurrence_score=0,
            repeatability_score=1,
            durable_asset_score=1,
            exit_trigger_defined=False,
        )
        self.assertEqual(result, OpportunityArchetype.EXPERIMENT_ONLY)


if __name__ == "__main__":
    unittest.main()
