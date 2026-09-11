import unittest

from research.opportunity_engine_v0.completion_spine import CompletionSpineInput, build_completion_spine
from research.opportunity_engine_v0.customer_contribution import ContributionLoop
from research.opportunity_engine_v0.customer_value_loop import CustomerValueReturn
from research.opportunity_engine_v0.hundred_user_general import HundredUserEvidence
from research.opportunity_engine_v0.trend_forecast import TrendSignalSnapshot


class CompletionSpineTests(unittest.TestCase):
    def trend(self, **kw):
        data = dict(candidate_id="candidate-x", observed_on="2026-09-11",
                    early_community_heat=4, creator_adoption_acceleration=4,
                    cross_region_spread=4, derivative_creation=4,
                    search_or_save_intent=4, collectibility_or_identity=4,
                    repeat_mention_persistence=4, mainstream_saturation=1,
                    evidence_strength=4)
        data.update(kw)
        return TrendSignalSnapshot(**data)

    def value(self, **kw):
        data = dict(utility_gain=4, learning_gain=4, saved_money_or_time=4,
                    identity_or_expression_gain=4, community_or_status_gain=3,
                    portable_asset_gain=4, transparency=5, manipulation_risk=0,
                    artificial_lock_in=0, seller_subsidy_cost=1)
        data.update(kw)
        return CustomerValueReturn(**data)

    def contribution(self, **kw):
        data = dict(customer_value_score=4, contribution_usefulness=4,
                    contribution_verifiability=4, consent_clarity=5,
                    reward_transparency=5, portability=4, abuse_risk=1,
                    manipulation_risk=0, estimated_reward_cost_per_user=1.0,
                    estimated_incremental_value_per_user=3.0)
        data.update(kw)
        return ContributionLoop(**data)

    def hundred(self, **kw):
        data = dict(users_observed=100, first_value_rate=.70, saved_state_rate=.50,
                    return_7d_rate=.40, second_action_rate=.35, share_output_rate=.20,
                    organic_return_path_rate=.25, premium_interest_signal_rate=.20,
                    owner_minutes_per_active_user=4.0, general_ai_substitution_rate=.30,
                    policy_or_safety_incidents=0)
        data.update(kw)
        return HundredUserEvidence(**data)

    def build(self, **kw):
        data = dict(trend_snapshot=self.trend(), customer_value=self.value(),
                    contribution_loop=self.contribution(), hundred_user_evidence=self.hundred(),
                    competitor_research_complete=True, legal_or_safety_hold=False)
        data.update(kw)
        return build_completion_spine(CompletionSpineInput(**data))

    def test_clean_settled_path_reaches_next_governed_gate(self):
        out = self.build()
        self.assertEqual(out["posture"], "READY_FOR_NEXT_GOVERNED_GATE")
        self.assertEqual(out["blockers"], [])
        self.assertFalse(out["adoption_authorized"])
        self.assertFalse(out["runtime_activation_authorized"])

    def test_missing_hundred_user_data_stops_at_governed_gate_not_fake_completion(self):
        out = self.build(hundred_user_evidence=None)
        self.assertEqual(out["posture"], "READY_FOR_GOVERNED_HUNDRED_USER_GATE")
        self.assertIn("HUNDRED_USER_EVIDENCE_NOT_AVAILABLE", out["blockers"])

    def test_competitor_research_is_reused_as_single_early_gate(self):
        out = self.build(competitor_research_complete=False)
        self.assertEqual(out["posture"], "RESEARCH_ONLY")
        self.assertEqual(out["next_action"], "complete competitor/substitute/general-AI research once; reuse it downstream")

    def test_late_mainstream_candidate_does_not_advance(self):
        out = self.build(trend_snapshot=self.trend(mainstream_saturation=5))
        self.assertEqual(out["posture"], "RESEARCH_ONLY")
        self.assertIn("TREND_IGNORE", out["blockers"])

    def test_bad_customer_value_does_not_hide_behind_strong_trend(self):
        out = self.build(customer_value=self.value(utility_gain=0, learning_gain=0,
                                                   saved_money_or_time=0, portable_asset_gain=0))
        self.assertEqual(out["posture"], "RESEARCH_ONLY")
        self.assertIn("CUSTOMER_VALUE_REDESIGN", out["blockers"])

    def test_manipulative_contribution_is_rejected(self):
        out = self.build(contribution_loop=self.contribution(manipulation_risk=3))
        self.assertEqual(out["posture"], "RESEARCH_ONLY")
        self.assertIn("CONTRIBUTION_REJECT", out["blockers"])

    def test_hundred_user_failure_only_iterates_failed_stage(self):
        out = self.build(hundred_user_evidence=self.hundred(return_7d_rate=.10))
        self.assertEqual(out["posture"], "ITERATE_HUNDRED_USER_RESEARCH")
        self.assertIn("HUNDRED_USER_STAGE_NOT_PROMOTABLE", out["blockers"])

    def test_legal_hold_overrides_everything(self):
        out = self.build(legal_or_safety_hold=True)
        self.assertEqual(out["posture"], "HOLD_FAIL_CLOSED")
        self.assertFalse(out["automatic_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
