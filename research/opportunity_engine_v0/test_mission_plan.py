import unittest

from research.opportunity_engine_v0.advisor_track_record import AdvisorScore
from research.opportunity_engine_v0.growth_loop import GrowthLoopAssessment, LoopDecision
from research.opportunity_engine_v0.mission_plan import build_mission_plan
from research.opportunity_engine_v0.opportunity_archetype import OpportunityArchetype


class MissionPlanTests(unittest.TestCase):
    def advisor(self, provider="OPENAI"):
        return AdvisorScore(
            provider=provider,
            model="example-model",
            domain="competition",
            score=60.0,
            evidence_weight=0.5,
            sample_size=10,
            status="LIMITED_HISTORY",
            reasons=("OUTCOME_WEIGHTED",),
        )

    def route(self):
        return {
            "primary_environment": "PHONE_CLOUD",
            "phone_can_complete": True,
            "mac_leverage_score": 3,
        }

    def loop(self, decision=LoopDecision.LOOP_READY, score=70):
        return GrowthLoopAssessment(
            decision=decision,
            score=score,
            closed_pairs=(("owned", "platform"),) if decision == LoopDecision.LOOP_READY else (),
            reasons=("BIDIRECTIONAL_USER_FLOW",) if decision == LoopDecision.LOOP_READY else (),
            blockers=("LEGAL_RISK_TOO_HIGH",) if decision == LoopDecision.UNSAFE_OR_POLICY_FRAGILE else (),
            estimated_loop_multiplier=1.56 if score == 70 else 1.0,
        )

    def plan(self, **overrides):
        values = {
            "case_id": "case-001",
            "archetype": OpportunityArchetype.SHORT_WAVE_ONE_HIT,
            "execution_route": self.route(),
            "advisors": (self.advisor("OPENAI"), self.advisor("GOOGLE")),
            "review_independence_state": "CROSS_PROVIDER_NO_BLOCKER_FOUND_YET",
            "leverage_search_complete": True,
            "loadout_ready": True,
            "tactic_sequence_ready": True,
            "forecast_frozen": True,
            "competitor_research_complete": True,
            "legal_or_safety_hold": False,
        }
        values.update(overrides)
        return build_mission_plan(**values)

    def test_short_wave_ready_means_next_gate_not_execution(self):
        plan = self.plan()
        self.assertEqual(plan["mission_posture"], "TACTICAL_TEST_READY_FOR_GOVERNED_GATE")
        self.assertFalse(plan["live_execution_authorized"])
        self.assertTrue(plan["owner_gate_still_required"])

    def test_single_provider_independence_gap_blocks_readiness(self):
        plan = self.plan(
            advisors=(self.advisor("OPENAI"),),
            review_independence_state="INDEPENDENCE_INSUFFICIENT",
        )
        self.assertEqual(plan["mission_posture"], "RESEARCH_OR_TRAINING_ONLY")
        self.assertIn("REVIEW_INDEPENDENCE_INSUFFICIENT", plan["blockers"])

    def test_severe_review_challenge_holds_even_when_everything_else_ready(self):
        plan = self.plan(review_independence_state="CHALLENGE_REQUIRED")
        self.assertEqual(plan["mission_posture"], "HOLD_AND_RESOLVE_BLOCKER")

    def test_missing_competitor_research_blocks_even_cross_provider_support(self):
        plan = self.plan(competitor_research_complete=False)
        self.assertEqual(plan["mission_posture"], "RESEARCH_OR_TRAINING_ONLY")
        self.assertIn("COMPETITOR_RESEARCH_INCOMPLETE", plan["blockers"])

    def test_legal_hold_has_priority(self):
        plan = self.plan(legal_or_safety_hold=True)
        self.assertEqual(plan["mission_posture"], "HOLD_AND_RESOLVE_BLOCKER")
        self.assertIn("LEGAL_OR_SAFETY_HOLD", plan["blockers"])

    def test_durable_candidate_has_different_ready_posture(self):
        plan = self.plan(archetype=OpportunityArchetype.DURABLE_COMPOUNDER)
        self.assertEqual(plan["mission_posture"], "DURABLE_TEST_READY_FOR_GOVERNED_GATE")

    def test_required_ready_loop_can_pass_without_multiplier_stacking(self):
        plan = self.plan(growth_loop_required=True, growth_loop_assessment=self.loop())
        self.assertEqual(plan["mission_posture"], "TACTICAL_TEST_READY_FOR_GOVERNED_GATE")
        self.assertEqual(plan["growth_loop_decision"], "LOOP_READY")
        self.assertEqual(plan["growth_loop_score"], 70)
        self.assertFalse(plan["growth_loop_multiplier_applied_to_mission"])

    def test_required_loop_missing_blocks_readiness(self):
        plan = self.plan(growth_loop_required=True)
        self.assertEqual(plan["mission_posture"], "RESEARCH_OR_TRAINING_ONLY")
        self.assertIn("GROWTH_LOOP_NOT_ASSESSED", plan["blockers"])

    def test_required_one_way_amplifier_is_not_promoted_to_loop(self):
        plan = self.plan(
            growth_loop_required=True,
            growth_loop_assessment=self.loop(LoopDecision.ONE_WAY_AMPLIFIER, 45),
        )
        self.assertEqual(plan["mission_posture"], "RESEARCH_OR_TRAINING_ONLY")
        self.assertIn("GROWTH_LOOP_ONE_WAY_AMPLIFIER", plan["blockers"])

    def test_unsafe_loop_forces_hold_even_when_loop_not_required(self):
        plan = self.plan(
            growth_loop_required=False,
            growth_loop_assessment=self.loop(LoopDecision.UNSAFE_OR_POLICY_FRAGILE, 0),
        )
        self.assertEqual(plan["mission_posture"], "HOLD_AND_RESOLVE_BLOCKER")
        self.assertIn("GROWTH_LOOP_UNSAFE_OR_POLICY_FRAGILE", plan["blockers"])


if __name__ == "__main__":
    unittest.main()
