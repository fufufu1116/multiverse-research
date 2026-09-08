from __future__ import annotations

import json
import unittest
from unittest import mock

from automation.review_dispatcher_v1 import publisher
from automation.review_dispatcher_v1.model import ReviewContractError, result_marker


def job() -> dict:
    return {
        "lane": "LAB",
        "repo": "fufufu1116/multiverse-research",
        "pr": 999,
        "request_id": "request-001",
        "request_comment": 123,
        "request_sha256": "a" * 64,
        "head": "b" * 40,
        "tree": "c" * 40,
        "base": "d" * 40,
        "main": "e" * 40,
        "request": {"proof_ceiling": "TEST", "execution_state": "TEST"},
    }


def artifact(j: dict) -> dict:
    return {
        "schema_version": "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
        "lane": j["lane"],
        "request_id": j["request_id"],
        "request_comment": j["request_comment"],
        "request_sha256": j["request_sha256"],
        "reviewed_repo": j["repo"],
        "reviewed_pr": j["pr"],
        "reviewed_head": j["head"],
        "reviewed_tree": j["tree"],
        "reviewed_base": j["base"],
        "reviewed_main": j["main"],
        "verdict": "PASS",
        "findings": [],
        "producer": {
            "github_login": "multiverse-independent-lab[bot]",
            "github_app_id": 4819755,
        },
    }


def trusted_result(comment_id: int, j: dict, a: dict) -> dict:
    marker = result_marker(
        j["request_id"],
        j["head"],
        j["request_comment"],
        j["request_sha256"],
    )
    fence = chr(96) * 3
    body = "\n".join(
        [
            marker + "build -->",
            fence + "json",
            json.dumps(a, sort_keys=True),
            fence,
        ]
    )
    return {
        "id": comment_id,
        "body": body,
        "user": {
            "login": "multiverse-independent-lab[bot]",
            "type": "Bot",
        },
        "performed_via_github_app": {
            "slug": "multiverse-independent-lab",
        },
    }


class PublisherResilienceIntegrationTests(unittest.TestCase):
    def test_01_existing_canonical_result_recovers_without_republish(self):
        j = job()
        a = artifact(j)
        existing = trusted_result(10, j, a)
        with mock.patch.object(publisher, "_fresh_verify", return_value=[existing]), mock.patch.object(
            publisher, "_original_publish"
        ) as original:
            receipt = publisher.publish(j, a)
        original.assert_not_called()
        self.assertTrue(receipt["recovered"])
        self.assertEqual(receipt["published_comment_id"], 10)

    def test_02_new_publication_must_be_canonical(self):
        j = job()
        a = artifact(j)
        posted = trusted_result(20, j, a)
        receipt = {"published_comment_id": 20}
        with mock.patch.object(
            publisher, "_fresh_verify", side_effect=[[], [posted]]
        ), mock.patch.object(
            publisher, "_original_publish", return_value=receipt
        ):
            self.assertIs(publisher.publish(j, a), receipt)

    def test_03_precheck_race_recovers_existing_result(self):
        j = job()
        a = artifact(j)
        existing = trusted_result(10, j, a)
        with mock.patch.object(
            publisher, "_fresh_verify", side_effect=[[], [existing]]
        ), mock.patch.object(
            publisher,
            "_original_publish",
            side_effect=ReviewContractError("CURRENT_REQUEST_RESULT_ALREADY_EXISTS:10"),
        ):
            receipt = publisher.publish(j, a)
        self.assertTrue(receipt["recovered"])
        self.assertEqual(receipt["published_comment_id"], 10)

    def test_04_later_duplicate_cannot_emit_successful_receipt(self):
        j = job()
        a = artifact(j)
        first = trusted_result(10, j, a)
        later = trusted_result(20, j, a)
        with mock.patch.object(
            publisher, "_fresh_verify", side_effect=[[], [first, later]]
        ), mock.patch.object(
            publisher, "_original_publish", return_value={"published_comment_id": 20}
        ):
            with self.assertRaises(ReviewContractError):
                publisher.publish(j, a)

    def test_05_post_publish_request_supersession_fails_closed(self):
        j = job()
        a = artifact(j)
        with mock.patch.object(
            publisher,
            "_fresh_verify",
            side_effect=[[], ReviewContractError("PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT")],
        ), mock.patch.object(
            publisher, "_original_publish", return_value={"published_comment_id": 20}
        ):
            with self.assertRaises(ReviewContractError):
                publisher.publish(j, a)

    def test_06_recovery_rechecks_legacy_base_binding(self):
        j = job()
        a = artifact(j)
        a["reviewed_base"] = "f" * 40
        existing = trusted_result(10, j, a)
        with mock.patch.object(publisher, "_fresh_verify", return_value=[existing]), mock.patch.object(
            publisher, "_original_publish"
        ) as original:
            with self.assertRaises(ReviewContractError):
                publisher.publish(j, a)
        original.assert_not_called()


    def test_07_post_publish_visibility_delay_converges_without_repost(self):
        j = job()
        a = artifact(j)
        posted = trusted_result(20, j, a)
        receipt = {"published_comment_id": 20}
        with mock.patch.object(
            publisher,
            "_fresh_verify",
            side_effect=[[], [], [posted]],
        ), mock.patch.object(
            publisher,
            "_original_publish",
            return_value=receipt,
        ) as original, mock.patch.object(
            publisher.time,
            "sleep",
        ) as sleep:
            self.assertIs(publisher.publish(j, a), receipt)
        original.assert_called_once_with(j, a)
        sleep.assert_called_once_with(
            publisher.POST_WRITE_VISIBILITY_DELAY_SECONDS
        )

    def test_08_post_publish_visibility_deadline_fails_without_repost(self):
        j = job()
        a = artifact(j)
        receipt = {"published_comment_id": 20}
        with mock.patch.object(
            publisher,
            "POST_WRITE_VISIBILITY_MAX_READS",
            3,
        ), mock.patch.object(
            publisher,
            "_fresh_verify",
            side_effect=[[], [], [], []],
        ), mock.patch.object(
            publisher,
            "_original_publish",
            return_value=receipt,
        ) as original, mock.patch.object(
            publisher.time,
            "sleep",
        ) as sleep:
            with self.assertRaisesRegex(
                ReviewContractError,
                "POST_WRITE_VISIBILITY_DEADLINE_EXHAUSTED",
            ):
                publisher.publish(j, a)
        original.assert_called_once_with(j, a)
        self.assertEqual(sleep.call_count, 2)

    def test_09_delayed_earlier_canonical_result_beats_own_later_post(self):
        j = job()
        a = artifact(j)
        first = trusted_result(10, j, a)
        later = trusted_result(20, j, a)
        receipt = {"published_comment_id": 20}
        with mock.patch.object(
            publisher,
            "_fresh_verify",
            side_effect=[[], [], [first, later]],
        ), mock.patch.object(
            publisher,
            "_original_publish",
            return_value=receipt,
        ) as original, mock.patch.object(
            publisher.time,
            "sleep",
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "NONCANONICAL_DUPLICATE_RESULT",
            ):
                publisher.publish(j, a)
        original.assert_called_once_with(j, a)

    def test_10_post_publish_visibility_reread_rechecks_request_freshness(self):
        j = job()
        a = artifact(j)
        receipt = {"published_comment_id": 20}
        with mock.patch.object(
            publisher,
            "_fresh_verify",
            side_effect=[
                [],
                [],
                ReviewContractError(
                    "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT"
                ),
            ],
        ), mock.patch.object(
            publisher,
            "_original_publish",
            return_value=receipt,
        ) as original, mock.patch.object(
            publisher.time,
            "sleep",
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT",
            ):
                publisher.publish(j, a)
        original.assert_called_once_with(j, a)


if __name__ == "__main__":
    unittest.main()
