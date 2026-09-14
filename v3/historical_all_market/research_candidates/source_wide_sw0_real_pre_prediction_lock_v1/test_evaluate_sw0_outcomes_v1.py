import json
from evaluate_sw0_outcomes_v1 import race_metrics, summarize

def test_synthetic_two_races():
    rows=[
      {"race_id":"R1","dev_index":1,"ordered_top3_probabilities":[[1,2,3,.50],[1,3,2,.20],[2,1,3,.10],[2,3,1,.08],[3,1,2,.07],[3,2,1,.05]]},
      {"race_id":"R2","dev_index":2,"ordered_top3_probabilities":[[1,2,3,.10],[1,3,2,.10],[2,1,3,.20],[2,3,1,.30],[3,1,2,.15],[3,2,1,.15]]},
    ]
    m1=race_metrics(rows[0],(1,2,3)); m2=race_metrics(rows[1],(2,3,1))
    s=summarize([m1,m2])
    assert s["race_count"]==2
    assert s["top1_accuracy"]==1.0
    assert s["ordered_top3_hit_rate"]==1.0
    assert s["primary_effect_uniform_minus_sw0"]>0
