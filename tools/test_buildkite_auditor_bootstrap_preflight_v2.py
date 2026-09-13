from __future__ import annotations

import unittest

from tools.buildkite_auditor_bootstrap_preflight_v2 import inspect_pipeline_text


GOOD = '''
steps:
  - label: "MULTIVERSE Independent Auditor"
    agents:
      queue: "independent-auditor"
    command: |
      git fetch origin main:refs/remotes/origin/main
      git rev-parse --verify refs/remotes/origin/main^{commit}
      git archive refs/remotes/origin/main automation/review_dispatcher_v1 | tar -x -C .mv_dispatcher
      DISPATCHER_REF="$(git rev-parse refs/remotes/origin/main)"
      export MULTIVERSE_DISPATCHER_REF="$$DISPATCHER_REF"
      PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.dispatcher'
      PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py --head "$$BUILDKITE_COMMIT"
      PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py
'''


class BootstrapPreflightV2Tests(unittest.TestCase):
    def test_good_payload_passes(self) -> None:
        self.assertTrue(inspect_pipeline_text(GOOD)["ok"])

    def test_rejects_fetch_head(self) -> None:
        bad = GOOD.replace(
            "refs/remotes/origin/main automation/review_dispatcher_v1",
            "FETCH_HEAD automation/review_dispatcher_v1",
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("FETCH_HEAD_DEPENDENCY", result["findings"])

    def test_rejects_single_dollar_buildkite_commit(self) -> None:
        bad = GOOD.replace("$$BUILDKITE_COMMIT", "$BUILDKITE_COMMIT")
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("SINGLE_DOLLAR_BUILDKITE_COMMIT", result["findings"])

    def test_rejects_pwd_export_pythonpath(self) -> None:
        bad = GOOD.replace(
            "PYTHONPATH=.mv_dispatcher python3 -c",
            'export PYTHONPATH="$PWD/.mv_dispatcher"\n      python3 -c',
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("AMBIENT_PWD_PYTHONPATH", result["findings"])

    def test_requires_import_smoke_line(self) -> None:
        bad = GOOD.replace(
            "PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.dispatcher'\n",
            "",
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(str(x).startswith("MISSING_REQUIRED_TOKEN:") for x in result["findings"])
        )

    def test_requires_inline_pythonpath_for_all_python_steps(self) -> None:
        bad = GOOD.replace(
            "PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py",
            "python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py",
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("INLINE_PYTHONPATH_COUNT_LT_3", result["findings"])

    def test_missing_hosted_queue_fails(self) -> None:
        bad = GOOD.replace('queue: "independent-auditor"', 'queue: "default"')
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
