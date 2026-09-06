from __future__ import annotations

import copy
import json
import unittest

from automation.review_dispatcher_v1 import dispatcher
from automation.review_dispatcher_v1.model import (
    REQUEST_MARKER,
    ReviewContractError,
    dotted_get,
    extract_request_from_comment,
    result_marker,
    validate_request,
    validate_public_https_url,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def nonauthority() -> dict:
    return {
        "provider_resource_mutation": False,
        "deploy": False,
        "database_mutation": False,
        "provider_effect_enablement": False,
        "runtime_activation_bridge_enablement": False,
        "runtime_activation": False,
        "production_credentials": False,
        "production_deployment": False,
        "protected_data": False,
        "live_business_effect": False,
        "additional_spend": False,
        "merge": False,
        "main_mutation": False,
        "ruleset_mutation": False,
        "workflow_dispatch_rerun": False,
    }


def base_recipe() -> dict:
    return {
        "subtrees": {},
        "durable_comments": [],
        "source_rules": [],
        "unittest_modules": [],
        "validators": [],
        "secret_scan_paths": [],
        "forbidden_patterns": [],
        "http": None,
    }


def lab_request(request_id: str = "test-lab-request") -> dict:
    return {
        "schema": "MULTIVERSE_REVIEW_REQUEST_v1",
        "request_id": request_id,
        "lane": "LAB",
        "mode": "REPOSITORY_ONLY",
        "repo": "fufufu1116/multiverse-research",
        "pr": 999,
        "head": SHA_A,
        "tree": SHA_B,
        "base": SHA_C,
        "main": SHA_D,
        "proof_ceiling": "TEST_ONLY",
        "execution_state": "TEST_REQUESTED",
        "recipe": base_recipe(),
        "upstream": {},
        "nonauthority": nonauthority(),
    }


def request_body(request: dict) -> str:
    fence = chr(96) * 3
    return "\n".join(
        [
            REQUEST_MARKER,
            fence + "json",
            json.dumps(request, indent=2, sort_keys=True),
            fence,
        ]
    )


class ModelTests(unittest.TestCase):
    def test_01_valid_lab_request(self):
        request = lab_request()
        self.assertEqual(validate_request(request), request)

    def test_02_auditor_requires_exact_upstream(self):
        request = lab_request("auditor-request")
        request["lane"] = "AUDITOR"
        request["upstream"] = {
            "lab_pass_comment": 123,
            "t1_comment": 456,
        }
        self.assertEqual(validate_request(request), request)

        broken = copy.deepcopy(request)
        broken["upstream"] = {}
        with self.assertRaises(ReviewContractError):
            validate_request(broken)

    def test_03_recipe_rejects_arbitrary_shell_key(self):
        request = lab_request()
        request["recipe"]["shell"] = "rm -rf /"
        with self.assertRaises(ReviewContractError):
            validate_request(request)

    def test_04_recipe_rejects_arbitrary_command_fragment_nested(self):
        request = lab_request()
        request["recipe"]["durable_comments"].append(
            {
                "id": 1,
                "login": None,
                "app_slug": None,
                "body_contains": ["safe"],
                "command_override": "unsafe",
            }
        )
        with self.assertRaises(ReviewContractError):
            validate_request(request)

    def test_05_public_http_rejects_private_address(self):
        with self.assertRaises(ReviewContractError):
            validate_public_https_url("https://127.0.0.1/evidence")

        with self.assertRaises(ReviewContractError):
            validate_public_https_url("https://10.0.0.2/evidence")

        self.assertEqual(
            validate_public_https_url("https://example.com/evidence"),
            "https://example.com/evidence",
        )

    def test_06_extract_request_marker_and_json(self):
        request = lab_request()
        parsed = extract_request_from_comment(request_body(request))
        self.assertEqual(parsed, request)

    def test_07_dotted_get(self):
        payload = {
            "a": {
                "b": [
                    {"c": 7},
                ]
            }
        }
        self.assertEqual(dotted_get(payload, "a.b.0.c"), 7)
        with self.assertRaises(ReviewContractError):
            dotted_get(payload, "a.b.1.c")


class DispatcherTests(unittest.TestCase):
    def fake_fetch_factory(
        self,
        comments: list[dict],
        *,
        pr_head: str = SHA_A,
        tree: str = SHA_B,
        base: str = SHA_C,
        main: str = SHA_D,
    ):
        repo = "fufufu1116/multiverse-research"

        def fake_fetch(url: str):
            if url.endswith(f"/commits/{pr_head}/pulls"):
                return [
                    {
                        "number": 999,
                        "state": "open",
                        "draft": True,
                        "merged": False,
                        "head": {
                            "sha": pr_head,
                            "ref": "agent/test",
                        },
                        "base": {
                            "sha": base,
                        },
                    }
                ]
            if url.endswith(f"/commits/{pr_head}"):
                return {
                    "commit": {
                        "tree": {
                            "sha": tree,
                        }
                    }
                }
            if url.endswith("/branches/main"):
                return {
                    "commit": {
                        "sha": main,
                    }
                }
            if url.endswith("/issues/999/comments?per_page=100"):
                return comments
            raise AssertionError(f"unexpected URL: {url}")

        return fake_fetch

    def test_08_discover_latest_exact_request(self):
        first = lab_request("first-request")
        second = lab_request("second-request")

        comments = [
            {
                "id": 10,
                "body": request_body(first),
                "user": {"login": "controller"},
            },
            {
                "id": 20,
                "body": request_body(second),
                "user": {"login": "controller"},
            },
        ]

        job = dispatcher.discover_request(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            head=SHA_A,
            fetch=self.fake_fetch_factory(comments),
        )

        self.assertEqual(job["request_id"], "second-request")
        self.assertEqual(job["request_comment"], 20)
        self.assertEqual(job["head"], SHA_A)
        self.assertEqual(job["tree"], SHA_B)

    def test_09_discover_ignores_other_lane(self):
        lab = lab_request("lab-request")
        auditor = lab_request("auditor-request")
        auditor["lane"] = "AUDITOR"
        auditor["upstream"] = {
            "lab_pass_comment": 100,
            "t1_comment": 101,
        }

        comments = [
            {
                "id": 10,
                "body": request_body(auditor),
                "user": {"login": "controller"},
            },
            {
                "id": 11,
                "body": request_body(lab),
                "user": {"login": "controller"},
            },
        ]

        job = dispatcher.discover_request(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            head=SHA_A,
            fetch=self.fake_fetch_factory(comments),
        )
        self.assertEqual(job["request_id"], "lab-request")

    def test_10_duplicate_result_fails_closed(self):
        request = lab_request("duplicate-request")
        request_comment = 10
        marker = result_marker(
            request["request_id"],
            request["head"],
            request_comment,
        )

        comments = [
            {
                "id": request_comment,
                "body": request_body(request),
                "user": {"login": "controller"},
            },
            {
                "id": 30,
                "body": marker + "build -->\nPASS",
                "user": {"login": "multiverse-independent-lab[bot]"},
            },
        ]

        with self.assertRaises(ReviewContractError):
            dispatcher.discover_request(
                repo="fufufu1116/multiverse-research",
                lane="LAB",
                head=SHA_A,
                fetch=self.fake_fetch_factory(comments),
            )

    def test_11_stale_main_request_is_not_selected(self):
        request = lab_request("stale-main")
        request["main"] = "e" * 40

        comments = [
            {
                "id": 10,
                "body": request_body(request),
                "user": {"login": "controller"},
            }
        ]

        with self.assertRaises(ReviewContractError):
            dispatcher.discover_request(
                repo="fufufu1116/multiverse-research",
                lane="LAB",
                head=SHA_A,
                fetch=self.fake_fetch_factory(comments),
            )

    def test_12_multiple_exact_open_prs_fail_closed(self):
        def fake_fetch(url: str):
            if url.endswith(f"/commits/{SHA_A}/pulls"):
                return [
                    {
                        "number": 1,
                        "state": "open",
                        "head": {"sha": SHA_A},
                    },
                    {
                        "number": 2,
                        "state": "open",
                        "head": {"sha": SHA_A},
                    },
                ]
            raise AssertionError(url)

        with self.assertRaises(ReviewContractError):
            dispatcher.discover_pr(
                "fufufu1116/multiverse-research",
                SHA_A,
                fetch=fake_fetch,
            )


if __name__ == "__main__":
    unittest.main()
