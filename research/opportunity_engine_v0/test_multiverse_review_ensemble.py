import unittest

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS, sha256_json
from research.opportunity_engine_v0.multiverse_bridge import (
    OpportunityBridgeError,
    build_multiverse_review_packet,
)
from research.opportunity_engine_v0.multiverse_review_ensemble import (
    aggregate_opportunity_reviews,
)


def nonauthority():
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


class MultiverseReviewEnsembleTests(unittest.TestCase):
    def packet(self):
        return build_multiverse_review_packet(
            opportunity_case={
                "case_id": "ensemble-case-001",
                "competitor_state": "RESEARCHED",
                "provisional_verdict": "WATCH",
            },
            case_ref="research/opportunity_engine_v0/cases/ensemble-case-001.json",
            task_id="opportunity-ensemble-task-001",
            snapshot_id="opportunity-ensemble-snapshot-001",
            created_at="2026-09-11T07:40:00+09:00",
            observed_at="2026-09-11T07:35:00+09:00",
        )

    def result(
        self,
        packet,
        *,
        role,
        suffix,
        position="SUPPORT",
        severity="LOW",
        claim_key="competitor-coverage",
        status="COMPLETED",
        uncertainty_factors=None,
    ):
        task = packet["research_task"]
        findings = []
        if status == "COMPLETED":
            findings = [
                {
                    "finding_id": f"finding-{suffix}",
                    "claim_key": claim_key,
                    "position": position,
                    "severity": severity,
                    "assertion": "Bounded ensemble review finding.",
                    "evidence": {
                        "primitive": "SOURCE_REF",
                        "ref": packet["case_ref"],
                        "sha256": packet["opportunity_case_sha256"],
                    },
                    "confidence": 0.8,
                    "uncertainty": "Frozen-snapshot review only.",
                    "recommendation": f"Recommendation {suffix}.",
                    "validation_plan": f"Validation plan {suffix}.",
                }
            ]
        return {
            "schema": "MULTIVERSE_RESEARCH_RESULT_v1",
            "task_id": task["task_id"],
            "task_sha256": sha256_json(task),
            "submission_id": f"submission-{suffix}",
            "snapshot_id": task["snapshot_id"],
            "produced_at": "2026-09-10T22:45:00Z",
            "model_identity": {
                "provider": f"TEST_PROVIDER_{suffix}",
                "model": f"test-model-{suffix}",
                "role": role,
            },
            "status": status,
            "findings": findings,
            "uncertainty_factors": [] if uncertainty_factors is None else uncertainty_factors,
            "nonauthority": nonauthority(),
        }

    def complete_support_set(self, packet):
        return [
            self.result(packet, role="competitor_challenge", suffix="a"),
            self.result(packet, role="economics_challenge", suffix="b"),
            self.result(packet, role="execution_risk_challenge", suffix="c"),
        ]

    def test_unanimous_support_is_not_approval(self):
        packet = self.packet()
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=self.complete_support_set(packet),
        )
        self.assertEqual(output["overall_state"], "NO_BLOCKER_FOUND_YET")
        self.assertEqual(output["recommended_next_action"], "HOLD_FOR_NEXT_GOVERNED_GATE")
        self.assertFalse(output["majority_confers_truth"])
        self.assertFalse(output["support_confers_approval"])
        self.assertFalse(output["automatic_advance_authorized"])
        self.assertTrue(all(flag is False for flag in output["authority"].values()))

    def test_one_high_opposition_blocks_two_supporters(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[2] = self.result(
            packet,
            role="execution_risk_challenge",
            suffix="c",
            position="OPPOSE",
            severity="HIGH",
        )
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=results,
        )
        self.assertEqual(output["overall_state"], "CHALLENGE_REQUIRED")
        self.assertEqual(output["recommended_next_action"], "DOWNRANK_AND_RUN_FALSIFICATION")
        self.assertEqual(output["claim_states"][0]["state"], "BLOCKING_CHALLENGE")

    def test_low_divergence_requires_falsification_not_vote(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[2] = self.result(
            packet,
            role="execution_risk_challenge",
            suffix="c",
            position="OPPOSE",
            severity="LOW",
        )
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=results,
        )
        self.assertEqual(output["overall_state"], "FALSIFICATION_REQUIRED")
        self.assertEqual(output["recommended_next_action"], "RUN_MECHANICAL_FALSIFICATION")

    def test_unknown_requires_more_evidence(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[1] = self.result(
            packet,
            role="economics_challenge",
            suffix="b",
            position="UNKNOWN",
            severity="MEDIUM",
            claim_key="economics-low-case",
        )
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=results,
        )
        self.assertEqual(output["overall_state"], "MORE_EVIDENCE_OR_REVISION")
        self.assertIn("ECONOMICS", output["affected_subsystems"])

    def test_missing_completed_requested_role_fail_closes(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[2] = self.result(
            packet,
            role="execution_risk_challenge",
            suffix="c",
            status="INFRA_FAILURE",
            uncertainty_factors=["review unavailable"],
        )
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=results,
        )
        self.assertEqual(output["overall_state"], "REVIEW_INCOMPLETE")
        self.assertIn("execution_risk_challenge", output["review_coverage"]["roles_without_completed_result"])

    def test_uncertainty_prevents_clean_state(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[0]["uncertainty_factors"] = ["competitor snapshot may be stale"]
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=results,
        )
        self.assertEqual(output["overall_state"], "MORE_EVIDENCE_OR_REVISION")

    def test_leverage_claim_routes_back_to_leverage_subsystem(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[0] = self.result(
            packet,
            role="competitor_challenge",
            suffix="a",
            position="UNKNOWN",
            severity="MEDIUM",
            claim_key="leverage-loadout-overlap",
        )
        output = aggregate_opportunity_reviews(
            review_packet=packet,
            research_results=results,
        )
        self.assertIn("LEVERAGE", output["affected_subsystems"])

    def test_out_of_manifest_evidence_is_rejected_before_aggregation(self):
        packet = self.packet()
        results = self.complete_support_set(packet)
        results[0]["findings"][0]["evidence"]["ref"] = "outside-frozen-manifest"
        with self.assertRaises(OpportunityBridgeError):
            aggregate_opportunity_reviews(
                review_packet=packet,
                research_results=results,
            )


if __name__ == "__main__":
    unittest.main()
