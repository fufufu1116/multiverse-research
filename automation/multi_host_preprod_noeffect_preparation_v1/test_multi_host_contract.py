import json
import unittest

from automation.multi_host_preprod_noeffect_preparation_v1.multi_host_contract import (
    AUTHORITY,
    ENVIRONMENT_CLASS,
    PROOF_CEILING,
    RUNTIME,
    TOPOLOGY_CLASS,
    ContractViolation,
    SyntheticSharedState,
    build_preparation_contract,
    payload_sha256,
    run_synthetic_failover_drill,
)


class StrSubclass(str):
    pass


class MultiHostPreparationContractTests(unittest.TestCase):
    def assert_violation(self, code, fn):
        with self.assertRaises(ContractViolation) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, code)

    def test_exact_preparation_boundary(self):
        contract = build_preparation_contract()

        self.assertEqual(
            contract["topology_class"],
            "RENDER_PREPRODUCTION_TWO_SERVICE_SHARED_POSTGRES_NO_EFFECT_v1",
        )
        self.assertEqual(
            contract["environment_class"],
            "PRE_PRODUCTION",
        )
        self.assertEqual(contract["provider_family"], "RENDER")
        self.assertEqual(
            contract["proof_ceiling"],
            "MULTI_HOST_PREPRODUCTION_SYNTHETIC_NO_EFFECT_PREPARATION_ONLY",
        )
        self.assertEqual(contract["runtime"], "OFF")

        topology = contract["planned_topology"]
        self.assertEqual(topology["worker_count"], 2)
        self.assertEqual(
            [worker["worker_id"] for worker in topology["workers"]],
            ["worker-a", "worker-b"],
        )
        self.assertTrue(
            all(
                worker["provisioned"] is False
                for worker in topology["workers"]
            )
        )
        self.assertIs(
            topology["shared_state"]["provisioned"],
            False,
        )
        self.assertIs(
            topology["actual_remote_execution_performed"],
            False,
        )

    def test_authority_is_exact_false(self):
        self.assertTrue(AUTHORITY)
        for key, value in AUTHORITY.items():
            with self.subTest(key=key):
                self.assertIs(type(value), bool)
                self.assertIs(value, False)

        contract = build_preparation_contract()
        self.assertEqual(
            set(contract["authority"]),
            set(AUTHORITY),
        )
        for value in contract["authority"].values():
            self.assertIs(type(value), bool)
            self.assertIs(value, False)

    def test_synthetic_failover_drill(self):
        receipt = run_synthetic_failover_drill()

        self.assertEqual(
            receipt["topology_class"],
            TOPOLOGY_CLASS,
        )
        self.assertEqual(
            receipt["environment_class"],
            ENVIRONMENT_CLASS,
        )
        self.assertEqual(
            receipt["execution_scope"],
            "REPOSITORY_SYNTHETIC_ONLY",
        )
        self.assertIs(
            receipt["actual_remote_execution_performed"],
            False,
        )
        self.assertIs(
            receipt["remote_resources_created"],
            False,
        )

        self.assertEqual(
            receipt["worker_a_initial_fence_token"],
            1,
        )
        self.assertEqual(
            receipt["worker_b_successor_fence_token"],
            2,
        )
        self.assertEqual(
            receipt["worker_a_second_successor_fence_token"],
            3,
        )

        self.assertIs(receipt["fencing_monotonic"], True)
        self.assertIs(
            receipt["concurrent_acquire_rejected"],
            True,
        )
        self.assertIs(
            receipt["stale_owner_rejected"],
            True,
        )
        self.assertIs(
            receipt["stale_fence_rejected"],
            True,
        )
        self.assertIs(
            receipt["split_brain_rejected"],
            True,
        )
        self.assertIs(
            receipt["cross_worker_idempotency_pass"],
            True,
        )
        self.assertIs(
            receipt["conflicting_payload_rejected"],
            True,
        )
        self.assertIs(
            receipt["duplicate_external_effect"],
            False,
        )
        self.assertEqual(
            receipt["simulated_effect_count_before_second_failover"],
            1,
        )
        self.assertEqual(
            receipt["snapshot_sha256"],
            receipt["restored_snapshot_sha256"],
        )
        self.assertIs(
            receipt["snapshot_restore_match"],
            True,
        )
        self.assertEqual(receipt["findings"], [])
        self.assertEqual(receipt["runtime"], RUNTIME)
        self.assertEqual(
            receipt["proof_ceiling"],
            PROOF_CEILING,
        )

    def test_lease_rejects_competing_owner_before_expiry(self):
        state = SyntheticSharedState()
        lease = state.acquire("worker-a", 0, 10)

        self.assertEqual(lease.fence_token, 1)

        self.assert_violation(
            "LEASE_HELD",
            lambda: state.acquire("worker-b", 9, 10),
        )

        successor = state.acquire("worker-b", 10, 10)
        self.assertEqual(successor.fence_token, 2)
        self.assertEqual(successor.owner, "worker-b")

    def test_fencing_rejects_stale_owner_and_stale_token(self):
        state = SyntheticSharedState()
        a = state.acquire("worker-a", 0, 5)
        b = state.acquire("worker-b", 5, 5)
        digest = payload_sha256(b"x")

        self.assert_violation(
            "STALE_OWNER",
            lambda: state.mutate(
                "worker-a",
                a.fence_token,
                6,
                "k1",
                digest,
            ),
        )

        self.assert_violation(
            "STALE_FENCE_TOKEN",
            lambda: state.mutate(
                "worker-b",
                a.fence_token,
                6,
                "k2",
                digest,
            ),
        )

        applied = state.mutate(
            "worker-b",
            b.fence_token,
            6,
            "k3",
            digest,
        )
        self.assertIs(applied.applied, True)

    def test_cross_worker_idempotency_is_global(self):
        state = SyntheticSharedState()
        a = state.acquire("worker-a", 0, 5)
        digest = payload_sha256(b"payload")

        first = state.mutate(
            "worker-a",
            a.fence_token,
            1,
            "shared-key",
            digest,
        )
        self.assertIs(first.applied, True)
        self.assertEqual(first.simulated_effect_count, 1)

        b = state.acquire("worker-b", 5, 5)

        duplicate = state.mutate(
            "worker-b",
            b.fence_token,
            6,
            "shared-key",
            digest,
        )
        self.assertIs(duplicate.applied, False)
        self.assertIs(duplicate.duplicate, True)
        self.assertEqual(duplicate.simulated_effect_count, 1)

    def test_same_idempotency_key_with_different_payload_rejected(self):
        state = SyntheticSharedState()
        lease = state.acquire("worker-a", 0, 10)
        digest_a = payload_sha256(b"a")
        digest_b = payload_sha256(b"b")

        state.mutate(
            "worker-a",
            lease.fence_token,
            1,
            "same-key",
            digest_a,
        )

        self.assert_violation(
            "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
            lambda: state.mutate(
                "worker-a",
                lease.fence_token,
                2,
                "same-key",
                digest_b,
            ),
        )

    def test_snapshot_restore_is_canonical_and_tamper_fail_closed(self):
        state = SyntheticSharedState()
        lease = state.acquire("worker-a", 0, 10)
        digest = payload_sha256(b"snapshot")

        state.mutate(
            "worker-a",
            lease.fence_token,
            1,
            "snapshot-key",
            digest,
        )

        snapshot = state.snapshot_bytes()
        restored = SyntheticSharedState.restore(snapshot)

        self.assertEqual(
            restored.snapshot_bytes(),
            snapshot,
        )

        payload = json.loads(snapshot.decode())
        payload["simulated_effect_count"] = 2
        tampered = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

        self.assert_violation(
            "SNAPSHOT_EFFECT_COUNT_MISMATCH",
            lambda: SyntheticSharedState.restore(tampered),
        )

    def test_exact_types_reject_bool_and_str_subclass_confusion(self):
        state = SyntheticSharedState()

        self.assert_violation(
            "WORKER_ID_TYPE",
            lambda: state.acquire(
                StrSubclass("worker-a"),
                0,
                5,
            ),
        )

        self.assert_violation(
            "LOGICAL_TIME_TYPE",
            lambda: state.acquire(
                "worker-a",
                True,
                5,
            ),
        )

        self.assert_violation(
            "LEASE_TTL_TYPE",
            lambda: state.acquire(
                "worker-a",
                0,
                True,
            ),
        )

        lease = state.acquire(
            "worker-a",
            0,
            5,
        )

        digest = payload_sha256(b"type")

        self.assert_violation(
            "FENCE_TOKEN_TYPE",
            lambda: state.mutate(
                "worker-a",
                True,
                1,
                "k",
                digest,
            ),
        )

        self.assert_violation(
            "REQUEST_KEY_TYPE",
            lambda: state.mutate(
                "worker-a",
                lease.fence_token,
                1,
                StrSubclass("k"),
                digest,
            ),
        )

        self.assert_violation(
            "PAYLOAD_DIGEST_TYPE",
            lambda: state.mutate(
                "worker-a",
                lease.fence_token,
                1,
                "k",
                StrSubclass(digest),
            ),
        )

    def test_renewal_requires_live_exact_owner_and_token(self):
        state = SyntheticSharedState()
        lease = state.acquire("worker-a", 0, 5)

        renewed = state.renew(
            "worker-a",
            lease.fence_token,
            2,
            5,
        )
        self.assertEqual(
            renewed.fence_token,
            lease.fence_token,
        )
        self.assertEqual(
            renewed.lease_expires_at,
            7,
        )

        self.assert_violation(
            "STALE_OWNER",
            lambda: state.renew(
                "worker-b",
                lease.fence_token,
                3,
                5,
            ),
        )

        self.assert_violation(
            "STALE_FENCE_TOKEN",
            lambda: state.renew(
                "worker-a",
                lease.fence_token + 1,
                3,
                5,
            ),
        )

        self.assert_violation(
            "LEASE_EXPIRED",
            lambda: state.renew(
                "worker-a",
                lease.fence_token,
                7,
                5,
            ),
        )


if __name__ == "__main__":
    unittest.main()
