from __future__ import annotations

import json
import unittest
from unittest import mock

from automation.review_dispatcher_v1 import t2
from automation.review_dispatcher_v1.model import ReviewContractError, t2_marker


def trusted(comment_id: int, marker: str, lane: str) -> dict:
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
    return {
        "id": comment_id,
        "body": marker + " build -->\nPASS",
        "user": {"login": login, "type": "Bot"},
        "performed_via_github_app": {"slug": slug},
    }


def job() -> dict:
    return {
        "lane": "AUDITOR",
        "repo": "fufufu1116/multiverse-research",
        "pr": 999,
        "request_id": "auditor-request-001",
        "request_comment": 55,
        "request_sha256": "a" * 64,
        "head": "b" * 40,
        "tree": "c" * 40,
        "base": "d" * 40,
        "main": "e" * 40,
        "dispatcher_ref": "e" * 40,
        "request": {
            "proof_ceiling": "TEST_ONLY",
            "execution_state": "TEST",
            "nonauthority": {"merge": False},
            "upstream": {
                "lab_request_sha256": "f" * 64,
                "lab_pass_comment": 10,
                "t1_comment": 20,
            },
        },
    }


def receipt() -> dict:
    return {
        "published_comment_id": 77,
        "published_by": "multiverse-independent-auditor[bot]",
        "github_app_id": 4821179,
        "request_sha256": "a" * 64,
    }


def t2_artifact(j: dict, auditor_comment_id: int = 77) -> dict:
    return {
        "schema_version": "MULTIVERSE_FIXED_T2_RESULT_v1",
        "gate": "T2",
        "verdict": "PASS",
        "request_id": j["request_id"],
        "request_comment": j["request_comment"],
        "request_sha256": j["request_sha256"],
        "reviewed_repo": j["repo"],
        "reviewed_pr": j["pr"],
        "reviewed_head": j["head"],
        "reviewed_tree": j["tree"],
        "reviewed_base": j["base"],
        "reviewed_main": j["main"],
        "auditor_pass_comment": auditor_comment_id,
        "auditor_producer": "multiverse-independent-auditor[bot]",
        "auditor_app_id": 4821179,
        "proof_ceiling": j["request"]["proof_ceiling"],
        "execution_state": j["request"]["execution_state"],
        "nonauthority": j["request"]["nonauthority"],
    }


def exact_t2_comment(j: dict, art: dict, comment_id: int = 100) -> dict:
    marker = t2_marker(j["request_id"], j["head"], 77, j["request_sha256"])
    fence = chr(96) * 3
    return {
        "id": comment_id,
        "body": "\n".join([
            marker + " build -->",
            fence + "json",
            json.dumps(art, sort_keys=True),
            fence,
        ]),
        "user": {"login": "multiverse-independent-auditor[bot]", "type": "Bot"},
        "performed_via_github_app": {"slug": "multiverse-independent-auditor"},
    }


class T2ResilienceIntegrationTests(unittest.TestCase):
    def test_01_noncanonical_lab_duplicate_is_filtered(self):
        j = job()
        marker = "LAB-MARKER"
        comments = [trusted(10, marker, "LAB"), trusted(20, marker, "LAB"), {"id": 30, "body": "other"}]
        with mock.patch.object(t2, "_lab_binding", return_value=(marker, 10)):
            filtered = t2._filter_noncanonical_lab_duplicates(j, comments)
        self.assertEqual([item["id"] for item in filtered], [10, 30])

    def test_02_existing_canonical_t2_recovers_receipt(self):
        j = job()
        r = receipt()
        art = t2_artifact(j)
        comment = exact_t2_comment(j, art)
        with mock.patch.object(t2, "_lab_binding", return_value=("LAB", 10)), mock.patch.object(t2, "_all_comments", return_value=[comment]):
            recovered = t2.publish_t2(j, {}, r)
        self.assertEqual(recovered["t2_comment_id"], 100)
        self.assertTrue(recovered["recovered"])

    def test_03_new_publish_must_be_canonical(self):
        j = job()
        r = receipt()
        marker = t2_marker(j["request_id"], j["head"], 77, j["request_sha256"])
        post = [trusted(100, marker, "AUDITOR")]
        with mock.patch.object(
            t2, "_lab_binding", return_value=("LAB", 10)
        ), mock.patch.object(
            t2, "_all_comments", return_value=[]
        ), mock.patch.object(
            t2, "_fresh_t2_verify", return_value=post
        ), mock.patch.object(
            t2, "_original_publish_t2", return_value={"t2_comment_id": 100}
        ):
            result = t2.publish_t2(j, {}, r)
        self.assertEqual(result["t2_comment_id"], 100)

    def test_04_late_new_publish_is_rejected(self):
        j = job()
        r = receipt()
        marker = t2_marker(j["request_id"], j["head"], 77, j["request_sha256"])
        post = [trusted(90, marker, "AUDITOR"), trusted(100, marker, "AUDITOR")]
        with mock.patch.object(
            t2, "_lab_binding", return_value=("LAB", 10)
        ), mock.patch.object(
            t2, "_all_comments", return_value=[]
        ), mock.patch.object(
            t2, "_fresh_t2_verify", return_value=post
        ), mock.patch.object(
            t2, "_original_publish_t2", return_value={"t2_comment_id": 100}
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "NONCANONICAL_DUPLICATE_T2",
            ):
                t2.publish_t2(j, {}, r)

    def test_05_recovery_rejects_base_drift(self):
        j = job()
        art = t2_artifact(j)
        art["reviewed_base"] = "0" * 40
        with self.assertRaisesRegex(ReviewContractError, "REVIEWED_BASE"):
            t2._validate_recovery_t2_artifact(j, art, 77)


    def test_06_post_write_visibility_delay_recovers_without_repost(self):
        j = job()
        r = receipt()
        marker = t2_marker(
            j["request_id"],
            j["head"],
            77,
            j["request_sha256"],
        )
        art = t2_artifact(j)
        posted = exact_t2_comment(j, art, comment_id=100)
        with mock.patch.object(
            t2,
            "_lab_binding",
            return_value=("LAB", 10),
        ), mock.patch.object(
            t2,
            "_all_comments",
            return_value=[],
        ), mock.patch.object(
            t2,
            "_fresh_t2_verify",
            side_effect=[[], [posted]],
        ), mock.patch.object(
            t2,
            "_original_publish_t2",
            return_value={"t2_comment_id": 100},
        ) as original, mock.patch.object(
            t2.time,
            "sleep",
        ) as sleep:
            recovered = t2.publish_t2(j, {}, r)
        original.assert_called_once_with(j, {}, r)
        self.assertTrue(recovered["recovered"])
        self.assertEqual(recovered["t2_comment_id"], 100)
        sleep.assert_called_once_with(
            t2.T2_POST_WRITE_VISIBILITY_DELAY_SECONDS
        )
        self.assertIn(marker, posted["body"])

    def test_07_post_write_visibility_deadline_fails_without_repost(self):
        j = job()
        r = receipt()
        with mock.patch.object(
            t2,
            "T2_POST_WRITE_VISIBILITY_MAX_READS",
            3,
        ), mock.patch.object(
            t2,
            "_lab_binding",
            return_value=("LAB", 10),
        ), mock.patch.object(
            t2,
            "_all_comments",
            return_value=[],
        ), mock.patch.object(
            t2,
            "_fresh_t2_verify",
            side_effect=[[], [], []],
        ), mock.patch.object(
            t2,
            "_original_publish_t2",
            return_value={"t2_comment_id": 100},
        ) as original, mock.patch.object(
            t2.time,
            "sleep",
        ) as sleep:
            with self.assertRaisesRegex(
                ReviewContractError,
                "T2_POST_WRITE_VISIBILITY_DEADLINE_EXHAUSTED",
            ):
                t2.publish_t2(j, {}, r)
        original.assert_called_once_with(j, {}, r)
        self.assertEqual(sleep.call_count, 2)

    def test_08_delayed_earlier_canonical_t2_rejects_own_later_post(self):
        j = job()
        r = receipt()
        marker = t2_marker(
            j["request_id"],
            j["head"],
            77,
            j["request_sha256"],
        )
        post = [
            trusted(90, marker, "AUDITOR"),
            trusted(100, marker, "AUDITOR"),
        ]
        with mock.patch.object(
            t2,
            "_lab_binding",
            return_value=("LAB", 10),
        ), mock.patch.object(
            t2,
            "_all_comments",
            return_value=[],
        ), mock.patch.object(
            t2,
            "_fresh_t2_verify",
            side_effect=[[], post],
        ), mock.patch.object(
            t2,
            "_original_publish_t2",
            return_value={"t2_comment_id": 100},
        ) as original, mock.patch.object(
            t2.time,
            "sleep",
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "NONCANONICAL_DUPLICATE_T2",
            ):
                t2.publish_t2(j, {}, r)
        original.assert_called_once_with(j, {}, r)

    def test_09_post_write_reread_rechecks_current_request(self):
        j = job()
        r = receipt()
        with mock.patch.object(
            t2,
            "_lab_binding",
            return_value=("LAB", 10),
        ), mock.patch.object(
            t2,
            "_all_comments",
            return_value=[],
        ), mock.patch.object(
            t2,
            "_fresh_t2_verify",
            side_effect=[
                [],
                ReviewContractError(
                    "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT"
                ),
            ],
        ), mock.patch.object(
            t2,
            "_original_publish_t2",
            return_value={"t2_comment_id": 100},
        ) as original, mock.patch.object(
            t2.time,
            "sleep",
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT",
            ):
                t2.publish_t2(j, {}, r)
        original.assert_called_once_with(j, {}, r)

    def test_10_post_write_reread_rechecks_upstream_lab_binding(self):
        j = job()
        r = receipt()
        with mock.patch.object(
            t2,
            "_lab_binding",
            return_value=("LAB", 10),
        ), mock.patch.object(
            t2,
            "_all_comments",
            return_value=[],
        ), mock.patch.object(
            t2,
            "_fresh_t2_verify",
            side_effect=[
                [],
                ReviewContractError(
                    "LATEST_LAB_REQUEST_SHA256_MISMATCH"
                ),
            ],
        ), mock.patch.object(
            t2,
            "_original_publish_t2",
            return_value={"t2_comment_id": 100},
        ) as original, mock.patch.object(
            t2.time,
            "sleep",
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "LATEST_LAB_REQUEST_SHA256_MISMATCH",
            ):
                t2.publish_t2(j, {}, r)
        original.assert_called_once_with(j, {}, r)

    def test_11_fresh_t2_verify_rechecks_t1_binding(self):
        j = job()
        r = receipt()
        auditor_artifact = {"artifact": "auditor-pass"}

        def public_github(url: str):
            if url.endswith("/pulls/999"):
                return {
                    "number": 999,
                    "state": "open",
                    "draft": True,
                    "merged": False,
                    "head": {
                        "sha": j["head"],
                        "ref": "agent/test",
                    },
                    "base": {"sha": j["base"]},
                }
            if url.endswith("/branches/main"):
                return {"commit": {"sha": j["main"]}}
            if url.endswith(f"/commits/{j['head']}"):
                return {"commit": {"tree": {"sha": j["tree"]}}}
            if url.endswith("/issues/comments/77"):
                return {
                    "body": "auditor",
                    "user": {
                        "login": "multiverse-independent-auditor[bot]",
                        "type": "Bot",
                    },
                    "performed_via_github_app": {
                        "slug": "multiverse-independent-auditor"
                    },
                }
            if url.endswith("/issues/comments/20"):
                return {
                    "body": "T1 WITHOUT REQUIRED BINDINGS",
                    "user": {"login": "fufufu1116"},
                }
            raise AssertionError(url)

        with mock.patch.object(
            t2._legacy,
            "public_github",
            side_effect=public_github,
        ), mock.patch.object(
            t2,
            "_all_comments",
            return_value=[],
        ), mock.patch.object(
            t2,
            "assert_job_request_still_canonical",
        ), mock.patch.object(
            t2,
            "_lab_binding",
            return_value=("LAB", 10),
        ), mock.patch.object(
            t2._legacy,
            "json_block",
            return_value=auditor_artifact,
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "T1_LAB_BINDING_MISSING",
            ):
                t2._fresh_t2_verify(j, auditor_artifact, r)


if __name__ == "__main__":
    unittest.main()
