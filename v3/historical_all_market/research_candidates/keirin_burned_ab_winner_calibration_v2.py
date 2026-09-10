#!/usr/bin/env python3
"""Tie-aware fail-closed burned A+B winner calibration for frozen Candidate A vs B1a.
Only authorized burned A/B are accepted. Segment C / ECON_HOLDOUT1000 are not inputs.
No refit, no threshold change, no production effect.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,random
from collections import defaultdict
from pathlib import Path
PRED_SHA='772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51'
A_SHA='436846591b082689cf29687b2e63e82b0f12b47b4fa70a596d90b00978079cdd'
B_SHA='95096fac61c320484d6ab0456971a3e7debdf311498b00d6390658c072c71a72'
MODELS=('candidate_a_win_prob','b1a_reconstituted_v1_win_prob')
class FailClosed(RuntimeError): pass
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def labels(path,seg,expected_sha,n):
 if sha(path)!=expected_sha: raise FailClosed(f'{seg} SHA drift')
 out={}
 with open(path,encoding='utf-8') as f:
  for line in f:
   if not line.strip(): continue
   r=json.loads(line)
   if r.get('segment')!=seg: raise FailClosed('segment drift')
   ws=set()
   for market in ('3rentan','2shatan'):
    for ticket,pay in r['settlements_yen_per_100'].get(market,{}).items():
     if int(pay)>0: ws.add(int(str(ticket).split('-')[0]))
   if not ws: raise FailClosed(f"{r['race_id']}: no winner evidence")
   out[str(r['race_id'])]=ws
 if len(out)!=n: raise FailClosed(f'{seg} rows={len(out)} expected={n}')
 return out
def predictions(path):
 if sha(path)!=PRED_SHA: raise FailClosed('prediction SHA drift')
 by=defaultdict(dict); rows=0
 with open(path,encoding='utf-8',newline='') as f:
  for r in csv.DictReader(f):
   rows+=1; by[str(r['race_id'])][int(r['car_no'])]={m:float(r[m]) for m in MODELS}
 if rows!=14255 or len(by)!=2000: raise FailClosed('prediction cardinality drift')
 for rid,cars in by.items():
  for m in MODELS:
   if abs(sum(v[m] for v in cars.values())-1)>1e-8: raise FailClosed(f'{rid}: probability sum drift')
 return by
def ece(xs):
 n=len(xs); z=0.0
 for b in range(10):
  lo=b/10; hi=(b+1)/10
  q=[x for x in xs if lo<=x[0]<(hi if b<9 else hi+1e-15)]
  if q: z+=len(q)/n*abs(sum(x[0] for x in q)/len(q)-sum(x[1] for x in q)/len(q))
 return z
def metric(pred,labs,rids,m):
 top=[]; br=[]; ll=[]
 for rid in rids:
  ws=labs[rid]; cars=pred[rid]; tc=max(cars,key=lambda c:(cars[c][m],-c)); conf=cars[tc][m]
  top.append((conf,1.0 if tc in ws else 0.0)); q=1/len(ws)
  br.append(sum((v[m]-(q if c in ws else 0.0))**2 for c,v in cars.items()))
  ll.append(-math.log(max(sum(cars[c][m] for c in ws),1e-15)))
 return {'n':len(rids),'top1_hit_rate':sum(h for _,h in top)/len(top),'mean_top1_probability':sum(c for c,_ in top)/len(top),'top1_ece_10bin':ece(top),'multiclass_brier_equal_share_ties':sum(br)/len(br),'winner_set_log_loss':sum(ll)/len(ll)}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--predictions',required=True); ap.add_argument('--settlement-a',required=True); ap.add_argument('--settlement-b',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
 la=labels(a.settlement_a,'A',A_SHA,1000); lb=labels(a.settlement_b,'B',B_SHA,500); labs={**la,**lb}; pred=predictions(a.predictions)
 if len(labs)!=1500 or any(r not in pred for r in labs): raise FailClosed('join drift')
 out={'record':'KEIRIN_BURNED_AB_WINNER_CALIBRATION_TIE_AWARE_v2','status':'PASS_FIXED_MODEL_DIAGNOSTIC_ONLY','retuned':False,'segment_c_opened':False,'ECON_HOLDOUT1000':'SEALED','tie_race_count':sum(len(w)>1 for w in labs.values()),'metrics':{}}
 for scope,rids in [('A',list(la)),('B',list(lb)),('AB',list(labs))]: out['metrics'][scope]={m:metric(pred,labs,rids,m) for m in MODELS}
 Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps({'status':out['status'],'sha256':sha(a.output)},ensure_ascii=False))
if __name__=='__main__': main()
