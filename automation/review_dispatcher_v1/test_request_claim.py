from __future__ import annotations

import unittest

from automation.review_dispatcher_v1.request_claim import (
    RequestClaimError,
    acquire_claim,
    build_claim,
    claim_ref,
    envelope_sha256,
    verify_claim_binding,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
SHA_E = "e" * 40
SHA_F = "f" * 40


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


class FakeAtomicRefs:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}

    def create(self, ref: str, sha: str) -> None:
        if ref in self.refs:
            raise RequestClaimError("CLAIM_REF_ALREADY_EXISTS")
        self.refs[ref] = sha


class RequestClaimTests(unittest.TestCase):
    def test_01_envelope_hash_and_ref_are_deterministic(self):
        first = envelope()
        second = dict(reversed(list(first.items())))
        self.assertEqual(envelope_sha256(first), envelope_sha256(second))
        self.assertEqual(claim_ref(first), claim_ref(second))

    def test_02_exact_envelope_change_changes_claim_ref(self):
        first = envelope()
        second = envelope()
        second["head"] = SHA_E
        self.assertNotEqual(claim_ref(first), claim_ref(second))

    def test_03_atomic_ref_create_has_single_winner(self):
        refs = FakeAtomicRefs()
        env = envelope()
        claim_a = build_claim(
            envelope=env,
            request_id="request-a",
            claimant="control-a",
            nonce="nonce-control-a-0001",
            predecessor_sha256=None,
        )
        claim_b = build_claim(
            envelope=env,
            request_id="request-b",
            claimant="control-b",
            nonce="nonce-control-b-0001",
            predecessor_sha256=None,
        )

        acquired = acquire_claim(
            claim=claim_a,
            claim_commit_sha=SHA_E,
            create_ref=refs.create,
        )
        self.assertEqual(acquired["claim_commit_sha"], SHA_E)

        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REF_ALREADY_EXISTS"):
            acquire_claim(
                claim=claim_b,
                claim_commit_sha=SHA_F,
                create_ref=refs.create,
            )

    def test_04_winner_binding_rejects_loser_commit(self):
        claim = build_claim(
            envelope=envelope(),
            request_id="request-a",
            claimant="control-a",
            nonce="nonce-control-a-0001",
            predecessor_sha256=None,
        )
        verify_claim_binding(
            claim=claim,
            claim_commit_sha=SHA_E,
            observed_ref_sha=SHA_E,
            request_id="request-a",
            predecessor_sha256=None,
        )
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_REF_OWNERSHIP_LOST"):
            verify_claim_binding(
                claim=claim,
                claim_commit_sha=SHA_F,
                observed_ref_sha=SHA_E,
                request_id="request-a",
                predecessor_sha256=None,
            )

    def test_05_claim_binds_immediate_predecessor(self):
        predecessor = "1" * 64
        claim = build_claim(
            envelope=envelope(),
            request_id="request-a",
            claimant="control-a",
            nonce="nonce-control-a-0001",
            predecessor_sha256=predecessor,
        )
        with self.assertRaisesRegex(RequestClaimError, "CLAIM_PREDECESSOR_DRIFT"):
            verify_claim_binding(
                claim=claim,
                claim_commit_sha=SHA_E,
                observed_ref_sha=SHA_E,
                request_id="request-a",
                predecessor_sha256="2" * 64,
            )


if __name__ == "__main__":
    unittest.main()
