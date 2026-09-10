import copy
import unittest

from research.opportunity_engine_v0.multiverse_bridge import (
    BRIDGE_SCHEMA,
    OpportunityBridgeError,
    build_multiverse_review_packet,
    validate_multiverse_review_packet,
)


class MultiverseBridgeTests(unittest.TestCase):
    def case(self):
        return {
            "case_id": "example-case-001",
            "signal": {
                "signal_id": "sig-example-001",
                "market": "Japan",
                "fact": "Frozen research fact for deterministic bridge testing.",
            },
            "competitor_state": "RESEARCHED",
            "provisional_verdict": "WATCH",
            "leverage_candidates": ["existing-system reuse"],
        }

    def build(self, **overrides):
        args = dict(
            opportunity_case=self.case(),
            case_ref="research/opportunity_engine_v0/cases/example-case-001.json",
            task_id="opportunity-review-example-001",
            snapshot_id="opportunity-snapshot-example-001",
            created_at="2026-09-11T07:30:00+09:00",
            observed_at="2026-09-11T07:20:00+09:00",
        )
        args.update(overrides)
        return build_multiverse_review_packet(**args)

    def test_builds_existing_multiverse_task_v2_without_authority(self):
        packet = self.build()
        self.assertEqual(packet["schema"], BRIDGE_SCHEMA)
        self.assertEqual(packet["research_task"]["schema"], "MULTIVERSE_RESEARCH_TASK_v2")
        self.assertEqual(packet["research_task"]["domain"], "opportunity_engine")
        self.assertEqual(packet["research_task"]["constraints"]["network_access"], "NONE")
        self.assertTrue(all(flag is False for flag in packet["bridge_authority"].values()))
        self.assertTrue(all(flag is False for flag in packet["research_task"]["nonauthority"].values()))
        validate_multiverse_review_packet(packet)

    def test_case_is_hash_bound_into_task_and_manifest(self):
        packet = self.build()
        digest = packet["opportunity_case_sha256"]
        self.assertEqual(packet["research_task"]["source_refs"][0]["sha256"], digest)
        self.assertEqual(packet["research_task"]["evidence_manifest"][0]["sha256"], digest)

    def test_mutating_case_after_freeze_is_detected(self):
        packet = self.build()
        packet["opportunity_case"]["provisional_verdict"] = "BUILD_CANDIDATE"
        with self.assertRaises(OpportunityBridgeError):
            validate_multiverse_review_packet(packet)

    def test_mutating_task_source_hash_is_detected(self):
        packet = self.build()
        packet["research_task"]["source_refs"][0]["sha256"] = "0" * 64
        with self.assertRaises((OpportunityBridgeError, RuntimeError)):
            validate_multiverse_review_packet(packet)

    def test_bridge_cannot_grant_live_authority(self):
        packet = self.build()
        packet["bridge_authority"]["spend"] = True
        with self.assertRaises(OpportunityBridgeError):
            validate_multiverse_review_packet(packet)

    def test_packet_hash_detects_outer_packet_rewrite(self):
        packet = self.build()
        original = copy.deepcopy(packet)
        packet["case_ref"] = "research/opportunity_engine_v0/cases/other.json"
        with self.assertRaises(OpportunityBridgeError):
            validate_multiverse_review_packet(packet)
        validate_multiverse_review_packet(original)

    def test_timezone_is_normalized_to_utc(self):
        packet = self.build()
        task = packet["research_task"]
        self.assertEqual(task["created_at"], "2026-09-10T22:30:00Z")
        self.assertEqual(task["source_refs"][0]["observed_at"], "2026-09-10T22:20:00Z")

    def test_future_observation_is_rejected(self):
        with self.assertRaises(OpportunityBridgeError):
            self.build(
                created_at="2026-09-11T07:20:00+09:00",
                observed_at="2026-09-11T07:30:00+09:00",
            )


if __name__ == "__main__":
    unittest.main()
