from __future__ import annotations

import unittest

from automation.multimodel_research_v1.phase_b_live_pilot_preauth import (
    ALLOWED_HOST,
    ALLOWED_OPERATION,
    API_VERSION,
    CURRENT_CANONICAL_MAIN,
    CURRENT_CANONICAL_TREE,
    CURRENT_MULTIMODEL_SUBTREE,
    EXPECTED_CATALOG_AGE_SECONDS,
    FORBIDDEN_BODY_KEYS,
    MAX_COST_USD_MICROS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    PREDECESSOR_PACKET_SHA256,
    SELECTED_MODEL,
    SELECTED_PROVIDER,
    build_first_live_provider_preauth_packet,
    classify_preauth_outcome,
    first_live_provider_preauth_packet_sha256,
    preauth_summary,
    validate_first_live_provider_preauth_packet,
)


class PhaseBFirstLiveProviderPreauthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = build_first_live_provider_preauth_packet()

    def _valid_observation(self) -> dict:
        return {
            "http_success": True,
            "provider": SELECTED_PROVIDER,
            "model_id": SELECTED_MODEL,
            "native_status": "completed",
            "strict_local_schema_valid": True,
            "semantic_refusal": False,
            "premature_termination": False,
            "incomplete_observation": False,
            "termination_valid": True,
            "receipt_valid": True,
            "result_or_failure_receipt_present": True,
            "input_tokens": 1000,
            "output_tokens": 500,
            "actual_cost_usd_micros": 2625,
        }

    def test_521_preauth_packet_validates(self):
        self.assertEqual(validate_first_live_provider_preauth_packet(self.packet), self.packet)

    def test_522_preauth_binds_current_canonical_tuple(self):
        self.assertEqual(
            self.packet["canonical"],
            {
                "main": CURRENT_CANONICAL_MAIN,
                "tree": CURRENT_CANONICAL_TREE,
                "multimodel_subtree": CURRENT_MULTIMODEL_SUBTREE,
            },
        )

    def test_523_preauth_binds_integrated_pr297_predecessor_packet(self):
        self.assertEqual(self.packet["predecessor"]["integrated_pr"], 297)
        self.assertEqual(self.packet["predecessor"]["execution_packet_sha256"], PREDECESSOR_PACKET_SHA256)

    def test_524_catalog_freshness_is_within_24h(self):
        self.assertEqual(self.packet["catalog_freshness"]["age_seconds"], EXPECTED_CATALOG_AGE_SECONDS)
        self.assertLessEqual(self.packet["catalog_freshness"]["age_seconds"], 86400)

    def test_525_official_recheck_is_current_gemini_binding(self):
        row = self.packet["official_recheck"]
        self.assertEqual(row["provider"], SELECTED_PROVIDER)
        self.assertEqual(row["model_id"], SELECTED_MODEL)
        self.assertEqual(row["lifecycle"], "GA")
        self.assertEqual(row["api_version"], API_VERSION)
        self.assertTrue(row["structured_json"])
        self.assertEqual(row["response_shape"], "steps")

    def test_526_provider_host_operation_api_version_are_exact(self):
        binding = self.packet["provider_binding"]
        self.assertEqual(binding["provider"], SELECTED_PROVIDER)
        self.assertEqual(binding["model_id"], SELECTED_MODEL)
        self.assertEqual(binding["allowed_host"], ALLOWED_HOST)
        self.assertEqual(binding["allowed_operation"], ALLOWED_OPERATION)
        self.assertEqual(binding["api_version"], API_VERSION)

    def test_527_store_false_is_explicit_in_contract_and_body(self):
        self.assertIs(self.packet["request_contract"]["store"], False)
        self.assertIs(self.packet["request_contract"]["rendered_body"]["store"], False)

    def test_528_tool_search_code_file_memory_function_surfaces_are_closed(self):
        closure = self.packet["request_contract"]["capability_closure"]
        self.assertTrue(closure)
        self.assertTrue(all(value is False for value in closure.values()))
        body = self.packet["request_contract"]["rendered_body"]
        self.assertFalse(set(body) & FORBIDDEN_BODY_KEYS)

    def test_529_stateless_nonstreaming_foreground_only(self):
        request = self.packet["request_contract"]
        self.assertTrue(request["stateless_single_turn"])
        self.assertFalse(request["previous_interaction_id_allowed"])
        self.assertFalse(request["background"])
        self.assertFalse(request["stream"])

    def test_530_single_attempt_and_no_automatic_retry(self):
        request = self.packet["request_contract"]
        self.assertEqual(request["max_attempts"], 1)
        self.assertFalse(request["automatic_retry_on_timeout"])
        self.assertFalse(request["automatic_retry_on_5xx"])
        self.assertFalse(request["automatic_retry_on_ambiguous_outcome"])

    def test_531_synthetic_only_data_ceiling(self):
        self.assertEqual(self.packet["request_contract"]["data_ceiling"], "SYNTHETIC_ONLY")

    def test_532_token_and_cost_ceilings_are_exact(self):
        self.assertEqual(self.packet["limits"]["max_input_tokens"], MAX_INPUT_TOKENS)
        self.assertEqual(self.packet["limits"]["max_output_tokens"], MAX_OUTPUT_TOKENS)
        self.assertEqual(self.packet["limits"]["max_cost_usd_micros"], MAX_COST_USD_MICROS)
        self.assertEqual(MAX_COST_USD_MICROS, 39936)
        self.assertLessEqual(MAX_COST_USD_MICROS, 1_000_000)

    def test_533_credential_handle_only_no_material_or_use_authority(self):
        boundary = self.packet["credential_boundary"]
        self.assertTrue(boundary["credential_handle_id"])
        self.assertFalse(boundary["credential_material_present"])
        self.assertFalse(boundary["credential_retrieval_authorized"])
        self.assertFalse(boundary["credential_use_authorized"])

    def test_534_all_live_authorities_false_and_runtime_off(self):
        authority = self.packet["authority"]
        for key in (
            "provider_call_authorized",
            "credential_authorized",
            "spend_authorized",
            "runtime_activation",
            "live_execution_performed",
            "protected_data",
            "live_business_effect",
            "adoption_authority",
        ):
            self.assertFalse(authority[key], key)
        self.assertTrue(authority["owner_gate_required_before_provider_call"])
        self.assertEqual(authority["runtime"], "OFF")

    def test_535_exact_task_prompt_schema_body_envelope_hashes_preserved(self):
        expected = {
            "predecessor_execution_packet_sha256": PREDECESSOR_PACKET_SHA256,
            "synthetic_task_sha256": "3c68888aff3374cfe2b3354b483b39d1b738aa224e905961d693648d97eee844",
            "assignment_sha256": "bda4cd5b9c6044d4849213258e80edff6d6b3306979b946d0dbcd38e2044afb3",
            "provider_neutral_prompt_sha256": "b0938af624e850562700f2352b6dc528d91462adc0ff3d6686dad5223283bed3",
            "strict_local_result_schema_sha256": "e98309cc04606bcc08f3718e0e6ead0ba2374b6ee0b250892514ce33b984661b",
            "provider_wire_response_schema_sha256": "0cad630dd2079468fcff569615afb2d4939a4c9c76729ec0664cb82db79d4706",
            "rendered_request_body_sha256": "34b7ede1d6a74a130e7b5c220df1245d62f537da97400b626d3faf2f26dca006",
            "request_envelope_sha256": "aec776bdd8ad606ec3abd26067a1c77f78546602dce65aa22a8b71c90a10f7ff",
            "transport_binding_sha256": "419073d3906815c67bc7501770c7c31bacd766cb89d89479cf510a93c50f8ebd",
            "result_ingestion_requirements_sha256": "44e2509a0c8d05843f6622712ebc700e794d450fbcd05b57e4649d02bf57fe7a",
            "termination_receipt_requirements_sha256": "1b43ca363f8e7c5beb613ddd53f4f87aafb61143afb2118fb3098742d86bd99c",
        }
        for key, value in expected.items():
            self.assertEqual(self.packet["hashes"][key], value, key)

    def test_536_only_fully_valid_completed_observation_is_success(self):
        outcome = classify_preauth_outcome(self._valid_observation())
        self.assertTrue(outcome["success"])
        self.assertEqual(outcome["classification"], "SUCCESS")
        self.assertEqual(outcome["failure_reasons"], [])

    def test_537_http_failure_is_fail_closed(self):
        observation = self._valid_observation()
        observation["http_success"] = False
        outcome = classify_preauth_outcome(observation)
        self.assertFalse(outcome["success"])
        self.assertIn("HTTP_NOT_SUCCESS", outcome["failure_reasons"])

    def test_538_semantic_refusal_is_never_success(self):
        observation = self._valid_observation()
        observation["semantic_refusal"] = True
        outcome = classify_preauth_outcome(observation)
        self.assertFalse(outcome["success"])
        self.assertIn("SEMANTIC_REFUSAL", outcome["failure_reasons"])

    def test_539_incomplete_or_premature_termination_is_never_success(self):
        for key, reason in (
            ("incomplete_observation", "INCOMPLETE_OBSERVATION"),
            ("premature_termination", "PREMATURE_TERMINATION"),
        ):
            observation = self._valid_observation()
            observation[key] = True
            outcome = classify_preauth_outcome(observation)
            self.assertFalse(outcome["success"])
            self.assertIn(reason, outcome["failure_reasons"])

    def test_540_schema_validity_is_required_beyond_http_success(self):
        observation = self._valid_observation()
        observation["strict_local_schema_valid"] = False
        outcome = classify_preauth_outcome(observation)
        self.assertFalse(outcome["success"])
        self.assertIn("STRICT_SCHEMA_INVALID", outcome["failure_reasons"])

    def test_541_provider_or_model_drift_is_fail_closed(self):
        for key, value, reason in (
            ("provider", "OTHER", "PROVIDER_DRIFT"),
            ("model_id", "other-model", "MODEL_DRIFT"),
        ):
            observation = self._valid_observation()
            observation[key] = value
            outcome = classify_preauth_outcome(observation)
            self.assertFalse(outcome["success"])
            self.assertIn(reason, outcome["failure_reasons"])

    def test_542_token_or_cost_ceiling_excess_is_fail_closed(self):
        cases = (
            ("input_tokens", MAX_INPUT_TOKENS + 1, "INPUT_TOKEN_CEILING_EXCEEDED"),
            ("output_tokens", MAX_OUTPUT_TOKENS + 1, "OUTPUT_TOKEN_CEILING_EXCEEDED"),
            ("actual_cost_usd_micros", MAX_COST_USD_MICROS + 1, "COST_CEILING_EXCEEDED"),
        )
        for key, value, reason in cases:
            observation = self._valid_observation()
            observation[key] = value
            outcome = classify_preauth_outcome(observation)
            self.assertFalse(outcome["success"])
            self.assertIn(reason, outcome["failure_reasons"])

    def test_543_termination_or_receipt_failure_is_fail_closed(self):
        cases = (
            ("termination_valid", False, "TERMINATION_INVALID"),
            ("receipt_valid", False, "RECEIPT_INVALID"),
            ("result_or_failure_receipt_present", False, "RECEIPT_MISSING"),
        )
        for key, value, reason in cases:
            observation = self._valid_observation()
            observation[key] = value
            outcome = classify_preauth_outcome(observation)
            self.assertFalse(outcome["success"])
            self.assertIn(reason, outcome["failure_reasons"])

    def test_544_preauth_packet_digest_is_deterministic(self):
        first = first_live_provider_preauth_packet_sha256(self.packet)
        second = first_live_provider_preauth_packet_sha256(build_first_live_provider_preauth_packet())
        self.assertEqual(first, second)
        self.assertEqual(preauth_summary()["packet_sha256"], first)


if __name__ == "__main__":
    unittest.main()
