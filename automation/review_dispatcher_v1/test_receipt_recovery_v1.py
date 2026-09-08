from __future__ import annotations

import json
import unittest

from automation.review_dispatcher_v1.model import ReviewContractError, result_marker
from automation.review_dispatcher_v1.receipt_recovery_v1 import recover_publish_receipt


def base_job(lane: str = "LAB") -> dict:
    return {
        "lane": lane,
        "request_id": "request-001",
        "request_comment": 123,
        "request_sha256": "a" * 64,
        "head": "b" * 40,
        "tree": "c" * 40,
        "main": "d" * 40,
    }


def artifact(job: dict) -> dict:
    return {
        "schema_version": "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
        "result_schema": "MULTIVERSE_FIXED_REVIEW_RESULT_v1",
        "lane": job["lane"],
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_head": job["head"],
        "reviewed_tree": job["tree"],
        "reviewed_main": job["main"],
        "verdict": "PASS",
        "findings": [],
    }


def comment(job: dict, art: dict, *, trusted: bool = True) -> dict:
    lane = job["lane"]
    login = (
        "multiverse-independent-lab[bot]"
        if lane == "LAB"
        else "multiverse-independent-auditor[bot]"
    )
    slug = (
        "multiverse-independent-lab"
        if lane == "LAB"
        else "multiverse-independent-auditor"
    )
    if not trusted:
        login = "attacker"
    marker = result_marker(
        job["request_id"],
        job["head"],
        job["request_comment"],
        job["request_sha256"],
    )
    fence = chr(96) * 3
    return {
        "id": 777,
        "body": "\n".join([marker + " build -->", fence + "json", json.dumps(art, sort_keys=True), fence]),
        "user": {"login": login, "type": "Bot" if trusted else "User"},
        "performed_via_github_app": {"slug": slug} if trusted else None,
    }


class ReceiptRecoveryTests(unittest.TestCase):
    def test_01_exact_lab_result_recovers_receipt(self):
        job = base_job("LAB")
        art = artifact(job)
        receipt = recover_publish_receipt(
            job=job,
            artifact=art,
            canonical_result_comment=comment(job, art),
        )
        self.assertEqual(receipt["published_comment_id"], 777)
        self.assertEqual(receipt["published_by"], "multiverse-independent-lab[bot]")
        self.assertTrue(receipt["recovered"])

    def test_02_exact_auditor_result_recovers_receipt(self):
        job = base_job("AUDITOR")
        art = artifact(job)
        receipt = recover_publish_receipt(
            job=job,
            artifact=art,
            canonical_result_comment=comment(job, art),
        )
        self.assertEqual(receipt["published_by"], "multiverse-independent-auditor[bot]")

    def test_03_untrusted_result_fails_closed(self):
        job = base_job()
        art = artifact(job)
        with self.assertRaisesRegex(ReviewContractError, "PRODUCER_NOT_TRUSTED"):
            recover_publish_receipt(
                job=job,
                artifact=art,
                canonical_result_comment=comment(job, art, trusted=False),
            )

    def test_04_artifact_drift_fails_closed(self):
        job = base_job()
        art = artifact(job)
        published = dict(art)
        published["reviewed_tree"] = "e" * 40
        with self.assertRaisesRegex(ReviewContractError, "ARTIFACT_DRIFT"):
            recover_publish_receipt(
                job=job,
                artifact=art,
                canonical_result_comment=comment(job, published),
            )

    def test_05_marker_mismatch_fails_closed(self):
        job = base_job()
        art = artifact(job)
        bad = comment(job, art)
        bad["body"] = bad["body"].replace(job["request_id"], "other-request")
        with self.assertRaisesRegex(ReviewContractError, "MARKER_MISMATCH"):
            recover_publish_receipt(
                job=job,
                artifact=art,
                canonical_result_comment=bad,
            )

    def test_06_nonpass_artifact_fails_closed(self):
        job = base_job()
        art = artifact(job)
        art["verdict"] = "FIX_REQUIRED"
        with self.assertRaisesRegex(ReviewContractError, "NOT_CLEAN_PASS"):
            recover_publish_receipt(
                job=job,
                artifact=art,
                canonical_result_comment=comment(job, art),
            )


if __name__ == "__main__":
    unittest.main()
