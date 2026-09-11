import unittest

from research.opportunity_engine_v0.scale import (
    ScaleClass,
    ScalePolicy,
    ScaleProfile,
    evaluate_scale,
)


POLICY = ScalePolicy(
    sustain_monthly_profit_yen=300000,
    growth_monthly_profit_yen=1000000,
    portfolio_monthly_profit_yen=5000000,
    platform_monthly_profit_yen=20000000,
)


def profile(**overrides):
    data = dict(
        current_monthly_profit_yen=0,
        credible_monthly_profit_ceiling_yen=1200000,
        months_to_ceiling=6,
        existing_service_coverage=0.90,
        custom_build_share=0.10,
        automation_ratio=0.90,
        owner_hours_per_week_at_ceiling=5,
        scale_steps=("prove one channel", "automate delivery", "replicate to adjacent demand"),
        ceiling_blocker="distribution saturation",
    )
    data.update(overrides)
    return ScaleProfile(**data)


class ScaleTests(unittest.TestCase):
    def test_path_beyond_small_income_is_visible(self):
        result = evaluate_scale(profile(), POLICY)
        self.assertEqual(result.scale_class, ScaleClass.GROWTH)
        self.assertIn("HAS_PATH_TO_SUSTAINING_INCOME", result.reasons)

    def test_low_ceiling_is_not_mistaken_for_a_living_business(self):
        result = evaluate_scale(
            profile(
                credible_monthly_profit_ceiling_yen=120000,
                scale_steps=("capture short demand",),
            ),
            POLICY,
        )
        self.assertEqual(result.scale_class, ScaleClass.TACTICAL)
        self.assertIn("CEILING_BELOW_SUSTAINING_TARGET", result.blockers)

    def test_existing_services_are_rewarded(self):
        result = evaluate_scale(profile(), POLICY)
        self.assertGreaterEqual(result.existing_system_leverage_score, 85)
        self.assertIn("EXISTING_SYSTEM_LEVERAGE_HIGH", result.reasons)

    def test_build_heavy_path_is_flagged(self):
        result = evaluate_scale(
            profile(existing_service_coverage=0.20, custom_build_share=0.70),
            POLICY,
        )
        self.assertIn("CUSTOM_BUILD_TOO_HEAVY", result.blockers)

    def test_human_scaling_constraints_are_flagged(self):
        result = evaluate_scale(
            profile(
                owner_hours_per_week_at_ceiling=30,
                requires_team_at_ceiling=True,
                requires_sales_calls_at_ceiling=True,
            ),
            POLICY,
        )
        self.assertIn("OWNER_TIME_CEILING_TOO_HIGH", result.blockers)
        self.assertIn("TEAM_REQUIRED_AT_CEILING", result.blockers)
        self.assertIn("SALES_CALLS_REQUIRED_AT_CEILING", result.blockers)

    def test_higher_scale_classes_exist(self):
        self.assertEqual(
            evaluate_scale(profile(credible_monthly_profit_ceiling_yen=6000000), POLICY).scale_class,
            ScaleClass.PORTFOLIO,
        )
        self.assertEqual(
            evaluate_scale(profile(credible_monthly_profit_ceiling_yen=25000000), POLICY).scale_class,
            ScaleClass.PLATFORM,
        )


if __name__ == "__main__":
    unittest.main()
