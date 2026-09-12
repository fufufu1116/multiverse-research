from __future__ import annotations

import copy
import json
import unittest

from automation.review_dispatcher_v1.model import (
    AUDITOR_APP_ID,
    AUDITOR_APP_SLUG,
    AUDITOR_LOGIN,
    LAB_APP_SLUG,
    LAB_LOGIN,
    ReviewContractError,
    result_marker,
    t2_marker,
)
from automation.review_dispatcher_v1.result_canonicalization_v1 import (
    assert_published_result_is_canonical,
    canonical_result_comment_id,
)
from automation.review_dispatcher_v1.receipt_recovery_v1 import (
    recover_publish_receipt,
)
from automation.review_dispatcher_v1.t2_idempotence_v1 import (
    assert_published_t2_is_canonical,
    assert_referenced_result_is_canonical,
    canonical_trusted_comment_id,
)
from automation.review_dispatcher_v1.t2_receipt_recovery_v1 import (
    recover_t2_receipt,
)

HEAD = "a" * 40
TREE = "b" * 40
MAIN = "c" * 40
REQUEST_SHA = "d" * 64


def trusted_comment(cid: int, body: str, lane: str) -> dict:
    if lane == "LAB":
        login = LAB_LOGIN
        slug = LAB_APP_SLUG
    else:
        login = AUDITOR_LOGIN
        slug = AUDITOR_APP_SLUG
    return {
        "id": cid,
        "body": body,
        "user": {"login": login, "type": "Bot"},
        "performed_via_github_app": {"slug": slug},
    }


def json_body(marker: str, payload: dict) -> str:
    fence = chr(96) * 3
    return "\n".join(
        [marker + "build -->", fence + "json", json.dumps(payload, sort_keys=True), fence]
    )


def job(lane: str = "LAB") -> dict:
    return {
        "lane": lane,
        "repo": "fufufu1116/multiverse-research",
        "pr": 999,
        "request_id": "integration-request-v1",
        "request_comment": 10,
        "request_sha256": REQUEST_SHA,
        "head": HEAD,
        "tree": TREE,
        "base": MAIN,
        "main": MAIN,
    }


def review_artifact(j: dict) -> dict:
    return {
        "request_id": j["request_id"],
        "request_comment": j["request_comment"],
        "request_sha256": j["request_sha256"],
        "reviewed_head": j["head"],
        "reviewed_tree": j["tree"],
        "reviewed_main": j["main"],
        "verdict": "PASS",
        "findings": [],
    }


def t2_artifact(j: dict, auditor_comment_id: int) -> dict:
    return {
        "gate": "T2",
        "verdict": "PASS",
        "request_id": j["request_id"],
        "request_sha256": j["request_sha256"],
        "reviewed_head": j["head"],
        "reviewed_tree": j["tree"],
        "reviewed_main": j["main"],
        "auditor_pass_comment": auditor_comment_id,
        "auditor_producer": AUDITOR_LOGIN,
        "auditor_app_id": AUDITOR_APP_ID,
    }


class ControlPlaneRecoveryIntegrationTests(unittest.TestCase):
    def test_01_result_selection_recovery_and_downstream_consumption_compose(self):
        j = job("LAB")
        artifact = review_artifact(j)
        marker = result_marker(
            j["request_id"], j["head"], j["request_comment"], j["request_sha256"]
        )
        comments = [
            trusted_comment(101, json_body(marker, artifact), "LAB"),
            trusted_comment(102, json_body(marker, artifact), "LAB"),
        ]

        canonical = canonical_result_comment_id(comments, lane="LAB", marker=marker)
        self.assertEqual(canonical, 101)
        self.assertEqual(
            assert_published_result_is_canonical(
                comments, lane="LAB", marker=marker, published_comment_id=101
            ),
            101,
        )
        receipt = recover_publish_receipt(
            job=j, artifact=artifact, canonical_result_comment=comments[0]
        )
        self.assertEqual(receipt["published_comment_id"], 101)
        self.assertTrue(receipt["recovered"])
        self.assertEqual(
            assert_referenced_result_is_canonical(
                comments,
                lane="LAB",
                marker=marker,
                referenced_comment_id=receipt["published_comment_id"],
            ),
            101,
        )

    def test_02_noncanonical_duplicate_cannot_be_referenced_downstream(self):
        j = job("LAB")
        artifact = review_artifact(j)
        marker = result_marker(
            j["request_id"], j["head"], j["request_comment"], j["request_sha256"]
        )
        comments = [
            trusted_comment(101, json_body(marker, artifact), "LAB"),
            trusted_comment(102, json_body(marker, artifact), "LAB"),
        ]
        with self.assertRaises(ReviewContractError):
            assert_referenced_result_is_canonical(
                comments, lane="LAB", marker=marker, referenced_comment_id=102
            )

    def test_03_result_recovery_rejects_artifact_drift(self):
        j = job("LAB")
        artifact = review_artifact(j)
        marker = result_marker(
            j["request_id"], j["head"], j["request_comment"], j["request_sha256"]
        )
        comment = trusted_comment(101, json_body(marker, artifact), "LAB")
        drifted = copy.deepcopy(artifact)
        drifted["reviewed_tree"] = "e" * 40
        with self.assertRaises(ReviewContractError):
            recover_publish_receipt(
                job=j, artifact=drifted, canonical_result_comment=comment
            )

    def test_04_t2_selection_and_receipt_recovery_compose(self):
        j = job("AUDITOR")
        auditor_comment_id = 150
        artifact = t2_artifact(j, auditor_comment_id)
        marker = t2_marker(
            j["request_id"], j["head"], auditor_comment_id, j["request_sha256"]
        )
        comments = [
            trusted_comment(201, json_body(marker, artifact), "AUDITOR"),
            trusted_comment(202, json_body(marker, artifact), "AUDITOR"),
        ]

        self.assertEqual(
            canonical_trusted_comment_id(comments, lane="AUDITOR", marker=marker),
            201,
        )
        self.assertEqual(
            assert_published_t2_is_canonical(
                comments, marker=marker, published_comment_id=201
            ),
            201,
        )
        receipt = recover_t2_receipt(
            job=j,
            auditor_comment_id=auditor_comment_id,
            expected_t2_artifact=artifact,
            canonical_t2_comment=comments[0],
        )
        self.assertEqual(receipt["t2_comment_id"], 201)
        self.assertTrue(receipt["recovered"])

    def test_05_noncanonical_duplicate_t2_is_nonconsumable(self):
        j = job("AUDITOR")
        auditor_comment_id = 150
        artifact = t2_artifact(j, auditor_comment_id)
        marker = t2_marker(
            j["request_id"], j["head"], auditor_comment_id, j["request_sha256"]
        )
        comments = [
            trusted_comment(201, json_body(marker, artifact), "AUDITOR"),
            trusted_comment(202, json_body(marker, artifact), "AUDITOR"),
        ]
        with self.assertRaises(ReviewContractError):
            assert_published_t2_is_canonical(
                comments, marker=marker, published_comment_id=202
            )

    def test_06_untrusted_comment_cannot_preempt_or_recover(self):
        j = job("LAB")
        artifact = review_artifact(j)
        marker = result_marker(
            j["request_id"], j["head"], j["request_comment"], j["request_sha256"]
        )
        attacker = {
            "id": 1,
            "body": json_body(marker, artifact),
            "user": {"login": "attacker", "type": "User"},
        }
        trusted = trusted_comment(101, json_body(marker, artifact), "LAB")
        self.assertEqual(
            canonical_result_comment_id([attacker, trusted], lane="LAB", marker=marker),
            101,
        )
        with self.assertRaises(ReviewContractError):
            recover_publish_receipt(
                job=j, artifact=artifact, canonical_result_comment=attacker
            )


if __name__ == "__main__":
    unittest.main()
