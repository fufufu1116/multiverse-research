#!/usr/bin/env python3
"""Recover complete 3rentan settlements for a PRE-frozen selection using one
or more locked result-blind universe CSVs (Jul-Aug + Sep1-8).
"""
from __future__ import annotations
import argparse,csv,hashlib,json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec

spec=spec_from_file_location("p","tools/keirin_successor_selected_3rentan_payout_recovery_v2.py")
p=module_from_spec(spec);spec.loader.exec_module(p)

LOCKS={
 '8ba2d9d66e90d486eaa8d311e55a6ae71773aa4f84bd4e32d7cdc0e6181fa8db':4768,
 'a2eb309979a2082cfcbbe760b601d2eae9bbf5b46ce9d6a904ffa55276ad4339':607,
}
FIELDS=p.FIELDS

def load_universe(path):
    raw=Path(path).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha not in LOCKS:raise SystemExit(f'FAIL-CLOSED:unknown_lock:{sha}')
    with open(path,encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=LOCKS[sha]:raise SystemExit(f'FAIL-CLOSED:count:{sha}:{len(rows)}')
    return sha,{r['race_id']:{'date':r['race_date'],'url':r['url']} for r in rows}

def acquire(rid,meta,timeout):
    last=None
    for attempt in range(3):
        try:
            body,final=p.pre.fetch(meta['url'],timeout)
            if final.rstrip('/')!=meta['url'].rstrip('/'):raise ValueError('redirect')
            r=p.parse(body,meta['url'],meta['date'])
            if r['race_id']!=rid:raise ValueError('identity')
            return {'ok':True,'row':r}
        except Exception as e:
            last=str(e);time.sleep(.5*(attempt+1))
    return {'ok':False,'reject':{'race_id':rid,'race_date':meta['date'],'reason':last}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--universe-csv',action='append',required=True);ap.add_argument('--out-csv',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--workers',type=int,default=12);ap.add_argument('--timeout',type=int,default=25)
    a=ap.parse_args()
    fr=json.loads(Path(a.freeze).read_text(encoding='utf-8'));s=fr['safeguards']
    if any(s.get(k) is not False for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']):raise SystemExit('FAIL-CLOSED:freeze_not_blind')
    mapping={};locks=[]
    for u in a.universe_csv:
        sha,m=load_universe(u);locks.append({'path':Path(u).name,'sha256':sha,'count':len(m)})
        overlap=set(mapping)&set(m)
        if overlap:raise SystemExit(f'FAIL-CLOSED:universe_overlap:{list(overlap)[:3]}')
        mapping.update(m)
    sel=fr['selected'];ids={r['race_id'] for r in sel};missing=ids-set(mapping)
    if missing:raise SystemExit(f'FAIL-CLOSED:selected_not_in_locks:{sorted(missing)[:5]}')
    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,16))) as ex:
        fut=[ex.submit(acquire,rid,mapping[rid],a.timeout) for rid in sorted(ids)]
        for f in as_completed(fut):got.append(f.result())
    rows=[g['row'] for g in got if g['ok']];rows.sort(key=lambda r:(r['race_date'],r['race_id']));rej=[g['reject'] for g in got if not g['ok']]
    Path(a.out_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    multi=sum(len(json.loads(r['winning_3rentan_settlements_json']))>1 for r in rows)
    rec={'record':'KEIRIN_LOCKED_MULTI_UNIVERSE_SELECTED_3RENTAN_SETTLEMENT_RECEIPT_v1','freeze_record':fr['record'],
      'universe_locks':locks,'selected_requested':len(sel),'successful_races':len(rows),'multiple_settlement_races':multi,'rejected':len(rej),'rejects':rej,
      'selection_changed':False,'raw_mixed_html_written':False,'pre_fields_emitted':False,'odds_fields_emitted':False,'model_fields_emitted':False}
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_MULTI_UNIVERSE_PAYOUT',json.dumps({k:v for k,v in rec.items() if k!='rejects'},sort_keys=True))
    return 0 if len(rows)==len(sel) else 3
if __name__=='__main__':raise SystemExit(main())
