import unittest

from automation.multimodel_research_v1.model import NONAUTHORITY_KEYS, sha256_json
from research.opportunity_engine_v0.multiverse_bridge import (
    OpportunityBridgeError,
    build_multiverse_review_packet,
)
from research.opportunity_engine_v0.multiverse_result_bridge import (
    ingest_multiverse_review_result,
)


def nonauthority():
    return {key: False for key in sorted(NONAUTHORITY_KEYS)}


class MultiverseResultBridgeTests(unittest.TestCase):
    def packet(self):
        return build_multiverse_review_packet(
            opportunity_case={
                "case_id": "result-bridge-case-001",
                "competitor_state": "RESEARCHED",
                "provisional_verdict": "WATCH",
            },
            case_ref="research/opportunity_engine_v0/cases/result-bridge-case-001.json",
            task_id="opportunity-result-bridge-task-001",
            snapshot_id="opportunity-result-bridge-snapshot-001",
            created_at="2026-09-11T07:40:00+09:00",
            observed_at="2026-09-11T07:35:00+09:00",
        )

    def result(self, packet, *, position="SUPPORT", severity="LOW", status="COMPLETED", uncertainty_factors=None):
        task = packet["research_task"]
        findings = []
        if status == "COMPLETED":
            findings = [
                {
                    "finding_id": "finding-001",
                    "claim_key": "competitor-coverage",
                    "position": position,
                    "severity": severity,
                    "assertion": "Bounded independent review finding.",
                    "evidence": {
                        "primitive": "SOURCE_REF",
                        "ref": packet["case_ref"],
                        "sha256": packet["opportunity_case_sha256"],
                    },
                    "confidence": 0.8,
                    "uncertainty": "Bounded frozen-snapshot review only.",
                    "recommendation": "Run the next reversible evidence test.",
                    "validation_plan": "Compare the claim against a new frozen evidence snapshot.",
                }
            ]
        return {
            "schema": "MULTIVERSE_RESEARCH_RESULT_v1",
            "task_id": task["task_id"],
            "task_sha256": sha256_json(task),
            "submission_id": "submission-001",
            "snapshot_id": task["snapshot_id"],
            "produced_at": "2026-09-10T22:45:00Z",
            "model_identity": {
                "provider": "INTERNAL_TEST",
                "model": "test-model-v1",
                "role": "competitor_challenge",
            },
            "status": status,
            "findings": findings,
            "uncertainty_factors": [] if uncertainty_factors is None else uncertainty_factors,
            "nonauthority": nonauthority(),
        }

    def test_support_never_becomes_approval(self):
        packet = self.packet()
        feedback = ingest_multiverse_review_result(
            review_packet=packet,
            research_result=self.result(packet),
        )
        self.assertEqual(feedback["review_state"], "NO_BLOCKER_FOUND_YET")
        self.assertIn("not approval", feedback["note"])
        self.assertTrue(all(flag is False for flag in feedback["authority"].values()))

    def test_high_opposition_requires_challenge(self):
        packet = self.packet()
        feedback = ingest_multiverse_review_result(
            review_packet=packet,
            research_result=self.result(packet, position="OPPOSE", severity="HIGH"),
        )
        self.assertEqual(feedback["review_state"], "CHALLENGE_REQUIRED")
        self.assertEqual(feedback["oppose_count"], 1)
        self.assertEqual(feedback["max_severity"], "HIGH")

    def test_unknown_or_uncertainty_requires_more_evidence(self):
        packet = self.packet()
        feedback = ingest_multiverse_review_result(
            review_packet=packet,
            research_result=self.result(packet, position="UNKNOWN", severity="MEDIUM"),
        )
        self.assertEqual(feedback["review_state"], "MORE_EVIDENCE")

    def test_noncompleted_review_cannot_advance_candidate(self):
        packet = self.packet()
        feedback = ingest_multiverse_review_result(
            review_packet=packet,
            research_result=self.result(packet, status="INFRA_FAILURE", uncertainty_factors=["review unavailable"]),
        )
        self.assertEqual(feedback["review_state"], "REVIEW_UNAVAILABLE")
        self.assertEqual(feedback["findings"], [])

    def test_result_task_hash_mismatch_is_rejected(self):
        packet = self.packet()
        result = self.result(packet)
        result["task_sha256"] = "0" * 64
        with self.assertRaises(OpportunityBridgeError):
            ingest_multiverse_review_result(review_packet=packet, research_result=result)

    def test_evidence_outside_frozen_manifest_is_rejected(self):
        packet = self.packet()
        result = self.result(packet)
        result["findings"][0]["evidence"]["ref"] = "other-ref"
        with self.assertRaises(OpportunityBridgeError):
            ingest_multiverse_review_result(review_packet=packet, research_result=result)


if __name__ == "__main__":
    unittest.main()
