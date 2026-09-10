import unittest

from research.opportunity_engine_v0.leverage import (
    LeverageDecision,
    LeverageKind,
    LeverageOption,
    LeverageScan,
    assess_leverage,
    conservative_combined_multiplier,
)


def option(**overrides):
    data = dict(
        name="existing-marketplace distribution",
        kind=LeverageKind.DISTRIBUTION,
        verified_available=True,
        evidence_count=2,
        expected_output_multiplier=2.0,
        setup_cost_yen=0,
        setup_days=1,
        recurring_cost_yen_month=0,
        owner_hours_month=1,
        automation_gain_pct=20,
        reusable_asset_gain=3,
        copy_exposure_risk=1,
        vendor_lock_in_risk=1,
        legal_risk=1,
        reversibility=5,
        existing_system_share=0.90,
    )
    data.update(overrides)
    return LeverageOption(**data)


def scan(**overrides):
    data = dict(
        searched_at="2026-09-11T07:00:00+09:00",
        distribution_checked=True,
        automation_checked=True,
        ai_checked=True,
        monetization_checked=True,
        data_checked=True,
        reuse_checked=True,
        geography_checked=True,
        partner_checked=True,
        infrastructure_checked=True,
        options=(option(),),
    )
    data.update(overrides)
    return LeverageScan(**data)


class LeverageTests(unittest.TestCase):
    def test_broad_leverage_search_is_mandatory(self):
        result = assess_leverage(scan(geography_checked=False))
        self.assertEqual(result.decision, LeverageDecision.SEARCH_INCOMPLETE)
        self.assertIn("LEVERAGE_SEARCH_INCOMPLETE", result.hard_failures)

    def test_existing_system_leverage_can_rank(self):
        result = assess_leverage(scan())
        self.assertEqual(result.decision, LeverageDecision.LEVERAGE_READY)
        self.assertEqual(result.ranked[0].option.name, "existing-marketplace distribution")
        self.assertIn("HIGH_EXISTING_SYSTEM_REUSE", result.ranked[0].reasons)
        self.assertIn("HIGH_REVERSIBILITY", result.ranked[0].reasons)

    def test_copy_exposure_can_disqualify_apparent_growth(self):
        dangerous = option(
            name="publish core discovery method",
            expected_output_multiplier=8.0,
            copy_exposure_risk=5,
        )
        result = assess_leverage(scan(options=(dangerous,)))
        self.assertEqual(result.decision, LeverageDecision.NO_SAFE_LEVERAGE)
        self.assertIn("COPY_EXPOSURE_TOO_HIGH", result.hard_failures)

    def test_human_scaling_leverage_is_rejected_for_owner_constraints(self):
        call_center = option(
            name="sales-call expansion",
            expected_output_multiplier=6.0,
            requires_team=True,
            requires_sales_calls=True,
        )
        result = assess_leverage(scan(options=(call_center,)))
        self.assertEqual(result.decision, LeverageDecision.NO_SAFE_LEVERAGE)
        self.assertIn("REQUIRES_TEAM", result.hard_failures)
        self.assertIn("REQUIRES_SALES_CALLS", result.hard_failures)

    def test_compounding_data_and_automation_are_rewarded(self):
        compound = option(
            name="automated outcome-history loop",
            kind=LeverageKind.DATA,
            expected_output_multiplier=1.5,
            automation_gain_pct=80,
            reusable_asset_gain=5,
            existing_system_share=0.85,
        )
        result = assess_leverage(scan(options=(compound,)))
        self.assertEqual(result.decision, LeverageDecision.LEVERAGE_READY)
        self.assertIn("STRONG_AUTOMATION_GAIN", result.ranked[0].reasons)
        self.assertIn("COMPOUNDING_ASSET", result.ranked[0].reasons)

    def test_combined_multiplier_is_conservative_not_naively_multiplicative(self):
        options = (
            option(name="A", expected_output_multiplier=3.0),
            option(name="B", expected_output_multiplier=2.0),
            option(name="C", expected_output_multiplier=2.0),
        )
        estimate = conservative_combined_multiplier(options)
        self.assertEqual(estimate, 3.75)
        self.assertLess(estimate, 12.0)

    def test_deceptive_or_high_legal_risk_leverage_is_never_a_weapon(self):
        deceptive = option(name="deceptive urgency", deceptive_tactics_required=True)
        risky = option(name="legally risky shortcut", legal_risk=5)
        result = assess_leverage(scan(options=(deceptive, risky)))
        self.assertEqual(result.decision, LeverageDecision.NO_SAFE_LEVERAGE)
        self.assertIn("DECEPTIVE_TACTICS_REQUIRED", result.hard_failures)
        self.assertIn("LEGAL_RISK_TOO_HIGH", result.hard_failures)


if __name__ == "__main__":
    unittest.main()
