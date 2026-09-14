from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.main_drift_guard_v1 import (
    MAX_COMPARE_FILES,
    MAX_SAFE_DRIFT_COMMITS,
    assess_unrelated_main_drift,
)
from automation.review_dispatcher_v1.model import ReviewContractError


OLD = "a" * 40
LIVE = "b" * 40
BASE = "c" * 40


def compare(
    *,
    status="ahead",
    merge_base=OLD,
    files=(),
    ahead_by=1,
    behind_by=0,
    total_commits=None,
):
    return {
        "status": status,
        "ahead_by": ahead_by,
        "behind_by": behind_by,
        "total_commits": ahead_by if total_commits is None else total_commits,
        "too_large": None,
        "merge_base_commit": {"sha": merge_base},
        "files": [
            item if isinstance(item, dict) else {"filename": item}
            for item in files
        ],
    }


def candidate(*, files=("automation/review_dispatcher_v1/x.py",), **kwargs):
    return compare(merge_base=BASE, files=files, **kwargs)


class MainDriftGuardTests(unittest.TestCase):
    def call(self, *, drift=None, candidate_compare=None, live=LIVE):
        return assess_unrelated_main_drift(
            request_main=OLD,
            live_main=live,
            candidate_base=BASE,
            candidate_compare=candidate_compare or candidate(),
            drift_compare=drift or compare(files=("research/opportunity_engine_v0/note.md",)),
        )

    def test_01_exact_main_passes(self):
        result = self.call(live=OLD)
        self.assertEqual(result["mode"], "EXACT_MAIN")
        self.assertEqual(result["drift_files"], [])

    def test_02_unrelated_research_drift_passes(self):
        result = self.call()
        self.assertEqual(result["mode"], "SAFE_UNRELATED_MAIN_DRIFT")
        self.assertEqual(result["request_main"], OLD)
        self.assertEqual(result["live_main"], LIVE)

    def test_03_candidate_overlap_fails_closed(self):
        path = "research/shared.md"
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_TARGET_OVERLAP"):
            self.call(
                candidate_compare=candidate(files=(path,)),
                drift=compare(files=(path,)),
            )

    def test_04_dispatcher_drift_is_not_allowlisted(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_ALLOWLISTED"):
            self.call(drift=compare(files=("automation/review_dispatcher_v1/model.py",)))

    def test_05_workflow_drift_is_not_allowlisted(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_ALLOWLISTED"):
            self.call(drift=compare(files=(".github/workflows/x.yml",)))

    def test_06_control_doc_drift_is_not_allowlisted(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_ALLOWLISTED"):
            self.call(drift=compare(files=("docs/control/RULE.md",)))

    def test_07_diverged_main_fails_closed(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_DESCENDANT"):
            self.call(drift=compare(status="diverged", files=("research/b.md",)))

    def test_08_wrong_drift_merge_base_fails_closed(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_MERGE_BASE_MISMATCH"):
            self.call(drift=compare(merge_base="d" * 40, files=("research/b.md",)))

    def test_09_too_large_compare_fails_closed(self):
        payload = compare(files=("research/b.md",))
        payload["too_large"] = True
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_COMPARE_TOO_LARGE"):
            self.call(drift=payload)

    def test_10_bootstrap_drift_is_not_allowlisted(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_ALLOWLISTED"):
            self.call(drift=compare(files=("MULTIVERSE_BOOTSTRAP.md",)))

    def test_11_rename_previous_filename_participates_in_overlap(self):
        old_path = "research/shared.md"
        drift = compare(
            files=({"filename": "research/renamed.md", "previous_filename": old_path},)
        )
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_TARGET_OVERLAP"):
            self.call(
                candidate_compare=candidate(files=(old_path,)),
                drift=drift,
            )

    def test_12_rename_from_nonresearch_path_fails_closed(self):
        drift = compare(
            files=({
                "filename": "research/now-safe.md",
                "previous_filename": "automation/review_dispatcher_v1/old.py",
            },)
        )
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_NOT_ALLOWLISTED"):
            self.call(drift=drift)

    def test_13_commit_budget_fails_closed(self):
        too_many = MAX_SAFE_DRIFT_COMMITS + 1
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_COMMIT_BUDGET"):
            self.call(
                drift=compare(
                    files=("research/b.md",),
                    ahead_by=too_many,
                    total_commits=too_many,
                )
            )

    def test_14_file_budget_fails_closed(self):
        files = tuple(f"research/f{i}.md" for i in range(MAX_COMPARE_FILES + 1))
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_COMPARE_FILE_BUDGET"):
            self.call(drift=compare(files=files))

    def test_15_candidate_merge_base_must_match_bound_base(self):
        with self.assertRaisesRegex(ReviewContractError, "CANDIDATE_COMPARE_MERGE_BASE_MISMATCH"):
            self.call(
                candidate_compare=candidate(merge_base="d" * 40)
            )

    def test_16_candidate_compare_must_be_ahead(self):
        with self.assertRaisesRegex(ReviewContractError, "CANDIDATE_COMPARE_NOT_AHEAD"):
            self.call(
                candidate_compare=candidate(status="diverged")
            )

    def test_17_behind_drift_fails_closed(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_BEHIND"):
            self.call(
                drift=compare(files=("research/b.md",), behind_by=1)
            )

    def test_18_ambiguous_commit_count_fails_closed(self):
        with self.assertRaisesRegex(ReviewContractError, "MAIN_DRIFT_COMMIT_COUNT_AMBIGUOUS"):
            self.call(
                drift=compare(
                    files=("research/b.md",),
                    ahead_by=2,
                    total_commits=1,
                )
            )


if __name__ == "__main__":
    unittest.main()
