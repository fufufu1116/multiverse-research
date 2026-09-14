import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("char", HERE / "characterize_sw0_result_schema_v1.py")
char = importlib.util.module_from_spec(spec)
spec.loader.exec_module(char)

def sha(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()

class CharacterizeSchemaTests(unittest.TestCase):
    def make_prediction(self, p, race_ids):
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for rid in race_ids:
                f.write(json.dumps({"race_id": rid, "tuple": [1,2,3], "prob": 0.1}) + "\n")

    def test_ab_only_deserialized_and_no_outcome_values_emitted(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pred = td/"p.jsonl.gz"
            self.make_prediction(pred, ["A","B"])
            result = td/"r.jsonl"
            rows = [
                {"race_id":"A","first_set":[1],"second_set":[2],"third_set":[3],"parser":"fixture","race_date":"2026-01-01","status":"OK"},
                {"race_id":"C","first_set":["SECRET_C"],"second_set":["SECRET_C2"],"third_set":["SECRET_C3"],"parser":"protected","race_date":"2026-01-02","status":"PROTECTED"},
                {"race_id":"B","first_set":[4],"second_set":[5],"third_set":[6],"parser":"fixture","race_date":"2026-01-03","status":"OK"},
            ]
            result.write_text("".join(json.dumps(r,separators=(",",":"))+"\n" for r in rows), encoding="utf-8")
            rep = char.characterize(result, pred, sha(result), sha(pred), expected_ab_count=2, expected_total_lines=3)
            self.assertEqual(rep["ab_rows_characterized"], 2)
            self.assertTrue(rep["rank_sets_pairwise_disjoint_all_ab"])
            self.assertFalse(rep["non_ab_rows_outcome_values_deserialized"])
            self.assertNotIn("SECRET_C", json.dumps(rep))

    def test_ab_schema_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pred = td/"p.jsonl.gz"
            self.make_prediction(pred, ["A"])
            result = td/"r.jsonl"
            row = {"race_id":"A","first_set":[1],"second_set":[2],"third_set":[3],"parser":"fixture","race_date":"2026-01-01","status":"OK","extra":"x"}
            result.write_text(json.dumps(row)+"\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "AB_SCHEMA_MISMATCH"):
                char.characterize(result, pred, sha(result), sha(pred), expected_ab_count=1, expected_total_lines=1)

if __name__ == "__main__":
    unittest.main()
