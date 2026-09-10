from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from automation.postgres_runtime_bridge_preprod_v1 import app
from automation.postgres_runtime_bridge_preprod_v1 import bridge_validation as bv
from automation.postgres_runtime_bridge_preprod_v1.validator import validate
from automation.runtime_postgres_adapter_v1.postgres_adapter import PostgresControlViolation

ROOT = Path(__file__).resolve().parent


class FakeCheckpoint:
    def __init__(self, value):
        self.value = value


class FakeStore:
    def __init__(self):
        self.records = {"bridge:last_cycle": FakeCheckpoint({"cursor": 1})}
        self.final = None

    def get_checkpoint(self, key):
        if key == bv.FINAL_EVIDENCE_CHECKPOINT:
            return self.final
        return self.records.get(key)


class FakeBridge:
    def __init__(self, store):
        self.store = store
        self.op_calls = 0

    def prepare_session(self, worker_id, instance_id, *, ttl_seconds=30):
        fence = 1 if worker_id.endswith("-a") else 2
        return SimpleNamespace(
            identity=SimpleNamespace(worker_id=worker_id, instance_id=instance_id),
            lease=SimpleNamespace(fence_token=fence),
        )

    def renew_session(self, session, *, ttl_seconds=30):
        raise PostgresControlViolation("STALE_OWNER")

    def checkpoint(self, session, key, value):
        if key == bv.FINAL_EVIDENCE_CHECKPOINT:
            self.store.final = FakeCheckpoint(dict(value))
        return {
            "checkpoint_key": key,
            "value": value,
            "worker_id": session.identity.worker_id,
            "instance_id": session.identity.instance_id,
            "fence_token": session.lease.fence_token,
        }

    def reserve_inert_operation(self, session, request_key, payload):
        if payload == bv.CONFLICT_PAYLOAD:
            raise PostgresControlViolation("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")
        self.op_calls += 1
        first = self.op_calls == 1
        return {
            "applied": first,
            "duplicate": not first,
            "request_key": request_key,
            "payload_sha256": "digest",
            "applied_by": session.identity.worker_id,
            "fence_token": session.lease.fence_token,
            "external_effect_executed": False,
        }

    def readiness(self, session):
        return {
            "runtime": "OFF",
            "kill_switch_engaged": True,
            "provider_effect_adapter_enabled": False,
            "runtime_activation_bridge_enabled": False,
            "activation_ready": False,
            "ready": False,
        }


class PreparationTests(unittest.TestCase):
    def exact_env(self):
        return {
            "MULTIVERSE_TARGET_CLASS": app.TARGET_CLASS,
            "MULTIVERSE_ENVIRONMENT_CLASS": app.ENVIRONMENT_CLASS,
            "MULTIVERSE_POSTGRES_RUNTIME_BRIDGE_EXECUTION_AUTHORITY": app.EXECUTION_AUTHORITY,
            "MULTIVERSE_RUNTIME": "OFF",
            "MULTIVERSE_RUNTIME_ACTIVATION_BRIDGE_ENABLED": "false",
            "MULTIVERSE_PROVIDER_EFFECT_ADAPTER_ENABLED": "false",
            "MULTIVERSE_LIVE_BUSINESS_EFFECT": "false",
            "MULTIVERSE_PROTECTED_KEIRIN_DATA": "false",
            "MULTIVERSE_PRODUCTION_CREDENTIALS": "false",
            "MULTIVERSE_INCREMENTAL_SPEND_USD": "0",
            "MULTIVERSE_EXPECTED_POSTGRES_ID": app.EXPECTED_POSTGRES_ID,
            "MULTIVERSE_RUNTIME_ID": bv.RUNTIME_ID,
        }

    def test_01_contract_is_fail_closed(self):
        contract = json.loads(
            (ROOT / "BRIDGE_VALIDATION_PREPARATION_CONTRACT_v1.json").read_text()
        )
        self.assertEqual(
            contract["proof_ceiling"],
            "POSTGRES_RUNTIME_BRIDGE_PREPRODUCTION_VALIDATION_PREPARATION_ONLY",
        )
        self.assertEqual(
            contract["execution_state"],
            "BRIDGE_REMOTE_VALIDATION_NOT_AUTHORIZED",
        )
        self.assertFalse(contract["remote_postgres_execution"])
        self.assertFalse(contract["runtime_activation_bridge_enabled"])
        self.assertFalse(contract["provider_effect_adapter_enabled"])
        self.assertFalse(contract["activation_ready"])
        self.assertEqual(contract["runtime"], "OFF")

    def test_02_environment_accepts_exact_and_rejects_drift(self):
        env = self.exact_env()
        self.assertEqual(app.validate_nonsecret_environment(env), env)

        bad = dict(env)
        bad["MULTIVERSE_RUNTIME"] = "ON"
        with self.assertRaises(app.BridgeExecutionViolation):
            app.validate_nonsecret_environment(bad)

        missing = dict(env)
        del missing["MULTIVERSE_POSTGRES_RUNTIME_BRIDGE_EXECUTION_AUTHORITY"]
        with self.assertRaises(app.BridgeExecutionViolation):
            app.validate_nonsecret_environment(missing)

    def test_03_psycopg_import_is_nested_only_in_connection_factory(self):
        source = (ROOT / "app.py").read_text()
        parsed = ast.parse(source)
        locations = []

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.stack = []

            def visit_FunctionDef(self, node):
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name == "psycopg":
                        locations.append(tuple(self.stack))
                self.generic_visit(node)

        Visitor().visit(parsed)
        self.assertEqual(locations, [("build_connection_factory",)])

    def test_04_http_surface_is_get_only_and_mutations_denied(self):
        source = (ROOT / "app.py").read_text()
        for token in (
            'self.path == "/health"',
            'self.path == "/ready"',
            'self.path == "/evidence"',
            "def do_POST",
            "def do_PUT",
            "def do_PATCH",
            "def do_DELETE",
            "state_changes_disabled_over_http",
        ):
            self.assertIn(token, source)

    def test_05_bridge_orchestration_happy_path_is_no_effect(self):
        store = FakeStore()
        with patch.object(bv, "PreparedPostgresRuntimeBridge", FakeBridge):
            evidence = bv.run_bridge_validation(store, sleeper=lambda _: None)

        self.assertTrue(evidence["complete"])
        self.assertEqual(evidence["bridge_class"], "PreparedPostgresRuntimeBridge")
        self.assertEqual(evidence["lease"]["worker_a_fence"], 1)
        self.assertEqual(evidence["lease"]["worker_b_fence"], 2)
        self.assertTrue(evidence["lease"]["fence_increased"])
        self.assertTrue(evidence["lease"]["stale_owner_rejected"])
        self.assertTrue(evidence["checkpoint"]["resume_visible"])
        self.assertFalse(evidence["idempotency"]["external_effect_executed"])
        self.assertFalse(evidence["readiness"]["runtime_activation_bridge_enabled"])
        self.assertFalse(evidence["readiness"]["activation_ready"])
        self.assertEqual(evidence["runtime"], "OFF")

    def test_06_restart_recovery_returns_checkpoint_without_bridge_replay(self):
        store = FakeStore()
        store.final = FakeCheckpoint(
            {"complete": True, "runtime": "OFF", "recovered_after_restart": False}
        )

        class ShouldNotConstruct:
            def __init__(self, store):
                raise AssertionError("BRIDGE_REPLAYED")

        with patch.object(bv, "PreparedPostgresRuntimeBridge", ShouldNotConstruct):
            evidence = bv.run_bridge_validation(store, sleeper=lambda _: None)

        self.assertTrue(evidence["complete"])
        self.assertTrue(evidence["recovered_after_restart"])

    def test_07_state_changes_route_through_bridge(self):
        source = (ROOT / "bridge_validation.py").read_text()
        for token in (
            "PreparedPostgresRuntimeBridge",
            "bridge.prepare_session",
            "bridge.renew_session",
            "bridge.checkpoint",
            "bridge.reserve_inert_operation",
            "bridge.readiness",
        ):
            self.assertIn(token, source)

        self.assertNotIn("store.acquire_lease(", source)
        self.assertNotIn("store.renew_lease(", source)
        self.assertNotIn("store.reserve_operation(", source)
        self.assertNotIn("store.checkpoint(", source)

    def test_08_validator_passes(self):
        result = validate()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["remote_postgres_execution"])
        self.assertFalse(result["runtime_activation_bridge_enabled"])
        self.assertFalse(result["activation_ready"])
        self.assertEqual(result["runtime"], "OFF")


if __name__ == "__main__":
    unittest.main()
