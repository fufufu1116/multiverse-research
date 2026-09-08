from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.model import ReviewContractError
from automation.review_dispatcher_v1.t2_idempotence_v1 import (
    assert_published_t2_is_canonical,
    assert_referenced_result_is_canonical,
    canonical_trusted_comment_id,
)


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


class T2IdempotenceTests(unittest.TestCase):
    def test_01_lab_reference_may_ignore_late_duplicate(self):
        marker = "LAB-MARKER"
        comments = [trusted(10, marker, "LAB"), trusted(20, marker, "LAB")]
        self.assertEqual(
            assert_referenced_result_is_canonical(
                comments,
                lane="LAB",
                marker=marker,
                referenced_comment_id=10,
            ),
            10,
        )

    def test_02_late_lab_duplicate_cannot_be_referenced(self):
        marker = "LAB-MARKER"
        comments = [trusted(10, marker, "LAB"), trusted(20, marker, "LAB")]
        with self.assertRaisesRegex(ReviewContractError, "REFERENCED_RESULT_NOT_CANONICAL"):
            assert_referenced_result_is_canonical(
                comments,
                lane="LAB",
                marker=marker,
                referenced_comment_id=20,
            )

    def test_03_t2_earliest_auditor_comment_wins(self):
        marker = "T2-MARKER"
        comments = [trusted(30, marker, "AUDITOR"), trusted(15, marker, "AUDITOR")]
        self.assertEqual(
            canonical_trusted_comment_id(comments, lane="AUDITOR", marker=marker),
            15,
        )

    def test_04_late_t2_duplicate_fails_closed(self):
        marker = "T2-MARKER"
        comments = [trusted(15, marker, "AUDITOR"), trusted(30, marker, "AUDITOR")]
        with self.assertRaisesRegex(ReviewContractError, "NONCANONICAL_DUPLICATE_T2"):
            assert_published_t2_is_canonical(
                comments,
                marker=marker,
                published_comment_id=30,
            )

    def test_05_lab_and_auditor_namespaces_do_not_collide(self):
        marker = "SHARED"
        comments = [trusted(5, marker, "LAB"), trusted(7, marker, "AUDITOR")]
        self.assertEqual(canonical_trusted_comment_id(comments, lane="LAB", marker=marker), 5)
        self.assertEqual(canonical_trusted_comment_id(comments, lane="AUDITOR", marker=marker), 7)

    def test_06_untrusted_earlier_comment_cannot_preempt(self):
        marker = "T2-MARKER"
        attacker = {
            "id": 1,
            "body": marker,
            "user": {"login": "attacker", "type": "User"},
        }
        comments = [attacker, trusted(9, marker, "AUDITOR")]
        self.assertEqual(canonical_trusted_comment_id(comments, lane="AUDITOR", marker=marker), 9)

    def test_07_missing_canonical_comment_fails_closed(self):
        with self.assertRaisesRegex(ReviewContractError, "NO_CANONICAL_TRUSTED_COMMENT"):
            canonical_trusted_comment_id([], lane="LAB", marker="missing")


if __name__ == "__main__":
    unittest.main()
