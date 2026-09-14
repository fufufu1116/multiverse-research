from __future__ import annotations

import unittest

from pathlib import Path

from automation.review_dispatcher_v1.model import cross_lane_execution_state_valid


class CrossLaneExecutionStateTests(unittest.TestCase):
    def test_exact_pr510_pattern_passes(self):
        self.assertTrue(cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_REVIEW_REQUESTED",
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_AUDIT_REQUESTED",
        ))

    def test_wrong_lab_suffix_fails(self):
        self.assertFalse(cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_AUDIT_REQUESTED",
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_AUDIT_REQUESTED",
        ))

    def test_wrong_auditor_suffix_fails(self):
        self.assertFalse(cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_REVIEW_REQUESTED",
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_REVIEW_REQUESTED",
        ))

    def test_cross_family_alias_fails(self):
        self.assertFalse(cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_A_REVIEW_REQUESTED",
            "FIXED_REQUEST_ONLY_B_AUDIT_REQUESTED",
        ))

    def test_non_string_fails(self):
        self.assertFalse(cross_lane_execution_state_valid(None, "X_AUDIT_REQUESTED"))

    def test_review_and_t2_both_use_shared_lane_validator(self):
        root = Path(__file__).resolve().parents[1]
        review_source = (root / "automation/review_dispatcher_v1/review.py").read_text()
        t2_source = (root / "automation/review_dispatcher_v1/t2.py").read_text()
        token = "cross_lane_execution_state_valid("
        self.assertIn(token, review_source)
        self.assertIn(token, t2_source)



if __name__ == "__main__":
    unittest.main()
