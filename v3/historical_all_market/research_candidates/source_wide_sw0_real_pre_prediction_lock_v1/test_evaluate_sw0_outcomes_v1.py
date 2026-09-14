import json, hashlib, os, tempfile
from evaluate_sw0_outcomes_v1 import load_outcomes, race_metrics, summarize

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        h.update(f.read())
    return h.hexdigest()

def test_synthetic_two_races_and_jsonl_loader():
    rows=[
      {"race_id":"R1","dev_index":1,"ordered_top3_probabilities":[[1,2,3,.50],[1,3,2,.20],[2,1,3,.10],[2,3,1,.08],[3,1,2,.07],[3,2,1,.05]]},
      {"race_id":"R2","dev_index":2,"ordered_top3_probabilities":[[1,2,3,.10],[1,3,2,.10],[2,1,3,.20],[2,3,1,.30],[3,1,2,.15],[3,2,1,.15]]},
    ]
    with tempfile.TemporaryDirectory() as d:
        op=os.path.join(d,"o.jsonl")
        with open(op,"w",encoding="utf-8") as f:
            f.write(json.dumps({"race_id":"R1","first":1,"second":2,"third":3},separators=(",",":"))+"\n")
            f.write(json.dumps({"race_id":"R2","first":2,"second":3,"third":1},separators=(",",":"))+"\n")
        outs=load_outcomes(op,sha(op))
        m1=race_metrics(rows[0],outs["R1"]); m2=race_metrics(rows[1],outs["R2"])
        s=summarize([m1,m2])
        assert s["race_count"]==2
        assert s["top1_accuracy"]==1.0
        assert s["ordered_top3_hit_rate"]==1.0
        assert s["primary_effect_uniform_minus_sw0"]>0

def test_extra_field_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        op=os.path.join(d,"o.jsonl")
        with open(op,"w",encoding="utf-8") as f:
            f.write(json.dumps({"race_id":"R1","first":1,"second":2,"third":3,"payout":999})+"\n")
        try:
            load_outcomes(op,sha(op))
        except SystemExit as e:
            assert "OUTCOME_SCHEMA_OR_EXTRA_FIELDS" in str(e)
        else:
            raise AssertionError("expected fail closed")
