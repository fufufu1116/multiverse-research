import unittest

from research.opportunity_engine_v0.mission_continuation import choose_mission_continuation, derive_continuation_actions


class MissionContinuationTests(unittest.TestCase):
    def mission(self, blockers=(), posture="RESEARCH_OR_TRAINING_ONLY"):
        return {
            "case_id": "case-1",
            "mission_posture": posture,
            "blockers": list(blockers),
        }

    def test_competitor_research_continues_without_owner(self):
        result = choose_mission_continuation(self.mission(["COMPETITOR_RESEARCH_INCOMPLETE"]))
        self.assertEqual(result["decision"], "CONTINUE_AUTONOMOUS_RESEARCH")
        self.assertEqual(result["selected_action_id"], "research-competitors")
        self.assertFalse(result["owner_action_required"])

    def test_multiple_research_blockers_choose_first_continuable_action(self):
        result = choose_mission_continuation(self.mission([
            "LEVERAGE_SEARCH_INCOMPLETE",
            "FORECAST_NOT_FROZEN",
        ]))
        self.assertEqual(result["decision"], "CONTINUE_AUTONOMOUS_RESEARCH")
        self.assertEqual(result["selected_action_id"], "research-leverage")
        self.assertIn("freeze-forecast", result["candidate_action_ids"])

    def test_safety_hold_routes_to_safe_research_not_execution(self):
        result = choose_mission_continuation(self.mission(["LEGAL_OR_SAFETY_HOLD"], "HOLD_AND_RESOLVE_BLOCKER"))
        self.assertEqual(result["decision"], "CONTINUE_AUTONOMOUS_RESEARCH")
        self.assertEqual(result["selected_action_id"], "resolve-safety-research")
        self.assertFalse(result["automatic_execution_authorized"])

    def test_ready_packet_is_first_point_owner_gate_is_needed(self):
        result = choose_mission_continuation(self.mission(
            blockers=(),
            posture="DURABLE_TEST_READY_FOR_GOVERNED_GATE",
        ))
        self.assertEqual(result["decision"], "OWNER_ACTION_REQUIRED")
        self.assertEqual(result["selected_action_id"], "request-governed-gate")
        self.assertTrue(result["owner_action_required"])

    def test_unknown_nonready_state_audits_before_interrupting_owner(self):
        result = choose_mission_continuation(self.mission(blockers=(), posture="RESEARCH_OR_TRAINING_ONLY"))
        self.assertEqual(result["decision"], "CONTINUE_AUTONOMOUS_RESEARCH")
        self.assertEqual(result["selected_action_id"], "audit-mission-completeness")

    def test_growth_loop_gap_remains_research_only(self):
        actions = derive_continuation_actions(self.mission(["GROWTH_LOOP_FRAGILE_LOOP"]))
        self.assertEqual(actions[0].action_id, "research-growth-loop")
        self.assertTrue(actions[0].reversible_repository_only)


if __name__ == "__main__":
    unittest.main()
