import unittest

from real_infrastructure_contract import (
    ENVIRONMENT_CLASS,
    HOST_BOUNDARY,
    PROVIDER_BINDING,
    REQUIRED_EVIDENCE_DOMAINS,
    SERVICE_BOUNDARY,
    TARGET_CLASS,
    RealInfrastructurePreparationGateError,
    RealInfrastructurePreparationSpec,
    canonical_receipt_sha256,
)


def refs():
    return {
        domain: f"SYNTHETIC_REF:evidence/{domain}:planned-v1"
        for domain in REQUIRED_EVIDENCE_DOMAINS
    }


def credential_refs():
    return {
        "provisioning":
            "SYNTHETIC_REF:credential/provisioning:planned-v1",
        "rotation":
            "SYNTHETIC_REF:credential/rotation:planned-v1",
        "revocation":
            "SYNTHETIC_REF:credential/revocation:planned-v1",
    }


def valid(**overrides):
    data = dict(
        target_class=TARGET_CLASS,
        environment_class=ENVIRONMENT_CLASS,
        provider_binding=PROVIDER_BINDING,
        host_boundary=HOST_BOUNDARY,
        service_boundary=SERVICE_BOUNDARY,
        evidence_refs=refs(),
        credential_refs=credential_refs(),
    )
    data.update(overrides)
    return RealInfrastructurePreparationSpec(**data)


class EqualToPreprod:
    def __eq__(self, other):
        return other == ENVIRONMENT_CLASS

    def __hash__(self):
        return hash(ENVIRONMENT_CLASS)


class ContractTests(unittest.TestCase):
    def test_valid_preparation_receipt_is_fail_closed(self):
        receipt = valid().receipt()
        self.assertEqual(receipt["runtime"], "OFF")
        self.assertFalse(receipt["ready_for_external_execution"])
        self.assertEqual(receipt["target_class"], TARGET_CLASS)
        self.assertEqual(
            set(receipt["evidence_refs"]),
            REQUIRED_EVIDENCE_DOMAINS,
        )
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

        for value in receipt["authority"].values():
            self.assertIs(value, False)

        for value in receipt["existence_claims"].values():
            self.assertIs(value, False)

    def test_target_class_mismatch_rejected(self):
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(target_class="PRODUCTION").validate()

    def test_target_class_str_subclass_rejected(self):
        class S(str):
            pass

        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(target_class=S(TARGET_CLASS)).validate()

    def test_environment_custom_equality_rejected(self):
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(environment_class=EqualToPreprod()).validate()

    def test_environment_str_subclass_rejected(self):
        class S(str):
            pass

        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(environment_class=S(ENVIRONMENT_CLASS)).validate()

    def test_provider_binding_mismatch_rejected(self):
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(provider_binding="LIVE_PROVIDER").validate()

    def test_evidence_ref_domain_set_exact(self):
        bad = refs()
        bad.pop("backup_restore")
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(evidence_refs=bad).validate()

    def test_extra_evidence_ref_rejected(self):
        bad = refs()
        bad["extra"] = "SYNTHETIC_REF:evidence/extra:planned-v1"
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(evidence_refs=bad).validate()

    def test_evidence_refs_must_be_exact_dict(self):
        class D(dict):
            pass

        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(evidence_refs=D(refs())).validate()

    def test_evidence_ref_must_be_synthetic(self):
        bad = refs()
        bad["backup_restore"] = "https://example.invalid/live"
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(evidence_refs=bad).validate()

    def test_evidence_ref_str_subclass_rejected(self):
        class S(str):
            pass

        bad = refs()
        bad["backup_restore"] = S(
            "SYNTHETIC_REF:evidence/backup_restore:planned-v1"
        )
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(evidence_refs=bad).validate()

    def test_credential_refs_exact_set(self):
        bad = credential_refs()
        bad.pop("revocation")
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(credential_refs=bad).validate()

    def test_real_credential_reference_rejected(self):
        bad = credential_refs()
        bad["provisioning"] = "secret://production/api-key"
        with self.assertRaises(RealInfrastructurePreparationGateError):
            valid(credential_refs=bad).validate()

    def test_all_authority_expansions_rejected(self):
        fields = (
            "real_network_execution",
            "live_provider_execution",
            "external_effect_enabled",
            "spend_enabled",
            "protected_keirin_data_enabled",
            "production_credentials_enabled",
            "production_deployment_enabled",
            "runtime_activation",
        )
        for field in fields:
            with self.subTest(field=field):
                with self.assertRaises(
                    RealInfrastructurePreparationGateError
                ):
                    valid(**{field: True}).validate()

    def test_authority_bool_type_confusion_rejected(self):
        for value in (0, 0.0, None, "false"):
            with self.subTest(value=value):
                with self.assertRaises(
                    RealInfrastructurePreparationGateError
                ):
                    valid(runtime_activation=value).validate()

    def test_existence_overclaims_rejected(self):
        fields = (
            "remote_host_provisioned",
            "remote_service_deployed",
            "remote_state_store_provisioned",
            "real_credentials_provisioned",
            "network_path_verified",
        )
        for field in fields:
            with self.subTest(field=field):
                with self.assertRaises(
                    RealInfrastructurePreparationGateError
                ):
                    valid(**{field: True}).validate()

    def test_receipt_hash_requires_exact_dict(self):
        with self.assertRaises(RealInfrastructurePreparationGateError):
            canonical_receipt_sha256([])


if __name__ == "__main__":
    unittest.main()
