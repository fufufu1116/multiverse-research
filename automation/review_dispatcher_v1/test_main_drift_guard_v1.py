from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.main_drift_guard_v1 import (
    assess_unrelated_main_drift,
)
from automation.review_dispatcher_v1.model import ReviewContractError


OLD = "a" * 40
LIVE = "b" * 40
HEAD = "c" * 40


def compare(*, status="ahead", merge_base=OLD, files=()):
    return {
        "status": status,
        "too_large": None,
        "merge_base_commit": {"sha": merge_base},
        "files": [{"filename": path} for path in files],
    }


class MainDriftGuardTests(unittest.TestCase):
    def test_01_exact_main_passes(self):
        result = assess_unrelated_main_drift(
            request_main=OLD,
            live_main=OLD,
            candidate_compare=compare(files=("src/a.py",)),
            drift_compare=compare(files=()),
        )
        self.assertEqual(result["mode"], "EXACT_MAIN")

    def test_02_unrelated_research_drift_passes(self):
        result = assess_unrelated_main_drift(
            request_main=OLD,
            live_main=LIVE,
            candidate_compare=compare(files=("automation/other_lane/tool.py",)),
            drift_compare=compare(
                files=("research/opportunity_engine_v0/note.md",)
            ),
        )
        self.assertEqual(result["mode"], "SAFE_UNRELATED_MAIN_DRIFT")

    def test_03_candidate_overlap_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_TARGET_OVERLAP",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/shared.md",)),
                drift_compare=compare(files=("research/shared.md",)),
            )

    def test_04_dispatcher_control_drift_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_CRITICAL_PATH",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=compare(
                    files=("automation/review_dispatcher_v1/model.py",)
                ),
            )

    def test_05_workflow_drift_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_CRITICAL_PATH",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=compare(files=(".github/workflows/x.yml",)),
            )

    def test_06_control_doc_drift_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_CRITICAL_PATH",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=compare(files=("docs/control/RULE.md",)),
            )

    def test_07_diverged_main_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_NOT_DESCENDANT",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=compare(status="diverged", files=("research/b.md",)),
            )

    def test_08_wrong_merge_base_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_MERGE_BASE_MISMATCH",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=compare(
                    merge_base="d" * 40,
                    files=("research/b.md",),
                ),
            )

    def test_09_too_large_compare_fails_closed(self):
        payload = compare(files=("research/b.md",))
        payload["too_large"] = True
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_COMPARE_TOO_LARGE",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=payload,
            )

    def test_10_bootstrap_drift_fails_closed(self):
        with self.assertRaisesRegex(
            ReviewContractError,
            "MAIN_DRIFT_CRITICAL_PATH",
        ):
            assess_unrelated_main_drift(
                request_main=OLD,
                live_main=LIVE,
                candidate_compare=compare(files=("research/a.md",)),
                drift_compare=compare(files=("MULTIVERSE_BOOTSTRAP.md",)),
            )


if __name__ == "__main__":
    unittest.main()
