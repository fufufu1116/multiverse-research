from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.review import _cross_lane_execution_state_valid


class CrossLaneExecutionStateTests(unittest.TestCase):
    def test_exact_pr510_pattern_passes(self):
        self.assertTrue(_cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_REVIEW_REQUESTED",
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_AUDIT_REQUESTED",
        ))

    def test_wrong_lab_suffix_fails(self):
        self.assertFalse(_cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_AUDIT_REQUESTED",
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_AUDIT_REQUESTED",
        ))

    def test_wrong_auditor_suffix_fails(self):
        self.assertFalse(_cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_REVIEW_REQUESTED",
            "FIXED_REQUEST_ONLY_AUDITOR_POST_WRITE_VISIBILITY_CACHE_BYPASS_V1_REVIEW_REQUESTED",
        ))

    def test_cross_family_alias_fails(self):
        self.assertFalse(_cross_lane_execution_state_valid(
            "FIXED_REQUEST_ONLY_A_REVIEW_REQUESTED",
            "FIXED_REQUEST_ONLY_B_AUDIT_REQUESTED",
        ))

    def test_non_string_fails(self):
        self.assertFalse(_cross_lane_execution_state_valid(None, "X_AUDIT_REQUESTED"))


if __name__ == "__main__":
    unittest.main()
