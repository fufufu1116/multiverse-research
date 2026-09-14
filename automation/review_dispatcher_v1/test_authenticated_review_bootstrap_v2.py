from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from automation.review_dispatcher_v1 import review
from automation.review_dispatcher_v1.authenticated_review_bootstrap_v2 import (
    BootstrapAuthError,
    LANE_PRIVATE_KEY_ENV,
    READ_PERMISSIONS,
    authenticated_fetcher,
    mint_downscoped_read_token,
    run_authenticated_review,
)


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._raw = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class AuthenticatedReviewBootstrapV2Tests(unittest.TestCase):
    def tearDown(self) -> None:
        for name in LANE_PRIVATE_KEY_ENV.values():
            os.environ.pop(name, None)
        os.environ.pop("BUILDKITE_BUILD_ID", None)

    def test_01_mint_requests_downscoped_read_permissions(self) -> None:
        calls: list[tuple[object, ...]] = []

        def fake_call(*args: object) -> object:
            calls.append(args)
            if args[0] == "GET":
                return {"id": 123}
            return {"token": "ghs_read_only_token"}

        token = mint_downscoped_read_token(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            private_key="private-key",
            github_call=fake_call,
            jwt_factory=lambda app_id, key: "app-jwt",
        )

        self.assertEqual(token, "ghs_read_only_token")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "GET")
        self.assertEqual(calls[1][0], "POST")
        self.assertEqual(
            calls[1][3],
            {"permissions": dict(READ_PERMISSIONS)},
        )

    def test_02_authenticated_fetch_adds_bearer_header(self) -> None:
        seen: dict[str, str | None] = {}

        def fake_urlopen(req, timeout=0):
            seen["authorization"] = req.get_header("Authorization")
            seen["user_agent"] = req.get_header("User-agent")
            return _FakeResponse({"ok": True})

        fetch = authenticated_fetcher(
            "ghs_read_token",
            user_agent="mv-auth-test",
        )
        with mock.patch(
            "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.urllib.request.urlopen",
            side_effect=fake_urlopen,
        ):
            payload = fetch(
                "https://api.github.com/repos/fufufu1116/multiverse-research"
            )

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(seen["authorization"], "Bearer ghs_read_token")
        self.assertEqual(seen["user_agent"], "mv-auth-test")

    def test_03_authenticated_fetch_rejects_non_github_host(self) -> None:
        fetch = authenticated_fetcher(
            "ghs_read_token",
            user_agent="mv-auth-test",
        )
        with self.assertRaisesRegex(BootstrapAuthError, "READ_URL_HOST"):
            fetch("https://example.com/repos/fufufu1116/multiverse-research")

    def test_04_candidate_environment_inherits_no_control_secret(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY"] = "private"
            os.environ["MULTIVERSE_GITHUB_READ_TOKEN"] = "token"
            candidate_env = review._candidate_env(Path(td))

        self.assertNotIn(
            "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
            candidate_env,
        )
        self.assertNotIn("MULTIVERSE_GITHUB_READ_TOKEN", candidate_env)
        self.assertEqual(
            set(candidate_env),
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

    def test_05_run_unsets_lane_private_key_before_dispatch_and_review(self) -> None:
        os.environ["MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY"] = "private-key"
        fake_job = {
            "lane": "LAB",
            "pr": 466,
            "head": "head",
            "request_comment": 123,
            "request_sha256": "digest",
        }
        fake_artifact = {"verdict": "PASS"}

        def fake_discover_request(**kwargs):
            self.assertNotIn(
                "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
                os.environ,
            )
            return fake_job

        def fake_run_review(job, **kwargs):
            self.assertNotIn(
                "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
                os.environ,
            )
            self.assertNotIn("MULTIVERSE_GITHUB_READ_TOKEN", os.environ)
            self.assertIs(job, fake_job)
            return fake_artifact

        with tempfile.TemporaryDirectory() as td:
            job_path = Path(td) / "job.json"
            artifact_path = Path(td) / "artifact.json"
            with mock.patch(
                "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.dispatcher.discover_request",
                side_effect=fake_discover_request,
            ), mock.patch(
                "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.dispatcher.write_job",
            ), mock.patch(
                "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.review.run_review",
                side_effect=fake_run_review,
            ), mock.patch(
                "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.authenticated_fetcher",
                return_value=lambda url: {"ok": True},
            ):
                job, artifact = run_authenticated_review(
                    lane="LAB",
                    repo="fufufu1116/multiverse-research",
                    head="head",
                    job_output=job_path,
                    artifact_output=artifact_path,
                    repo_root=Path(td),
                    mint=lambda **kwargs: "ghs_read_token",
                )

        self.assertIs(job, fake_job)
        self.assertIs(artifact, fake_artifact)
        self.assertNotIn(
            "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
            os.environ,
        )

    def test_06_cross_lane_private_key_fails_closed(self) -> None:
        os.environ["MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY"] = "lab-private"
        os.environ["MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY"] = "aud-private"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(
                BootstrapAuthError,
                "CROSS_LANE_PRIVATE_KEY_PRESENT",
            ):
                run_authenticated_review(
                    lane="LAB",
                    repo="fufufu1116/multiverse-research",
                    head="head",
                    job_output=Path(td) / "job.json",
                    artifact_output=Path(td) / "artifact.json",
                    repo_root=Path(td),
                    mint=lambda **kwargs: "ghs_read_token",
                )

    def test_07_no_token_or_private_key_is_printed(self) -> None:
        os.environ["MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY"] = "private-key"
        fake_job = {
            "lane": "LAB",
            "pr": 466,
            "head": "head",
            "request_comment": 123,
            "request_sha256": "digest",
        }
        fake_artifact = {"verdict": "PASS"}

        with tempfile.TemporaryDirectory() as td, mock.patch(
            "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.dispatcher.discover_request",
            return_value=fake_job,
        ), mock.patch(
            "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.dispatcher.write_job",
        ), mock.patch(
            "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.review.run_review",
            return_value=fake_artifact,
        ), mock.patch(
            "automation.review_dispatcher_v1.authenticated_review_bootstrap_v2.authenticated_fetcher",
            return_value=lambda url: {"ok": True},
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                run_authenticated_review(
                    lane="LAB",
                    repo="fufufu1116/multiverse-research",
                    head="head",
                    job_output=Path(td) / "job.json",
                    artifact_output=Path(td) / "artifact.json",
                    repo_root=Path(td),
                    mint=lambda **kwargs: "ghs_read_token",
                )

        text = output.getvalue()
        self.assertNotIn("private-key", text)
        self.assertNotIn("ghs_read_token", text)

    def test_08_buildkite_templates_bind_correct_lane_secret_and_wrapper(self) -> None:
        root = Path(__file__).resolve().parents[2]
        cases = (
            (
                root / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml",
                "MULTIVERSE_INDEPENDENT_LAB_PRIVATE_KEY",
                "--lane LAB",
            ),
            (
                root / "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml",
                "MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY",
                "--lane AUDITOR",
            ),
        )
        for path, secret, lane_flag in cases:
            text = path.read_text()
            first_step = text.split("  - wait", 1)[0]
            self.assertIn(f"      - {secret}", first_step)
            self.assertIn("authenticated_review_bootstrap_v2.py", first_step)
            self.assertIn(lane_flag, first_step)
            self.assertNotIn("MULTIVERSE_GITHUB_READ_TOKEN", first_step)


if __name__ == "__main__":
    unittest.main()
