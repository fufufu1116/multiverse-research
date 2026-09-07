from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from automation.review_dispatcher_v1 import dispatcher, github_app, review
from automation.review_dispatcher_v1.model import (
    LAB_APP_SLUG,
    REQUEST_MARKER,
    ReviewContractError,
    dotted_get,
    extract_request_from_comment,
    fetch_all_pages,
    github_branch_commit_sha,
    github_comment_id,
    github_commit_tree_sha,
    github_full_pr_binding,
    lane_result_comment_trusted,
    lane_result_outer_app_trusted,
    latest_exact_current_owner_request,
    resolve_public_https_target,
    result_marker,
    sha256_json,
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
        "supersedes_request_sha256": None,
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
            "lab_request_sha256": "f" * 64,
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
                        "head": {
                            "sha": pr_head,
                            "ref": "agent/test",
                        },
                        "base": {
                            "sha": base,
                        },
                    }
                ]
            if url.endswith("/pulls/999"):
                return {
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
        second["supersedes_request_sha256"] = sha256_json(first)

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
            "lab_request_sha256": "f" * 64,
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
            sha256_json(request),
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
                "user": {
                    "login": "multiverse-independent-lab[bot]",
                    "type": "Bot",
                },
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

    def test_15_lane_bot_app_slug_allows_nullable_outer_metadata(self):
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
                "user": {
                    "login": "multiverse-independent-lab[bot]",
                    "type": "Bot",
                },
                "performed_via_github_app": None,
                "body": "PASS",
            }

        checks = {}
        findings = []
        review._check_comments(job, fake_fetch, checks, findings)
        self.assertEqual(findings, [])
        self.assertEqual(
            checks["comment:123:app_slug"],
            "PASS",
        )

    def test_16_auditor_upstream_requires_latest_exact_lab_and_owner_t1(self):
        auditor_request = lab_request("auditor-upstream")
        auditor_request["lane"] = "AUDITOR"
        latest_lab = lab_request("latest-lab")
        latest_lab_sha256 = sha256_json(latest_lab)
        auditor_request["upstream"] = {
            "lab_pass_comment": 123,
            "lab_request_sha256": latest_lab_sha256,
            "t1_comment": 456,
        }
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
            "request_sha256": latest_lab_sha256,
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
            latest_lab_sha256,
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
                latest_lab_sha256,
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
                "user": {
                    "login": "multiverse-independent-lab[bot]",
                    "type": "Bot",
                },
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
        second["supersedes_request_sha256"] = sha256_json(first)
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



    def test_24_same_head_supersession_without_digest_fails_closed(self):
        first = lab_request("first-chain")
        second = lab_request("second-chain")
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
        with self.assertRaises(ReviewContractError):
            latest_exact_current_owner_request(
                comments,
                repo=first["repo"],
                pr=first["pr"],
                lane="LAB",
                head=first["head"],
                tree=first["tree"],
                base=first["base"],
                main=first["main"],
            )

    def test_25_explicit_same_head_supersession_chain_is_accepted(self):
        first = lab_request("first-chain")
        second = lab_request("second-chain")
        first_sha256 = sha256_json(first)
        second["supersedes_request_sha256"] = first_sha256
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
        self.assertEqual(request["request_id"], "second-chain")
        self.assertEqual(
            request["supersedes_request_sha256"],
            first_sha256,
        )

    def test_26_dispatcher_job_binds_exact_request_sha256(self):
        request = lab_request("digest-bound")
        comments = [
            {
                "id": 10,
                "body": request_body(request),
                "user": {"login": "fufufu1116"},
            }
        ]
        helper = DispatcherTests()
        job = dispatcher.discover_request(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            head=SHA_A,
            fetch=helper.fake_fetch_factory(comments),
        )
        self.assertEqual(job["request_sha256"], sha256_json(request))

    def test_27_auditor_requires_exact_lab_request_sha256(self):
        request = lab_request("auditor-digest")
        request["lane"] = "AUDITOR"
        request["upstream"] = {
            "lab_pass_comment": 123,
            "lab_request_sha256": "f" * 64,
            "t1_comment": 456,
        }
        self.assertEqual(validate_request(request), request)

        broken = copy.deepcopy(request)
        broken["upstream"]["lab_request_sha256"] = "not-a-digest"
        with self.assertRaises(ReviewContractError):
            validate_request(broken)



    def test_28_lane_result_trust_accepts_present_exact_app(self):
        comment = {
            "user": {
                "login": "multiverse-independent-lab[bot]",
                "type": "Bot",
            },
            "performed_via_github_app": {
                "slug": "multiverse-independent-lab",
            },
        }
        self.assertTrue(
            lane_result_comment_trusted(comment, "LAB")
        )

    def test_29_lane_result_trust_rejects_present_wrong_app(self):
        comment = {
            "user": {
                "login": "multiverse-independent-lab[bot]",
                "type": "Bot",
            },
            "performed_via_github_app": {
                "slug": "wrong-app",
            },
        }
        self.assertFalse(
            lane_result_comment_trusted(comment, "LAB")
        )

    def test_30_lane_result_trust_rejects_non_bot_on_null_app(self):
        comment = {
            "user": {
                "login": "multiverse-independent-lab[bot]",
                "type": "User",
            },
            "performed_via_github_app": None,
        }
        self.assertFalse(
            lane_result_comment_trusted(comment, "LAB")
        )

    def test_31_lane_result_trust_rejects_wrong_login_on_null_app(self):
        comment = {
            "user": {
                "login": "attacker[bot]",
                "type": "Bot",
            },
            "performed_via_github_app": None,
        }
        self.assertFalse(
            lane_result_comment_trusted(comment, "LAB")
        )

    def test_32_generic_app_rule_still_requires_outer_attribution(self):
        job = {
            "repo": "fufufu1116/multiverse-research",
            "request": {
                "recipe": {
                    "durable_comments": [
                        {
                            "id": 789,
                            "login": "fufufu1116",
                            "app_slug": "chatgpt-codex-connector",
                            "body_contains": ["SAFE"],
                        }
                    ]
                }
            },
        }

        def fake_fetch(_url: str):
            return {
                "user": {
                    "login": "fufufu1116",
                    "type": "User",
                },
                "performed_via_github_app": None,
                "body": "SAFE",
            }

        checks = {}
        findings = []
        review._check_comments(job, fake_fetch, checks, findings)
        self.assertTrue(findings)
        self.assertEqual(
            checks["comment:789:app_slug"],
            "FIX_REQUIRED",
        )


    def test_33_fixed_pipeline_bootstrap_uses_fetch_head(self):
        repo_root = Path(__file__).resolve().parents[2]
        for relative in (
            "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml",
            "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml",
        ):
            text = (repo_root / relative).read_text()
            fetch_index = text.index("git fetch origin main")
            ref = 'DISPATCHER_REF="$(git rev-parse FETCH_HEAD)"'
            ref_index = text.index(ref)
            self.assertLess(fetch_index, ref_index)
            self.assertNotIn("git rev-parse origin/main", text)


    def test_34_fixed_pipeline_runtime_vars_escaped_and_failure_artifacts_retained(self):
        repo_root = Path(__file__).resolve().parents[2]
        runtime_names = (
            "DISPATCHER_REF",
            "FRESH_DISPATCHER_REF",
            "JOB_DISPATCHER_REF",
            "BUILDKITE_COMMIT",
        )
        for relative in (
            "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_LAB_FIXED_v1.yml",
            "buildkite/review_dispatcher_v1/MULTIVERSE_INDEPENDENT_AUDITOR_FIXED_v1.yml",
        ):
            text = (repo_root / relative).read_text()

            for runtime_name in runtime_names:
                escaped = "$" * 2 + runtime_name
                unescaped = "$" + runtime_name
                self.assertIn(escaped, text)
                self.assertNotIn(
                    unescaped,
                    text.replace(escaped, ""),
                )

            for required in (
                "rm -f .mv_review_pass",
                "if PYTHONPATH=.mv_dispatcher",
                "touch .mv_review_pass",
                "if [ -f review_artifact.json ]; then",
                "test -f .mv_review_pass",
            ):
                self.assertIn(required, text)

            review_index = text.index("review.py")
            job_upload_index = text.index(
                "buildkite-agent artifact upload",
                review_index,
            )
            artifact_guard_index = text.index(
                "if [ -f review_artifact.json ]; then"
            )
            final_status_index = text.index("test -f .mv_review_pass")
            self.assertLess(review_index, job_upload_index)
            self.assertLess(job_upload_index, artifact_guard_index)
            self.assertLess(artifact_guard_index, final_status_index)


    def test_35_dispatcher_refetches_full_pr_when_summary_omits_merged(self):
        request = lab_request("summary-full-pr")
        comments = [
            {
                "id": 10,
                "body": request_body(request),
                "user": {"login": "fufufu1116"},
            }
        ]
        helper = DispatcherTests()
        seen = []

        base_fetch = helper.fake_fetch_factory(comments)

        def fake_fetch(url: str):
            seen.append(url)
            return base_fetch(url)

        job = dispatcher.discover_request(
            repo="fufufu1116/multiverse-research",
            lane="LAB",
            head=SHA_A,
            fetch=fake_fetch,
        )
        self.assertEqual(job["pr"], 999)
        self.assertEqual(job["branch"], "agent/test")
        self.assertTrue(
            any(url.endswith("/pulls/999") for url in seen)
        )

    def test_36_full_pr_missing_or_malformed_required_fields_fails_closed(self):
        request = lab_request("malformed-full-pr")
        comments = [
            {
                "id": 10,
                "body": request_body(request),
                "user": {"login": "fufufu1116"},
            }
        ]
        helper = DispatcherTests()
        base_fetch = helper.fake_fetch_factory(comments)

        malformed = (
            {},
            {
                "number": 999,
                "state": "open",
                "draft": True,
                "head": {"sha": SHA_A, "ref": "agent/test"},
                "base": {"sha": SHA_C},
            },
            {
                "number": 999,
                "state": "open",
                "draft": "true",
                "merged": False,
                "head": {"sha": SHA_A, "ref": "agent/test"},
                "base": {"sha": SHA_C},
            },
            {
                "number": 999,
                "state": "open",
                "draft": True,
                "merged": False,
                "head": {"sha": SHA_B, "ref": "agent/test"},
                "base": {"sha": SHA_C},
            },
            {
                "number": 999,
                "state": "open",
                "draft": True,
                "merged": False,
                "head": {"sha": SHA_A, "ref": ""},
                "base": {"sha": SHA_C},
            },
        )

        for full_pr in malformed:
            with self.subTest(full_pr=full_pr):
                def fake_fetch(url: str):
                    if url.endswith("/pulls/999"):
                        return full_pr
                    return base_fetch(url)

                with self.assertRaises(ReviewContractError):
                    dispatcher.discover_request(
                        repo="fufufu1116/multiverse-research",
                        lane="LAB",
                        head=SHA_A,
                        fetch=fake_fetch,
                    )

    def test_37_malformed_commit_or_main_shape_fails_closed_without_keyerror(self):
        request = lab_request("malformed-outer")
        comments = [
            {
                "id": 10,
                "body": request_body(request),
                "user": {"login": "fufufu1116"},
            }
        ]
        helper = DispatcherTests()
        base_fetch = helper.fake_fetch_factory(comments)

        cases = (
            ("commit", {}),
            ("commit", {"commit": {}}),
            ("commit", {"commit": {"tree": {}}}),
            ("main", {}),
            ("main", {"commit": {}}),
        )
        for kind, payload in cases:
            with self.subTest(kind=kind, payload=payload):
                def fake_fetch(url: str):
                    if (
                        kind == "commit"
                        and url.endswith(f"/commits/{SHA_A}")
                    ):
                        return payload
                    if (
                        kind == "main"
                        and url.endswith("/branches/main")
                    ):
                        return payload
                    return base_fetch(url)

                with self.assertRaises(ReviewContractError):
                    dispatcher.discover_request(
                        repo="fufufu1116/multiverse-research",
                        lane="LAB",
                        head=SHA_A,
                        fetch=fake_fetch,
                    )


    def test_38_shared_github_response_normalizers_are_fail_closed(self):
        full_pr = {
            "number": 999,
            "state": "open",
            "draft": True,
            "merged": False,
            "head": {
                "sha": SHA_A,
                "ref": "agent/test",
            },
            "base": {
                "sha": SHA_C,
            },
        }
        binding = github_full_pr_binding(
            full_pr,
            expected_number=999,
            expected_head=SHA_A,
        )
        self.assertEqual(binding["head_sha"], SHA_A)
        self.assertEqual(binding["base_sha"], SHA_C)

        self.assertEqual(
            github_commit_tree_sha(
                {"commit": {"tree": {"sha": SHA_B}}}
            ),
            SHA_B,
        )
        self.assertEqual(
            github_branch_commit_sha(
                {"commit": {"sha": SHA_D}}
            ),
            SHA_D,
        )
        self.assertEqual(
            github_comment_id({"id": 123}),
            123,
        )

        malformed_prs = (
            {},
            {
                "number": 999,
                "state": "open",
                "draft": True,
                "head": {"sha": SHA_A, "ref": "agent/test"},
                "base": {"sha": SHA_C},
            },
            {
                "number": 999,
                "state": "open",
                "draft": True,
                "merged": False,
                "head": {"sha": "bad", "ref": "agent/test"},
                "base": {"sha": SHA_C},
            },
        )
        for payload in malformed_prs:
            with self.subTest(payload=payload):
                with self.assertRaises(ReviewContractError):
                    github_full_pr_binding(
                        payload,
                        expected_number=999,
                        expected_head=SHA_A,
                    )

        for payload in ({}, {"commit": {}}, {"commit": {"tree": {}}}):
            with self.subTest(commit_payload=payload):
                with self.assertRaises(ReviewContractError):
                    github_commit_tree_sha(payload)

        for payload in ({}, {"commit": {}}):
            with self.subTest(branch_payload=payload):
                with self.assertRaises(ReviewContractError):
                    github_branch_commit_sha(payload)

        for payload in ({}, {"id": 0}, {"id": "123"}):
            with self.subTest(comment_payload=payload):
                with self.assertRaises(ReviewContractError):
                    github_comment_id(payload)


    def test_39_pagination_and_owner_request_comment_shapes_fail_closed(self):
        def bad_page_fetch(_url: str):
            return [{"id": 1}, "not-an-object"]

        with self.assertRaises(ReviewContractError):
            fetch_all_pages(
                bad_page_fetch,
                "https://api.github.com/repos/o/r/issues/1/comments",
            )

        request = lab_request("owner-comment-id-contract")
        comments = [
            {
                "body": request_body(request),
                "user": {"login": "fufufu1116"},
            }
        ]
        with self.assertRaises(ReviewContractError):
            latest_exact_current_owner_request(
                comments,
                repo=request["repo"],
                pr=request["pr"],
                lane=request["lane"],
                head=request["head"],
                tree=request["tree"],
                base=request["base"],
                main=request["main"],
            )

    def test_40_github_app_installation_and_token_shapes_fail_closed(self):
        with mock.patch.object(
            github_app,
            "app_jwt",
            return_value="jwt",
        ):
            with mock.patch.object(
                github_app,
                "github_json",
                return_value={},
            ):
                with self.assertRaises(github_app.GitHubAppError):
                    github_app.installation_token(
                        repo="fufufu1116/multiverse-research",
                        app_id=1,
                        private_key="unused",
                    )

            with mock.patch.object(
                github_app,
                "github_json",
                side_effect=[
                    {"id": 123},
                    {},
                ],
            ):
                with self.assertRaises(github_app.GitHubAppError):
                    github_app.installation_token(
                        repo="fufufu1116/multiverse-research",
                        app_id=1,
                        private_key="unused",
                    )

            with mock.patch.object(
                github_app,
                "github_json",
                side_effect=[
                    {"id": 123},
                    {"token": "installation-token"},
                ],
            ):
                self.assertEqual(
                    github_app.installation_token(
                        repo="fufufu1116/multiverse-research",
                        app_id=1,
                        private_key="unused",
                    ),
                    "installation-token",
                )


    def test_41_nullable_outer_app_helper_accepts_none_and_rejects_wrong_slug(self):
        for lane, login, slug in (
            ("LAB", "multiverse-independent-lab[bot]", "multiverse-independent-lab"),
            ("AUDITOR", "multiverse-independent-auditor[bot]", "multiverse-independent-auditor"),
        ):
            base_comment = {
                "user": {
                    "login": login,
                    "type": "Bot",
                },
                "performed_via_github_app": None,
            }
            self.assertTrue(
                lane_result_outer_app_trusted(base_comment, lane)
            )
            self.assertTrue(
                lane_result_comment_trusted(base_comment, lane)
            )

            exact = copy.deepcopy(base_comment)
            exact["performed_via_github_app"] = {"slug": slug}
            self.assertTrue(
                lane_result_outer_app_trusted(exact, lane)
            )
            self.assertTrue(
                lane_result_comment_trusted(exact, lane)
            )

            wrong = copy.deepcopy(base_comment)
            wrong["performed_via_github_app"] = {"slug": "wrong-app"}
            self.assertFalse(
                lane_result_outer_app_trusted(wrong, lane)
            )
            self.assertFalse(
                lane_result_comment_trusted(wrong, lane)
            )

            malformed = copy.deepcopy(base_comment)
            malformed["performed_via_github_app"] = "wrong-type"
            self.assertFalse(
                lane_result_outer_app_trusted(malformed, lane)
            )
            self.assertFalse(
                lane_result_comment_trusted(malformed, lane)
            )

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
            / "t2.py"
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


if __name__ == "__main__":
    unittest.main()