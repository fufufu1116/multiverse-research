from __future__ import annotations

import json
import unittest
from unittest import mock

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


def request(request_id: str, *, lane: str = "LAB", predecessor: str | None = None, upstream: dict | None = None) -> dict:
    return {
        "schema": "MULTIVERSE_REVIEW_REQUEST_v1",
        "request_id": request_id,
        "lane": lane,
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
        "upstream": {} if upstream is None else upstream,
        "nonauthority": nonauthority(),
    }


def request_comment(comment_id: int, req: dict, login: str = "fufufu1116") -> dict:
    fence = "```"
    return {
        "id": comment_id,
        "body": "\n".join((model.REQUEST_MARKER, fence + "json", json.dumps(req, sort_keys=True), fence)),
        "user": {"login": login},
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


def artifact_for(job: dict) -> dict:
    login = model.LAB_LOGIN if job["lane"] == "LAB" else model.AUDITOR_LOGIN
    app_id = model.LAB_APP_ID if job["lane"] == "LAB" else model.AUDITOR_APP_ID
    return {
        "schema_version": "MULTIVERSE_FIXED_REVIEW_ARTIFACT_v1",
        "lane": job["lane"],
        "request_id": job["request_id"],
        "request_comment": job["request_comment"],
        "request_sha256": job["request_sha256"],
        "reviewed_repo": REPO,
        "reviewed_pr": 999,
        "reviewed_head": SHA_A,
        "reviewed_tree": SHA_B,
        "reviewed_base": SHA_C,
        "reviewed_main": SHA_D,
        "verdict": "PASS",
        "findings": [],
        "producer": {"github_login": login, "github_app_id": app_id},
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
        self.assertEqual(winner["id"], 100)

    def test_03_actual_publisher_recovery_binding_rejects_drift(self):
        job = {
            "lane": "LAB", "request_id": "request-001", "request_comment": 10,
            "request_sha256": "e" * 64, "repo": REPO, "pr": 999,
            "head": SHA_A, "tree": SHA_B, "base": SHA_C, "main": SHA_D,
        }
        artifact = artifact_for(job)
        publisher._validate_recovery_artifact(job, artifact)
        artifact["reviewed_tree"] = "f" * 40
        with self.assertRaises(model.ReviewContractError):
            publisher._validate_recovery_artifact(job, artifact)

    def test_04_actual_t2_canonicalizes_duplicate_t2(self):
        marker = "T2-MARKER"
        comments = [trusted_result(201, marker, "AUDITOR"), trusted_result(200, marker, "AUDITOR")]
        winner = t2._canonical_t2_comment_or_none(comments, marker)
        self.assertEqual(winner["id"], 200)

    def test_05_public_model_publisher_t2_replay_with_fault_race_recovery(self):
        lab_req = request("lab-request")
        lab_sha = model.sha256_json(lab_req)
        upstream = {"lab_pass_comment": 90, "lab_request_sha256": lab_sha, "t1_comment": 91}
        first = request("auditor-first", lane="AUDITOR", upstream=upstream)
        sibling = request("auditor-sibling", lane="AUDITOR", upstream=upstream)
        second = request("auditor-second", lane="AUDITOR", predecessor=model.sha256_json(first), upstream=upstream)
        untrusted = request("auditor-attacker", lane="AUDITOR", upstream=upstream)

        base_comments = [
            request_comment(1, untrusted, login="attacker"),
            request_comment(10, first), request_comment(20, sibling), request_comment(30, second),
            request_comment(50, lab_req),
        ]
        selected = model.latest_exact_current_owner_request(
            base_comments, repo=REPO, pr=999, lane="AUDITOR",
            head=SHA_A, tree=SHA_B, base=SHA_C, main=SHA_D,
        )
        self.assertEqual(selected[0], 30)
        self.assertEqual(selected[1]["request_id"], "auditor-second")

        stale_job = {
            "lane": "AUDITOR", "repo": REPO, "pr": 999,
            "head": SHA_A, "tree": SHA_B, "base": SHA_C, "main": SHA_D,
            "request": first, "request_id": first["request_id"],
            "request_comment": 10, "request_sha256": model.sha256_json(first),
        }
        with mock.patch.object(publisher, "_original_fresh_verify", return_value=base_comments):
            with self.assertRaises(model.ReviewContractError):
                publisher.publish(stale_job, artifact_for(stale_job))

        job = {
            "lane": "AUDITOR", "repo": REPO, "pr": 999,
            "head": SHA_A, "tree": SHA_B, "base": SHA_C, "main": SHA_D,
            "request": second, "request_id": second["request_id"],
            "request_comment": 30, "request_sha256": model.sha256_json(second),
        }
        artifact = artifact_for(job)
        result_marker = model.result_marker(job["request_id"], SHA_A, 30, job["request_sha256"])
        pre_publish = list(base_comments)
        post_publish = base_comments + [
            trusted_result(100, result_marker, "AUDITOR"),
            trusted_result(101, result_marker, "AUDITOR"),
        ]
        receipt = {"published_comment_id": 100, "published_by": model.AUDITOR_LOGIN, "github_app_id": model.AUDITOR_APP_ID, "request_sha256": job["request_sha256"]}
        with mock.patch.object(publisher, "_original_fresh_verify", side_effect=[pre_publish, post_publish]), \
             mock.patch.object(publisher, "_original_publish", return_value=receipt):
            published = publisher.publish(job, artifact)
        self.assertEqual(published["published_comment_id"], 100)

        lab_marker = model.result_marker(lab_req["request_id"], SHA_A, 50, lab_sha)
        t2_pre = post_publish + [trusted_result(90, lab_marker, "LAB")]
        t2_marker = model.t2_marker(job["request_id"], SHA_A, 100, job["request_sha256"])
        t2_post = t2_pre + [
            trusted_result(200, t2_marker, "AUDITOR"),
            trusted_result(201, t2_marker, "AUDITOR"),
        ]
        t2_result = {"t2_comment_id": 200}
        with mock.patch.object(t2, "_all_comments", return_value=t2_pre), \
             mock.patch.object(t2, "_fresh_t2_verify", return_value=t2_post), \
             mock.patch.object(t2, "_original_publish_t2", return_value=t2_result):
            final = t2.publish_t2(job, artifact, published)
        self.assertEqual(final["t2_comment_id"], 200)

        loser_receipt = dict(receipt)
        loser_receipt["published_comment_id"] = 101
        with mock.patch.object(publisher, "_original_fresh_verify", side_effect=[pre_publish, post_publish]), \
             mock.patch.object(publisher, "_original_publish", return_value=loser_receipt):
            with self.assertRaises(model.ReviewContractError):
                publisher.publish(job, artifact)

        loser_t2 = {"t2_comment_id": 201}
        with mock.patch.object(t2, "_all_comments", return_value=t2_pre), \
             mock.patch.object(t2, "_fresh_t2_verify", return_value=t2_post), \
             mock.patch.object(t2, "_original_publish_t2", return_value=loser_t2):
            with self.assertRaises(model.ReviewContractError):
                t2.publish_t2(job, artifact, published)


if __name__ == "__main__":
    unittest.main()
