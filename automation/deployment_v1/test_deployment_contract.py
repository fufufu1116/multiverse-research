import json
import tempfile
import unittest
from pathlib import Path

from deployment_contract import (
    ADOPTED_RUNTIME_HEAD,
    CANONICAL_MAIN,
    DEFAULT_DENY_CAPABILITIES,
    DeploymentGateError,
    DeploymentManifest,
    MODE,
    RUNTIME,
    TARGET_ENVIRONMENT,
    health_receipt,
    restore_bytes,
    snapshot_bytes,
)


class DeploymentContractTests(unittest.TestCase):
    def manifest(self, **overrides):
        values = {
            "adopted_runtime_head": ADOPTED_RUNTIME_HEAD,
            "canonical_main": CANONICAL_MAIN,
            "mode": MODE,
            "runtime": RUNTIME,
            "target_environment": TARGET_ENVIRONMENT,
            "artifact_sha256": "a" * 64,
            "rollback_ref": ADOPTED_RUNTIME_HEAD,
            "credential_source": "INJECTED_EPHEMERAL_ONLY",
            "credential_persistence": False,
            "capabilities": dict(DEFAULT_DENY_CAPABILITIES),
        }
        values.update(overrides)
        return DeploymentManifest(**values)

    def test_exact_manifest_passes(self):
        receipt = self.manifest().receipt()
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["runtime"], "OFF")
        self.assertTrue(all(v is False for v in receipt["capabilities"].values()))

    def test_any_capability_enable_fails_closed(self):
        caps = dict(DEFAULT_DENY_CAPABILITIES)
        caps["network"] = True
        with self.assertRaisesRegex(DeploymentGateError, "CAPABILITY_DEFAULT_DENY_REQUIRED"):
            self.manifest(capabilities=caps).validate()

    def test_secret_persistence_fails_closed(self):
        with self.assertRaisesRegex(DeploymentGateError, "SECRET_PERSISTENCE_FORBIDDEN"):
            self.manifest(credential_persistence=True).validate()

    def test_wrong_lineage_fails_closed(self):
        with self.assertRaisesRegex(DeploymentGateError, "ADOPTED_RUNTIME_HEAD_MISMATCH"):
            self.manifest(adopted_runtime_head="0" * 40).validate()

    def test_rollback_must_bind_adopted_head(self):
        with self.assertRaisesRegex(DeploymentGateError, "ROLLBACK_BINDING_REQUIRED"):
            self.manifest(rollback_ref="0" * 40).validate()

    def test_kill_switch_must_stay_engaged(self):
        with self.assertRaisesRegex(DeploymentGateError, "KILL_SWITCH_MUST_REMAIN_ENGAGED"):
            health_receipt(self.manifest(), kill_switch_engaged=False)

    def test_health_is_explicitly_not_live_ready(self):
        receipt = health_receipt(self.manifest(), kill_switch_engaged=True)
        self.assertFalse(receipt["ready_for_live_activation"])
        self.assertEqual(receipt["runtime"], "OFF")

    def test_snapshot_restore_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "state.db"
            snap = root / "state.snapshot"
            restored = root / "state.restored"
            source.write_bytes(b"sealed-state-v1\x00\x01")
            s = snapshot_bytes(source, snap)
            r = restore_bytes(snap, restored)
            self.assertEqual(s["source_sha256"], s["snapshot_sha256"])
            self.assertEqual(r["snapshot_sha256"], r["restored_sha256"])
            self.assertEqual(source.read_bytes(), restored.read_bytes())


if __name__ == "__main__":
    unittest.main()
