from __future__ import annotations

import hashlib
import os
import re
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from automation.review_dispatcher_v1 import review
from tools import buildkite_lab_auth_escape_v1 as escape


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools/buildkite_lab_auth_escape_v1.py"
TEMP_STEPS = (
    ROOT
    / "buildkite/review_dispatcher_v1/"
    "TEMP_MULTIVERSE_INDEPENDENT_LAB_AUTH_ESCAPE_v1.yml"
)
CANONICAL_LAB_STEPS = (
    ROOT
    / "buildkite/review_dispatcher_v1/"
    "MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml"
)
EXPECTED_WRAPPER_SHA256 = (
    "a91b8ccc509b34f6b469a9cf11ca0d325495dceeb51fa43e217af919a8bc400f"
)
EXPECTED_STEPS_SHA256 = (
    "bf94f05c6b700c23990109896cd59f5f2d116d52b938549965ae2691e08993b6"
)


class _FakeResponse:
    def __init__(self, payload: bytes = b"{}") -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeOpener:
    def __init__(self) -> None:
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append((request, timeout))
        return _FakeResponse()


class LabAuthEscapeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.real_urlopen = urllib.request.urlopen
        self.real_original = escape._ORIGINAL_URLOPEN

    def tearDown(self) -> None:
        urllib.request.urlopen = self.real_urlopen
        escape._ORIGINAL_URLOPEN = self.real_original
        for name in (
            escape.LAB_PRIVATE_KEY_ENV,
            escape.AUDITOR_PRIVATE_KEY_ENV,
            escape.LEGACY_READ_TOKEN_ENV,
        ):
            os.environ.pop(name, None)

    def test_01_mint_is_repo_scoped_and_read_only(self) -> None:
        os.environ[escape.LAB_PRIVATE_KEY_ENV] = "private-key"
        calls = []

        def fake_json(method, url, token, payload=None):
            calls.append((method, url, token, payload))
            if method == "GET":
                return {"id": 123}
            return {"token": "short-read-token"}

        with mock.patch.object(escape, "app_jwt", return_value="app-jwt"), mock.patch.object(
            escape, "github_json", side_effect=fake_json
        ):
            token = escape.mint_read_token()

        self.assertEqual(token, "short-read-token")
        self.assertNotIn(escape.LAB_PRIVATE_KEY_ENV, os.environ)
        self.assertEqual(calls[0][0], "GET")
        self.assertEqual(
            calls[0][1],
            "https://api.github.com/repos/fufufu1116/multiverse-research/installation",
        )
        self.assertEqual(calls[1][0], "POST")
        self.assertEqual(
            calls[1][3],
            {
                "repositories": ["multiverse-research"],
                "permissions": {
                    "contents": "read",
                    "issues": "read",
                    "pull_requests": "read",
                },
            },
        )

    def test_02_cross_lane_secret_fails_closed_before_mint(self) -> None:
        os.environ[escape.LAB_PRIVATE_KEY_ENV] = "lab-key"
        os.environ[escape.AUDITOR_PRIVATE_KEY_ENV] = "auditor-key"
        with self.assertRaisesRegex(
            escape.BootstrapTransportError,
            "CROSS_LANE_AUDITOR_PRIVATE_KEY_PRESENT",
        ):
            escape.mint_read_token()

    def test_03_missing_lab_secret_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            escape.BootstrapTransportError,
            "LAB_PRIVATE_KEY_REQUIRED",
        ):
            escape.mint_read_token()

    def test_04_transport_adds_token_only_to_github_https_get(self) -> None:
        fake_original_calls = []
        fake_opener = _FakeOpener()

        def fake_original(req, *args, **kwargs):
            fake_original_calls.append((req, args, kwargs))
            return _FakeResponse()

        escape._ORIGINAL_URLOPEN = fake_original
        os.environ[escape.LEGACY_READ_TOKEN_ENV] = "must-be-removed"
        with mock.patch(
            "tools.buildkite_lab_auth_escape_v1.urllib.request.build_opener",
            return_value=fake_opener,
        ):
            escape.install_authenticated_get_transport("short-token")
            req = urllib.request.Request(
                "https://api.github.com/repos/fufufu1116/multiverse-research"
            )
            urllib.request.urlopen(req, timeout=9)
            urllib.request.urlopen("https://example.com/public")

        self.assertNotIn(escape.LEGACY_READ_TOKEN_ENV, os.environ)
        self.assertEqual(len(fake_opener.requests), 1)
        github_req, timeout = fake_opener.requests[0]
        self.assertEqual(timeout, 9)
        self.assertEqual(
            github_req.get_header("Authorization"),
            "Bearer short-token",
        )
        self.assertEqual(len(fake_original_calls), 1)
        outside_req = fake_original_calls[0][0]
        self.assertEqual(outside_req, "https://example.com/public")

    def test_05_authenticated_non_get_is_denied(self) -> None:
        fake_opener = _FakeOpener()
        with mock.patch(
            "tools.buildkite_lab_auth_escape_v1.urllib.request.build_opener",
            return_value=fake_opener,
        ):
            escape.install_authenticated_get_transport("short-token")
            req = urllib.request.Request(
                "https://api.github.com/repos/fufufu1116/multiverse-research/issues",
                data=b"{}",
                method="POST",
            )
            with self.assertRaisesRegex(
                escape.BootstrapTransportError,
                "AUTHENTICATED_NON_GET_DENIED",
            ):
                urllib.request.urlopen(req)
        self.assertEqual(fake_opener.requests, [])

    def test_06_candidate_subprocess_environment_has_no_control_secret(self) -> None:
        os.environ[escape.LAB_PRIVATE_KEY_ENV] = "private-key"
        os.environ[escape.LEGACY_READ_TOKEN_ENV] = "token"
        with tempfile.TemporaryDirectory() as td:
            env = review._candidate_env(Path(td))
        self.assertNotIn(escape.LAB_PRIVATE_KEY_ENV, env)
        self.assertNotIn(escape.AUDITOR_PRIVATE_KEY_ENV, env)
        self.assertNotIn(escape.LEGACY_READ_TOKEN_ENV, env)
        self.assertEqual(
            set(env),
            {
                "PATH",
                "LANG",
                "LC_ALL",
                "PYTHONHASHSEED",
                "PYTHONNOUSERSITE",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONPATH",
            },
        )

    def test_07_frozen_steps_embed_exact_wrapper_bytes_and_hashes(self) -> None:
        wrapper = WRAPPER.read_text()
        steps = TEMP_STEPS.read_text()
        self.assertEqual(
            hashlib.sha256(wrapper.encode()).hexdigest(),
            EXPECTED_WRAPPER_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(steps.encode()).hexdigest(),
            EXPECTED_STEPS_SHA256,
        )

        match = re.search(
            r"cat > \.mv_bootstrap/bootstrap_escape_runner\.py <<'PY'\n"
            r"(.*?)\n      PY\n",
            steps,
            re.S,
        )
        self.assertIsNotNone(match)
        embedded_lines = []
        for line in match.group(1).splitlines():
            self.assertTrue(line.startswith("      ") or line == "")
            embedded_lines.append(line[6:] if line.startswith("      ") else line)
        embedded = "\n".join(embedded_lines) + "\n"
        self.assertEqual(embedded, wrapper)

    def test_08_temp_steps_use_main_dispatcher_and_leave_publisher_exact(self) -> None:
        temp = TEMP_STEPS.read_text()
        canonical = CANONICAL_LAB_STEPS.read_text()
        first = temp.split("  - wait\n", 1)[0]
        self.assertIn("git fetch origin main", first)
        self.assertIn(
            'git archive "$$DISPATCHER_REF" automation/review_dispatcher_v1',
            first,
        )
        self.assertIn("- MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY", first)
        self.assertIn("bootstrap_escape_runner.py dispatch", first)
        self.assertIn("bootstrap_escape_runner.py review", first)
        self.assertNotIn("authenticated_review_bootstrap_v2.py", first)
        self.assertNotIn("system-improvement-authenticated-review-bootstrap", first)
        self.assertEqual(
            temp.split("  - wait\n", 1)[1],
            canonical.split("  - wait\n", 1)[1],
        )

    def test_09_failure_artifacts_remain_before_final_status(self) -> None:
        text = TEMP_STEPS.read_text()
        wrapper_index = text.index("bootstrap_escape_runner.py review")
        job_upload_index = text.index("buildkite-agent artifact upload", wrapper_index)
        artifact_guard_index = text.index(
            "if [ -f review_artifact.json ]; then",
            wrapper_index,
        )
        cleanup_index = text.index("rm -rf .mv_bootstrap", wrapper_index)
        final_index = text.index("test -f .mv_review_pass", wrapper_index)
        self.assertLess(wrapper_index, job_upload_index)
        self.assertLess(job_upload_index, artifact_guard_index)
        self.assertLess(artifact_guard_index, cleanup_index)
        self.assertLess(cleanup_index, final_index)


if __name__ == "__main__":
    unittest.main()
