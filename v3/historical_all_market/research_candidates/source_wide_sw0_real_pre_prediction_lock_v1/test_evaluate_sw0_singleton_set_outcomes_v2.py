import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ev", HERE / "evaluate_sw0_singleton_set_outcomes_v2.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

def sha(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()

def probs_for(cars, favored):
    rows = []
    mass = 0.0
    triples = []
    for a in cars:
        for b in cars:
            for c in cars:
                if len({a,b,c}) < 3:
                    continue
                w = 3.0 if (a,b,c) == favored else 1.0
                triples.append([a,b,c,w])
                mass += w
    return [[a,b,c,w/mass] for a,b,c,w in triples]

class SingletonSetEvalTests(unittest.TestCase):
    def make_prediction(self, p, specs):
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for rid, dev_index, cars, favored in specs:
                f.write(json.dumps({
                    "race_id": rid,
                    "dev_index": dev_index,
                    "ordered_top3_probabilities": probs_for(cars, favored)
                }, separators=(",",":")) + "\n")

    def test_strict_rows_scored_nonstrict_excluded_and_c_not_deserialized(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pred = td/"p.jsonl.gz"
            specs = [
                ("A", 1, [1,2,3], (1,2,3)),
                ("B", 1001, [4,5,6], (4,5,6)),
                ("T", 1002, [7,8,9], (7,8,9)),
            ]
            self.make_prediction(pred, specs)
            result = td/"r.jsonl"
            rows = [
                {"race_id":"A","first_set":[1],"second_set":[2],"third_set":[3],"parser":"result-v4.1-tie-aware","race_date":"2026-01-01","status":"OK"},
                {"race_id":"C","first_set":["SECRET_C"],"second_set":["SECRET_C2"],"third_set":["SECRET_C3"],"parser":"protected","race_date":"2026-01-02","status":"PROTECTED"},
                {"race_id":"B","first_set":[4],"second_set":[5],"third_set":[6],"parser":"result-v4.1-tie-aware","race_date":"2026-01-03","status":"OK"},
                {"race_id":"T","first_set":[7,8],"second_set":[],"third_set":[9],"parser":"result-v4.1-tie-aware","race_date":"2026-01-04","status":"OK"},
            ]
            result.write_text("".join(json.dumps(r,separators=(",",":"))+"\n" for r in rows), encoding="utf-8")
            rep = ev.evaluate(
                pred, sha(pred), result, sha(result),
                expected_prediction_count=3,
                expected_total_lines=4,
                min_strict_count=2,
                bootstrap_reps=100,
                bootstrap_seed=7,
            )
            self.assertEqual(rep["coverage"]["strict_singleton_rows_scored"], 2)
            self.assertEqual(rep["coverage"]["non_strict_rows_excluded_from_scoring"], 1)
            self.assertEqual(rep["coverage"]["excluded_shape_histogram"], {"2-0-1": 1})
            self.assertFalse(rep["method"]["non_singleton_tie_rows_scalarized"])
            self.assertNotIn("SECRET_C", json.dumps(rep))

    def test_schema_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pred = td/"p.jsonl.gz"
            self.make_prediction(pred, [("A", 1, [1,2,3], (1,2,3))])
            result = td/"r.jsonl"
            row = {"race_id":"A","first_set":[1],"second_set":[2],"third_set":[3],"parser":"result-v4.1-tie-aware","race_date":"2026-01-01","status":"OK","extra":"x"}
            result.write_text(json.dumps(row)+"\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "AB_RESULT_SCHEMA"):
                ev.evaluate(
                    pred, sha(pred), result, sha(result),
                    expected_prediction_count=1,
                    expected_total_lines=1,
                    min_strict_count=1,
                    bootstrap_reps=10,
                )

    def test_parser_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pred = td/"p.jsonl.gz"
            self.make_prediction(pred, [("A", 1, [1,2,3], (1,2,3))])
            result = td/"r.jsonl"
            row = {"race_id":"A","first_set":[1],"second_set":[2],"third_set":[3],"parser":"other-parser","race_date":"2026-01-01","status":"OK"}
            result.write_text(json.dumps(row)+"\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "PARSER_DRIFT"):
                ev.evaluate(
                    pred, sha(pred), result, sha(result),
                    expected_prediction_count=1,
                    expected_total_lines=1,
                    min_strict_count=1,
                    bootstrap_reps=10,
                )

if __name__ == "__main__":
    unittest.main()
