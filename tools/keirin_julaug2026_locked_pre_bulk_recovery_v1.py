#!/usr/bin/env python3
"""PRE-only recovery from an externally locked result-blind universe CSV.

Designed for the locked Jul-Aug 2026 universe. Reuses the corrected semantic
PRE parser; does not inspect result, payout, odds, forecast or comments.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec

spec=spec_from_file_location("base","tools/keirin_successor9201_pre_bulk_recovery_v1.py")
base=module_from_spec(spec);spec.loader.exec_module(base)

EXPECTED_COUNT=4768
EXPECTED_SHA='8ba2d9d66e90d486eaa8d311e55a6ae71773aa4f84bd4e32d7cdc0e6181fa8db'
ROLE='RETROSPECTIVE_PRE_JULAUG2026_LOCKED_UNIVERSE_BLIND_v1'
LOCK_FIELDS=['race_id','race_date','venue_code','grade','url','data_status']

def load_locked(path):
    raw=Path(path).read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=EXPECTED_SHA:raise SystemExit(f'FAIL-CLOSED:universe_sha:{sha}')
    with open(path,encoding='utf-8',newline='') as f:
        rd=csv.reader(f);rows=list(rd)
    if not rows or rows[0]!=LOCK_FIELDS:raise SystemExit(f'FAIL-CLOSED:header:{rows[:1]}')
    data=[tuple(r) for r in rows[1:]]
    if len(data)!=EXPECTED_COUNT:raise SystemExit(f'FAIL-CLOSED:count:{len(data)}')
    if len({r[0] for r in data})!=len(data):raise SystemExit('FAIL-CLOSED:duplicate_race_id')
    return data

def acquire(pos,row,timeout):
    rid,rdate,venue_code,grade,url,status=row
    last=None
    for attempt in range(3):
        try:
            body,final=base.fetch(url,timeout)
            if final.rstrip('/')!=url.rstrip('/'):raise ValueError('FAIL-CLOSED:redirect')
            pr=base.parse_pre(body,url)
            # Override evidence role emitted by the imported parser.
            for x in pr:x['evidence_role']=ROLE
            if pr[0]['race_id']!=rid or pr[0]['race_date']!=rdate:raise ValueError('FAIL-CLOSED:identity')
            return {'ok':True,'position':pos,'rows':pr,'summary':{'position':pos,'race_id':rid,'race_date':rdate,'pre_rows':len(pr),'source_file_sha256':pr[0]['source_file_sha256']}}
        except Exception as e:
            last=str(e);time.sleep(.5*(attempt+1))
    return {'ok':False,'position':pos,'summary':{'position':pos,'race_id':rid,'race_date':rdate,'reason':last}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--universe-csv',required=True);ap.add_argument('--start-position',type=int,required=True);ap.add_argument('--end-position',type=int,required=True);ap.add_argument('--workers',type=int,default=10);ap.add_argument('--timeout',type=int,default=25);ap.add_argument('--pre-csv',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--min-success-rate',type=float,default=.90)
    a=ap.parse_args()
    locked=load_locked(a.universe_csv)
    if not 1<=a.start_position<=a.end_position<=len(locked):raise SystemExit('invalid range')
    selected=[(i+1,locked[i]) for i in range(a.start_position-1,a.end_position)]
    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,16))) as ex:
        fut=[ex.submit(acquire,pos,row,a.timeout) for pos,row in selected]
        for f in as_completed(fut):got.append(f.result())
    got.sort(key=lambda x:x['position']);rows=[r for g in got if g['ok'] for r in g['rows']]
    Path(a.pre_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.pre_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=base.FIELDS);w.writeheader();w.writerows(rows)
    accepted=[g['summary'] for g in got if g['ok']];rejected=[g['summary'] for g in got if not g['ok']]
    rec={'record':'KEIRIN_JULAUG2026_PRE_ONLY_BULK_RECOVERY_RECEIPT_v1','status':'PASS' if not rejected else 'PASS_WITH_REJECTIONS',
      'locked_universe_count':EXPECTED_COUNT,'locked_universe_sha256':EXPECTED_SHA,'start_position':a.start_position,'end_position':a.end_position,
      'requested_races':len(selected),'successful_races':len(accepted),'rejected_races':len(rejected),'pre_rows':len(rows),
      'accepted':accepted,'rejected':rejected,'corrected_semantic_parser':True,'raw_mixed_html_written':False,
      'result_fields_emitted':False,'payout_fields_emitted':False,'odds_fields_emitted':False,'forecast_or_comment_fields_emitted':False,
      'formal_support_increment_authorized':False,'model_promotion_authorized':False,'evidence_role':ROLE}
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_JULAUG_PRE',json.dumps({k:v for k,v in rec.items() if k not in {'accepted','rejected'}},sort_keys=True))
    return 0 if len(accepted)>=a.min_success_rate*len(selected) else 3
if __name__=='__main__':raise SystemExit(main())
