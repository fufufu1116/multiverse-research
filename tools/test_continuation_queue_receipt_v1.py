import unittest

from tools.continuation_queue_receipt_v1 import make_receipt, summarize


class ContinuationQueueReceiptV1Tests(unittest.TestCase):
    def test_make_receipt(self):
        r = make_receipt("q1", "executor-a", "CLAIMED", "2026-09-13T00:00:00Z", "owner_free")
        self.assertEqual(r["schema"], "MULTIVERSE_CONTINUATION_RECEIPT_v1")
        self.assertEqual(r["runtime"], "OFF")

    def test_summarize(self):
        r1 = make_receipt("q1", "executor-a", "CLAIMED", "2026-09-13T00:00:00Z", "owner_free")
        r2 = make_receipt("q1", "executor-a", "DONE", "2026-09-13T00:00:10Z", "success")
        out = summarize([r1, r2])
        self.assertEqual(out["receipt_count"], 2)
        self.assertEqual(out["events"]["CLAIMED"], 1)
        self.assertEqual(out["events"]["DONE"], 1)

    def test_runtime_on_rejected(self):
        r = make_receipt("q1", "executor-a", "CLAIMED", "2026-09-13T00:00:00Z", "owner_free")
        r["runtime"] = "ON"
        with self.assertRaises(ValueError):
            summarize([r])


if __name__ == "__main__":
    unittest.main()
