from __future__ import annotations

import unittest
from unittest.mock import patch

from automation.review_dispatcher_v1.model import ReviewContractError
from tools.review_build_admission_preflight_v2 import run_preflight

JOB = {
    "pr": 510,
    "lane": "AUDITOR",
    "head": "a" * 40,
    "tree": "b" * 40,
    "main": "c" * 40,
    "request_comment": 123,
    "request_sha256": "d" * 64,
    "request_id": "req-r2",
    "request": {"upstream": {}},
}


class BuildAdmissionPreflightV2Tests(unittest.TestCase):
    @patch("tools.review_build_admission_preflight_v2._check_auditor_upstream")
    @patch("tools.review_build_admission_preflight_v2.discover_request", return_value=JOB)
    def test_exact_binding_and_review_semantics_pass(self, _, upstream):
        out = run_preflight(
            repo="fufufu1116/multiverse-research", lane="AUDITOR", head="a" * 40,
            expected_request_comment=123, expected_request_sha256="d" * 64,
            expected_main="c" * 40, expected_tree="b" * 40,
        )
        upstream.assert_called_once()
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["auditor_upstream_review_semantics"], "PASS")
        self.assertFalse(out["publication_attempted"])
        self.assertFalse(out["owner_build_consumed"])

    @patch("tools.review_build_admission_preflight_v2._check_auditor_upstream")
    @patch("tools.review_build_admission_preflight_v2.discover_request", return_value=JOB)
    def test_review_semantic_findings_fail_closed(self, _, upstream):
        def fail(job, fetch, checks, findings):
            findings.append("upstream_lab_request_execution_state: wrong")
        upstream.side_effect = fail
        with self.assertRaisesRegex(ReviewContractError, "ADMISSION_AUDITOR_UPSTREAM_REVIEW_SEMANTICS"):
            run_preflight(
                repo="fufufu1116/multiverse-research", lane="AUDITOR", head="a" * 40,
                expected_request_comment=123, expected_request_sha256="d" * 64,
                expected_main="c" * 40, expected_tree="b" * 40,
            )

    @patch("tools.review_build_admission_preflight_v2._check_auditor_upstream")
    @patch("tools.review_build_admission_preflight_v2.discover_request", return_value=JOB)
    def test_request_drift_fails_before_semantic_review(self, _, upstream):
        with self.assertRaisesRegex(ReviewContractError, "ADMISSION_REQUEST_COMMENT_DRIFT"):
            run_preflight(
                repo="fufufu1116/multiverse-research", lane="AUDITOR", head="a" * 40,
                expected_request_comment=124, expected_request_sha256="d" * 64,
                expected_main="c" * 40, expected_tree="b" * 40,
            )
        upstream.assert_not_called()


if __name__ == "__main__":
    unittest.main()
