from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.request_claim_v2 import (
    RequestClaimError,
    acquire_claim,
    build_claim,
    canonical_bytes,
    claim_payload_without_digest,
    claim_ref,
    git_blob_sha1,
    verify_claim_binding,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def envelope() -> dict:
    return {"repo": "fufufu1116/multiverse-research", "pr": 999, "lane": "LAB", "head": SHA_A, "tree": SHA_B, "base": SHA_C, "main": SHA_D}


class FakeGitObjects:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}

    def create_blob(self, payload: bytes) -> str:
        return git_blob_sha1(payload)

    def create_ref(self, ref: str, sha: str) -> None:
        if ref in self.refs:
            raise RequestClaimError("CLAIM_REF_ALREADY_EXISTS")
        self.refs[ref] = sha


class RequestClaimV2Tests(unittest.TestCase):
    def claim(self, request_id: str = "request-a") -> dict:
        return build_claim(envelope=envelope(), request_id=request_id, claimant="sole-control", nonce="nonce-sole-control-0001", predecessor_sha256=None)

    def test_01_claim_uses_tag_namespace(self):
        self.assertTrue(claim_ref(envelope()).startswith("refs/tags/multiverse-review-claims/v2/"))

    def test_02_claim_blob_digest_is_exact_git_blob_sha(self):
        claim = self.claim()
        payload = canonical_bytes(claim_payload_without_digest(claim))
        self.assertEqual(claim["claim_blob_sha1"], git_blob_sha1(payload))

    def test_03_atomic_ref_create_has_single_winner(self):
        git = FakeGitObjects()
        first = self.claim("request-a")
        second = self.claim("request-b")
        acquired = acquire_claim(claim=first, create_blob=git.create_blob, create_ref=git.create_ref)
        self.assertEqual(git.refs[acquired["claim_ref"]], acquired["claim_blob_sha1"])
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REF_ALREADY_EXISTS"):
            acquire_claim(claim=second, create_blob=git.create_blob, create_ref=git.create_ref)

    def test_04_wrong_blob_from_provider_fails_before_ref_create(self):
        git = FakeGitObjects()
        claim = self.claim()
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_BLOB_SHA_MISMATCH"):
            acquire_claim(claim=claim, create_blob=lambda payload: "f" * 40, create_ref=git.create_ref)
        self.assertEqual(git.refs, {})

    def test_05_dispatch_binding_rejects_other_blob(self):
        claim = self.claim()
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REF_BLOB_MISMATCH"):
            verify_claim_binding(claim=claim, observed_ref_sha="f" * 40, request_id="request-a", predecessor_sha256=None)

    def test_06_request_and_predecessor_drift_fail_closed(self):
        claim = self.claim()
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REQUEST_ID_DRIFT"):
            verify_claim_binding(claim=claim, observed_ref_sha=claim["claim_blob_sha1"], request_id="request-x", predecessor_sha256=None)
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_PREDECESSOR_DRIFT"):
            verify_claim_binding(claim=claim, observed_ref_sha=claim["claim_blob_sha1"], request_id="request-a", predecessor_sha256="1" * 64)


if __name__ == "__main__":
    unittest.main()
