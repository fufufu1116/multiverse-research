from __future__ import annotations

import copy
import json
import unittest

from automation.review_dispatcher_v1.model import (
    REQUEST_MARKER,
    ReviewContractError,
    sha256_json,
)
from automation.review_dispatcher_v1.publisher_freshness_v1 import (
    assert_job_request_still_canonical,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
REPO = "fufufu1116/multiverse-research"


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


def comment(comment_id: int, req: dict, login: str = "fufufu1116") -> dict:
    fence = "```"
    body = "\n".join((REQUEST_MARKER, fence + "json", json.dumps(req, sort_keys=True), fence))
    return {"id": comment_id, "body": body, "user": {"login": login}}


def job(req: dict, comment_id: int) -> dict:
    return {
        "repo": REPO,
        "pr": 999,
        "lane": "LAB",
        "head": SHA_A,
        "tree": SHA_B,
        "base": SHA_C,
        "main": SHA_D,
        "request_comment": comment_id,
        "request_sha256": sha256_json(req),
        "request": req,
    }


class PublisherFreshnessV1Tests(unittest.TestCase):
    def test_01_current_request_passes(self):
        req = request("request-current")
        assert_job_request_still_canonical(job(req, 10), [comment(10, req)])

    def test_02_legitimate_supersession_rejects_old_job(self):
        first = request("request-first")
        second = request("request-second", sha256_json(first))
        with self.assertRaisesRegex(ReviewContractError, "PUBLISH_REQUEST_NO_LONGER_CANONICAL_COMMENT"):
            assert_job_request_still_canonical(
                job(first, 10),
                [comment(10, first), comment(20, second)],
            )

    def test_03_current_superseding_job_passes(self):
        first = request("request-first")
        second = request("request-second", sha256_json(first))
        assert_job_request_still_canonical(
            job(second, 20),
            [comment(10, first), comment(20, second)],
        )

    def test_04_job_sha_drift_fails_closed(self):
        req = request("request-current")
        broken = job(req, 10)
        broken["request_sha256"] = "f" * 64
        with self.assertRaisesRegex(ReviewContractError, "PUBLISH_REQUEST_NO_LONGER_CANONICAL_SHA256"):
            assert_job_request_still_canonical(broken, [comment(10, req)])


if __name__ == "__main__":
    unittest.main()
