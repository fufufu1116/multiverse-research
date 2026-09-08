from __future__ import annotations

import json
import unittest

from automation.review_dispatcher_v1.model import ReviewContractError, t2_marker
from automation.review_dispatcher_v1.t2_receipt_recovery_v1 import recover_t2_receipt


def job() -> dict:
    return {
        "request_id": "auditor-request-001",
        "request_sha256": "a" * 64,
        "head": "b" * 40,
        "tree": "c" * 40,
        "main": "d" * 40,
    }


def artifact(j: dict, auditor_comment_id: int = 456) -> dict:
    return {
        "schema_version": "MULTIVERSE_FIXED_T2_RESULT_v1",
        "gate": "T2",
        "verdict": "PASS",
        "request_id": j["request_id"],
        "request_sha256": j["request_sha256"],
        "reviewed_head": j["head"],
        "reviewed_tree": j["tree"],
        "reviewed_main": j["main"],
        "auditor_pass_comment": auditor_comment_id,
        "auditor_producer": "multiverse-independent-auditor[bot]",
        "auditor_app_id": 4821179,
    }


def comment(j: dict, art: dict, auditor_comment_id: int = 456, trusted: bool = True) -> dict:
    marker = t2_marker(j["request_id"], j["head"], auditor_comment_id, j["request_sha256"])
    fence = chr(96) * 3
    return {
        "id": 999,
        "body": "\n".join([marker + " build -->", fence + "json", json.dumps(art, sort_keys=True), fence]),
        "user": {
            "login": "multiverse-independent-auditor[bot]" if trusted else "attacker",
            "type": "Bot" if trusted else "User",
        },
        "performed_via_github_app": {"slug": "multiverse-independent-auditor"} if trusted else None,
    }


class T2ReceiptRecoveryTests(unittest.TestCase):
    def test_01_exact_t2_recovers_receipt(self):
        j = job()
        art = artifact(j)
        receipt = recover_t2_receipt(
            job=j,
            auditor_comment_id=456,
            expected_t2_artifact=art,
            canonical_t2_comment=comment(j, art),
        )
        self.assertEqual(receipt["t2_comment_id"], 999)
        self.assertTrue(receipt["recovered"])

    def test_02_untrusted_t2_fails_closed(self):
        j = job()
        art = artifact(j)
        with self.assertRaisesRegex(ReviewContractError, "PRODUCER_NOT_TRUSTED"):
            recover_t2_receipt(
                job=j,
                auditor_comment_id=456,
                expected_t2_artifact=art,
                canonical_t2_comment=comment(j, art, trusted=False),
            )

    def test_03_marker_mismatch_fails_closed(self):
        j = job()
        art = artifact(j)
        bad = comment(j, art)
        bad["body"] = bad["body"].replace(j["request_id"], "other-request")
        with self.assertRaisesRegex(ReviewContractError, "MARKER_MISMATCH"):
            recover_t2_receipt(
                job=j,
                auditor_comment_id=456,
                expected_t2_artifact=art,
                canonical_t2_comment=bad,
            )

    def test_04_artifact_drift_fails_closed(self):
        j = job()
        art = artifact(j)
        published = dict(art)
        published["reviewed_tree"] = "e" * 40
        with self.assertRaisesRegex(ReviewContractError, "ARTIFACT_DRIFT"):
            recover_t2_receipt(
                job=j,
                auditor_comment_id=456,
                expected_t2_artifact=art,
                canonical_t2_comment=comment(j, published),
            )

    def test_05_wrong_auditor_binding_fails_closed(self):
        j = job()
        art = artifact(j, auditor_comment_id=123)
        with self.assertRaisesRegex(ReviewContractError, "AUDITOR_PASS_COMMENT_MISMATCH"):
            recover_t2_receipt(
                job=j,
                auditor_comment_id=456,
                expected_t2_artifact=art,
                canonical_t2_comment=comment(j, art),
            )

    def test_06_nonpass_t2_fails_closed(self):
        j = job()
        art = artifact(j)
        art["verdict"] = "FIX_REQUIRED"
        with self.assertRaisesRegex(ReviewContractError, "NOT_PASS"):
            recover_t2_receipt(
                job=j,
                auditor_comment_id=456,
                expected_t2_artifact=art,
                canonical_t2_comment=comment(j, art),
            )


if __name__ == "__main__":
    unittest.main()
