from __future__ import annotations

import unittest
from pathlib import Path

from tools.buildkite_auditor_bootstrap_preflight_v3 import inspect_pipeline_text
from tools.buildkite_auditor_bootstrap_smoke_v3 import run_smoke

PIPELINE = Path("buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_HOSTED_v3.yml")


class BootstrapPreflightV3Tests(unittest.TestCase):
    def test_stored_payload_passes(self) -> None:
        self.assertTrue(inspect_pipeline_text(PIPELINE.read_text())["ok"])

    def test_executable_archive_import_smoke(self) -> None:
        run_smoke(Path.cwd(), "HEAD")

    def test_requires_current_transitive_read_module_smoke(self) -> None:
        text = PIPELINE.read_text().replace(
            "PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.github_read_resilience_v1'\n",
            "",
        )
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertTrue(any("github_read_resilience_v1" in item for item in result["findings"]))

    def test_rejects_latest_failure_shape_direct_dispatcher_without_package_root(self) -> None:
        text = PIPELINE.read_text().replace(
            "PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py",
            "python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py",
        )
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertTrue(any(item.startswith("DIRECT_ENTRY_WITHOUT_PACKAGE_ROOT") for item in result["findings"]))

    def test_rejects_review_without_package_root(self) -> None:
        text = PIPELINE.read_text().replace(
            "if PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py",
            "if python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py",
        )
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertTrue(any(item.startswith("DIRECT_ENTRY_WITHOUT_PACKAGE_ROOT") for item in result["findings"]))

    def test_rejects_fetch_head(self) -> None:
        text = PIPELINE.read_text().replace("refs/remotes/origin/main", "FETCH_HEAD", 1)
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertIn("FETCH_HEAD_DEPENDENCY", result["findings"])

    def test_rejects_single_dollar_buildkite_commit(self) -> None:
        text = PIPELINE.read_text().replace("$$BUILDKITE_COMMIT", "$BUILDKITE_COMMIT")
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertIn("SINGLE_DOLLAR_RUNTIME_VARIABLE", result["findings"])

    def test_requires_three_auditor_stages(self) -> None:
        text = PIPELINE.read_text().replace('queue: "independent-auditor"', 'queue: "default"', 1)
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertIn("AUDITOR_QUEUE_STAGE_COUNT_NOT_3", result["findings"])

    def test_requires_two_waits(self) -> None:
        text = PIPELINE.read_text().replace("  - wait\n", "", 1)
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertIn("WAIT_STAGE_COUNT_NOT_2", result["findings"])


if __name__ == "__main__":
    unittest.main()
