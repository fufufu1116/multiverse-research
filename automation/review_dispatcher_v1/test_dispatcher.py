from __future__ import annotations

import io
import urllib.error
from pathlib import Path
from unittest import mock

from automation.review_dispatcher_v1 import test_dispatcher_legacy_v1 as _legacy
from automation.review_dispatcher_v1.github_read_resilience_v1 import (
    github_json_read,
    github_json_request,
)

for _name in dir(_legacy):
    if not _name.startswith("__") and _name != "HardeningTests":
        globals()[_name] = getattr(_legacy, _name)


class HardeningTests(_legacy.HardeningTests):
    def test_24_same_head_supersession_without_digest_fails_closed(self):
        first = _legacy.lab_request("first-chain")
        second = _legacy.lab_request("second-chain")
        comments = [
            {
                "id": 10,
                "body": _legacy.request_body(first),
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 20,
                "body": _legacy.request_body(second),
                "user": {"login": "fufufu1116"},
            },
        ]
        cid, request, _ = _legacy.latest_exact_current_owner_request(
            comments,
            repo=first["repo"],
            pr=first["pr"],
            lane="LAB",
            head=first["head"],
            tree=first["tree"],
            base=first["base"],
            main=first["main"],
        )
        self.assertEqual(cid, 10)
        self.assertEqual(request["request_id"], "first-chain")

    def test_42_review_and_t2_use_shared_nullable_outer_app_helper(self):
        repo_root = Path(__file__).resolve().parents[2]
        review_source = (
            repo_root
            / "automation"
            / "review_dispatcher_v1"
            / "review.py"
        ).read_text()
        t2_source = (
            repo_root
            / "automation"
            / "review_dispatcher_v1"
            / "t2_legacy_v1.py"
        ).read_text()

        self.assertIn(
            'lane_result_outer_app_trusted(lab_comment, "LAB")',
            review_source,
        )
        self.assertNotIn(
            "lab_app == LAB_APP_SLUG",
            review_source,
        )

        self.assertIn(
            'lane_result_outer_app_trusted(auditor_comment, "AUDITOR")',
            t2_source,
        )
        self.assertIn(
            'lane_result_outer_app_trusted(lab_comment, "LAB")',
            t2_source,
        )
        self.assertNotIn(
            "outer_app == AUDITOR_APP_SLUG",
            t2_source,
        )
        self.assertNotIn(
            "lab_app == LAB_APP_SLUG",
            t2_source,
        )

    def test_43_validator_assigns_nullable_app_tokens_to_correct_modules(self):
        repo_root = Path(__file__).resolve().parents[2]
        validator_source = (
            repo_root
            / "automation"
            / "review_dispatcher_v1"
            / "validator_legacy_v1.py"
        ).read_text()

        dispatcher_start = validator_source.index(
            'dispatcher_source = (ROOT / "dispatcher.py").read_text()'
        )
        review_start = validator_source.index(
            'review_source = (ROOT / "review.py").read_text()'
        )
        publisher_start = validator_source.index(
            'publisher_source = (ROOT / "publisher.py").read_text()'
        )
        t2_start = validator_source.index(
            't2_source = (ROOT / "t2.py").read_text()'
        )
        github_app_start = validator_source.index(
            'github_app_source = (ROOT / "github_app.py").read_text()'
        )

        dispatcher_block = validator_source[
            dispatcher_start:review_start
        ]
        review_block = validator_source[
            review_start:publisher_start
        ]
        t2_block = validator_source[
            t2_start:github_app_start
        ]

        lab_token = 'lane_result_outer_app_trusted(lab_comment, "LAB")'
        auditor_token = (
            'lane_result_outer_app_trusted(auditor_comment, "AUDITOR")'
        )

        self.assertNotIn(lab_token, dispatcher_block)
        self.assertIn(lab_token, review_block)
        self.assertIn(lab_token, t2_block)
        self.assertIn(auditor_token, t2_block)


class GitHubReadRateLimitTests(_legacy.unittest.TestCase):
    @staticmethod
    def _http_error(
        *,
        code=403,
        reason="Forbidden",
        headers=None,
        body=b"",
    ):
        return urllib.error.HTTPError(
            "https://api.github.com/repos/o/r",
            code,
            reason,
            headers or {},
            io.BytesIO(body),
        )

    def test_44_retry_after_rate_limit_recovers_bounded_read(self):
        first = self._http_error(
            headers={"Retry-After": "2"},
            body=b'{"message":"API rate limit exceeded"}',
        )
        opener = mock.Mock(
            side_effect=[first, io.BytesIO(b'{"ok":true}')]
        )
        sleeper = mock.Mock()
        result = github_json_read(
            "https://api.github.com/repos/o/r",
            user_agent="test",
            opener=opener,
            sleeper=sleeper,
            clock=lambda: 100.0,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(2.0)

    def test_45_primary_reset_signal_recovers_bounded_read(self):
        first = self._http_error(
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "102",
            },
            body=b'{"message":"API rate limit exceeded"}',
        )
        opener = mock.Mock(
            side_effect=[first, io.BytesIO(b'{"ok":true}')]
        )
        sleeper = mock.Mock()
        result = github_json_read(
            "https://api.github.com/repos/o/r",
            user_agent="test",
            opener=opener,
            sleeper=sleeper,
            clock=lambda: 100.0,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(3.0)

    def test_46_non_rate_limit_403_fails_closed_without_retry(self):
        first = self._http_error(
            reason="Forbidden",
            headers={"Retry-After": "2"},
            body=b'{"message":"resource forbidden"}',
        )
        opener = mock.Mock(side_effect=first)
        sleeper = mock.Mock()
        with self.assertRaises(urllib.error.HTTPError):
            github_json_read(
                "https://api.github.com/repos/o/r",
                user_agent="test",
                opener=opener,
                sleeper=sleeper,
            )
        self.assertEqual(opener.call_count, 1)
        sleeper.assert_not_called()

    def test_47_repeated_rate_limit_exhaustion_fails_closed(self):
        errors = [
            self._http_error(
                reason="rate limit exceeded",
                headers={"Retry-After": "1"},
            ),
            self._http_error(
                reason="rate limit exceeded",
                headers={"Retry-After": "1"},
            ),
        ]
        opener = mock.Mock(side_effect=errors)
        sleeper = mock.Mock()
        with self.assertRaises(urllib.error.HTTPError):
            github_json_read(
                "https://api.github.com/repos/o/r",
                user_agent="test",
                opener=opener,
                sleeper=sleeper,
                max_attempts=2,
            )
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(1.0)

    def test_48_malformed_retry_header_fails_closed(self):
        first = self._http_error(
            reason="rate limit exceeded",
            headers={"Retry-After": "soon"},
        )
        opener = mock.Mock(side_effect=first)
        sleeper = mock.Mock()
        with self.assertRaises(urllib.error.HTTPError):
            github_json_read(
                "https://api.github.com/repos/o/r",
                user_agent="test",
                opener=opener,
                sleeper=sleeper,
            )
        self.assertEqual(opener.call_count, 1)
        sleeper.assert_not_called()

    def test_49_mutation_is_never_retried(self):
        first = self._http_error(
            reason="rate limit exceeded",
            headers={"Retry-After": "1"},
        )
        opener = mock.Mock(side_effect=first)
        sleeper = mock.Mock()
        with self.assertRaises(urllib.error.HTTPError):
            github_json_request(
                "https://api.github.com/repos/o/r/issues/1/comments",
                user_agent="test",
                method="POST",
                data=b"{}",
                opener=opener,
                sleeper=sleeper,
            )
        self.assertEqual(opener.call_count, 1)
        sleeper.assert_not_called()

    def test_50_body_only_rate_limit_403_is_not_enough_to_retry(self):
        first = self._http_error(
            reason="rate limit exceeded",
            body=b'{"message":"API rate limit exceeded"}',
        )
        opener = mock.Mock(side_effect=first)
        sleeper = mock.Mock()
        with self.assertRaises(urllib.error.HTTPError):
            github_json_read(
                "https://api.github.com/repos/o/r",
                user_agent="test",
                opener=opener,
                sleeper=sleeper,
            )
        self.assertEqual(opener.call_count, 1)
        sleeper.assert_not_called()

    def test_51_reset_beyond_total_wait_budget_fails_closed(self):
        first = self._http_error(
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1000",
            },
        )
        opener = mock.Mock(side_effect=first)
        sleeper = mock.Mock()
        with self.assertRaises(urllib.error.HTTPError):
            github_json_read(
                "https://api.github.com/repos/o/r",
                user_agent="test",
                opener=opener,
                sleeper=sleeper,
                clock=lambda: 100.0,
                max_total_wait_seconds=60.0,
            )
        self.assertEqual(opener.call_count, 1)
        sleeper.assert_not_called()
