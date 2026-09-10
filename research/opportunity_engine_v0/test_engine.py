import unittest

from research.opportunity_engine_v0.engine import evaluate, simulate_unit_economics
from research.opportunity_engine_v0.model import CompetitorResearch, Decision, OpportunityCandidate, RevenueRoute


COMPLETE_COMPETITOR_RESEARCH = CompetitorResearch(
    direct_competitors_checked=True,
    substitutes_checked=True,
    bigtech_replacement_checked=True,
    why_not_already_common_explained=True,
    existing_systems_to_reuse=("existing-search", "existing-marketplace"),
)


def candidate(**overrides):
    data = dict(
        name="synthetic opportunity",
        evidence_verified=True,
        buyer_clarity=4,
        attention=4,
        purchase_intent=4,
        why_now=4,
        why_not_before=4,
        competitor_pressure=2,
        incumbent_crush_risk=2,
        ai_substitutability=2,
        proprietary_edge=4,
        action_completion=4,
        reusable_asset=4,
        distribution=4,
        legal_risk=1,
        human_burden=1,
        initial_cost_yen=3000,
        build_days=2,
        demand_life_days=30,
        expected_profit_low_yen=6000,
        expected_profit_base_yen=30000,
        expected_profit_high_yen=120000,
        future_steps=(
            "attention rises",
            "purchase intent peaks",
            "competitors enter",
            "official substitute appears",
            "demand falls",
        ),
        exit_trigger="stop acquisition when demand falls 40% from peak",
        competitor_research=COMPLETE_COMPETITOR_RESEARCH,
    )
    data.update(overrides)
    return OpportunityCandidate(**data)


class OpportunityEngineTests(unittest.TestCase):
    def test_competitor_research_is_mandatory(self):
        c = candidate(
            competitor_research=CompetitorResearch(
                direct_competitors_checked=True,
                substitutes_checked=False,
                bigtech_replacement_checked=True,
                why_not_already_common_explained=True,
            )
        )
        result = evaluate(c)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("COMPETITOR_RESEARCH_INCOMPLETE", result.hard_failures)

    def test_plain_ai_answer_product_is_rejected(self):
        c = candidate(
            name="generic AI guide",
            ai_substitutability=5,
            proprietary_edge=1,
            action_completion=1,
        )
        result = evaluate(c)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("AI_SUBSTITUTABLE_WITHOUT_EDGE", result.hard_failures)

    def test_short_lived_opportunity_can_pass_when_fast_and_profitable(self):
        c = candidate(
            demand_life_days=14,
            build_days=1,
            expected_profit_low_yen=10000,
            initial_cost_yen=1000,
            attention=5,
            purchase_intent=4,
        )
        result = evaluate(c)
        self.assertIn(result.decision, (Decision.MICRO_TEST, Decision.BUILD_CANDIDATE))
        self.assertIn("FAST_ENOUGH_FOR_SHORT_LIVED_DEMAND", result.reasons)

    def test_short_lived_opportunity_rejected_when_build_too_slow(self):
        c = candidate(demand_life_days=10, build_days=5)
        result = evaluate(c)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("BUILD_TOO_SLOW_FOR_DEMAND_LIFE", result.hard_failures)

    def test_exit_trigger_required_for_short_lived_opportunity(self):
        c = candidate(exit_trigger="")
        result = evaluate(c)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("MISSING_EXIT_TRIGGER", result.hard_failures)

    def test_three_step_future_horizon_is_required(self):
        c = candidate(future_steps=("launch", "peak"))
        result = evaluate(c)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("FUTURE_HORIZON_TOO_SHALLOW", result.hard_failures)

    def test_deception_is_hard_reject(self):
        result = evaluate(candidate(deceptive_tactics_required=True))
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("DECEPTIVE_TACTICS_REQUIRED", result.hard_failures)

    def test_unverified_scandal_claims_are_hard_reject(self):
        result = evaluate(candidate(unverified_personal_claims_required=True))
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIn("UNVERIFIED_PERSONAL_CLAIMS_REQUIRED", result.hard_failures)

    def test_unit_economics(self):
        result = simulate_unit_economics(
            visitors=10000,
            conversion_rate=0.02,
            profit_per_conversion_yen=1500,
            ad_revenue_per_1000_visitors_yen=300,
            variable_cost_per_visitor_yen=5,
            fixed_cost_yen=20000,
        )
        self.assertEqual(result["conversions"], 200)
        self.assertEqual(result["profit_yen"], 233000)

    def test_revenue_route_prefers_internal_asset_for_data_moat(self):
        c = candidate(
            attention=1,
            purchase_intent=1,
            buyer_clarity=2,
            proprietary_edge=5,
            reusable_asset=5,
            action_completion=2,
            distribution=2,
            demand_life_days=None,
            exit_trigger="",
        )
        result = evaluate(c)
        self.assertEqual(result.revenue_route, RevenueRoute.INTERNAL_ASSET)


if __name__ == "__main__":
    unittest.main()
