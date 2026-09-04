import copy
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
    sha256_file,
    snapshot_bytes,
)


class _AlwaysEqual:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class _AlwaysEqualStr(str):
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


class DeploymentContractTests(unittest.TestCase):
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

    def validate(self, manifest=None):
        (manifest or self.manifest()).validate(
            artifact_path=self.artifact,
            rollback_artifact_path=self.rollback_artifact,
        )

    def test_exact_manifest_passes(self):
        receipt = self.manifest().receipt(
            artifact_path=self.artifact,
            rollback_artifact_path=self.rollback_artifact,
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["runtime"], "OFF")
        self.assertTrue(all(v is False for v in receipt["capabilities"].values()))

    def test_any_capability_enable_fails_closed(self):
        caps = dict(DEFAULT_DENY_CAPABILITIES)
        caps["network"] = True
        with self.assertRaisesRegex(DeploymentGateError, "CAPABILITY_DEFAULT_DENY_REQUIRED"):
            self.validate(self.manifest(capabilities=caps))

    def test_capability_numeric_and_wrong_type_confusion_fails_closed(self):
        for bad_value in (0, 0.0, None, "false", [], {}):
            with self.subTest(value=bad_value):
                caps = dict(DEFAULT_DENY_CAPABILITIES)
                caps["network"] = bad_value
                with self.assertRaisesRegex(DeploymentGateError, "CAPABILITY_DEFAULT_DENY_REQUIRED"):
                    self.validate(self.manifest(capabilities=caps))

    def test_capability_missing_extra_and_non_dict_fails_closed(self):
        missing = dict(DEFAULT_DENY_CAPABILITIES)
        missing.pop("network")
        extra = dict(DEFAULT_DENY_CAPABILITIES)
        extra["unknown"] = False
        for caps in (missing, extra, [], None):
            with self.subTest(caps=caps):
                with self.assertRaisesRegex(DeploymentGateError, "CAPABILITY_DEFAULT_DENY_REQUIRED"):
                    self.validate(self.manifest(capabilities=caps))

    def test_secret_persistence_fails_closed(self):
        with self.assertRaisesRegex(DeploymentGateError, "SECRET_PERSISTENCE_FORBIDDEN"):
            self.validate(self.manifest(credential_persistence=True))

    def test_wrong_lineage_fails_closed(self):
        with self.assertRaisesRegex(DeploymentGateError, "ADOPTED_RUNTIME_HEAD_MISMATCH"):
            self.validate(self.manifest(adopted_runtime_head="0" * 40))

    def test_rollback_ref_must_bind_adopted_head(self):
        with self.assertRaisesRegex(DeploymentGateError, "ROLLBACK_BINDING_REQUIRED"):
            self.validate(self.manifest(rollback_ref="0" * 40))

    def test_valid_looking_wrong_artifact_digest_fails_closed(self):
        with self.assertRaisesRegex(DeploymentGateError, "DEPLOYMENT_ARTIFACT_DIGEST_MISMATCH"):
            self.validate(self.manifest(artifact_sha256="0" * 64))

    def test_artifact_mutation_after_manifest_freeze_fails_closed(self):
        manifest = self.manifest()
        self.artifact.write_bytes(b"tampered")
        with self.assertRaisesRegex(DeploymentGateError, "DEPLOYMENT_ARTIFACT_DIGEST_MISMATCH"):
            self.validate(manifest)

    def test_rollback_artifact_digest_tamper_fails_closed(self):
        with self.assertRaisesRegex(DeploymentGateError, "ROLLBACK_ARTIFACT_DIGEST_MISMATCH"):
            self.validate(self.manifest(rollback_artifact_sha256="f" * 64))

    def test_rollback_artifact_mutation_fails_closed(self):
        manifest = self.manifest()
        self.rollback_artifact.write_bytes(b"tampered rollback")
        with self.assertRaisesRegex(DeploymentGateError, "ROLLBACK_ARTIFACT_DIGEST_MISMATCH"):
            self.validate(manifest)

    def test_kill_switch_must_stay_engaged(self):
        with self.assertRaisesRegex(DeploymentGateError, "KILL_SWITCH_MUST_REMAIN_ENGAGED"):
            health_receipt(
                self.manifest(),
                kill_switch_engaged=False,
                artifact_path=self.artifact,
                rollback_artifact_path=self.rollback_artifact,
            )

    def test_health_is_explicitly_not_live_ready(self):
        receipt = health_receipt(
            self.manifest(),
            kill_switch_engaged=True,
            artifact_path=self.artifact,
            rollback_artifact_path=self.rollback_artifact,
        )
        self.assertFalse(receipt["ready_for_live_activation"])
        self.assertEqual(receipt["runtime"], "OFF")

    def snapshot_fixture(self):
        source = self.root / "state.db"
        snap = self.root / "state.snapshot"
        restored = self.root / "state.restored"
        source.write_bytes(b"sealed-state-v1\x00\x01")
        receipt = snapshot_bytes(source, snap, snapshot_identity="runtime-state-primary")
        return source, snap, restored, receipt

    def test_snapshot_restore_integrity(self):
        source, snap, restored, receipt = self.snapshot_fixture()
        result = restore_bytes(
            snap,
            restored,
            expected_receipt=receipt,
            expected_identity="runtime-state-primary",
        )
        self.assertEqual(result["integrity"], "PASS")
        self.assertEqual(source.read_bytes(), restored.read_bytes())

    def test_corrupted_snapshot_fails_before_restore_write(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        snap.write_bytes(b"corrupt")
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_DIGEST_MISMATCH"):
            restore_bytes(
                snap,
                restored,
                expected_receipt=receipt,
                expected_identity="runtime-state-primary",
            )
        self.assertFalse(restored.exists())

    def test_truncated_snapshot_fails_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        snap.write_bytes(snap.read_bytes()[:-1])
        with self.assertRaises(DeploymentGateError):
            restore_bytes(
                snap,
                restored,
                expected_receipt=receipt,
                expected_identity="runtime-state-primary",
            )

    def test_wrong_snapshot_identity_fails_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_IDENTITY_MISMATCH"):
            restore_bytes(
                snap,
                restored,
                expected_receipt=receipt,
                expected_identity="other-state",
            )

    def test_wrong_snapshot_schema_fails_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        bad = copy.deepcopy(receipt)
        bad["schema_version"] = "WRONG"
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_SCHEMA_MISMATCH"):
            restore_bytes(
                snap,
                restored,
                expected_receipt=bad,
                expected_identity="runtime-state-primary",
            )

    def test_wrong_snapshot_runtime_head_fails_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        bad = copy.deepcopy(receipt)
        bad["adopted_runtime_head"] = "0" * 40
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_RUNTIME_HEAD_MISMATCH"):
            restore_bytes(
                snap,
                restored,
                expected_receipt=bad,
                expected_identity="runtime-state-primary",
            )

    def test_wrong_snapshot_main_fails_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        bad = copy.deepcopy(receipt)
        bad["canonical_main"] = "0" * 40
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_MAIN_MISMATCH"):
            restore_bytes(
                snap,
                restored,
                expected_receipt=bad,
                expected_identity="runtime-state-primary",
            )

    def test_snapshot_byte_length_wrong_types_fail_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        for bad_value in (False, True, 1.0, "1", None):
            with self.subTest(value=bad_value):
                bad = copy.deepcopy(receipt)
                bad["byte_length"] = bad_value
                with self.assertRaises(DeploymentGateError):
                    restore_bytes(
                        snap,
                        restored,
                        expected_receipt=bad,
                        expected_identity="runtime-state-primary",
                    )

    def test_snapshot_string_field_wrong_types_fail_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        for field in (
            "schema_version",
            "snapshot_identity",
            "adopted_runtime_head",
            "canonical_main",
            "source_sha256",
            "snapshot_sha256",
        ):
            for bad_value in (False, 0, 0.0, None, b"x"):
                with self.subTest(field=field, value=bad_value):
                    bad = copy.deepcopy(receipt)
                    bad[field] = bad_value
                    with self.assertRaises(DeploymentGateError):
                        restore_bytes(
                            snap,
                            restored,
                            expected_receipt=bad,
                            expected_identity="runtime-state-primary",
                        )

    def test_snapshot_receipt_missing_extra_and_non_dict_fails_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        missing = copy.deepcopy(receipt)
        missing.pop("byte_length")
        extra = copy.deepcopy(receipt)
        extra["unexpected"] = "field"
        for bad in (missing, extra, None, []):
            with self.subTest(receipt=bad):
                with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_RECEIPT_INVALID"):
                    restore_bytes(
                        snap,
                        restored,
                        expected_receipt=bad,
                        expected_identity="runtime-state-primary",
                    )

    def test_expected_snapshot_identity_argument_types_fail_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        bad_values = (
            False,
            0,
            0.0,
            None,
            b"x",
            [],
            {},
            _AlwaysEqual(),
            _AlwaysEqualStr("runtime-state-primary"),
            "",
            " runtime-state-primary",
            "runtime-state-primary ",
        )
        for bad_value in bad_values:
            with self.subTest(value=bad_value):
                with self.assertRaisesRegex(
                    DeploymentGateError,
                    "SNAPSHOT_EXPECTED_IDENTITY_INVALID",
                ):
                    restore_bytes(
                        snap,
                        restored,
                        expected_receipt=receipt,
                        expected_identity=bad_value,
                    )
                self.assertFalse(restored.exists())

    def test_expected_runtime_and_main_argument_types_fail_closed(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        cases = (
            (
                "expected_runtime_head",
                "SNAPSHOT_EXPECTED_RUNTIME_HEAD_INVALID",
                "0" * 40,
                ADOPTED_RUNTIME_HEAD,
            ),
            (
                "expected_main",
                "SNAPSHOT_EXPECTED_MAIN_INVALID",
                "0" * 40,
                CANONICAL_MAIN,
            ),
        )
        for argument, error, wrong_string, exact_string in cases:
            bad_values = (
                False,
                0,
                0.0,
                None,
                b"x",
                [],
                {},
                _AlwaysEqual(),
                _AlwaysEqualStr(exact_string),
                wrong_string,
            )
            for bad_value in bad_values:
                with self.subTest(argument=argument, value=bad_value):
                    kwargs = {
                        "expected_identity": "runtime-state-primary",
                        "expected_runtime_head": ADOPTED_RUNTIME_HEAD,
                        "expected_main": CANONICAL_MAIN,
                    }
                    kwargs[argument] = bad_value
                    with self.assertRaisesRegex(DeploymentGateError, error):
                        restore_bytes(
                            snap,
                            restored,
                            expected_receipt=receipt,
                            **kwargs,
                        )
                    self.assertFalse(restored.exists())

    def test_custom_equality_cannot_bypass_forged_expected_bindings(self):
        _, snap, restored, receipt = self.snapshot_fixture()
        cases = (
            (
                "snapshot_identity",
                "expected_identity",
                "forged-runtime-state",
                "SNAPSHOT_EXPECTED_IDENTITY_INVALID",
            ),
            (
                "adopted_runtime_head",
                "expected_runtime_head",
                "0" * 40,
                "SNAPSHOT_EXPECTED_RUNTIME_HEAD_INVALID",
            ),
            (
                "canonical_main",
                "expected_main",
                "0" * 40,
                "SNAPSHOT_EXPECTED_MAIN_INVALID",
            ),
        )
        for receipt_field, argument, forged_value, error in cases:
            with self.subTest(field=receipt_field):
                forged = copy.deepcopy(receipt)
                forged[receipt_field] = forged_value
                kwargs = {
                    "expected_identity": "runtime-state-primary",
                    "expected_runtime_head": ADOPTED_RUNTIME_HEAD,
                    "expected_main": CANONICAL_MAIN,
                }
                kwargs[argument] = _AlwaysEqual()
                with self.assertRaisesRegex(DeploymentGateError, error):
                    restore_bytes(
                        snap,
                        restored,
                        expected_receipt=forged,
                        **kwargs,
                    )
                self.assertFalse(restored.exists())

    def test_cross_run_receipt_fails_closed(self):
        _, snap, restored, _ = self.snapshot_fixture()
        other_source = self.root / "other.db"
        other_snap = self.root / "other.snapshot"
        other_source.write_bytes(b"different-state")
        other_receipt = snapshot_bytes(
            other_source,
            other_snap,
            snapshot_identity="runtime-state-primary",
        )
        with self.assertRaisesRegex(DeploymentGateError, "SNAPSHOT_DIGEST_MISMATCH"):
            restore_bytes(
                snap,
                restored,
                expected_receipt=other_receipt,
                expected_identity="runtime-state-primary",
            )


if __name__ == "__main__":
    unittest.main()
