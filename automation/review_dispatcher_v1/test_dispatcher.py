from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from automation.review_dispatcher_v1 import dispatcher, review
from automation.review_dispatcher_v1.model import (
    LAB_APP_SLUG,
    REQUEST_MARKER,
    ReviewContractError,
    dotted_get,
    extract_request_from_comment,
    fetch_all_pages,
    latest_exact_current_owner_request,
    resolve_public_https_target,
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
            validate_public_https_url("https://example.com"),
            "https://example.com",
        )

        for unsafe in (
            "https://user:pass@example.com",
            "https://example.com?token=secret",
            "https://example.com#fragment",
            "https://example.com/base",
        ):
            with self.assertRaises(ReviewContractError):
                validate_public_https_url(unsafe)

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
            if f"/commits/{pr_head}/pulls?" in url:
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
            if "/issues/999/comments?per_page=100&page=1" in url:
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
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 20,
                "body": request_body(second),
                "user": {"login": "fufufu1116"},
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
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 11,
                "body": request_body(lab),
                "user": {"login": "fufufu1116"},
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
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 30,
                "body": marker + "build -->\nPASS",
                "user": {"login": "multiverse-independent-lab[bot]"},
                "performed_via_github_app": {
                    "slug": "multiverse-independent-lab",
                },
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
                "user": {"login": "fufufu1116"},
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
            if f"/commits/{SHA_A}/pulls?" in url:
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


class HardeningTests(unittest.TestCase):
    def test_13_fetch_all_pages_reads_beyond_first_100(self):
        first = [{"id": i} for i in range(100)]
        second = [{"id": 100}]

        def fake_fetch(url: str):
            if url.endswith("page=1"):
                return first
            if url.endswith("page=2"):
                return second
            raise AssertionError(url)

        items = fetch_all_pages(
            fake_fetch,
            "https://api.github.com/repos/o/r/issues/1/comments",
        )
        self.assertEqual(len(items), 101)
        self.assertEqual(items[-1]["id"], 100)

    def test_14_untrusted_newer_request_is_ignored(self):
        trusted = lab_request("trusted-request")
        untrusted = lab_request("untrusted-request")
        comments = [
            {
                "id": 10,
                "body": request_body(trusted),
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 20,
                "body": request_body(untrusted),
                "user": {"login": "attacker"},
            },
        ]
        helper = DispatcherTests()
        job = dispatcher.discover_request(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            head=SHA_A,
            fetch=helper.fake_fetch_factory(comments),
        )
        self.assertEqual(job["request_id"], "trusted-request")
        self.assertEqual(job["request_comment"], 10)

    def test_15_requested_app_slug_requires_exact_attribution(self):
        job = {
            "repo": "fufufu1116/multiverse-research",
            "request": {
                "recipe": {
                    "durable_comments": [
                        {
                            "id": 123,
                            "login": "multiverse-independent-lab[bot]",
                            "app_slug": LAB_APP_SLUG,
                            "body_contains": ["PASS"],
                        }
                    ]
                }
            },
        }

        def fake_fetch(_url: str):
            return {
                "user": {"login": "multiverse-independent-lab[bot]"},
                "performed_via_github_app": None,
                "body": "PASS",
            }

        checks = {}
        findings = []
        review._check_comments(job, fake_fetch, checks, findings)
        self.assertTrue(findings)
        self.assertEqual(
            checks["comment:123:app_slug"],
            "FIX_REQUIRED",
        )

    def test_16_auditor_upstream_requires_latest_exact_lab_and_owner_t1(self):
        auditor_request = lab_request("auditor-upstream")
        auditor_request["lane"] = "AUDITOR"
        auditor_request["upstream"] = {
            "lab_pass_comment": 123,
            "t1_comment": 456,
        }
        latest_lab = lab_request("latest-lab")
        latest_lab_comment_id = 111

        job = {
            "lane": "AUDITOR",
            "repo": auditor_request["repo"],
            "pr": auditor_request["pr"],
            "head": auditor_request["head"],
            "tree": auditor_request["tree"],
            "base": auditor_request["base"],
            "main": auditor_request["main"],
            "request": auditor_request,
        }
        lab_artifact = {
            "schema_version": "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
            "result_schema": "MULTIVERSE_FIXED_REVIEW_RESULT_v1",
            "lane": "LAB",
            "request_id": latest_lab["request_id"],
            "request_comment": latest_lab_comment_id,
            "mode": latest_lab["mode"],
            "verdict": "PASS",
            "findings": [],
            "reviewed_repo": auditor_request["repo"],
            "reviewed_pr": auditor_request["pr"],
            "reviewed_head": auditor_request["head"],
            "reviewed_tree": auditor_request["tree"],
            "reviewed_base": auditor_request["base"],
            "reviewed_main": auditor_request["main"],
            "proof_ceiling": auditor_request["proof_ceiling"],
            "execution_state": auditor_request["execution_state"],
            "producer": {
                "github_login": "multiverse-independent-lab[bot]",
                "github_app_id": 4819755,
            },
        }
        marker = result_marker(
            latest_lab["request_id"],
            auditor_request["head"],
            latest_lab_comment_id,
        )
        fence = chr(96) * 3
        lab_body = "\n".join(
            [
                marker + "build -->",
                fence + "json",
                json.dumps(lab_artifact, sort_keys=True),
                fence,
            ]
        )
        t1_body = " ".join(
            [
                "T1 PASS",
                "123",
                auditor_request["head"],
                auditor_request["tree"],
                auditor_request["base"],
                auditor_request["main"],
            ]
        )
        comments = [
            {
                "id": latest_lab_comment_id,
                "body": request_body(latest_lab),
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 123,
                "body": lab_body,
                "user": {"login": "multiverse-independent-lab[bot]"},
                "performed_via_github_app": {
                    "slug": "multiverse-independent-lab",
                },
            },
        ]

        def fake_fetch(url: str):
            if "/issues/999/comments?per_page=100&page=1" in url:
                return comments
            if url.endswith("/issues/comments/123"):
                return comments[1]
            if url.endswith("/issues/comments/456"):
                return {
                    "user": {"login": "fufufu1116"},
                    "body": t1_body,
                }
            raise AssertionError(url)

        checks = {}
        findings = []
        review._check_auditor_upstream(
            job,
            fake_fetch,
            checks,
            findings,
        )
        self.assertEqual(findings, [])
        self.assertTrue(
            all(value == "PASS" for value in checks.values())
        )

    def test_17_pinned_https_connection_uses_validated_ip_and_sni(self):
        raw = object()
        wrapped = object()
        context = mock.Mock()
        context.wrap_socket.return_value = wrapped
        with mock.patch.object(
            review.socket,
            "create_connection",
            return_value=raw,
        ) as create:
            connection = review._PinnedHTTPSConnection(
                "example.com",
                443,
                "8.8.8.8",
                context=context,
            )
            connection.connect()

        create.assert_called_once_with(
            ("8.8.8.8", 443),
            45,
            None,
        )
        context.wrap_socket.assert_called_once_with(
            raw,
            server_hostname="example.com",
        )
        self.assertIs(connection.sock, wrapped)

    def test_18_unittests_execute_out_of_process(self):
        job = {
            "request": {
                "recipe": {
                    "unittest_modules": [
                        {
                            "module": "automation.example.tests",
                            "count": 3,
                        }
                    ]
                }
            }
        }
        proc = SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="Ran 3 tests in 0.001s\n\nOK\n",
        )
        checks = {}
        findings = []
        with (
            mock.patch.object(
                review,
                "_repo_file",
                return_value=Path("automation/example/tests.py"),
            ),
            mock.patch.object(
                review,
                "_run_candidate_process",
                return_value=proc,
            ) as run,
        ):
            count = review._run_unittests(
                Path("."),
                job,
                checks,
                findings,
            )

        self.assertEqual(count, 3)
        self.assertEqual(findings, [])
        self.assertEqual(
            checks["unittest_result:automation.example.tests"],
            "PASS",
        )
        args = run.call_args.args[0]
        self.assertEqual(
            args,
            [
                review.sys.executable,
                "-m",
                "unittest",
                "automation.example.tests",
                "-v",
            ],
        )


    def test_19_untrusted_malformed_request_marker_cannot_dos_dispatcher(self):
        trusted = lab_request("trusted-request")
        comments = [
            {
                "id": 10,
                "body": request_body(trusted),
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 20,
                "body": REQUEST_MARKER + "\nnot-json",
                "user": {"login": "attacker"},
            },
        ]
        helper = DispatcherTests()
        job = dispatcher.discover_request(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            head=SHA_A,
            fetch=helper.fake_fetch_factory(comments),
        )
        self.assertEqual(job["request_id"], "trusted-request")

    def test_20_repo_file_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            target = Path(tmp) / "outside.txt"
            target.write_text("outside")
            link = root / "inside.txt"
            link.symlink_to(target)
            with self.assertRaises(ReviewContractError):
                review._repo_file(root, "inside.txt")

    def test_21_candidate_env_strips_control_plane_variables(self):
        with mock.patch.dict(
            os.environ,
            {
                "PATH": "/usr/bin:/bin",
                "BUILDKITE_AGENT_ACCESS_TOKEN": "secret",
                "GITHUB_TOKEN": "secret",
                "DATABASE_URL": "secret",
            },
            clear=True,
        ):
            env = review._candidate_env(Path("."))
        self.assertNotIn("BUILDKITE_AGENT_ACCESS_TOKEN", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("DATABASE_URL", env)
        self.assertIn("PYTHONPATH", env)

    def test_22_latest_exact_current_owner_request_selects_newest(self):
        first = lab_request("first")
        second = lab_request("second")
        comments = [
            {
                "id": 10,
                "body": request_body(first),
                "user": {"login": "fufufu1116"},
            },
            {
                "id": 20,
                "body": request_body(second),
                "user": {"login": "fufufu1116"},
            },
        ]
        cid, request, _ = latest_exact_current_owner_request(
            comments,
            repo=first["repo"],
            pr=first["pr"],
            lane="LAB",
            head=first["head"],
            tree=first["tree"],
            base=first["base"],
            main=first["main"],
        )
        self.assertEqual(cid, 20)
        self.assertEqual(request["request_id"], "second")

    def test_23_dns_target_rejects_private_resolution(self):
        public_info = [
            (review.socket.AF_INET, review.socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
        ]
        private_info = [
            (review.socket.AF_INET, review.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ]
        with mock.patch(
            "automation.review_dispatcher_v1.model.socket.getaddrinfo",
            return_value=public_info,
        ):
            host, port, addresses = resolve_public_https_target(
                "https://example.com"
            )
        self.assertEqual(host, "example.com")
        self.assertEqual(port, 443)
        self.assertEqual(addresses, ("8.8.8.8",))

        with mock.patch(
            "automation.review_dispatcher_v1.model.socket.getaddrinfo",
            return_value=private_info,
        ):
            with self.assertRaises(ReviewContractError):
                resolve_public_https_target("https://example.com")



if __name__ == "__main__":
    unittest.main()
