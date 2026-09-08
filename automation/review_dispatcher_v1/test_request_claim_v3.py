from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.request_claim_v3 import (
    RequestClaimError,
    acquire_claim,
    build_claim,
    canonical_bytes,
    claim_payload_without_digest,
    claim_ref,
    generation_sha256,
    git_blob_sha1,
    verify_claim_binding,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def envelope() -> dict:
    return {
        "repo": "fufufu1116/multiverse-research",
        "pr": 999,
        "lane": "LAB",
        "head": SHA_A,
        "tree": SHA_B,
        "base": SHA_C,
        "main": SHA_D,
    }


class FakeGitObjects:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}

    def create_blob(self, payload: bytes) -> str:
        return git_blob_sha1(payload)

    def create_ref(self, ref: str, sha: str) -> None:
        if ref in self.refs:
            raise RequestClaimError("CLAIM_REF_ALREADY_EXISTS")
        self.refs[ref] = sha


class RequestClaimV3Tests(unittest.TestCase):
    def claim(self, request_id: str = "request-a", predecessor: str | None = None) -> dict:
        return build_claim(
            envelope=envelope(),
            request_id=request_id,
            claimant="sole-control",
            nonce="nonce-sole-control-0001",
            predecessor_sha256=predecessor,
        )

    def test_01_same_generation_has_same_ref(self):
        predecessor = "1" * 64
        self.assertEqual(
            claim_ref(envelope(), predecessor),
            claim_ref(dict(reversed(list(envelope().items()))), predecessor),
        )

    def test_02_new_predecessor_creates_new_generation(self):
        first = None
        second = "1" * 64
        self.assertNotEqual(
            generation_sha256(envelope(), first),
            generation_sha256(envelope(), second),
        )
        self.assertNotEqual(
            claim_ref(envelope(), first),
            claim_ref(envelope(), second),
        )

    def test_03_same_generation_race_has_single_winner(self):
        git = FakeGitObjects()
        predecessor = "1" * 64
        first = self.claim("request-a", predecessor)
        second = build_claim(
            envelope=envelope(),
            request_id="request-b",
            claimant="sole-control-2",
            nonce="nonce-sole-control-0002",
            predecessor_sha256=predecessor,
        )
        acquired = acquire_claim(
            claim=first,
            create_blob=git.create_blob,
            create_ref=git.create_ref,
        )
        self.assertEqual(git.refs[acquired["claim_ref"]], acquired["claim_blob_sha1"])
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REF_ALREADY_EXISTS"):
            acquire_claim(
                claim=second,
                create_blob=git.create_blob,
                create_ref=git.create_ref,
            )

    def test_04_legitimate_supersession_can_claim_next_generation(self):
        git = FakeGitObjects()
        first = self.claim("request-a", None)
        first_acquired = acquire_claim(
            claim=first,
            create_blob=git.create_blob,
            create_ref=git.create_ref,
        )
        predecessor = "2" * 64
        second = self.claim("request-b", predecessor)
        second_acquired = acquire_claim(
            claim=second,
            create_blob=git.create_blob,
            create_ref=git.create_ref,
        )
        self.assertNotEqual(first_acquired["claim_ref"], second_acquired["claim_ref"])
        self.assertEqual(len(git.refs), 2)

    def test_05_blob_digest_binds_exact_payload(self):
        claim = self.claim()
        payload = canonical_bytes(claim_payload_without_digest(claim))
        self.assertEqual(claim["claim_blob_sha1"], git_blob_sha1(payload))

    def test_06_wrong_blob_fails_before_ref_creation(self):
        git = FakeGitObjects()
        claim = self.claim()
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_BLOB_SHA_MISMATCH"):
            acquire_claim(
                claim=claim,
                create_blob=lambda payload: "f" * 40,
                create_ref=git.create_ref,
            )
        self.assertEqual(git.refs, {})

    def test_07_dispatch_binding_fails_on_ref_or_chain_drift(self):
        claim = self.claim("request-a", "1" * 64)
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REF_BLOB_MISMATCH"):
            verify_claim_binding(
                claim=claim,
                observed_ref_sha="f" * 40,
                request_id="request-a",
                predecessor_sha256="1" * 64,
            )
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_PREDECESSOR_DRIFT"):
            verify_claim_binding(
                claim=claim,
                observed_ref_sha=claim["claim_blob_sha1"],
                request_id="request-a",
                predecessor_sha256="2" * 64,
            )


if __name__ == "__main__":
    unittest.main()
