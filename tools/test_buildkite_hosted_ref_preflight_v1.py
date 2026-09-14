import unittest

from tools.buildkite_hosted_ref_preflight_v1 import inspect_pipeline_text

GOOD = '''steps:\n  - label: "MULTIVERSE Independent Auditor"\n    agents:\n      queue: "independent-auditor"\n    command: |\n      set -euo pipefail\n      git fetch origin main:refs/remotes/origin/main\n      git rev-parse --verify refs/remotes/origin/main^{commit}\n      git archive refs/remotes/origin/main automation/review_dispatcher_v1 | tar -x -C .mv_dispatcher\n      python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py \\\n        --lane AUDITOR \\\n        --repo fufufu1116/multiverse-research \\\n        --head "$BUILDKITE_COMMIT" \\\n        --output review_job.json\n'''


class HostedAuditorRefPreflightV1Tests(unittest.TestCase):
    def test_explicit_remote_main_ref_passes(self):
        self.assertTrue(inspect_pipeline_text(GOOD)["ok"])

    def test_fetch_head_dependency_fails(self):
        bad = GOOD.replace(
            "git fetch origin main:refs/remotes/origin/main\n      git rev-parse --verify refs/remotes/origin/main^{commit}\n      git archive refs/remotes/origin/main automation/review_dispatcher_v1",
            'git fetch origin main\n      DISPATCHER_REF="$(git rev-parse FETCH_HEAD)"\n      git archive "$DISPATCHER_REF" automation/review_dispatcher_v1',
        )
        result = inspect_pipeline_text(bad)
        self.assertFalse(result["ok"])
        self.assertIn("FORBIDDEN_FETCH_HEAD_DEPENDENCY", result["findings"])

    def test_missing_hosted_queue_fails(self):
        result = inspect_pipeline_text(GOOD.replace('queue: "independent-auditor"\n', ""))
        self.assertFalse(result["ok"])

    def test_missing_ref_verification_fails(self):
        result = inspect_pipeline_text(
            GOOD.replace("      git rev-parse --verify refs/remotes/origin/main^{commit}\n", "")
        )
        self.assertFalse(result["ok"])

    def test_missing_dynamic_candidate_head_fails(self):
        result = inspect_pipeline_text(GOOD.replace('--head "$BUILDKITE_COMMIT"', "--head fixed"))
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
