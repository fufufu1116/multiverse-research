from __future__ import annotations

import unittest

from automation.multimodel_research_v1.phase_b_live_preauth import (
    API_VERSION,
    CANONICAL_MAIN,
    CANONICAL_MULTIMODEL_SUBTREE,
    CANONICAL_TREE,
    CREDENTIAL_HANDLE_REF,
    ENDPOINT,
    EXPECTED_BODY_KEYS,
    EXPECTED_CATALOG_AGE_SECONDS,
    HOST,
    MAX_ATTEMPTS,
    MAX_COST_USD_MICROS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MODEL_ID,
    OPERATION,
    PREDECESSOR_PACKET_SHA256,
    PROVIDER,
    build_first_live_provider_preauth,
    classify_pilot_outcome,
    first_live_provider_preauth_sha256,
    valid_success_fixture,
    validate_first_live_provider_preauth,
)


class PhaseBLivePreauthTests(unittest.TestCase):
    def packet(self):
        return build_first_live_provider_preauth()

    def fail_outcome(self, **changes):
        value = valid_success_fixture()
        value.update(changes)
        result = classify_pilot_outcome(value)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "FAIL_CLOSED")
        self.assertFalse(result["grants_authority"])
        self.assertEqual(result["runtime"], "OFF")
        return result

    def test_521_build_and_validate(self):
        packet = self.packet()
        self.assertIs(validate_first_live_provider_preauth(packet), packet)

    def test_522_current_canonical_exact(self):
        self.assertEqual(self.packet()["canonical"]["main"], CANONICAL_MAIN)
        self.assertEqual(self.packet()["canonical"]["tree"], CANONICAL_TREE)
        self.assertEqual(self.packet()["canonical"]["multimodel_subtree"], CANONICAL_MULTIMODEL_SUBTREE)

    def test_523_predecessor_packet_hash_exact(self):
        self.assertEqual(self.packet()["canonical"]["predecessor_execution_packet_sha256"], PREDECESSOR_PACKET_SHA256)

    def test_524_catalog_freshness_le_24h(self):
        fresh = self.packet()["catalog_freshness"]
        self.assertEqual(fresh["age_seconds"], EXPECTED_CATALOG_AGE_SECONDS)
        self.assertLessEqual(fresh["age_seconds"], fresh["max_age_seconds"])
        self.assertTrue(fresh["fresh_le_24h"])

    def test_525_official_provider_model_lifecycle(self):
        v = self.packet()["fresh_official_verification"]
        self.assertEqual((v["provider"], v["model_id"], v["lifecycle"], v["classification"]),
                         (PROVIDER, MODEL_ID, "GA", "STABLE"))

    def test_526_api_v1_host_endpoint_operation(self):
        c = self.packet()["connection"]
        self.assertEqual((c["api_version"], c["host"], c["endpoint"], c["operation"]),
                         (API_VERSION, HOST, ENDPOINT, OPERATION))

    def test_527_structured_output_current_shape(self):
        v = self.packet()["fresh_official_verification"]["structured_output"]
        self.assertTrue(v["supported"])
        self.assertEqual(v["request_field"], "response_format")
        self.assertFalse(v["legacy_response_mime_type_allowed"])

    def test_528_migration_steps_and_response_format(self):
        m = self.packet()["fresh_official_verification"]["migration"]
        self.assertEqual(m["current_response_field"], "steps")
        self.assertEqual(m["current_format_field"], "response_format")
        self.assertFalse(m["legacy_schema_allowed"])

    def test_529_store_false_required(self):
        self.assertIs(self.packet()["exact_request_body"]["store"], False)

    def test_530_exact_minimal_body_keys(self):
        self.assertEqual(set(self.packet()["exact_request_body"]), EXPECTED_BODY_KEYS)

    def test_531_background_false(self):
        self.assertIs(self.packet()["exact_request_body"]["background"], False)

    def test_532_stream_false(self):
        self.assertIs(self.packet()["exact_request_body"]["stream"], False)

    def test_533_no_previous_interaction_id(self):
        self.assertNotIn("previous_interaction_id", self.packet()["exact_request_body"])

    def test_534_dynamic_capabilities_all_forbidden(self):
        ceiling = self.packet()["capability_ceiling"]
        self.assertTrue(ceiling)
        self.assertTrue(all(value is False for value in ceiling.values()))

    def test_535_synthetic_only(self):
        data = self.packet()["data_boundary"]
        self.assertEqual(data["classification"], "SYNTHETIC_ONLY")
        self.assertTrue(all(value is False for key, value in data.items() if key != "classification"))

    def test_536_max_attempts_one(self):
        p = self.packet()
        self.assertEqual(p["limits"]["max_attempts"], MAX_ATTEMPTS)
        self.assertEqual(p["retry_policy"]["max_attempts"], 1)

    def test_537_no_automatic_retry_any_failure(self):
        r = self.packet()["retry_policy"]
        self.assertFalse(r["automatic_retry"])
        self.assertFalse(r["retry_on_timeout"])
        self.assertFalse(r["retry_on_5xx"])
        self.assertFalse(r["retry_on_ambiguous_outcome"])
        self.assertTrue(r["any_retry_requires_new_owner_authority"])

    def test_538_exact_cost_ceiling_39936(self):
        limits = self.packet()["limits"]
        self.assertEqual(limits["proposed_owner_spend_ceiling_usd_micros"], MAX_COST_USD_MICROS)
        self.assertLessEqual(MAX_COST_USD_MICROS, limits["repository_absolute_ceiling_usd_micros"])

    def test_539_credential_handle_reference_only(self):
        c = self.packet()["credential_boundary"]
        self.assertEqual(c["credential_handle_ref"], CREDENTIAL_HANDLE_REF)
        self.assertFalse(c["credential_material_in_repository"])
        self.assertFalse(c["credential_material_in_packet"])
        self.assertFalse(c["credential_resolution_authorized"])
        self.assertFalse(c["credential_use_authorized"])
        self.assertFalse(c["owner_secret_copy_paste_required"])

    def test_540_all_live_authorities_false(self):
        a = self.packet()["authority"]
        self.assertEqual(a["runtime"], "OFF")
        self.assertTrue(all(value is False for key, value in a.items() if key != "runtime"))

    def test_541_packet_hash_deterministic(self):
        a = self.packet()
        b = self.packet()
        self.assertEqual(first_live_provider_preauth_sha256(a), first_live_provider_preauth_sha256(b))

    def test_542_full_success_accepts(self):
        result = classify_pilot_outcome(valid_success_fixture())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["classification"], "SUCCESS")
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["grants_authority"])

    def test_543_incomplete_fails(self):
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="incomplete")["failure_reasons"])

    def test_544_failed_fails(self):
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="failed")["failure_reasons"])

    def test_545_cancelled_fails(self):
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="cancelled")["failure_reasons"])

    def test_546_requires_action_fails(self):
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="requires_action")["failure_reasons"])

    def test_547_budget_exceeded_fails(self):
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="budget_exceeded")["failure_reasons"])

    def test_548_queued_or_in_progress_fails(self):
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="queued")["failure_reasons"])
        self.assertIn("NATIVE_NOT_COMPLETED", self.fail_outcome(native_status="in_progress")["failure_reasons"])

    def test_549_model_mismatch_fails(self):
        self.assertIn("MODEL_MISMATCH", self.fail_outcome(observed_model_id="other-model")["failure_reasons"])

    def test_550_normalized_refusal_fails(self):
        self.assertIn("NORMALIZED_NOT_COMPLETED", self.fail_outcome(normalized_state="PROVIDER_REFUSED")["failure_reasons"])

    def test_551_result_refused_fails(self):
        self.assertIn("RESULT_NOT_COMPLETED", self.fail_outcome(result_status="REFUSED")["failure_reasons"])

    def test_552_strict_schema_invalid_fails(self):
        self.assertIn("STRICT_SCHEMA_INVALID", self.fail_outcome(strict_schema_valid=False)["failure_reasons"])

    def test_553_semantic_refusal_fails(self):
        self.assertIn("SEMANTIC_REFUSAL", self.fail_outcome(semantic_refusal=True)["failure_reasons"])

    def test_554_missing_receipt_fails(self):
        self.assertIn("RECEIPT_MISSING", self.fail_outcome(receipt_present=False)["failure_reasons"])

    def test_555_unexpected_capability_step_fails(self):
        self.assertIn("UNEXPECTED_CAPABILITY_STEP", self.fail_outcome(unexpected_capability_step=True)["failure_reasons"])

    def test_556_token_or_cost_overflow_fails(self):
        self.assertIn("INPUT_TOKEN_CEILING", self.fail_outcome(input_tokens=MAX_INPUT_TOKENS + 1)["failure_reasons"])
        self.assertIn("OUTPUT_TOKEN_CEILING", self.fail_outcome(output_tokens=MAX_OUTPUT_TOKENS + 1)["failure_reasons"])
        self.assertIn("COST_CEILING", self.fail_outcome(computed_cost_usd_micros=MAX_COST_USD_MICROS + 1)["failure_reasons"])


if __name__ == "__main__":
    unittest.main()
