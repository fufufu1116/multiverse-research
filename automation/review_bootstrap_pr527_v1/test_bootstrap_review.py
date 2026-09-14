from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest import mock

from automation.review_bootstrap_pr527_v1 import bootstrap_review as b
from automation.review_dispatcher_v1 import review as core


def exact_job():
    request = {
        "lane": "AUDITOR",
        "repo": b.TARGET_REPO,
        "pr": b.TARGET_PR,
        "head": b.TARGET_HEAD,
        "tree": b.TARGET_TREE,
        "base": b.TARGET_MAIN,
        "main": b.TARGET_MAIN,
        "request_id": b.TARGET_REQUEST_ID,
        "upstream": {
            "lab_pass_comment": b.TARGET_LAB_PASS_COMMENT,
            "lab_request_sha256": b.TARGET_LAB_REQUEST_SHA256,
            "t1_comment": b.TARGET_T1_COMMENT,
        },
    }
    return {
        "lane": "AUDITOR",
        "repo": b.TARGET_REPO,
        "pr": b.TARGET_PR,
        "head": b.TARGET_HEAD,
        "tree": b.TARGET_TREE,
        "base": b.TARGET_MAIN,
        "main": b.TARGET_MAIN,
        "request_comment": b.TARGET_REQUEST_COMMENT,
        "request_sha256": b.TARGET_REQUEST_SHA256,
        "request_id": b.TARGET_REQUEST_ID,
        "request": request,
    }


class BootstrapTargetTests(unittest.TestCase):
    def test_exact_target_is_accepted(self):
        b.validate_bootstrap_target(exact_job())

    def test_wrong_head_fails_closed(self):
        job = exact_job()
        job["head"] = "0" * 40
        with self.assertRaises(core.ReviewContractError):
            b.validate_bootstrap_target(job)

    def test_wrong_request_sha_fails_closed(self):
        job = exact_job()
        job["request_sha256"] = "0" * 64
        with self.assertRaises(core.ReviewContractError):
            b.validate_bootstrap_target(job)

    def test_wrong_lab_binding_fails_closed(self):
        job = exact_job()
        job["request"]["upstream"]["lab_pass_comment"] += 1
        with self.assertRaises(core.ReviewContractError):
            b.validate_bootstrap_target(job)


class CrossLaneStateTests(unittest.TestCase):
    def test_valid_lane_split(self):
        family = "FIXED_REQUEST_ONLY_CROSS_LANE_EXECUTION_STATE_ALIASING_REPAIR_V1"
        self.assertTrue(
            b.cross_lane_execution_state_valid(
                family + "_REVIEW_REQUESTED",
                family + "_AUDIT_REQUESTED",
            )
        )

    def test_same_state_is_rejected(self):
        state = "FAMILY_REVIEW_REQUESTED"
        self.assertFalse(b.cross_lane_execution_state_valid(state, state))

    def test_wrong_family_is_rejected(self):
        self.assertFalse(
            b.cross_lane_execution_state_valid(
                "A_REVIEW_REQUESTED",
                "B_AUDIT_REQUESTED",
            )
        )

    def test_wrong_suffix_is_rejected(self):
        self.assertFalse(
            b.cross_lane_execution_state_valid(
                "A_AUDIT_REQUESTED",
                "A_AUDIT_REQUESTED",
            )
        )


class PatchIsolationTests(unittest.TestCase):
    def test_bootstrap_patch_is_temporary(self):
        job = exact_job()
        original = core._check_auditor_upstream
        seen = {}

        def fake_run_review(job_arg, *, repo_root, fetch, endpoint_fn):
            seen["patched"] = core._check_auditor_upstream is b._check_auditor_upstream_bootstrap
            return {"verdict": "PASS"}

        with mock.patch.object(core, "run_review", side_effect=fake_run_review):
            artifact = b.run_bootstrap_review(
                job,
                repo_root=Path("."),
                fetch=lambda _: {},
                endpoint_fn=lambda *args, **kwargs: (200, {}),
            )
        self.assertEqual(artifact["verdict"], "PASS")
        self.assertTrue(seen["patched"])
        self.assertIs(core._check_auditor_upstream, original)

    def test_bootstrap_does_not_mutate_job(self):
        job = exact_job()
        before = copy.deepcopy(job)
        with mock.patch.object(core, "run_review", return_value={"verdict": "PASS"}):
            b.run_bootstrap_review(job, repo_root=Path("."))
        self.assertEqual(job, before)


if __name__ == "__main__":
    unittest.main()
