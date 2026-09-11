from __future__ import annotations

import io
import json
import urllib.error
import unittest
from unittest import mock

from automation.review_dispatcher_v1 import github_read_resilience_v1 as read_resilience
from automation.review_dispatcher_v1 import t2


URL = "https://api.github.com/repos/fufufu1116/multiverse-research/issues/comments/5629486699"


def response(payload: object):
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def http_error(*, headers: dict[str, str] | None = None, body: str = "rate limit exceeded", code: int = 403):
    return urllib.error.HTTPError(
        URL,
        code,
        "Forbidden",
        headers or {},
        io.BytesIO(body.encode("utf-8")),
    )


class T2GitHubReadResilienceTests(unittest.TestCase):
    def test_01_retry_after_rate_limit_403_recovers_bounded_get(self):
        calls = []
        sleeps = []

        def opener(req, timeout=30):
            calls.append((req.get_method(), req.data, timeout))
            if len(calls) == 1:
                raise http_error(
                    headers={"Retry-After": "2"},
                    body='{"message":"API rate limit exceeded"}',
                )
            return response({"ok": True})

        result = read_resilience.github_json_read(
            URL,
            user_agent="test-t2",
            opener=opener,
            sleeper=sleeps.append,
            clock=lambda: 100.0,
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [2.0])
        self.assertTrue(all(method == "GET" and data is None for method, data, _ in calls))

    def test_02_exhausted_primary_reset_recovers_bounded_get(self):
        calls = []
        sleeps = []

        def opener(req, timeout=30):
            calls.append(req)
            if len(calls) == 1:
                raise http_error(
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "110",
                    },
                    body="rate limit exceeded",
                )
            return response({"ok": "reset"})

        result = read_resilience.github_json_read(
            URL,
            user_agent="test-t2",
            opener=opener,
            sleeper=sleeps.append,
            clock=lambda: 100.0,
        )
        self.assertEqual(result, {"ok": "reset"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [11.0])

    def test_03_ordinary_403_with_retry_after_but_no_rate_limit_signal_fails_closed(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req)
            raise http_error(headers={"Retry-After": "1"}, body="forbidden")

        with self.assertRaises(urllib.error.HTTPError):
            read_resilience.github_json_read(
                URL,
                user_agent="test-t2",
                opener=opener,
                sleeper=lambda _: self.fail("must not sleep"),
            )
        self.assertEqual(len(calls), 1)

    def test_04_body_only_rate_limit_403_without_trusted_headers_fails_closed(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req)
            raise http_error(body="API rate limit exceeded")

        with self.assertRaises(urllib.error.HTTPError):
            read_resilience.github_json_read(
                URL,
                user_agent="test-t2",
                opener=opener,
                sleeper=lambda _: self.fail("must not sleep"),
            )
        self.assertEqual(len(calls), 1)

    def test_05_malformed_retry_after_fails_closed(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req)
            raise http_error(
                headers={"Retry-After": "1.5"},
                body="API rate limit exceeded",
            )

        with self.assertRaises(urllib.error.HTTPError):
            read_resilience.github_json_read(
                URL,
                user_agent="test-t2",
                opener=opener,
                sleeper=lambda _: self.fail("must not sleep"),
            )
        self.assertEqual(len(calls), 1)

    def test_06_retry_delay_beyond_aggregate_budget_fails_without_sleep(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req)
            raise http_error(
                headers={"Retry-After": "61"},
                body="API rate limit exceeded",
            )

        with self.assertRaises(urllib.error.HTTPError):
            read_resilience.github_json_read(
                URL,
                user_agent="test-t2",
                opener=opener,
                sleeper=lambda _: self.fail("must not sleep"),
                max_total_wait_seconds=60.0,
            )
        self.assertEqual(len(calls), 1)

    def test_07_mutation_or_body_request_is_never_retried(self):
        calls = []

        def opener(req, timeout=30):
            calls.append(req)
            raise http_error(
                headers={"Retry-After": "1"},
                body="API rate limit exceeded",
            )

        with self.assertRaises(urllib.error.HTTPError):
            read_resilience.github_json_request(
                URL,
                user_agent="test-t2",
                method="POST",
                data=b"{}",
                opener=opener,
                sleeper=lambda _: self.fail("must not sleep"),
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].get_method(), "POST")
        self.assertEqual(calls[0].data, b"{}")

    def test_08_exact_post_auditor_comment_get_uses_bounded_helper_and_recovers_trusted_403(self):
        calls = []
        sleeps = []

        def opener(req, timeout=30):
            calls.append((req.full_url, req.get_method(), req.data))
            if len(calls) == 1:
                raise http_error(
                    headers={"Retry-After": "1"},
                    body='{"message":"API rate limit exceeded"}',
                )
            return response({"id": 5629486699, "body": "AUDITOR PASS"})

        def bounded(url: str, *, user_agent: str):
            return read_resilience.github_json_read(
                url,
                user_agent=user_agent,
                opener=opener,
                sleeper=sleeps.append,
                clock=lambda: 100.0,
            )

        self.assertIs(t2._legacy.public_github, t2._bounded_public_github)
        with mock.patch.object(t2, "github_json_read", side_effect=bounded) as helper:
            result = t2._legacy.public_github(URL)

        self.assertEqual(result["id"], 5629486699)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [1.0])
        self.assertTrue(all(url == URL for url, _, _ in calls))
        self.assertTrue(all(method == "GET" and data is None for _, method, data in calls))
        helper.assert_called_once_with(URL, user_agent="multiverse-fixed-t2-v1")


if __name__ == "__main__":
    unittest.main()
