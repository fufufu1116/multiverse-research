from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from automation.review_dispatcher_v1 import t2_main_drift_v1 as t2md
from automation.review_dispatcher_v1.model import ReviewContractError, sha256_json


MAIN = "a" * 40
LIVE = "b" * 40
DISPATCHER = "c" * 40
HEAD = "d" * 40
TREE = "e" * 40
BASE = "f" * 40
REPO = "fufufu1116/multiverse-research"


def lab_request(main=MAIN):
    return {
        "request_id": "lab-safe-main-drift",
        "main": main,
        "proof_ceiling": "REPOSITORY_ONLY",
        "execution_state": "CANDIDATE_ONLY",
    }


def auditor_job(*, lab=lab_request()):
    return {
        "repo": REPO,
        "pr": 466,
        "lane": "AUDITOR",
        "head": HEAD,
        "tree": TREE,
        "base": BASE,
        "main": MAIN,
        "dispatcher_ref": DISPATCHER,
        "request_comment": 200,
        "request_sha256": "1" * 64,
        "request": {
            "proof_ceiling": "REPOSITORY_ONLY",
            "execution_state": "CANDIDATE_ONLY",
            "upstream": {
                "lab_request_sha256": sha256_json(lab),
                "lab_pass_comment": 300,
                "t1_comment": 400,
            },
        },
    }


class T2MainDriftTests(unittest.TestCase):
    def test_safe_lab_binding_preserves_same_request_main_snapshot(self):
        lab = lab_request()
        job = auditor_job(lab=lab)
        canonical = Mock()
        with patch.object(
            t2md,
            "select_request_for_live_main",
            return_value=(100, lab, {}, {"mode": "SAFE_UNRELATED_MAIN_DRIFT"}),
        ), patch.object(
            t2md._t2,
            "assert_referenced_result_is_canonical",
            canonical,
        ):
            marker, referenced = t2md._safe_lab_binding(
                job,
                [],
                live_main=LIVE,
                fetch=lambda _url: {},
            )
        self.assertEqual(referenced, 300)
        self.assertIn("lab-safe-main-drift", marker)
        canonical.assert_called_once()

    def test_safe_lab_binding_rejects_cross_snapshot_rebinding(self):
        old_lab = lab_request()
        newer_lab = lab_request(main=LIVE)
        job = auditor_job(lab=old_lab)
        with patch.object(
            t2md,
            "select_request_for_live_main",
            return_value=(101, newer_lab, {}, {"mode": "EXACT_MAIN"}),
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "LATEST_LAB_REQUEST_MAIN_SNAPSHOT_MISMATCH",
            ):
                t2md._safe_lab_binding(
                    job,
                    [],
                    live_main=LIVE,
                    fetch=lambda _url: {},
                )

    def test_t2_prewrite_guard_blocks_post_when_freshness_turns_unsafe(self):
        job = auditor_job()
        artifact = {"verdict": "PASS"}
        receipt = {"comment_id": 1}
        real_mutation = Mock(return_value={"id": 999})

        def legacy_publish(_job, _artifact, _receipt):
            return t2md._legacy.github_json(
                "POST",
                "https://api.github.com/repos/x/y/issues/1/comments",
                "token",
                {"body": "T2"},
            )

        with patch.object(
            t2md,
            "_assert_safe_freshness",
            side_effect=[(LIVE, []), ReviewContractError("MAIN_DRIFT_NOT_ALLOWLISTED")],
        ), patch.object(
            t2md,
            "_original_exact_publish_t2",
            side_effect=legacy_publish,
        ), patch.object(
            t2md._legacy,
            "public_github",
            lambda _url: {},
        ), patch.object(
            t2md._legacy,
            "github_json",
            real_mutation,
        ):
            with self.assertRaisesRegex(
                ReviewContractError,
                "MAIN_DRIFT_NOT_ALLOWLISTED",
            ):
                t2md._safe_exact_publish_t2(job, artifact, receipt)

        real_mutation.assert_not_called()

    def test_t2_prewrite_guard_allows_post_only_after_second_fresh_check(self):
        job = auditor_job()
        artifact = {"verdict": "PASS"}
        receipt = {"comment_id": 1}
        real_mutation = Mock(return_value={"id": 999})
        freshness = Mock(return_value=(LIVE, []))

        def legacy_publish(_job, _artifact, _receipt):
            return t2md._legacy.github_json(
                "POST",
                "https://api.github.com/repos/x/y/issues/1/comments",
                "token",
                {"body": "T2"},
            )

        with patch.object(t2md, "_assert_safe_freshness", freshness), patch.object(
            t2md,
            "_original_exact_publish_t2",
            side_effect=legacy_publish,
        ), patch.object(
            t2md._legacy,
            "public_github",
            lambda _url: {},
        ), patch.object(
            t2md._legacy,
            "github_json",
            real_mutation,
        ):
            result = t2md._safe_exact_publish_t2(job, artifact, receipt)

        self.assertEqual(result, {"id": 999})
        self.assertGreaterEqual(freshness.call_count, 2)
        real_mutation.assert_called_once()

    def test_postwrite_verify_runs_safe_freshness_before_legacy_verify(self):
        job = auditor_job()
        artifact = {"verdict": "PASS"}
        receipt = {"comment_id": 1}
        order = []

        def fresh(*_args, **_kwargs):
            order.append("fresh")
            return LIVE, []

        def legacy_verify(*_args, **_kwargs):
            order.append("legacy")
            return None

        with patch.object(t2md, "_assert_safe_freshness", side_effect=fresh), patch.object(
            t2md,
            "_original_fresh_t2_verify",
            side_effect=legacy_verify,
        ), patch.object(
            t2md._legacy,
            "public_github",
            lambda _url: {},
        ):
            t2md._safe_fresh_t2_verify(job, artifact, receipt)

        self.assertEqual(order[0], "fresh")
        self.assertIn("legacy", order)


if __name__ == "__main__":
    unittest.main()
