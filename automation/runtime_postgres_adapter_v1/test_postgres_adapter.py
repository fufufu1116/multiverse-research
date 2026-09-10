from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

try:
    from .fake_dbapi import ConnectionFactoryQueue, ExpectedCall, ScriptedConnection
    from .postgres_adapter import (
        ACQUIRE_LEASE_SQL,
        CHECKPOINT_READ_SQL,
        CHECKPOINT_UPSERT_SQL,
        CONTROL_FOR_UPDATE_SQL,
        ENSURE_CONTROL_SQL,
        OPERATION_INSERT_SQL,
        OPERATION_READ_SQL,
        RENEW_LEASE_SQL,
        PostgresControlViolation,
        PostgresDistributedControlStore,
        PostgresLeaseGrant,
        RuntimeIdentity,
    )
    from .postgres_runtime_bridge import PreparedPostgresRuntimeBridge
    from .validator import validate
except ImportError:
    from fake_dbapi import ConnectionFactoryQueue, ExpectedCall, ScriptedConnection
    from postgres_adapter import (
        ACQUIRE_LEASE_SQL,
        CHECKPOINT_READ_SQL,
        CHECKPOINT_UPSERT_SQL,
        CONTROL_FOR_UPDATE_SQL,
        ENSURE_CONTROL_SQL,
        OPERATION_INSERT_SQL,
        OPERATION_READ_SQL,
        RENEW_LEASE_SQL,
        PostgresControlViolation,
        PostgresDistributedControlStore,
        PostgresLeaseGrant,
        RuntimeIdentity,
    )
    from postgres_runtime_bridge import PreparedPostgresRuntimeBridge
    from validator import validate


UTC = timezone.utc


class PostgresAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_id = "runtime-preprod-a"
        self.identity = RuntimeIdentity("worker-a", "instance-a")
        self.now = datetime(2026, 9, 6, 6, 0, tzinfo=UTC)
        self.expiry = self.now + timedelta(seconds=30)

    def control_row(
        self,
        *,
        owner_worker=None,
        owner_instance=None,
        fence=0,
        expiry=None,
        db_now=None,
        kill=True,
        activation=False,
        provider=False,
    ):
        return (
            owner_worker,
            owner_instance,
            fence,
            expiry,
            kill,
            activation,
            provider,
            self.now if db_now is None else db_now,
        )

    def factory_for(self, calls):
        conn = ScriptedConnection(calls)
        factory = ConnectionFactoryQueue([conn])
        store = PostgresDistributedControlStore(
            runtime_id=self.runtime_id,
            connection_factory=factory,
        )
        return store, conn, factory

    def assert_code(self, code, fn):
        with self.assertRaises(PostgresControlViolation) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, code)

    def test_acquire_uses_db_time_parameterized_sql_and_monotonic_fence(self):
        calls = [
            ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
            ExpectedCall(
                CONTROL_FOR_UPDATE_SQL,
                (self.runtime_id,),
                self.control_row(fence=2, expiry=self.now - timedelta(seconds=1)),
            ),
            ExpectedCall(
                ACQUIRE_LEASE_SQL,
                ("worker-a", "instance-a", 30, self.runtime_id),
                (3, self.expiry),
            ),
        ]
        store, conn, factory = self.factory_for(calls)
        grant = store.acquire_lease(self.identity, ttl_seconds=30)
        self.assertEqual(grant.fence_token, 3)
        self.assertEqual(grant.lease_expires_at, self.expiry)
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)
        self.assertTrue(conn.closed)
        self.assertTrue(conn.cursor_obj.closed)
        self.assertEqual(factory.calls, 1)
        self.assertEqual(conn.cursor_obj.expected, [])

    def test_held_lease_fails_closed_and_rolls_back(self):
        calls = [
            ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
            ExpectedCall(
                CONTROL_FOR_UPDATE_SQL,
                (self.runtime_id,),
                self.control_row(
                    owner_worker="worker-b",
                    owner_instance="instance-b",
                    fence=7,
                    expiry=self.now + timedelta(seconds=5),
                ),
            ),
        ]
        store, conn, _ = self.factory_for(calls)
        self.assert_code(
            "LEASE_HELD",
            lambda: store.acquire_lease(self.identity, ttl_seconds=30),
        )
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)
        self.assertTrue(conn.closed)

    def test_default_deny_flags_are_authority_preconditions(self):
        for kwargs, code in (
            ({"kill": False}, "KILL_SWITCH_NOT_ENGAGED"),
            ({"activation": True}, "ACTIVATION_BRIDGE_NOT_DISABLED"),
            ({"provider": True}, "PROVIDER_EFFECT_ADAPTER_NOT_DISABLED"),
        ):
            with self.subTest(code=code):
                calls = [
                    ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
                    ExpectedCall(
                        CONTROL_FOR_UPDATE_SQL,
                        (self.runtime_id,),
                        self.control_row(**kwargs),
                    ),
                ]
                store, conn, _ = self.factory_for(calls)
                self.assert_code(
                    code,
                    lambda: store.acquire_lease(self.identity, ttl_seconds=30),
                )
                self.assertEqual(conn.rollbacks, 1)

    def current_grant(self, fence=4):
        return PostgresLeaseGrant(
            runtime_id=self.runtime_id,
            worker_id="worker-a",
            instance_id="instance-a",
            fence_token=fence,
            lease_expires_at=self.expiry,
        )

    def current_lock_calls(self, fence=4):
        return [
            ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
            ExpectedCall(
                CONTROL_FOR_UPDATE_SQL,
                (self.runtime_id,),
                self.control_row(
                    owner_worker="worker-a",
                    owner_instance="instance-a",
                    fence=fence,
                    expiry=self.expiry,
                ),
            ),
        ]

    def test_renew_requires_exact_owner_instance_fence_and_expiry(self):
        calls = self.current_lock_calls() + [
            ExpectedCall(
                RENEW_LEASE_SQL,
                (20, self.runtime_id),
                (self.now + timedelta(seconds=20),),
            )
        ]
        store, conn, _ = self.factory_for(calls)
        renewed = store.renew_lease(
            self.identity,
            self.current_grant(),
            ttl_seconds=20,
        )
        self.assertEqual(renewed.fence_token, 4)
        self.assertEqual(
            renewed.lease_expires_at,
            self.now + timedelta(seconds=20),
        )
        self.assertEqual(conn.commits, 1)

    def test_stale_fence_and_expired_lease_rollback(self):
        cases = [
            (
                self.current_lock_calls(fence=5),
                self.current_grant(fence=4),
                "STALE_FENCE_TOKEN",
            ),
            (
                [
                    ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
                    ExpectedCall(
                        CONTROL_FOR_UPDATE_SQL,
                        (self.runtime_id,),
                        self.control_row(
                            owner_worker="worker-a",
                            owner_instance="instance-a",
                            fence=4,
                            expiry=self.expiry,
                            db_now=self.expiry,
                        ),
                    ),
                ],
                self.current_grant(),
                "LEASE_EXPIRED",
            ),
        ]
        for calls, grant, code in cases:
            with self.subTest(code=code):
                store, conn, _ = self.factory_for(calls)
                self.assert_code(
                    code,
                    lambda: store.assert_current(self.identity, grant),
                )
                self.assertEqual(conn.rollbacks, 1)

    def test_checkpoint_is_fence_bound_and_parameterized(self):
        calls = self.current_lock_calls() + [
            ExpectedCall(
                CHECKPOINT_UPSERT_SQL,
                (
                    self.runtime_id,
                    "scheduler:last_cycle",
                    '{"cursor":7}',
                    "worker-a",
                    "instance-a",
                    4,
                ),
            )
        ]
        store, conn, _ = self.factory_for(calls)
        record = store.checkpoint(
            self.identity,
            self.current_grant(),
            "scheduler:last_cycle",
            {"cursor": 7},
        )
        self.assertEqual(record.value, {"cursor": 7})
        self.assertEqual(record.fence_token, 4)
        self.assertEqual(conn.commits, 1)

    def test_checkpoint_read_round_trip_shape(self):
        calls = [
            ExpectedCall(
                CHECKPOINT_READ_SQL,
                (self.runtime_id, "scheduler:last_cycle"),
                ('{"cursor":7}', "worker-a", "instance-a", 4),
            )
        ]
        store, conn, _ = self.factory_for(calls)
        record = store.get_checkpoint("scheduler:last_cycle")
        self.assertIsNotNone(record)
        self.assertEqual(record.value, {"cursor": 7})
        self.assertEqual(conn.commits, 1)

    def test_idempotency_applied_duplicate_and_conflict(self):
        digest = PostgresDistributedControlStore.payload_digest({"x": 1})
        other = PostgresDistributedControlStore.payload_digest({"x": 2})

        applied_calls = self.current_lock_calls() + [
            ExpectedCall(
                OPERATION_INSERT_SQL,
                (self.runtime_id, "req-1", digest, "worker-a", 4),
                (digest, "worker-a", 4),
            )
        ]
        store, _, _ = self.factory_for(applied_calls)
        applied = store.reserve_operation(
            self.identity,
            self.current_grant(),
            "req-1",
            digest,
        )
        self.assertTrue(applied.applied)
        self.assertFalse(applied.duplicate)

        duplicate_calls = self.current_lock_calls() + [
            ExpectedCall(
                OPERATION_INSERT_SQL,
                (self.runtime_id, "req-1", digest, "worker-a", 4),
                None,
            ),
            ExpectedCall(
                OPERATION_READ_SQL,
                (self.runtime_id, "req-1"),
                (digest, "worker-b", 3),
            ),
        ]
        store, _, _ = self.factory_for(duplicate_calls)
        duplicate = store.reserve_operation(
            self.identity,
            self.current_grant(),
            "req-1",
            digest,
        )
        self.assertFalse(duplicate.applied)
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(duplicate.applied_by, "worker-b")
        self.assertEqual(duplicate.fence_token, 3)

        conflict_calls = self.current_lock_calls() + [
            ExpectedCall(
                OPERATION_INSERT_SQL,
                (self.runtime_id, "req-1", other, "worker-a", 4),
                None,
            ),
            ExpectedCall(
                OPERATION_READ_SQL,
                (self.runtime_id, "req-1"),
                (digest, "worker-b", 3),
            ),
        ]
        store, conn, _ = self.factory_for(conflict_calls)
        self.assert_code(
            "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
            lambda: store.reserve_operation(
                self.identity,
                self.current_grant(),
                "req-1",
                other,
            ),
        )
        self.assertEqual(conn.rollbacks, 1)

    def test_bridge_never_reports_ready_or_external_effect(self):
        acquire_calls = [
            ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
            ExpectedCall(
                CONTROL_FOR_UPDATE_SQL,
                (self.runtime_id,),
                self.control_row(),
            ),
            ExpectedCall(
                ACQUIRE_LEASE_SQL,
                ("worker-a", "instance-a", 30, self.runtime_id),
                (1, self.expiry),
            ),
        ]
        idempotency_calls = [
            ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
            ExpectedCall(
                CONTROL_FOR_UPDATE_SQL,
                (self.runtime_id,),
                self.control_row(
                    owner_worker="worker-a",
                    owner_instance="instance-a",
                    fence=1,
                    expiry=self.expiry,
                ),
            ),
            ExpectedCall(
                OPERATION_INSERT_SQL,
                (
                    self.runtime_id,
                    "req-1",
                    PostgresDistributedControlStore.payload_digest({"x": 1}),
                    "worker-a",
                    1,
                ),
                (
                    PostgresDistributedControlStore.payload_digest({"x": 1}),
                    "worker-a",
                    1,
                ),
            ),
        ]
        readiness_calls = [
            ExpectedCall(ENSURE_CONTROL_SQL, (self.runtime_id,)),
            ExpectedCall(
                CONTROL_FOR_UPDATE_SQL,
                (self.runtime_id,),
                self.control_row(
                    owner_worker="worker-a",
                    owner_instance="instance-a",
                    fence=1,
                    expiry=self.expiry,
                ),
            ),
        ]

        connections = [
            ScriptedConnection(acquire_calls),
            ScriptedConnection(idempotency_calls),
            ScriptedConnection(readiness_calls),
        ]
        factory = ConnectionFactoryQueue(connections)
        store = PostgresDistributedControlStore(
            runtime_id=self.runtime_id,
            connection_factory=factory,
        )
        bridge = PreparedPostgresRuntimeBridge(store)
        session = bridge.prepare_session("worker-a", "instance-a")
        op = bridge.reserve_inert_operation(session, "req-1", {"x": 1})
        readiness = bridge.readiness(session)
        self.assertFalse(op["external_effect_executed"])
        self.assertTrue(readiness["current_lease"])
        self.assertFalse(readiness["ready"])
        self.assertFalse(readiness["activation_ready"])
        self.assertTrue(readiness["kill_switch_engaged"])
        self.assertFalse(readiness["provider_effect_adapter_enabled"])
        self.assertFalse(readiness["runtime_activation_bridge_enabled"])
        self.assertEqual(readiness["runtime"], "OFF")

    def test_validator(self):
        result = validate()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["runtime"], "OFF")


if __name__ == "__main__":
    unittest.main()
