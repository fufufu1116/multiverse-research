from __future__ import annotations

import unittest

from automation.control.interruption_checkpoint_v1 import classify_resume, validate_checkpoint


def checkpoint(actions):
    return {
        "schema": "MULTIVERSE_INTERRUPTION_CHECKPOINT_v1",
        "lane": "SYSTEM_IMPROVEMENT",
        "authority_ref": "#394",
        "runtime": "OFF",
        "actions": actions,
    }


class InterruptionCheckpointV1Tests(unittest.TestCase):
    def test_receipted_action_never_replays(self):
        result = classify_resume(checkpoint([{
            "action_id": "gate-token-1",
            "kind": "control_receipt",
            "one_shot": False,
            "state": "RECEIPTED",
            "receipt_ref": "#394:123",
        }]))
        self.assertEqual(result[0].decision, "DO_NOT_REPLAY")

    def test_uncertain_action_fails_closed(self):
        result = classify_resume(checkpoint([{
            "action_id": "build-1",
            "kind": "build",
            "one_shot": True,
            "state": "UNCERTAIN",
            "receipt_ref": None,
        }]))
        self.assertEqual(result[0].decision, "VERIFY_EXTERNALLY_FAIL_CLOSED")

    def test_unreceipted_one_shot_requires_fresh_authority(self):
        result = classify_resume(checkpoint([{
            "action_id": "build-2",
            "kind": "build",
            "one_shot": True,
            "state": "NOT_RECEIPTED",
            "receipt_ref": None,
        }]))
        self.assertEqual(result[0].decision, "REQUIRE_FRESH_AUTHORITY_BEFORE_ACTION")

    def test_unreceipted_safe_work_can_continue_if_authorized(self):
        result = classify_resume(checkpoint([{
            "action_id": "research-1",
            "kind": "repository_research",
            "one_shot": False,
            "state": "NOT_RECEIPTED",
            "receipt_ref": None,
        }]))
        self.assertEqual(result[0].decision, "CONTINUE_IF_STILL_AUTHORIZED")

    def test_receipted_requires_receipt_reference(self):
        with self.assertRaisesRegex(ValueError, "RECEIPTED_REQUIRES_RECEIPT_REF"):
            validate_checkpoint(checkpoint([{
                "action_id": "x",
                "kind": "repository_research",
                "one_shot": False,
                "state": "RECEIPTED",
                "receipt_ref": None,
            }]))

    def test_uncertain_cannot_claim_receipt(self):
        with self.assertRaisesRegex(ValueError, "UNRECEIPTED_MUST_NOT_CLAIM_RECEIPT"):
            validate_checkpoint(checkpoint([{
                "action_id": "x",
                "kind": "build",
                "one_shot": True,
                "state": "UNCERTAIN",
                "receipt_ref": "fake",
            }]))

    def test_known_one_shot_kind_cannot_be_downgraded(self):
        with self.assertRaisesRegex(ValueError, "KNOWN_ONE_SHOT_KIND_MUST_BE_ONE_SHOT"):
            validate_checkpoint(checkpoint([{
                "action_id": "x",
                "kind": "merge",
                "one_shot": False,
                "state": "NOT_RECEIPTED",
                "receipt_ref": None,
            }]))

    def test_duplicate_action_ids_rejected(self):
        action = {
            "action_id": "dup",
            "kind": "repository_research",
            "one_shot": False,
            "state": "NOT_RECEIPTED",
            "receipt_ref": None,
        }
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ACTION_ID"):
            validate_checkpoint(checkpoint([action, dict(action)]))

    def test_runtime_must_remain_off(self):
        payload = checkpoint([])
        payload["runtime"] = "ON"
        with self.assertRaisesRegex(ValueError, "RUNTIME_MUST_BE_OFF"):
            validate_checkpoint(payload)


if __name__ == "__main__":
    unittest.main()
