import unittest

from research.opportunity_engine_v0.force_multiplier import (
    Capability,
    CapabilityProfile,
    LoadoutDecision,
    LoadoutPolicy,
    PairInteraction,
    TrainingAction,
    choose_training_plan,
    optimize_loadout,
)
from research.opportunity_engine_v0.leverage import LeverageKind, LeverageOption, LeverageScan


def option(name, kind, multiplier=1.5, **overrides):
    data = dict(
        name=name,
        kind=kind,
        verified_available=True,
        evidence_count=2,
        expected_output_multiplier=multiplier,
        setup_cost_yen=500,
        setup_days=0.5,
        recurring_cost_yen_month=0,
        owner_hours_month=0.5,
        automation_gain_pct=30,
        reusable_asset_gain=3,
        copy_exposure_risk=1,
        vendor_lock_in_risk=1,
        legal_risk=1,
        reversibility=5,
        existing_system_share=0.9,
    )
    data.update(overrides)
    return LeverageOption(**data)


def scan(options, **overrides):
    data = dict(
        searched_at="2026-09-11T07:03:00+09:00",
        distribution_checked=True,
        automation_checked=True,
        ai_checked=True,
        monetization_checked=True,
        data_checked=True,
        reuse_checked=True,
        geography_checked=True,
        partner_checked=True,
        infrastructure_checked=True,
        options=tuple(options),
    )
    data.update(overrides)
    return LeverageScan(**data)


POLICY = LoadoutPolicy(
    max_setup_cost_yen=5000,
    max_setup_days=3,
    max_recurring_cost_yen_month=3000,
    max_owner_hours_month=3,
    max_options=3,
    min_option_score=20,
)


class LoadoutTests(unittest.TestCase):
    def test_search_must_be_complete_before_claiming_best_loadout(self):
        s = scan([option("distribution", LeverageKind.DISTRIBUTION)], ai_checked=False)
        self.assertEqual(optimize_loadout(s, POLICY).decision, LoadoutDecision.SEARCH_INCOMPLETE)

    def test_complementary_stack_can_beat_single_flashy_option(self):
        distribution = option("distribution", LeverageKind.DISTRIBUTION, 1.7)
        automation = option("automation", LeverageKind.AUTOMATION, 1.6, automation_gain_pct=70)
        flashy_ai = option("flashy-ai", LeverageKind.AI, 2.2, recurring_cost_yen_month=2500, owner_hours_month=1.5)
        result = optimize_loadout(
            scan([distribution, automation, flashy_ai]),
            POLICY,
            (PairInteraction("distribution", "automation", synergy=5),),
        )
        names = {item.name for item in result.selected}
        self.assertEqual(result.decision, LoadoutDecision.LOADOUT_READY)
        self.assertIn("distribution", names)
        self.assertIn("automation", names)
        self.assertIn("VERIFIED_COMPLEMENTARITY", result.reasons)

    def test_stack_respects_cash_and_owner_time_caps(self):
        expensive = option("expensive", LeverageKind.DISTRIBUTION, 5.0, setup_cost_yen=6000)
        labor = option("labor", LeverageKind.AUTOMATION, 5.0, owner_hours_month=4)
        result = optimize_loadout(scan([expensive, labor]), POLICY)
        self.assertEqual(result.decision, LoadoutDecision.NO_FEASIBLE_LOADOUT)

    def test_unsafe_copy_exposure_is_not_selected_even_with_huge_multiplier(self):
        unsafe = option("publish-core", LeverageKind.DATA, 10.0, copy_exposure_risk=5)
        safe = option("safe", LeverageKind.REUSE, 1.4)
        result = optimize_loadout(scan([unsafe, safe]), POLICY)
        self.assertEqual(tuple(item.name for item in result.selected), ("safe",))

    def test_multiplier_remains_conservative(self):
        a = option("a", LeverageKind.DISTRIBUTION, 3.0)
        b = option("b", LeverageKind.AUTOMATION, 2.0)
        c = option("c", LeverageKind.MONETIZATION, 2.0)
        result = optimize_loadout(scan([a, b, c]), POLICY)
        self.assertLess(result.conservative_multiplier, 12.0)


class TrainingTests(unittest.TestCase):
    def test_training_targets_weak_measurable_capabilities(self):
        profile = CapabilityProfile(4, 1, 2, 4, 1, 3, 1)
        actions = (
            TrainingAction("distribution experiment", Capability.DISTRIBUTION, True, True, 4, 4, 500, 1, 1, 1),
            TrainingAction("forecast calibration", Capability.FORECASTING, True, True, 4, 5, 0, 1, 1, 1),
            TrainingAction("data loop", Capability.DATA, True, True, 4, 5, 500, 1, 1, 1),
            TrainingAction("already-strong monetization", Capability.MONETIZATION, True, True, 3, 2, 0, 1, 1, 1),
        )
        plan = choose_training_plan(profile, actions, max_actions=3, max_cost_yen=1500, max_owner_hours=3)
        targets = {item.target for item in plan.actions}
        self.assertEqual(targets, {Capability.DISTRIBUTION, Capability.FORECASTING, Capability.DATA})
        self.assertIn("WEAKEST_LINKS_FIRST", plan.reasons)
        self.assertIn("MEASURABLE_TRAINING", plan.reasons)

    def test_training_never_exposes_core_or_uses_high_legal_risk(self):
        profile = CapabilityProfile(1, 1, 1, 1, 1, 1, 1)
        actions = (
            TrainingAction("leak-core", Capability.DATA, True, True, 5, 5, 0, 0, 0, 1, exposes_core=True),
            TrainingAction("risky", Capability.DISTRIBUTION, True, True, 5, 5, 0, 0, 0, 5),
            TrainingAction("safe-calibration", Capability.FORECASTING, True, True, 3, 5, 0, 1, 1, 1),
        )
        plan = choose_training_plan(profile, actions)
        self.assertEqual(tuple(item.name for item in plan.actions), ("safe-calibration",))


if __name__ == "__main__":
    unittest.main()
