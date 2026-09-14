import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "control" / "CHAT_STREAM_INTERRUPTION_RECOVERY_CONTRACT_v1.json"


class ChatStreamResilienceContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_exact_state_machine(self):
        self.assertEqual(
            self.data["states"],
            [
                "NOT_AUTHORIZED",
                "AUTHORIZED_NOT_ATTEMPTED",
                "ATTEMPTED_CONSUMED",
                "RESULT_RECORDED",
            ],
        )
        self.assertEqual(
            self.data["allowed_transitions"],
            [
                ["NOT_AUTHORIZED", "AUTHORIZED_NOT_ATTEMPTED"],
                ["AUTHORIZED_NOT_ATTEMPTED", "ATTEMPTED_CONSUMED"],
                ["ATTEMPTED_CONSUMED", "RESULT_RECORDED"],
            ],
        )

    def test_no_backward_or_retry_semantics(self):
        invariants = self.data["invariants"]
        self.assertFalse(invariants["speculative_retry_after_interruption"])
        self.assertFalse(invariants["move_backward_from_attempted_consumed"])
        self.assertFalse(invariants["repeat_receipted_owner_action"])

    def test_resume_order_is_canonical_first(self):
        self.assertEqual(self.data["resume_order"][0], "canonical_main")
        self.assertEqual(self.data["resume_order"][-1], "first_uncommitted_step")

    def test_non_authority_boundary(self):
        self.assertEqual(self.data["runtime"], "OFF")
        self.assertTrue(all(value is False for value in self.data["authority"].values()))


if __name__ == "__main__":
    unittest.main()
