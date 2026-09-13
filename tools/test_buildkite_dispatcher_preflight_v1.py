import unittest

from tools.buildkite_dispatcher_preflight_v1 import inspect_pipeline_text


GENERIC = '''set -euo pipefail
git fetch origin main
python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py \\
  --lane AUDITOR \\
  --repo fufufu1116/multiverse-research \\
  --head "$BUILDKITE_COMMIT" \\
  --output review_job.json
'''


class BuildkiteDispatcherPreflightV1Tests(unittest.TestCase):
    def test_generic_pipeline_passes(self):
        self.assertTrue(inspect_pipeline_text(GENERIC)["ok"])

    def test_hard_pinned_candidate_head_fails(self):
        text = GENERIC + '\ntest "$BUILDKITE_COMMIT" = "' + ('a' * 40) + '"\n'
        result = inspect_pipeline_text(text)
        self.assertFalse(result["ok"])
        self.assertIn("CANDIDATE_SPECIFIC_BUILDKITE_COMMIT_HARD_PIN", result["findings"])

    def test_missing_main_fetch_fails(self):
        result = inspect_pipeline_text(GENERIC.replace("git fetch origin main\n", ""))
        self.assertFalse(result["ok"])

    def test_missing_dynamic_head_binding_fails(self):
        result = inspect_pipeline_text(GENERIC.replace('--head "$BUILDKITE_COMMIT"', "--head candidate"))
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
