import unittest

from research.opportunity_engine_v0.review_independence_gate import (
    assess_review_independence,
)


def ensemble(*, state="NO_BLOCKER_FOUND_YET", identities=None):
    if identities is None:
        identities = [
            ("OPENAI", "gpt-a", "competitor_challenge"),
            ("OPENAI", "gpt-a", "economics_challenge"),
            ("OPENAI", "gpt-a", "execution_risk_challenge"),
        ]
    return {
        "schema": "MULTIVERSE_OPPORTUNITY_REVIEW_ENSEMBLE_v1",
        "case_id": "case-001",
        "task_id": "task-001",
        "overall_state": state,
        "ensemble_sha256": "a" * 64,
        "individual_feedback": [
            {
                "submission_id": f"submission-{index}",
                "review_state": "NO_BLOCKER_FOUND_YET",
                "feedback_sha256": f"{index + 1:064x}"[-64:],
                "model_identity": {
                    "provider": provider,
                    "model": model,
                    "role": role,
                },
            }
            for index, (provider, model, role) in enumerate(identities)
        ],
    }


class ReviewIndependenceGateTests(unittest.TestCase):
    def test_same_model_three_roles_count_as_one_provider_model(self):
        result = assess_review_independence(ensemble=ensemble())
        self.assertEqual(result["provider_count"], 1)
        self.assertEqual(result["provider_model_count"], 1)
        self.assertEqual(result["advisory_identity_count"], 3)
        self.assertEqual(result["independence_state"], "INDEPENDENCE_INSUFFICIENT")

    def test_same_provider_multiple_models_still_lacks_cross_provider_clearance(self):
        result = assess_review_independence(
            ensemble=ensemble(
                identities=[
                    ("OPENAI", "gpt-a", "competitor_challenge"),
                    ("OPENAI", "gpt-b", "economics_challenge"),
                ]
            )
        )
        self.assertEqual(result["diversity_class"], "SINGLE_PROVIDER_MULTI_MODEL")
        self.assertEqual(result["independence_state"], "INDEPENDENCE_INSUFFICIENT")

    def test_cross_provider_no_blocker_can_only_reach_next_governed_gate(self):
        result = assess_review_independence(
            ensemble=ensemble(
                identities=[
                    ("OPENAI", "gpt-a", "competitor_challenge"),
                    ("GOOGLE_GEMINI", "gemini-a", "economics_challenge"),
                ]
            )
        )
        self.assertEqual(result["diversity_class"], "CROSS_PROVIDER")
        self.assertEqual(result["independence_state"], "CROSS_PROVIDER_NO_BLOCKER_FOUND_YET")
        self.assertFalse(result["support_confers_approval"])
        self.assertFalse(result["automatic_advance_authorized"])

    def test_single_provider_severe_challenge_still_blocks(self):
        result = assess_review_independence(
            ensemble=ensemble(state="CHALLENGE_REQUIRED")
        )
        self.assertEqual(result["independence_state"], "CHALLENGE_REQUIRED")
        self.assertTrue(result["negative_evidence_can_block_without_cross_provider"])

    def test_divergence_is_not_resolved_by_provider_count(self):
        result = assess_review_independence(
            ensemble=ensemble(
                state="FALSIFICATION_REQUIRED",
                identities=[
                    ("OPENAI", "gpt-a", "competitor_challenge"),
                    ("GOOGLE_GEMINI", "gemini-a", "economics_challenge"),
                    ("ANTHROPIC", "claude-a", "execution_risk_challenge"),
                ],
            )
        )
        self.assertEqual(result["independence_state"], "FALSIFICATION_REQUIRED")
        self.assertEqual(result["recommended_next_action"], "RUN_MECHANICAL_FALSIFICATION")

    def test_incomplete_review_stays_incomplete_even_with_many_providers(self):
        result = assess_review_independence(
            ensemble=ensemble(
                state="REVIEW_INCOMPLETE",
                identities=[
                    ("OPENAI", "gpt-a", "competitor_challenge"),
                    ("GOOGLE_GEMINI", "gemini-a", "economics_challenge"),
                    ("ANTHROPIC", "claude-a", "execution_risk_challenge"),
                ],
            )
        )
        self.assertEqual(result["independence_state"], "REVIEW_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
