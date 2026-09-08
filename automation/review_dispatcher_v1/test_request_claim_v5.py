from __future__ import annotations

import copy
import hashlib
import unittest

from automation.review_dispatcher_v1.model import ReviewContractError, sha256_json
from automation.review_dispatcher_v1.request_claim_v5 import (
    acquire_claim,
    build_claim,
    claim_commit_message,
    claim_ref,
    verify_request_claim,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
TREE_MAIN = "e" * 40


def nonauthority() -> dict:
    return {key: False for key in (
        "provider_resource_mutation", "deploy", "database_mutation",
        "provider_effect_enablement", "runtime_activation_bridge_enablement",
        "runtime_activation", "production_credentials", "production_deployment",
        "protected_data", "live_business_effect", "additional_spend", "merge",
        "main_mutation", "ruleset_mutation", "workflow_dispatch_rerun",
    )}


def request(request_id: str = "request-a", predecessor: str | None = None) -> dict:
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
        "supersedes_request_sha256": predecessor,
        "recipe": {
            "subtrees": {}, "durable_comments": [], "source_rules": [],
            "unittest_modules": [], "validators": [], "secret_scan_paths": [],
            "forbidden_patterns": [], "http": None,
        },
        "upstream": {},
        "nonauthority": nonauthority(),
    }


class FakeProvider:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}
        self.commits: dict[str, dict] = {
            SHA_D: {"sha": SHA_D, "message": "main", "parents": [], "tree": {"sha": TREE_MAIN}}
        }

    def create_commit(self, message: str, parent: str) -> str:
        sha = hashlib.sha1((message + parent).encode()).hexdigest()
        self.commits[sha] = {
            "sha": sha,
            "message": message,
            "parents": [{"sha": parent}],
            "tree": {"sha": TREE_MAIN},
        }
        return sha

    def create_branch(self, name: str, sha: str) -> None:
        ref = "refs/heads/" + name
        if ref in self.refs:
            raise ReviewContractError("CLAIM_REF_ALREADY_EXISTS")
        self.refs[ref] = sha

    def fetch(self, url: str):
        if "/git/ref/" in url:
            suffix = url.split("/git/ref/", 1)[1]
            ref = "refs/" + suffix
            if ref not in self.refs:
                raise ReviewContractError("CLAIM_REF_NOT_FOUND")
            return {"ref": ref, "object": {"type": "commit", "sha": self.refs[ref]}}
        if "/git/commits/" in url:
            sha = url.rsplit("/", 1)[1]
            return self.commits[sha]
        raise AssertionError(url)


class RequestClaimV5Tests(unittest.TestCase):
    def test_01_complete_request_sha_is_bound(self):
        req = request()
        claim = build_claim(request=req, claimant="sole-control", nonce="nonce-sole-control-0001")
        self.assertEqual(claim["request_sha256"], sha256_json(req))
        changed = copy.deepcopy(req)
        changed["proof_ceiling"] = "DIFFERENT"
        changed_claim = build_claim(request=changed, claimant="sole-control", nonce="nonce-sole-control-0001")
        self.assertEqual(claim["claim_ref"], changed_claim["claim_ref"])
        self.assertNotEqual(claim_commit_message(claim), claim_commit_message(changed_claim))

    def test_02_same_generation_has_one_branch_winner(self):
        p = FakeProvider()
        req = request()
        acquire_claim(request=req, claimant="sole-control", nonce="nonce-sole-control-0001", create_commit=p.create_commit, create_branch=p.create_branch)
        with self.assertRaisesRegex(ReviewContractError, "CLAIM_REF_ALREADY_EXISTS"):
            acquire_claim(request=copy.deepcopy(req), claimant="sole-control-2", nonce="nonce-sole-control-0002", create_commit=p.create_commit, create_branch=p.create_branch)

    def test_03_new_predecessor_creates_new_generation(self):
        self.assertNotEqual(claim_ref(request("a", None)), claim_ref(request("b", "1" * 64)))

    def test_04_exact_claim_verifies(self):
        p = FakeProvider()
        req = request()
        acquired = acquire_claim(request=req, claimant="sole-control", nonce="nonce-sole-control-0001", create_commit=p.create_commit, create_branch=p.create_branch)
        observed = verify_request_claim(request=req, fetch=p.fetch)
        self.assertEqual(observed["claim_commit_sha"], acquired["claim_commit_sha"])

    def test_05_request_drift_fails_closed(self):
        p = FakeProvider()
        req = request()
        acquire_claim(request=req, claimant="sole-control", nonce="nonce-sole-control-0001", create_commit=p.create_commit, create_branch=p.create_branch)
        changed = copy.deepcopy(req)
        changed["execution_state"] = "DRIFTED"
        with self.assertRaises(ReviewContractError):
            verify_request_claim(request=changed, fetch=p.fetch)

    def test_06_nonempty_claim_commit_fails_closed(self):
        p = FakeProvider()
        req = request()
        acquired = acquire_claim(request=req, claimant="sole-control", nonce="nonce-sole-control-0001", create_commit=p.create_commit, create_branch=p.create_branch)
        p.commits[acquired["claim_commit_sha"]]["tree"] = {"sha": "f" * 40}
        with self.assertRaisesRegex(ReviewContractError, "CLAIM_COMMIT_NOT_EMPTY"):
            verify_request_claim(request=req, fetch=p.fetch)

    def test_07_wrong_parent_main_fails_closed(self):
        p = FakeProvider()
        req = request()
        acquired = acquire_claim(request=req, claimant="sole-control", nonce="nonce-sole-control-0001", create_commit=p.create_commit, create_branch=p.create_branch)
        p.commits[acquired["claim_commit_sha"]]["parents"] = [{"sha": "f" * 40}]
        with self.assertRaisesRegex(ReviewContractError, "CLAIM_COMMIT_PARENT_MAIN_MISMATCH"):
            verify_request_claim(request=req, fetch=p.fetch)


if __name__ == "__main__":
    unittest.main()
