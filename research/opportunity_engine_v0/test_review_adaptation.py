import copy
import unittest

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS
from research.opportunity_engine_v0.multiverse_bridge import OpportunityBridgeError, sha256_json
from research.opportunity_engine_v0.multiverse_review_ensemble import ENSEMBLE_SCHEMA
from research.opportunity_engine_v0.review_adaptation import build_adaptation_plan


def nonauthority():
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


def ensemble(**overrides):
    data = {
        "schema": ENSEMBLE_SCHEMA,
        "case_id": "adapt-case-001",
        "task_id": "adapt-task-001",
        "snapshot_id": "adapt-snapshot-001",
        "review_packet_sha256": "1" * 64,
        "multiverse_aggregate_sha256": "2" * 64,
        "overall_state": "MORE_EVIDENCE_OR_REVISION",
        "recommended_next_action": "RESEARCH_REVISE_AND_REFREEZE",
        "claim_states": [
            {
                "claim_key": "leverage-loadout-overlap",
                "subsystem": "LEVERAGE",
                "state": "REVISION_OR_MORE_EVIDENCE",
                "max_severity": "MEDIUM",
                "support_count": 0,
                "oppose_count": 0,
                "unknown_count": 1,
                "cross_provider_divergence": False,
                "cross_model_divergence": False,
                "action_items": [],
                "majority_confers_truth": False,
            }
        ],
        "affected_subsystems": ["LEVERAGE"],
        "review_coverage": {
            "requested_role_completed_coverage_complete": True,
            "roles_without_completed_result": [],
            "completed_unique_advisory_identity_count": 3,
            "completed_unique_provider_model_count": 3,
            "completed_unique_provider_count": 2,
        },
        "individual_feedback": [],
        "majority_confers_truth": False,
        "support_confers_approval": False,
        "automatic_advance_authorized": False,
        "authority": nonauthority(),
        "note": "Advisory synthesis only.",
    }
    data.update(overrides)
    data["ensemble_sha256"] = sha256_json(data)
    return data


class ReviewAdaptationTests(unittest.TestCase):
    def test_leverage_challenge_reoptimizes_loadout_without_execution(self):
        plan = build_adaptation_plan(ensemble())
        self.assertEqual(plan["candidate_state"], "HOLD_FOR_REVISION")
        self.assertEqual(plan["tasks"][0]["action"], "REOPTIMIZE_LOADOUT")
        self.assertFalse(plan["automatic_execution_authorized"])
        self.assertFalse(plan["automatic_adoption_authorized"])

    def test_clean_review_only_reaches_next_governed_gate(self):
        clean = ensemble(
            overall_state="NO_BLOCKER_FOUND_YET",
            recommended_next_action="HOLD_FOR_NEXT_GOVERNED_GATE",
            claim_states=[],
            affected_subsystems=[],
        )
        plan = build_adaptation_plan(clean)
        self.assertEqual(plan["candidate_state"], "READY_FOR_NEXT_GOVERNED_GATE")
        self.assertEqual(plan["tasks"], [])
        self.assertFalse(plan["automatic_execution_authorized"])

    def test_high_challenge_downranks_and_holds(self):
        challenged = ensemble(
            overall_state="CHALLENGE_REQUIRED",
            recommended_next_action="DOWNRANK_AND_RUN_FALSIFICATION",
        )
        plan = build_adaptation_plan(challenged)
        self.assertEqual(plan["candidate_state"], "DOWNRANK_AND_HOLD")

    def test_review_gap_is_first_repair_task(self):
        incomplete = ensemble(
            overall_state="REVIEW_INCOMPLETE",
            recommended_next_action="RESTORE_REVIEW_COVERAGE",
        )
        plan = build_adaptation_plan(incomplete)
        self.assertEqual(plan["candidate_state"], "HOLD_REVIEW_INCOMPLETE")
        self.assertEqual(plan["tasks"][0]["action"], "RESTORE_MISSING_REVIEW_ROLES")

    def test_divergence_requires_mechanical_falsification(self):
        divergent_claim = copy.deepcopy(ensemble()["claim_states"][0])
        divergent_claim["claim_key"] = "competitor-gap"
        divergent_claim["subsystem"] = "COMPETITION"
        divergent_claim["state"] = "FALSIFICATION_REQUIRED"
        divergent = ensemble(
            overall_state="FALSIFICATION_REQUIRED",
            recommended_next_action="RUN_MECHANICAL_FALSIFICATION",
            claim_states=[divergent_claim],
            affected_subsystems=["COMPETITION"],
        )
        plan = build_adaptation_plan(divergent)
        self.assertEqual(plan["tasks"][0]["action"], "RUN_MECHANICAL_FALSIFICATION")
        self.assertEqual(plan["tasks"][1]["action"], "REFRESH_COMPETITOR_MATRIX")

    def test_forecast_revision_preserves_old_forecast(self):
        forecast_claim = copy.deepcopy(ensemble()["claim_states"][0])
        forecast_claim["claim_key"] = "forecast-decay-window"
        forecast_claim["subsystem"] = "FORECASTING"
        forecast = ensemble(
            claim_states=[forecast_claim],
            affected_subsystems=["FORECASTING"],
        )
        plan = build_adaptation_plan(forecast)
        self.assertEqual(plan["tasks"][0]["action"], "REFREEZE_FORECAST_VERSION")
        self.assertTrue(plan["preserve_old_forecasts"])

    def test_tampered_ensemble_is_rejected(self):
        value = ensemble()
        value["overall_state"] = "NO_BLOCKER_FOUND_YET"
        with self.assertRaises(OpportunityBridgeError):
            build_adaptation_plan(value)


if __name__ == "__main__":
    unittest.main()
