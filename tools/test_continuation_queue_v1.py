import unittest

from tools.continuation_queue_v1 import claim, complete, enqueue, idle_metrics


class ContinuationQueueV1Tests(unittest.TestCase):
    def item(self):
        return {
            "source_event_id": "run-1",
            "stage": "verify-results",
            "generation": "g1",
            "enqueued_at": "2026-09-13T00:00:00Z",
            "requires_gate": False,
            "runtime": "OFF",
        }

    def test_enqueue_is_idempotent(self):
        first = enqueue({}, self.item())
        second = enqueue(first["state"], self.item())
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["queue_key"], second["queue_key"])

    def test_claim_and_complete(self):
        out = enqueue({}, self.item())
        claimed = claim(out["state"], out["queue_key"], "executor-a", "2026-09-13T00:00:05Z")
        self.assertTrue(claimed["claimed"])
        done = complete(claimed["state"], out["queue_key"], "executor-a", "2026-09-13T00:00:20Z", "success")
        self.assertEqual(done["items"][out["queue_key"]]["status"], "DONE")

    def test_gate_blocks_claim(self):
        item = self.item(); item["requires_gate"] = True
        out = enqueue({}, item)
        claimed = claim(out["state"], out["queue_key"], "executor-a", "2026-09-13T00:00:05Z")
        self.assertFalse(claimed["claimed"])
        self.assertEqual(claimed["reason"], "gate_required")

    def test_active_lease_blocks_second_executor(self):
        out = enqueue({}, self.item())
        first = claim(out["state"], out["queue_key"], "executor-a", "2026-09-13T00:00:05Z", 300)
        second = claim(first["state"], out["queue_key"], "executor-b", "2026-09-13T00:01:00Z", 300)
        self.assertFalse(second["claimed"])
        self.assertEqual(second["reason"], "leased")

    def test_expired_lease_can_be_recovered(self):
        out = enqueue({}, self.item())
        first = claim(out["state"], out["queue_key"], "executor-a", "2026-09-13T00:00:05Z", 30)
        recovered = claim(first["state"], out["queue_key"], "executor-b", "2026-09-13T00:01:00Z", 30)
        self.assertTrue(recovered["claimed"])

    def test_idle_metrics(self):
        out = enqueue({}, self.item())
        metrics = idle_metrics(out["state"], "2026-09-13T00:01:00Z")
        self.assertEqual(metrics["open_items"], 1)
        self.assertEqual(metrics["average_wait_seconds"], 60)
        self.assertEqual(metrics["max_wait_seconds"], 60)

    def test_runtime_on_rejected(self):
        item = self.item(); item["runtime"] = "ON"
        with self.assertRaises(ValueError):
            enqueue({}, item)


if __name__ == "__main__":
    unittest.main()
