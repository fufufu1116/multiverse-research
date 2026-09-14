from __future__ import annotations

import unittest
from unittest.mock import patch

from automation.review_dispatcher_v1.model import ReviewContractError
from tools.review_build_admission_preflight_v1 import run_preflight


JOB = {
    "pr": 510,
    "lane": "AUDITOR",
    "head": "a" * 40,
    "tree": "b" * 40,
    "main": "c" * 40,
    "request_comment": 123,
    "request_sha256": "d" * 64,
    "request_id": "req-r2",
}


class BuildAdmissionPreflightTests(unittest.TestCase):
    @patch("tools.review_build_admission_preflight_v1.discover_request", return_value=JOB)
    def test_exact_binding_passes(self, _):
        out = run_preflight(repo="fufufu1116/multiverse-research", lane="AUDITOR",
            head="a"*40, expected_request_comment=123,
            expected_request_sha256="d"*64, expected_main="c"*40,
            expected_tree="b"*40)
        self.assertEqual(out["verdict"], "PASS")

    @patch("tools.review_build_admission_preflight_v1.discover_request", return_value=JOB)
    def test_request_drift_fails_closed(self, _):
        with self.assertRaisesRegex(ReviewContractError, "ADMISSION_REQUEST_COMMENT_DRIFT"):
            run_preflight(repo="fufufu1116/multiverse-research", lane="AUDITOR",
                head="a"*40, expected_request_comment=124,
                expected_request_sha256="d"*64, expected_main="c"*40,
                expected_tree="b"*40)


if __name__ == "__main__":
    unittest.main()
