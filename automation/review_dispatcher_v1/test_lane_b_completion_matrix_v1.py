from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from automation.review_dispatcher_v1.lane_b_completion_matrix_v1 import (
    completion_summary,
    load_matrix,
)

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs" / "lane_b_completion_matrix_v1.json"


class LaneBCompletionMatrixTests(unittest.TestCase):
    def test_01_current_matrix_is_valid_and_explicitly_incomplete(self):
        matrix = load_matrix(MATRIX)
        summary = completion_summary(matrix)
        self.assertEqual(summary["critical_rows"], 11)
        self.assertEqual(summary["counts"]["ADOPTED_PROVEN"], 4)
        self.assertEqual(summary["counts"]["FROZEN_CANDIDATE"], 6)
        self.assertEqual(summary["counts"]["OPEN_INTEGRATION"], 1)
        self.assertEqual(summary["progress_percent"], 71.82)
        self.assertFalse(summary["major_goal_complete"])
        self.assertIn("combined_fault_replay", summary["remaining_rows"])

    def test_02_all_adopted_rows_complete_major_goal(self):
        matrix = load_matrix(MATRIX)
        for row in matrix["rows"]:
            row["state"] = "ADOPTED_PROVEN"
        summary = completion_summary(matrix)
        self.assertEqual(summary["progress_percent"], 100.0)
        self.assertTrue(summary["major_goal_complete"])
        self.assertEqual(summary["remaining_rows"], [])

    def test_03_frozen_candidate_never_counts_as_complete(self):
        matrix = load_matrix(MATRIX)
        for row in matrix["rows"]:
            row["state"] = "ADOPTED_PROVEN"
        matrix["rows"][0]["state"] = "FROZEN_CANDIDATE"
        summary = completion_summary(matrix)
        self.assertFalse(summary["major_goal_complete"])
        self.assertLess(summary["progress_percent"], 100.0)

    def test_04_duplicate_row_id_is_rejected(self):
        raw = json.loads(MATRIX.read_text())
        raw["rows"][1]["id"] = raw["rows"][0]["id"]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "matrix.json"
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, "MATRIX_ROW_ID"):
                load_matrix(path)


if __name__ == "__main__":
    unittest.main()
