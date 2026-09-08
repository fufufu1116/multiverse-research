from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.combined_fault_replay_v1 import (
    ReplayError,
    Request,
    Result,
    T2,
    assert_job_still_current,
    canonical_request_chain,
    canonical_result,
    canonical_t2,
    recover_result_receipt,
    recover_t2_receipt,
    replay_happy_fault_sequence,
)


class CombinedFaultReplayTests(unittest.TestCase):
    def test_01_full_interleaved_replay_converges(self):
        result = replay_happy_fault_sequence()
        self.assertEqual(result["canonical_request_comments"], [10, 20])
        self.assertEqual(result["canonical_result_comment"], 100)
        self.assertEqual(result["canonical_t2_comment"], 200)
        self.assertTrue(result["result_receipt_recovered"])
        self.assertTrue(result["t2_receipt_recovered"])
        self.assertEqual(result["verdict"], "PASS")

    def test_02_same_generation_request_earliest_wins(self):
        a = Request(8, "a-request", "a" * 64, None)
        b = Request(9, "b-request", "b" * 64, None)
        self.assertEqual(canonical_request_chain([b, a]), [a])

    def test_03_loser_derived_successor_fails_closed(self):
        a = Request(8, "a-request", "a" * 64, None)
        b = Request(9, "b-request", "b" * 64, None)
        child = Request(10, "child-request", "c" * 64, b.sha256)
        with self.assertRaisesRegex(ReplayError, "UNKNOWN_OR_LOSER_PREDECESSOR"):
            canonical_request_chain([a, b, child])

    def test_04_old_job_rejected_after_supersession(self):
        a = Request(8, "a-request", "a" * 64, None)
        c = Request(10, "c-request", "c" * 64, a.sha256)
        chain = canonical_request_chain([a, c])
        with self.assertRaisesRegex(ReplayError, "STALE_JOB_REQUEST"):
            assert_job_still_current(a.sha256, chain)
        assert_job_still_current(c.sha256, chain)

    def test_05_concurrent_results_choose_earliest_trusted(self):
        sha = "c" * 64
        items = [Result(12, sha), Result(10, sha), Result(1, sha, trusted=False)]
        self.assertEqual(canonical_result(items, sha).comment_id, 10)
        with self.assertRaisesRegex(ReplayError, "NONCANONICAL_RESULT_RECEIPT"):
            recover_result_receipt(items, sha, 12)
        self.assertTrue(recover_result_receipt(items, sha, 10)["recovered"])

    def test_06_concurrent_t2_choose_earliest_trusted(self):
        sha = "c" * 64
        items = [T2(22, sha, 10), T2(20, sha, 10), T2(1, sha, 10, trusted=False)]
        self.assertEqual(canonical_t2(items, sha, 10).comment_id, 20)
        with self.assertRaisesRegex(ReplayError, "NONCANONICAL_T2_RECEIPT"):
            recover_t2_receipt(items, sha, 10, 22)
        self.assertTrue(recover_t2_receipt(items, sha, 10, 20)["recovered"])

    def test_07_duplicate_request_id_fails_closed(self):
        a = Request(8, "same", "a" * 64, None)
        b = Request(9, "same", "b" * 64, None)
        with self.assertRaisesRegex(ReplayError, "DUPLICATE_REQUEST_ID"):
            canonical_request_chain([a, b])

    def test_08_missing_trusted_evidence_fails_closed(self):
        sha = "c" * 64
        with self.assertRaisesRegex(ReplayError, "NO_TRUSTED_RESULT"):
            canonical_result([Result(1, sha, trusted=False)], sha)
        with self.assertRaisesRegex(ReplayError, "NO_TRUSTED_T2"):
            canonical_t2([T2(1, sha, 10, trusted=False)], sha, 10)


if __name__ == "__main__":
    unittest.main()
