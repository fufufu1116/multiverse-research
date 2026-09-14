from __future__ import annotations

import unittest

from automation.review_dispatcher_v1 import model
from automation.review_dispatcher_v1.model_legacy_v1 import ReviewContractError


def nonauthority():
    return {key: False for key in (
        "provider_resource_mutation", "deploy", "database_mutation",
        "provider_effect_enablement", "runtime_activation_bridge_enablement",
        "runtime_activation", "production_credentials", "production_deployment",
        "protected_data", "live_business_effect", "additional_spend", "merge",
        "main_mutation", "ruleset_mutation", "workflow_dispatch_rerun",
    )}


def request(upstream):
    return {
        "schema":"MULTIVERSE_REVIEW_REQUEST_v1", "request_id":"auditor-compat-r1",
        "lane":"AUDITOR", "mode":"REPOSITORY_ONLY", "repo":"fufufu1116/multiverse-research",
        "pr":505, "head":"a"*40, "tree":"b"*40, "base":"c"*40, "main":"c"*40,
        "proof_ceiling":"TEST_ONLY", "execution_state":"TEST_REQUESTED",
        "supersedes_request_sha256":None,
        "recipe":{"subtrees":{},"durable_comments":[],"source_rules":[],"unittest_modules":[],"validators":[],"secret_scan_paths":[],"forbidden_patterns":[],"http":None},
        "upstream":upstream, "nonauthority":nonauthority(),
    }


class AuditorUpstreamCompatV1Tests(unittest.TestCase):
    def test_current_minimal_shape_is_admitted(self):
        value = request({"lab_result_comment": 5665005264})
        self.assertIs(model.validate_request(value), value)

    def test_legacy_shape_remains_admitted(self):
        value = request({"lab_pass_comment":1,"lab_request_sha256":"d"*64,"t1_comment":2})
        self.assertIs(model.validate_request(value), value)

    def test_extra_key_fails_closed(self):
        value = request({"lab_result_comment":1,"t1_comment":2})
        with self.assertRaisesRegex(ReviewContractError, "AUDITOR_UPSTREAM_SCHEMA"):
            model.validate_request(value)

    def test_nonpositive_result_comment_fails_closed(self):
        value = request({"lab_result_comment":0})
        with self.assertRaisesRegex(ReviewContractError, "AUDITOR_UPSTREAM_LAB_RESULT_COMMENT"):
            model.validate_request(value)

    def test_authority_defect_still_fails_closed(self):
        value = request({"lab_result_comment":1})
        value["nonauthority"]["merge"] = True
        with self.assertRaisesRegex(ReviewContractError, "NONAUTHORITY_NOT_FALSE:merge"):
            model.validate_request(value)


if __name__ == "__main__":
    unittest.main()
