from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.model import ReviewContractError
from automation.review_dispatcher_v1.result_canonicalization_v1 import (
    assert_published_result_is_canonical,
    canonical_result_comment_id,
)


def trusted(comment_id: int, marker: str, lane: str = "LAB") -> dict:
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


class ResultCanonicalizationTests(unittest.TestCase):
    def test_01_single_result_is_canonical(self):
        marker = "<!-- MULTIVERSE_FIXED_REVIEW_RESULT_V1:req:"
        comments = [trusted(20, marker)]
        self.assertEqual(
            canonical_result_comment_id(comments, lane="LAB", marker=marker),
            20,
        )

    def test_02_earliest_trusted_result_wins(self):
        marker = "<!-- MULTIVERSE_FIXED_REVIEW_RESULT_V1:req:"
        comments = [trusted(30, marker), trusted(10, marker), trusted(20, marker)]
        self.assertEqual(
            canonical_result_comment_id(comments, lane="LAB", marker=marker),
            10,
        )

    def test_03_untrusted_earlier_comment_does_not_win(self):
        marker = "<!-- MULTIVERSE_FIXED_REVIEW_RESULT_V1:req:"
        attacker = {
            "id": 1,
            "body": marker + " fake -->",
            "user": {"login": "attacker", "type": "User"},
        }
        comments = [attacker, trusted(10, marker)]
        self.assertEqual(
            canonical_result_comment_id(comments, lane="LAB", marker=marker),
            10,
        )

    def test_04_late_duplicate_is_noncanonical(self):
        marker = "<!-- MULTIVERSE_FIXED_REVIEW_RESULT_V1:req:"
        comments = [trusted(10, marker), trusted(20, marker)]
        with self.assertRaisesRegex(ReviewContractError, "NONCANONICAL_DUPLICATE_RESULT"):
            assert_published_result_is_canonical(
                comments,
                lane="LAB",
                marker=marker,
                published_comment_id=20,
            )

    def test_05_auditor_lane_is_independent(self):
        marker = "<!-- MULTIVERSE_FIXED_REVIEW_RESULT_V1:req:"
        comments = [trusted(5, marker, "LAB"), trusted(7, marker, "AUDITOR")]
        self.assertEqual(
            canonical_result_comment_id(comments, lane="AUDITOR", marker=marker),
            7,
        )

    def test_06_missing_result_fails_closed(self):
        with self.assertRaisesRegex(ReviewContractError, "NO_TRUSTED_RESULT_FOR_MARKER"):
            canonical_result_comment_id([], lane="LAB", marker="marker")


if __name__ == "__main__":
    unittest.main()
