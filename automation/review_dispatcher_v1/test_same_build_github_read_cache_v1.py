from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from automation.review_dispatcher_v1 import github_read_resilience_v1 as r


PR_URL = "https://api.github.com/repos/fufufu1116/multiverse-research/pulls/382"
COMMENTS_URL = "https://api.github.com/repos/fufufu1116/multiverse-research/issues/382/comments?per_page=100&page=1"
COMMENT_URL = "https://api.github.com/repos/fufufu1116/multiverse-research/issues/comments/12345"


def response(payload: object):
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


class SameBuildGithubReadCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(lambda: os.chdir(self.cwd))

    def test_exact_get_reused_within_same_build_without_network(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req.full_url)
            return response({"number": 382})

        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": "build-a"}, clear=False):
            first = r.github_json_read(PR_URL, user_agent="test", opener=opener, clock=lambda: 100.0)
            second = r.github_json_read(
                PR_URL,
                user_agent="test",
                opener=lambda *a, **k: self.fail("network must not be used"),
                clock=lambda: 102.0,
            )

        self.assertEqual(first, {"number": 382})
        self.assertEqual(second, first)
        self.assertEqual(calls, [PR_URL])

    def test_direct_comment_can_be_derived_from_recent_issue_comments_page(self):
        payload = [{"id": 12345, "body": "PASS"}, {"id": 99, "body": "other"}]

        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": "build-b"}, clear=False):
            r.github_json_read(
                COMMENTS_URL,
                user_agent="test",
                opener=lambda req, timeout=30: response(payload),
                clock=lambda: 200.0,
            )
            comment = r.github_json_read(
                COMMENT_URL,
                user_agent="test",
                opener=lambda *a, **k: self.fail("network must not be used"),
                clock=lambda: 203.0,
            )

        self.assertEqual(comment, {"id": 12345, "body": "PASS"})

    def test_expired_entry_falls_back_to_live_get(self):
        calls = []

        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": "build-c"}, clear=False):
            r.github_json_read(
                PR_URL,
                user_agent="test",
                opener=lambda req, timeout=30: response({"v": 1}),
                clock=lambda: 300.0,
            )

            def opener(req, timeout=30):
                calls.append(req.full_url)
                return response({"v": 2})

            result = r.github_json_read(
                PR_URL,
                user_agent="test",
                opener=opener,
                clock=lambda: 306.0,
            )

        self.assertEqual(result, {"v": 2})
        self.assertEqual(calls, [PR_URL])

    def test_cache_is_scoped_by_build_id(self):
        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": "build-d1"}, clear=False):
            r.github_json_read(
                PR_URL,
                user_agent="test",
                opener=lambda req, timeout=30: response({"build": 1}),
                clock=lambda: 400.0,
            )

        calls = []
        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": "build-d2"}, clear=False):
            result = r.github_json_read(
                PR_URL,
                user_agent="test",
                opener=lambda req, timeout=30: (calls.append(req.full_url) or response({"build": 2})),
                clock=lambda: 401.0,
            )

        self.assertEqual(result, {"build": 2})
        self.assertEqual(calls, [PR_URL])

    def test_without_buildkite_build_id_cache_is_disabled(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req.full_url)
            return response({"ok": len(calls)})

        with mock.patch.dict(os.environ, {}, clear=True):
            a = r.github_json_read(PR_URL, user_agent="test", opener=opener, clock=lambda: 500.0)
            b = r.github_json_read(PR_URL, user_agent="test", opener=opener, clock=lambda: 501.0)

        self.assertEqual(a, {"ok": 1})
        self.assertEqual(b, {"ok": 2})
        self.assertEqual(calls, [PR_URL, PR_URL])

    def test_mutations_never_use_or_write_read_cache(self):
        calls = []

        def opener(req, timeout=30):
            calls.append((req.get_method(), req.data))
            return response({"ok": True})

        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": "build-e"}, clear=False):
            result = r.github_json_request(
                PR_URL,
                user_agent="test",
                method="POST",
                data=b"{}",
                opener=opener,
                clock=lambda: 600.0,
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, [("POST", b"{}")])
        root = Path(r.SAME_BUILD_CACHE_ROOT)
        self.assertFalse(root.exists())

    def test_cache_survives_separate_python_process_same_build(self):
        build_id = "build-process-boundary"
        payload = {"number": 382, "state": "open"}
        with mock.patch.dict(os.environ, {"BUILDKITE_BUILD_ID": build_id}, clear=False):
            r.github_json_read(
                PR_URL,
                user_agent="dispatcher-process",
                opener=lambda req, timeout=30: response(payload),
            )

        repo_root = str(Path(self.cwd).resolve())
        script = (
            "import json; "
            "from automation.review_dispatcher_v1.github_read_resilience_v1 import github_json_read; "
            f"v=github_json_read({PR_URL!r}, user_agent='review-process'); "
            "print(json.dumps(v, sort_keys=True))"
        )
        env = os.environ.copy()
        env["BUILDKITE_BUILD_ID"] = build_id
        env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=self.tmp.name,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), payload)


if __name__ == "__main__":
    unittest.main()
