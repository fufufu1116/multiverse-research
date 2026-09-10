import unittest

from preparation_plan import build_preparation_plan
from real_infrastructure_contract import (
    ENVIRONMENT_CLASS,
    REQUIRED_EVIDENCE_DOMAINS,
    TARGET_CLASS,
)


class PreparationPlanTests(unittest.TestCase):
    def test_plan_is_specification_only_and_fail_closed(self):
        plan = build_preparation_plan()

        self.assertEqual(plan["target_class"], TARGET_CLASS)
        self.assertEqual(
            plan["environment_class"],
            ENVIRONMENT_CLASS,
        )
        self.assertEqual(
            set(plan["evidence_refs"]),
            REQUIRED_EVIDENCE_DOMAINS,
        )
        self.assertEqual(plan["runtime"], "OFF")
        self.assertFalse(plan["ready_for_external_execution"])

        for value in plan["authority"].values():
            self.assertIs(value, False)

        for value in plan["existence_claims"].values():
            self.assertIs(value, False)

    def test_plan_does_not_claim_real_remote_infrastructure(self):
        plan = build_preparation_plan()
        claims = plan["existence_claims"]

        self.assertFalse(claims["remote_host_provisioned"])
        self.assertFalse(claims["remote_service_deployed"])
        self.assertFalse(claims["remote_state_store_provisioned"])
        self.assertFalse(claims["real_credentials_provisioned"])
        self.assertFalse(claims["network_path_verified"])

    def test_credential_material_is_synthetic_reference_only(self):
        plan = build_preparation_plan()

        for value in plan["credential_refs"].values():
            self.assertTrue(value.startswith("SYNTHETIC_REF:"))

    def test_single_host_proof_ceiling_is_explicit(self):
        plan = build_preparation_plan()

        self.assertTrue(
            plan["requirements"][
                "lease_fencing"
            ]["single_host_boundary_explicit"]
        )
        self.assertFalse(
            plan["requirements"][
                "lease_fencing"
            ]["multi_host_failover_proven"]
        )

    def test_external_execution_remains_unauthorized(self):
        plan = build_preparation_plan()
        safety = plan["requirements"]["provider_effect_safety"]

        self.assertFalse(
            safety["live_provider_execution_authorized"]
        )
        self.assertFalse(
            safety["real_network_execution_authorized"]
        )
        self.assertFalse(
            safety["external_effect_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
