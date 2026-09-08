from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class IntegratedResilienceConvergenceTests(unittest.TestCase):
    def source(self, name: str) -> str:
        return (ROOT / name).read_text()

    def test_01_publisher_wrapper_composes_three_resilience_layers(self):
        source = self.source("publisher.py")
        for token in (
            "assert_job_request_still_canonical(",
            "assert_published_result_is_canonical(",
            "recover_publish_receipt(",
        ):
            self.assertIn(token, source)

    def test_02_t2_wrapper_composes_canonicalization_and_recovery(self):
        source = self.source("t2.py")
        for token in (
            "assert_referenced_result_is_canonical(",
            "assert_published_t2_is_canonical(",
            "recover_t2_receipt(",
            "_filter_noncanonical_lab_duplicates(",
        ):
            self.assertIn(token, source)

    def test_03_legacy_implementations_remain_separate(self):
        publisher_legacy = self.source("publisher_legacy_v1.py")
        t2_legacy = self.source("t2_legacy_v1.py")
        self.assertIn("github_full_pr_binding(", publisher_legacy)
        self.assertIn("github_full_pr_binding(", t2_legacy)
        self.assertNotIn("recover_publish_receipt(", publisher_legacy)
        self.assertNotIn("recover_t2_receipt(", t2_legacy)

    def test_04_joint_validator_knows_both_wrapper_splits(self):
        source = self.source("validator.py")
        for token in (
            "PUBLISHER_LEGACY_REQUIRED",
            "PUBLISHER_WRAPPER_REQUIRED",
            "T2_LEGACY_REQUIRED",
            "T2_WRAPPER_REQUIRED",
            "combined_fault_replay_v1.py",
        ):
            self.assertIn(token, source)

    def test_05_combined_replay_surface_is_present(self):
        source = self.source("combined_fault_replay_v1.py")
        self.assertIn("canonical_result", source)
        self.assertIn("canonical_t2", source)
        self.assertIn("receipt", source)


if __name__ == "__main__":
    unittest.main()
