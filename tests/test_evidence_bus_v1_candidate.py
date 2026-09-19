import sqlite3
import tempfile
import unittest

from config.evidence import EvidenceBus


class EvidenceBusV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.bus = EvidenceBus(self.tmp.name)

    def test_put_and_verified_retrieval(self):
        rec = self.bus.put(task_id="task_1", source="unit-test", content=b"claim evidence", media_type="text/plain")
        got, content = self.bus.get_verified(rec.evidence_id)
        self.assertEqual(content, b"claim evidence")
        self.assertEqual(got.sha256, rec.sha256)
        self.assertEqual(self.bus.ref(rec.evidence_id), f"evidence://{rec.evidence_id}")

    def test_missing_evidence_fails_closed(self):
        with self.assertRaises(KeyError):
            self.bus.get_verified("ev_missing")

    def test_tampered_content_fails_closed(self):
        rec = self.bus.put(task_id="task_1", source="unit-test", content=b"original")
        with sqlite3.connect(self.tmp.name) as conn:
            conn.execute("UPDATE evidence_objects SET content=? WHERE evidence_id=?", (b"tampered", rec.evidence_id))
        with self.assertRaises(RuntimeError):
            self.bus.get_verified(rec.evidence_id)

    def test_integrity_does_not_claim_semantic_truth(self):
        rec = self.bus.put(task_id="task_1", source="untrusted-claim", content=b"the moon is cheese")
        got, _ = self.bus.get_verified(rec.evidence_id)
        self.assertEqual(got.source, "untrusted-claim")


if __name__ == "__main__":
    unittest.main()
