import unittest

from .owner_gate import ProposedAction, classify_owner_gate, choose_next_continuable_action


class OwnerGateTests(unittest.TestCase):
    def test_reversible_research_continues_without_owner(self):
        result = classify_owner_gate(ProposedAction(
            action_id="r1",
            description="Add research-only tests on the candidate branch",
            reversible_repository_only=True,
        ))
        self.assertEqual(result["decision"], "CONTINUE_AUTONOMOUS_RESEARCH")
        self.assertTrue(result["continue_without_owner"])

    def test_spend_requires_owner(self):
        result = classify_owner_gate(ProposedAction(
            action_id="s1",
            description="Buy a provider call",
            reversible_repository_only=False,
            spends_money=True,
        ))
        self.assertEqual(result["decision"], "OWNER_ACTION_REQUIRED")
        self.assertIn("SPEND", result["owner_gate_reasons"])

    def test_canonical_main_change_requires_owner(self):
        result = classify_owner_gate(ProposedAction(
            action_id="m1",
            description="Integrate candidate into canonical main",
            reversible_repository_only=False,
            changes_canonical_main=True,
            grants_adoption_or_merge_authority=True,
        ))
        self.assertEqual(result["decision"], "OWNER_ACTION_REQUIRED")

    def test_sensitive_data_risk_holds_fail_closed(self):
        result = classify_owner_gate(ProposedAction(
            action_id="p1",
            description="Expose sensitive owner facts in a packet",
            reversible_repository_only=True,
            deletes_or_exposes_sensitive_owner_data=True,
        ))
        self.assertEqual(result["decision"], "HOLD_FAIL_CLOSED")

    def test_gated_action_does_not_block_later_research_action(self):
        result = choose_next_continuable_action((
            ProposedAction(
                action_id="provider",
                description="Call a live provider",
                reversible_repository_only=False,
                triggers_live_provider_or_network_effect=True,
            ),
            ProposedAction(
                action_id="research",
                description="Improve local evidence model",
                reversible_repository_only=True,
            ),
        ))
        self.assertEqual(result["decision"], "CONTINUE_AUTONOMOUS_RESEARCH")
        self.assertEqual(result["selected_action_id"], "research")
        self.assertFalse(result["owner_action_required"])

    def test_owner_is_requested_only_when_no_continuable_action_remains(self):
        result = choose_next_continuable_action((
            ProposedAction(
                action_id="publish",
                description="Publish the live output",
                reversible_repository_only=False,
                publishes_or_contacts_external_party=True,
            ),
        ))
        self.assertEqual(result["decision"], "OWNER_ACTION_REQUIRED")
        self.assertTrue(result["owner_action_required"])
        self.assertEqual(result["selected_action_id"], "publish")

    def test_unclassified_nonreversible_action_holds(self):
        result = classify_owner_gate(ProposedAction(
            action_id="u1",
            description="Unknown non-reversible action",
            reversible_repository_only=False,
        ))
        self.assertEqual(result["decision"], "HOLD_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
