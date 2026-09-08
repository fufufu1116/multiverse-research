from __future__ import annotations

import base64
import copy
import unittest

from automation.review_dispatcher_v1.model import ReviewContractError, sha256_json
from automation.review_dispatcher_v1.request_claim_v4 import (
    acquire_claim,
    build_claim,
    canonical_bytes,
    claim_payload_without_digest,
    claim_ref,
    git_blob_sha1,
    verify_request_claim,
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
            "subtrees": {},
            "durable_comments": [],
            "source_rules": [],
            "unittest_modules": [],
            "validators": [],
            "secret_scan_paths": [],
            "forbidden_patterns": [],
            "http": None,
        },
        "upstream": {},
        "nonauthority": nonauthority(),
    }


class FakeGit:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}
        self.blobs: dict[str, bytes] = {}

    def create_blob(self, payload: bytes) -> str:
        sha = git_blob_sha1(payload)
        self.blobs[sha] = payload
        return sha

    def create_ref(self, ref: str, sha: str) -> None:
        if ref in self.refs:
            raise ReviewContractError("CLAIM_REF_ALREADY_EXISTS")
        self.refs[ref] = sha

    def fetch(self, url: str):
        marker = "/git/ref/"
        if marker in url:
            suffix = url.split(marker, 1)[1]
            ref = "refs/" + suffix
            if ref not in self.refs:
                raise ReviewContractError("CLAIM_REF_NOT_FOUND")
            return {
                "ref": ref,
                "object": {"type": "blob", "sha": self.refs[ref]},
            }
        marker = "/git/blobs/"
        if marker in url:
            sha = url.split(marker, 1)[1]
            payload = self.blobs[sha]
            return {
                "sha": sha,
                "encoding": "base64",
                "content": base64.b64encode(payload).decode("ascii"),
            }
        raise AssertionError(url)


class RequestClaimV4Tests(unittest.TestCase):
    def acquire(self, git: FakeGit, req: dict, request_id: str = "request-a") -> dict:
        req = copy.deepcopy(req)
        req["request_id"] = request_id
        return acquire_claim(
            request=req,
            claimant="sole-control",
            nonce="nonce-sole-control-0001",
            create_blob=git.create_blob,
            create_ref=git.create_ref,
        )

    def test_01_claim_binds_complete_request_sha256(self):
        req = request()
        claim = build_claim(
            request=req,
            claimant="sole-control",
            nonce="nonce-sole-control-0001",
        )
        self.assertEqual(claim["request_sha256"], sha256_json(req))

        changed = copy.deepcopy(req)
        changed["proof_ceiling"] = "DIFFERENT"
        changed_claim = build_claim(
            request=changed,
            claimant="sole-control",
            nonce="nonce-sole-control-0001",
        )
        self.assertEqual(claim["claim_ref"], changed_claim["claim_ref"])
        self.assertNotEqual(claim["claim_blob_sha1"], changed_claim["claim_blob_sha1"])

    def test_02_same_generation_has_one_atomic_winner(self):
        git = FakeGit()
        req = request()
        self.acquire(git, req, "request-a")
        with self.assertRaisesRegex(ReviewContractError, "CLAIM_REF_ALREADY_EXISTS"):
            self.acquire(git, req, "request-b")

    def test_03_new_predecessor_creates_new_generation(self):
        first = request("request-a", None)
        second = request("request-b", "1" * 64)
        self.assertNotEqual(claim_ref(first), claim_ref(second))

    def test_04_exact_ref_blob_request_binding_verifies(self):
        git = FakeGit()
        req = request()
        claim = self.acquire(git, req)
        observed = verify_request_claim(request=req, fetch=git.fetch)
        self.assertEqual(observed["claim_blob_sha1"], claim["claim_blob_sha1"])

    def test_05_request_body_drift_fails_closed(self):
        git = FakeGit()
        req = request()
        self.acquire(git, req)
        changed = copy.deepcopy(req)
        changed["execution_state"] = "DRIFTED"
        with self.assertRaises(ReviewContractError):
            verify_request_claim(request=changed, fetch=git.fetch)

    def test_06_ref_retarget_to_other_blob_fails_closed(self):
        git = FakeGit()
        req = request()
        claim = self.acquire(git, req)
        other_payload = canonical_bytes({"not": "the claim"})
        other_sha = git.create_blob(other_payload)
        git.refs[claim["claim_ref"]] = other_sha
        with self.assertRaises(ReviewContractError):
            verify_request_claim(request=req, fetch=git.fetch)

    def test_07_blob_payload_tamper_fails_closed(self):
        git = FakeGit()
        req = request()
        claim = self.acquire(git, req)
        original = git.blobs[claim["claim_blob_sha1"]]
        git.blobs[claim["claim_blob_sha1"]] = original + b" "
        with self.assertRaisesRegex(ReviewContractError, "CLAIM_BLOB_OBJECT_DIGEST_MISMATCH"):
            verify_request_claim(request=req, fetch=git.fetch)


if __name__ == "__main__":
    unittest.main()
