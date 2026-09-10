from __future__ import annotations

import unittest

try:
    from .activation_integration_validator import validate
    from .distributed_control import ControlViolation, MemoryDistributedControlStore, RuntimeIdentity
    from .runtime_activation_bridge import PreparedRuntimeActivationBridge
except ImportError:  # direct discovery from this directory
    from activation_integration_validator import validate
    from distributed_control import ControlViolation, MemoryDistributedControlStore, RuntimeIdentity
    from runtime_activation_bridge import PreparedRuntimeActivationBridge


class Clock:
    def __init__(self, value: float = 1000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class RuntimeActivationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = Clock()
        self.store = MemoryDistributedControlStore(clock=self.clock)
        self.bridge = PreparedRuntimeActivationBridge(self.store)

    def assert_code(self, code: str, fn) -> None:
        with self.assertRaises(ControlViolation) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, code)

    def test_fence_progression_stale_owner_and_restart_successor(self) -> None:
        a1 = self.bridge.prepare_session("worker-a", "instance-a1", ttl_seconds=10)
        self.assertEqual(a1.lease.fence_token, 1)
        self.assert_code("LEASE_HELD", lambda: self.bridge.prepare_session("worker-b", "instance-b1", ttl_seconds=10))
        self.clock.advance(10)
        b1 = self.bridge.prepare_session("worker-b", "instance-b1", ttl_seconds=10)
        self.assertEqual(b1.lease.fence_token, 2)
        self.assert_code("STALE_OWNER", lambda: self.store.assert_current(a1.identity, a1.lease))
        self.clock.advance(10)
        a2 = self.bridge.prepare_session("worker-a", "instance-a2", ttl_seconds=10)
        self.assertEqual(a2.lease.fence_token, 3)
        self.assertNotEqual(a1.identity.instance_id, a2.identity.instance_id)

    def test_stale_fence_and_identity_grant_mismatch_fail_closed(self) -> None:
        a = self.bridge.prepare_session("worker-a", "instance-a", ttl_seconds=30)
        wrong_identity = RuntimeIdentity("worker-b", "instance-b")
        self.assert_code("STALE_OWNER", lambda: self.store.assert_current(wrong_identity, a.lease))
        from dataclasses import replace
        stale = replace(a.lease, fence_token=a.lease.fence_token - 1)
        self.assert_code("STALE_FENCE_TOKEN", lambda: self.store.assert_current(a.identity, stale))

    def test_idempotency_duplicate_and_conflict(self) -> None:
        a = self.bridge.prepare_session("worker-a", "instance-a", ttl_seconds=30)
        first = self.bridge.reserve_inert_operation(a, "request-1", {"x": 1})
        duplicate = self.bridge.reserve_inert_operation(a, "request-1", {"x": 1})
        self.assertTrue(first["applied"])
        self.assertFalse(first["external_effect_executed"])
        self.assertTrue(duplicate["duplicate"])
        self.assertFalse(duplicate["external_effect_executed"])
        self.assert_code(
            "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
            lambda: self.bridge.reserve_inert_operation(a, "request-1", {"x": 2}),
        )
        self.assertEqual(self.store.snapshot()["operation_count"], 1)

    def test_checkpoint_is_fence_bound_and_resume_visible_to_successor(self) -> None:
        a1 = self.bridge.prepare_session("worker-a", "instance-a1", ttl_seconds=5)
        written = self.bridge.checkpoint(a1, "scheduler:last_cycle", {"cursor": 7})
        self.assertEqual(written["fence_token"], 1)
        self.clock.advance(5)
        b1 = self.bridge.prepare_session("worker-b", "instance-b1", ttl_seconds=5)
        self.assert_code(
            "STALE_OWNER",
            lambda: self.bridge.checkpoint(a1, "scheduler:last_cycle", {"cursor": 8}),
        )
        prior = self.store.get_checkpoint("scheduler:last_cycle")
        self.assertIsNotNone(prior)
        self.assertEqual(prior.value, {"cursor": 7})
        resumed = self.bridge.checkpoint(b1, "scheduler:last_cycle", {"cursor": 8, "resumed_from": 7})
        self.assertEqual(resumed["fence_token"], 2)

    def test_readiness_remains_false_even_with_current_lease(self) -> None:
        a = self.bridge.prepare_session("worker-a", "instance-a", ttl_seconds=30)
        readiness = self.bridge.readiness(a)
        self.assertTrue(readiness["current_lease"])
        self.assertTrue(readiness["kill_switch_engaged"])
        self.assertFalse(readiness["provider_effect_adapter_enabled"])
        self.assertFalse(readiness["runtime_activation_bridge_enabled"])
        self.assertFalse(readiness["activation_ready"])
        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["runtime"], "OFF")

    def test_contract_validator(self) -> None:
        result = validate()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["runtime"], "OFF")


if __name__ == "__main__":
    unittest.main()
