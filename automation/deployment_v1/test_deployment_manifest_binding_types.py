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
    restore_bytes,
    sha256_file,
    snapshot_bytes,
)


class _AlwaysEqual:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class _AlwaysEqualStr(str):
    __hash__ = str.__hash__

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class _HashCompatibleKey:
    def __hash__(self):
        return hash("production")

    def __eq__(self, other):
        return other == "production"


class _HashCompatibleReceiptKey:
    def __init__(self, target):
        self.target = target

    def __hash__(self):
        return hash(self.target)

    def __eq__(self, other):
        return other == self.target


class DeploymentManifestBindingTypeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "deployment.artifact"
        self.rollback_artifact = self.root / "rollback.artifact"
        self.artifact.write_bytes(b"sealed-deployment-artifact-v1")
        self.rollback_artifact.write_bytes(b"sealed-runtime-rollback-artifact-v1")

    def tearDown(self):
        self.tmp.cleanup()

    def manifest(self, **overrides):
        values = {
            "adopted_runtime_head": ADOPTED_RUNTIME_HEAD,
            "canonical_main": CANONICAL_MAIN,
            "mode": MODE,
            "runtime": RUNTIME,
            "target_environment": TARGET_ENVIRONMENT,
            "artifact_sha256": sha256_file(self.artifact),
            "rollback_ref": ADOPTED_RUNTIME_HEAD,
            "rollback_artifact_sha256": sha256_file(self.rollback_artifact),
            "credential_source": "INJECTED_EPHEMERAL_ONLY",
            "credential_persistence": False,
            "capabilities": dict(DEFAULT_DENY_CAPABILITIES),
        }
        values.update(overrides)
        return DeploymentManifest(**values)

    def validate(self, manifest):
        manifest.validate(
            artifact_path=self.artifact,
            rollback_artifact_path=self.rollback_artifact,
        )

    def test_authority_binding_fields_reject_custom_equality_and_str_subclasses(self):
        cases = (
            ("adopted_runtime_head", ADOPTED_RUNTIME_HEAD, "ADOPTED_RUNTIME_HEAD_MISMATCH"),
            ("canonical_main", CANONICAL_MAIN, "CANONICAL_MAIN_MISMATCH"),
            ("mode", MODE, "SEALED_MODE_REQUIRED"),
            ("runtime", RUNTIME, "SEALED_MODE_REQUIRED"),
            ("target_environment", TARGET_ENVIRONMENT, "TARGET_ENVIRONMENT_MISMATCH"),
            ("credential_source", "INJECTED_EPHEMERAL_ONLY", "EPHEMERAL_CREDENTIAL_INJECTION_REQUIRED"),
            ("rollback_ref", ADOPTED_RUNTIME_HEAD, "ROLLBACK_BINDING_REQUIRED"),
        )
        for field, exact_value, error in cases:
            for bad_value in (_AlwaysEqual(), _AlwaysEqualStr(exact_value)):
                with self.subTest(field=field, value=type(bad_value).__name__):
                    with self.assertRaisesRegex(DeploymentGateError, error):
                        self.validate(self.manifest(**{field: bad_value}))

    def test_authority_binding_fields_reject_wrong_runtime_types(self):
        cases = (
            ("adopted_runtime_head", "ADOPTED_RUNTIME_HEAD_MISMATCH"),
            ("canonical_main", "CANONICAL_MAIN_MISMATCH"),
            ("mode", "SEALED_MODE_REQUIRED"),
            ("runtime", "SEALED_MODE_REQUIRED"),
            ("target_environment", "TARGET_ENVIRONMENT_MISMATCH"),
            ("credential_source", "EPHEMERAL_CREDENTIAL_INJECTION_REQUIRED"),
            ("rollback_ref", "ROLLBACK_BINDING_REQUIRED"),
        )
        for field, error in cases:
            for bad_value in (False, 0, 0.0, None, b"x", [], {}, ()):
                with self.subTest(field=field, value=bad_value):
                    with self.assertRaisesRegex(DeploymentGateError, error):
                        self.validate(self.manifest(**{field: bad_value}))

    def test_wrong_normal_strings_still_fail_closed(self):
        cases = (
            ("adopted_runtime_head", "0" * 40, "ADOPTED_RUNTIME_HEAD_MISMATCH"),
            ("canonical_main", "0" * 40, "CANONICAL_MAIN_MISMATCH"),
            ("mode", "WRONG", "SEALED_MODE_REQUIRED"),
            ("runtime", "ON", "SEALED_MODE_REQUIRED"),
            ("target_environment", "PRODUCTION", "TARGET_ENVIRONMENT_MISMATCH"),
            ("credential_source", "PERSISTED", "EPHEMERAL_CREDENTIAL_INJECTION_REQUIRED"),
            ("rollback_ref", "0" * 40, "ROLLBACK_BINDING_REQUIRED"),
        )
        for field, bad_value, error in cases:
            with self.subTest(field=field):
                with self.assertRaisesRegex(DeploymentGateError, error):
                    self.validate(self.manifest(**{field: bad_value}))

    def test_capability_keys_reject_str_subclasses(self):
        capabilities = dict(DEFAULT_DENY_CAPABILITIES)
        capabilities.pop("production")
        capabilities[_AlwaysEqualStr("production")] = False
        with self.assertRaisesRegex(DeploymentGateError, "CAPABILITY_DEFAULT_DENY_REQUIRED"):
            self.validate(self.manifest(capabilities=capabilities))

    def test_capability_keys_reject_equality_hash_compatible_objects(self):
        capabilities = dict(DEFAULT_DENY_CAPABILITIES)
        capabilities.pop("production")
        capabilities[_HashCompatibleKey()] = False
        with self.assertRaisesRegex(DeploymentGateError, "CAPABILITY_DEFAULT_DENY_REQUIRED"):
            self.validate(self.manifest(capabilities=capabilities))

    def test_snapshot_receipt_keys_reject_str_subclasses_before_kwarg_binding(self):
        source = self.root / "state.db"
        snapshot = self.root / "state.snapshot"
        restored = self.root / "state.restored"
        source.write_bytes(b"sealed-runtime-state")
        receipt = snapshot_bytes(source, snapshot, snapshot_identity="runtime-state-primary")
        value = receipt.pop("snapshot_identity")
        receipt[_AlwaysEqualStr("snapshot_identity")] = value
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_RECEIPT_INVALID"):
            restore_bytes(
                snapshot,
                restored,
                expected_receipt=receipt,
                expected_identity="runtime-state-primary",
            )

    def test_snapshot_receipt_keys_reject_equality_hash_compatible_objects_before_kwarg_binding(self):
        source = self.root / "state.db"
        snapshot = self.root / "state.snapshot"
        restored = self.root / "state.restored"
        source.write_bytes(b"sealed-runtime-state")
        receipt = snapshot_bytes(source, snapshot, snapshot_identity="runtime-state-primary")
        value = receipt.pop("snapshot_identity")
        receipt[_HashCompatibleReceiptKey("snapshot_identity")] = value
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_RECEIPT_INVALID"):
            restore_bytes(
                snapshot,
                restored,
                expected_receipt=receipt,
                expected_identity="runtime-state-primary",
            )

    def test_exact_snapshot_receipt_still_restores_after_key_type_hardening(self):
        source = self.root / "state.db"
        snapshot = self.root / "state.snapshot"
        restored = self.root / "state.restored"
        source.write_bytes(b"sealed-runtime-state")
        receipt = snapshot_bytes(source, snapshot, snapshot_identity="runtime-state-primary")
        result = restore_bytes(
            snapshot,
            restored,
            expected_receipt=receipt,
            expected_identity="runtime-state-primary",
        )
        self.assertEqual(result["integrity"], "PASS")
        self.assertEqual(restored.read_bytes(), source.read_bytes())

    def test_exact_manifest_still_passes_after_type_hardening(self):
        self.validate(self.manifest())


if __name__ == "__main__":
    unittest.main()
