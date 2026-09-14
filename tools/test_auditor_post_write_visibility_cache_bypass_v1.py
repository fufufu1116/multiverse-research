from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error

from automation.review_dispatcher_v1.github_read_resilience_v1 import (
    github_json_fresh_read,
    github_json_read,
    github_json_request,
)


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class AuditorPostWriteVisibilityCacheBypassV1Tests(unittest.TestCase):
    def _with_build_cache(self):
        tmp = tempfile.TemporaryDirectory(prefix="mv-post-write-cache-v1-")
        previous_cwd = os.getcwd()
        previous_build_id = os.environ.get("BUILDKITE_BUILD_ID")
        os.chdir(tmp.name)
        os.environ["BUILDKITE_BUILD_ID"] = "post-write-visibility-test-build"

        def cleanup():
            os.chdir(previous_cwd)
            if previous_build_id is None:
                os.environ.pop("BUILDKITE_BUILD_ID", None)
            else:
                os.environ["BUILDKITE_BUILD_ID"] = previous_build_id
            tmp.cleanup()

        self.addCleanup(cleanup)
        return Path(tmp.name)

    def test_default_read_uses_same_build_cache(self):
        self._with_build_cache()
        calls = []

        def opener(req, timeout):
            calls.append(req.full_url)
            return _Response(b'{"generation":1}')

        first = github_json_read(
            "https://api.github.com/example/cache",
            user_agent="test",
            opener=opener,
            clock=lambda: 100.0,
        )
        second = github_json_read(
            "https://api.github.com/example/cache",
            user_agent="test",
            opener=opener,
            clock=lambda: 101.0,
        )

        self.assertEqual(first, {"generation": 1})
        self.assertEqual(second, {"generation": 1})
        self.assertEqual(len(calls), 1)

    def test_fresh_read_bypasses_stale_pre_write_cache_and_refreshes_it(self):
        self._with_build_cache()
        calls = []
        payloads = [b'[{"id":1}]', b'[{"id":1},{"id":2}]']

        def opener(req, timeout):
            calls.append(req.full_url)
            return _Response(payloads[len(calls) - 1])

        url = "https://api.github.com/repos/o/r/issues/9/comments"
        before_write = github_json_read(
            url, user_agent="test", opener=opener, clock=lambda: 100.0
        )
        still_stale = github_json_read(
            url, user_agent="test", opener=opener, clock=lambda: 101.0
        )
        after_write = github_json_fresh_read(
            url, user_agent="test", opener=opener, clock=lambda: 101.0
        )
        refreshed_cache = github_json_read(
            url, user_agent="test", opener=opener, clock=lambda: 102.0
        )

        self.assertEqual(before_write, [{"id": 1}])
        self.assertEqual(still_stale, [{"id": 1}])
        self.assertEqual(after_write, [{"id": 1}, {"id": 2}])
        self.assertEqual(refreshed_cache, after_write)
        self.assertEqual(len(calls), 2)

    def test_mutation_remains_non_retrying(self):
        calls = []

        def opener(req, timeout):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(
                req.full_url, 429, "rate limit", {"Retry-After": "1"}, None
            )

        with self.assertRaises(urllib.error.HTTPError):
            github_json_request(
                "https://api.github.com/example/write",
                user_agent="test",
                method="POST",
                data=b"{}",
                opener=opener,
                sleeper=lambda _: self.fail("mutation must not sleep/retry"),
            )
        self.assertEqual(len(calls), 1)

    def test_publisher_post_write_path_explicitly_disables_cache(self):
        source = Path("automation/review_dispatcher_v1/publisher.py").read_text()
        self.assertIn("comments = _fresh_verify(job, use_cache=False)", source)
        self.assertIn("github_json_fresh_read", source)
        self.assertIn("POST_WRITE_VISIBILITY_MAX_READS = 4", source)
        self.assertIn("POST_WRITE_VISIBILITY_DELAY_SECONDS = 1.0", source)

    def test_t2_post_write_path_explicitly_disables_cache(self):
        source = Path("automation/review_dispatcher_v1/t2.py").read_text()
        self.assertIn("use_cache=False", source)
        self.assertIn("github_json_fresh_read", source)
        self.assertIn("T2_POST_WRITE_VISIBILITY_MAX_READS = 4", source)
        self.assertIn("T2_POST_WRITE_VISIBILITY_DELAY_SECONDS = 1.0", source)


if __name__ == "__main__":
    unittest.main()
