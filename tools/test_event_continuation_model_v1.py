import unittest
from tools.event_continuation_model_v1 import evaluate


class EventContinuationModelV1Tests(unittest.TestCase):
    def event(self):
        return {
            "event_id": "run-100",
            "completed_at": "2026-09-13T00:00:00Z",
            "detected_at": "2026-09-13T00:00:08Z",
            "result": "success",
            "next_stage": "verify-results",
            "requires_gate": False,
            "generation": "g1",
        }

    def test_success_ready(self):
        out = evaluate(self.event(), set())
        self.assertEqual(out["decision"], "READY_FOR_NEXT_SAFE_STAGE")
        self.assertEqual(out["detection_latency_seconds"], 8)

    def test_gate_stops(self):
        e = self.event(); e["requires_gate"] = True
        self.assertEqual(evaluate(e, set())["decision"], "STOP")

    def test_failure_stops(self):
        e = self.event(); e["result"] = "failure"
        self.assertEqual(evaluate(e, set())["decision"], "STOP")

    def test_duplicate_noop(self):
        first = evaluate(self.event(), set())
        second = evaluate(self.event(), {first["idempotency_key"]})
        self.assertEqual(second["decision"], "NOOP_DUPLICATE")

    def test_generation_changes_key(self):
        first = evaluate(self.event(), set())
        e = self.event(); e["generation"] = "g2"
        self.assertNotEqual(first["idempotency_key"], evaluate(e, set())["idempotency_key"])


if __name__ == "__main__":
    unittest.main()
