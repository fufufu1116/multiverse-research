from __future__ import annotations

import json
import unittest

from automation.review_dispatcher_v1 import model, publisher, t2

REPO = "fufufu1116/multiverse-research"
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def nonauthority() -> dict:
    return {key: False for key in (
        "provider_resource_mutation", "deploy", "database_mutation",
        "provider_effect_enablement", "runtime_activation_bridge_enablement",
        "runtime_activation", "production_credentials", "production_deployment",
        "protected_data", "live_business_effect", "additional_spend", "merge",
        "main_mutation", "ruleset_mutation", "workflow_dispatch_rerun",
    )}


def request(request_id: str, predecessor: str | None = None) -> dict:
    return {
        "schema": "MULTIVERSE_REVIEW_REQUEST_v1",
        "request_id": request_id,
        "lane": "LAB",
        "mode": "REPOSITORY_ONLY",
        "repo": REPO,
        "pr": 999,
        "head": SHA_A,
        "tree": SHA_B,
        "base": SHA_C,
        "main": SHA_D,
        "proof_ceiling": "TEST_ONLY",
        "execution_state": "TEST_REQUESTED",
        "supersedes_request_sha256": predecessor,
        "recipe": {
            "subtrees": {}, "durable_comments": [], "source_rules": [],
            "unittest_modules": [], "validators": [], "secret_scan_paths": [],
            "forbidden_patterns": [], "http": None,
        },
        "upstream": {},
        "nonauthority": nonauthority(),
    }


def request_comment(comment_id: int, req: dict) -> dict:
    fence = "```"
    return {
        "id": comment_id,
        "body": "\n".join((model.REQUEST_MARKER, fence + "json", json.dumps(req, sort_keys=True), fence)),
        "user": {"login": "fufufu1116"},
    }


def trusted_result(comment_id: int, marker: str, lane: str) -> dict:
    login = model.LAB_LOGIN if lane == "LAB" else model.AUDITOR_LOGIN
    slug = model.LAB_APP_SLUG if lane == "LAB" else model.AUDITOR_APP_SLUG
    return {
        "id": comment_id,
        "body": marker + " build -->\nPASS",
        "user": {"login": login, "type": "Bot"},
        "performed_via_github_app": {"slug": slug},
    }


class IntegratedResilienceConvergenceTests(unittest.TestCase):
    def test_01_actual_model_arbitrates_same_generation(self):
        first = request("request-first")
        sibling = request("request-sibling")
        winner = model.latest_exact_current_owner_request(
            [request_comment(20, sibling), request_comment(10, first)],
            repo=REPO, pr=999, lane="LAB",
            head=SHA_A, tree=SHA_B, base=SHA_C, main=SHA_D,
        )
        self.assertEqual(winner[0], 10)
        self.assertEqual(winner[1]["request_id"], "request-first")

    def test_02_actual_publisher_canonicalizes_concurrent_result(self):
        marker = "RESULT-MARKER"
        comments = [trusted_result(101, marker, "LAB"), trusted_result(100, marker, "LAB")]
        winner = publisher._canonical_comment_or_none(comments, lane="LAB", marker=marker)
        self.assertIsNotNone(winner)
        self.assertEqual(winner["id"], 100)

    def test_03_actual_publisher_recovery_binding_rejects_drift(self):
        job = {
            "lane": "LAB", "request_id": "request-001", "request_comment": 10,
            "request_sha256": "e" * 64, "repo": REPO, "pr": 999,
            "head": SHA_A, "tree": SHA_B, "base": SHA_C, "main": SHA_D,
        }
        artifact = {
            "schema_version": "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
            "lane": "LAB", "request_id": job["request_id"],
            "request_comment": 10, "request_sha256": job["request_sha256"],
            "reviewed_repo": REPO, "reviewed_pr": 999,
            "reviewed_head": SHA_A, "reviewed_tree": SHA_B,
            "reviewed_base": SHA_C, "reviewed_main": SHA_D,
            "verdict": "PASS", "findings": [],
            "producer": {"github_login": model.LAB_LOGIN, "github_app_id": model.LAB_APP_ID},
        }
        publisher._validate_recovery_artifact(job, artifact)
        artifact["reviewed_tree"] = "f" * 40
        with self.assertRaises(model.ReviewContractError):
            publisher._validate_recovery_artifact(job, artifact)

    def test_04_actual_t2_canonicalizes_duplicate_t2(self):
        marker = "T2-MARKER"
        comments = [trusted_result(201, marker, "AUDITOR"), trusted_result(200, marker, "AUDITOR")]
        winner = t2._canonical_t2_comment_or_none(comments, marker)
        self.assertIsNotNone(winner)
        self.assertEqual(winner["id"], 200)

    def test_05_actual_modules_compose_fault_race_recovery_sequence(self):
        first = request("request-first")
        sibling = request("request-sibling")
        second = request("request-second", model.sha256_json(first))
        selected = model.latest_exact_current_owner_request(
            [request_comment(20, sibling), request_comment(30, second), request_comment(10, first)],
            repo=REPO, pr=999, lane="LAB",
            head=SHA_A, tree=SHA_B, base=SHA_C, main=SHA_D,
        )
        self.assertEqual(selected[0], 30)

        result_marker = "RESULT-SEQ"
        result_comments = [trusted_result(101, result_marker, "LAB"), trusted_result(100, result_marker, "LAB")]
        canonical_result = publisher._canonical_comment_or_none(result_comments, lane="LAB", marker=result_marker)
        self.assertEqual(canonical_result["id"], 100)

        t2_marker = "T2-SEQ"
        t2_comments = [trusted_result(201, t2_marker, "AUDITOR"), trusted_result(200, t2_marker, "AUDITOR")]
        canonical_t2 = t2._canonical_t2_comment_or_none(t2_comments, t2_marker)
        self.assertEqual(canonical_t2["id"], 200)


if __name__ == "__main__":
    unittest.main()
