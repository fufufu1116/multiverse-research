from __future__ import annotations

import unittest
from pathlib import Path

from tools.buildkite_auditor_bootstrap_preflight_v2 import inspect_pipeline_text
from tools.buildkite_auditor_bootstrap_smoke_v2 import run_smoke


GOOD = '''
steps:
  - label: "dispatcher"
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
  - wait
  - label: "publisher"
    agents:
      queue: "independent-auditor"
    secrets:
      - MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY
    command: |
      git fetch origin main:refs/remotes/origin/main
      PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.publisher'
      PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/publisher.py --receipt review_publish_receipt.json
  - wait
  - label: "t2"
    agents:
      queue: "independent-auditor"
    secrets:
      - MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY
    command: |
      git fetch origin main:refs/remotes/origin/main
      PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.t2'
      PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/t2.py --receipt review_publish_receipt.json --output t2_publish_receipt.json
'''


class BootstrapPreflightV2Tests(unittest.TestCase):
    def test_good_payload_passes(self) -> None:
        self.assertTrue(inspect_pipeline_text(GOOD)["ok"])

    def test_executable_archive_import_smoke(self) -> None:
        run_smoke(Path.cwd(), "HEAD")

    def test_rejects_fetch_head_anywhere(self) -> None:
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
        self.assertIn("SINGLE_DOLLAR_RUNTIME_VARIABLE", result["findings"])

    def test_rejects_any_single_dollar_runtime_variable(self) -> None:
        bad = GOOD.replace("$$DISPATCHER_REF", "$DISPATCHER_REF")
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("SINGLE_DOLLAR_RUNTIME_VARIABLE", result["findings"])

    def test_rejects_pwd_export_pythonpath(self) -> None:
        bad = GOOD.replace(
            "PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.dispatcher'",
            'export PYTHONPATH="$PWD/.mv_dispatcher"\n      python3 -c \'import automation.review_dispatcher_v1.dispatcher\'',
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("AMBIENT_PWD_PYTHONPATH", result["findings"])

    def test_requires_dispatcher_import_smoke(self) -> None:
        bad = GOOD.replace(
            "PYTHONPATH=.mv_dispatcher python3 -c 'import automation.review_dispatcher_v1.dispatcher'\n",
            "",
        )
        self.assertFalse(inspect_pipeline_text(bad)["ok"])

    def test_requires_publisher_stage(self) -> None:
        bad = GOOD.replace("publisher.py", "publisher_missing.py")
        self.assertFalse(inspect_pipeline_text(bad)["ok"])

    def test_requires_t2_stage(self) -> None:
        bad = GOOD.replace("t2.py", "t2_missing.py")
        self.assertFalse(inspect_pipeline_text(bad)["ok"])

    def test_requires_all_three_hosted_queues(self) -> None:
        bad = GOOD.replace('queue: "independent-auditor"', 'queue: "default"', 1)
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("AUDITOR_QUEUE_STAGE_COUNT_NOT_3", result["findings"])

    def test_requires_seven_inline_pythonpath_invocations(self) -> None:
        bad = GOOD.replace(
            "PYTHONPATH=.mv_dispatcher python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py",
            "python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py",
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("INLINE_PYTHONPATH_COUNT_LT_7", result["findings"])

    def test_requires_two_wait_boundaries(self) -> None:
        bad = GOOD.replace("  - wait\n", "", 1)
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("WAIT_STAGE_COUNT_NOT_2", result["findings"])


if __name__ == "__main__":
    unittest.main()
