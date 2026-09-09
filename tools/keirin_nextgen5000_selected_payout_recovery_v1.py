#!/usr/bin/env python3
"""Recover payout only for pre-frozen selected NEXTGEN5000 CandidateAB races.

Consumes the aggregate PREOUTCOME freeze, rediscovers the locked universe without
results, then fetches only the preselected race pages and emits 3renhuku payout.
"""
from __future__ import annotations
import argparse,csv,json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec

spec=spec_from_file_location("p","tools/keirin_nextgen5000_3renhuku_payout_bulk_recovery_v1.py")
m=module_from_spec(spec); spec.loader.exec_module(m)

FIELDS=m.FIELDS
QUARANTINE={'8320260327010001'}

def acquire(rid,rdate,url,timeout):
    last=None
    for attempt in range(3):
        try:
            b,final=m.fetch(url,timeout)
            if final.rstrip('/')!=url.rstrip('/'): raise ValueError('FAIL-CLOSED:detail_redirect')
            x=m.parse_payout(b,url,rdate)
            if x['race_id']!=rid: raise ValueError('FAIL-CLOSED:identity_mismatch')
            return {'ok':True,'row':x}
        except Exception as e:
            last=str(e); time.sleep(.5*(attempt+1))
    return {'ok':False,'reject':{'race_id':rid,'race_date':rdate,'reason':last}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--aggregate-freeze',required=True)
    ap.add_argument('--out-csv',required=True)
    ap.add_argument('--receipt',required=True)
    ap.add_argument('--workers',type=int,default=10)
    ap.add_argument('--timeout',type=int,default=25)
    a=ap.parse_args()

    freeze=json.loads(Path(a.aggregate_freeze).read_text(encoding='utf-8'))
    s=freeze.get('safeguards',{})
    if s.get('result_accessed') is not False or s.get('payout_accessed') is not False or s.get('odds_accessed') is not False:
        raise SystemExit('FAIL-CLOSED:aggregate_not_blind')
    selected=[r for r in freeze['selected_primary'] if r['race_id'] not in QUARANTINE]
    selected_ids={r['race_id'] for r in selected}
    if len(selected)!=freeze['summary']['selected_races_primary_after_process_quarantine']:
        raise SystemExit('FAIL-CLOSED:selected_count_mismatch')

    locked=m.rediscover_locked(a.timeout)
    mapping={r[0]:{'race_date':r[1],'url':r[4]} for r in locked if r[0] in selected_ids}
    missing=selected_ids-set(mapping)
    if missing: raise SystemExit(f'FAIL-CLOSED:selected_not_in_locked_universe:{sorted(missing)[:10]}')

    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,16))) as ex:
        fut=[ex.submit(acquire,rid,mapping[rid]['race_date'],mapping[rid]['url'],a.timeout) for rid in sorted(selected_ids)]
        for f in as_completed(fut): got.append(f.result())
    rows=[g['row'] for g in got if g['ok']]
    rows.sort(key=lambda r:(r['race_date'],r['race_id']))
    rejects=[g['reject'] for g in got if not g['ok']]

    Path(a.out_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    rec={
      'record':'KEIRIN_NEXTGEN5000_SELECTED_3RENHUKU_PAYOUT_ONLY_RECEIPT_v1',
      'aggregate_freeze_record':freeze['record'],
      'selected_requested':len(selected),'successful_payouts':len(rows),'rejected':len(rejects),
      'rejects':rejects,'raw_mixed_html_written':False,'pre_fields_emitted':False,
      'odds_fields_emitted':False,'model_fields_emitted':False,
      'selection_changed_after_payout':False,'process_quarantine':sorted(QUARANTINE)
    }
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in rec.items() if k!='rejects'},ensure_ascii=False,sort_keys=True))
    return 0 if len(rows)>=.98*len(selected) else 3

if __name__=='__main__':
    raise SystemExit(main())
