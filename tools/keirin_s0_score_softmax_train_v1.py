#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path


def softmax_probs(rows,beta):
    xs=[beta*(r['score']-sum(x['score'] for x in rows)/len(rows)) for r in rows]
    m=max(xs); ws=[math.exp(x-m) for x in xs]; z=sum(ws)
    return {r['car_no']:w/z for r,w in zip(rows,ws)}

def metrics(races,beta):
    ll=0.0; brier=0.0; n=0
    for race in races:
        p=softmax_probs(race['rows'],beta); winner=race['winner']; n+=1
        ll += -math.log(max(p[winner],1e-15))
        brier += sum((p[c]-(1.0 if c==winner else 0.0))**2 for c in p)
    return {'races':n,'log_loss':ll/n if n else None,'brier':brier/n if n else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('pre_csv'); ap.add_argument('outcome_jsonl'); ap.add_argument('model_json'); ap.add_argument('report_json')
    a=ap.parse_args()
    by=defaultdict(list)
    with open(a.pre_csv,encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            by[r['race_id']].append({'car_no':int(r['car_no']),'score':float(r['competition_score']),'race_date':r['race_date']})
    outs={}
    with open(a.outcome_jsonl,encoding='utf-8') as f:
        for line in f:
            if line.strip():
                x=json.loads(line); outs[str(x['race_id'])]=int(x['finish_1'])
    races=[]
    for rid,rows in by.items():
        if rid not in outs: continue
        races.append({'race_id':rid,'date':rows[0]['race_date'],'rows':rows,'winner':outs[rid]})
    races.sort(key=lambda x:(x['date'],x['race_id']))
    if len(races)<20: raise SystemExit('FAIL-CLOSED: need at least 20 joined races for fitting')
    cut=max(1,int(len(races)*0.8)); train=races[:cut]; dev=races[cut:]
    # deterministic score-only beta search; no outcome-aware feature selection.
    grid=[i/1000 for i in range(0,1001)]
    scored=[(metrics(train,b)['log_loss'],b) for b in grid]
    _,beta=min(scored)
    train_m=metrics(train,beta); dev_m=metrics(dev,beta)
    model={'record':'KEIRIN_S0_SCORE_ONLY_SOFTMAX_MODEL_v1','status':'DEVELOPMENT_ONLY','beta':beta,
           'formula':'p_i = exp(beta*(score_i-race_mean_score))/sum_j exp(beta*(score_j-race_mean_score))',
           'fit_races':len(train),'result_used_as_feature':False,'payout_access':False,'economics_computed':False}
    report={'record':'KEIRIN_S0_SCORE_ONLY_TEMPORAL_REPORT_v1','status':'DEVELOPMENT_ONLY','total_joined_races':len(races),
            'split':'first 80% chronological train / last 20% chronological development evaluation','train':train_m,'development':dev_m,
            'selection_metric':'train log_loss only','no_roi_model_selection':True}
    Path(a.model_json).write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Path(a.report_json).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'model':model,'report':report},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
