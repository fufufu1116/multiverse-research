#!/usr/bin/env python3
"""Stage-1 market-structure-only firewall extractor.

Reads the Stage-0 PRICE catalog and strips ALL numeric odds values.
Outputs only race/market/ticket-key structure required by the Stage-1
probability engine.

NO RESULT / PAYOUT / REFUND / EV / ROI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_PRICE_CATALOG_SHA256 = "2ca98097f74e5282fdc9c91629083f39bef4dafb94a1fc4f7e510acadefc407b"
EXPECTED_RACES = 2000
MARKETS = ("3rentan","2shatan","3renhuku","2shahuku","2wakutan","2wakuhuku","wide")
FORBIDDEN_KEYS = {
    "odds","price","prices","closing_price_catalogs","refund","refunds","settlement",
    "result","results","payout","payouts","ev","roi","profit","loss","pnl","hit"
}

class FailClosed(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def scan_forbidden(x:Any,path:str='$')->list[str]:
    bad=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in FORBIDDEN_KEYS: bad.append(f'{path}.{k}')
            bad.extend(scan_forbidden(v,f'{path}.{k}'))
    elif isinstance(x,list):
        for i,v in enumerate(x): bad.extend(scan_forbidden(v,f'{path}[{i}]'))
    return bad

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('price_catalog')
    ap.add_argument('output_jsonl')
    a=ap.parse_args()
    src=Path(a.price_catalog); out=Path(a.output_jsonl)
    if sha256_file(src)!=EXPECTED_PRICE_CATALOG_SHA256:
        raise FailClosed('Stage0 PRICE catalog SHA mismatch')
    seen=set(); n=0
    out.parent.mkdir(parents=True,exist_ok=True)
    with src.open('r',encoding='utf-8') as f, out.open('w',encoding='utf-8',newline='\n') as w:
        for ln,line in enumerate(f,1):
            if not line.strip(): continue
            r=json.loads(line)
            rid=str(r.get('race_id','')).strip()
            if not rid or rid in seen: raise FailClosed(f'duplicate/blank race_id line={ln} rid={rid!r}')
            seen.add(rid)
            sold=list(r.get('sold_markets',[]))
            cats=r.get('closing_price_catalogs',{})
            if set(cats)!=set(sold): raise FailClosed(f'{rid}: sold market/catalog key mismatch')
            keys={m:sorted(str(k) for k in cats[m].keys()) for m in sold}
            rec={
                'race_id':rid,
                'active_car_numbers':[int(x) for x in r['active_car_numbers']],
                'active_car_count':int(r['active_car_count']),
                'sold_markets':sold,
                'ticket_keys':keys,
                'source_price_catalog_sha256':EXPECTED_PRICE_CATALOG_SHA256,
                'numeric_odds_values_included':False,
            }
            bad=scan_forbidden(rec)
            if bad: raise FailClosed(f'{rid}: forbidden structure output keys={bad[:10]}')
            w.write(json.dumps(rec,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
            n+=1
    if n!=EXPECTED_RACES: raise FailClosed(f'race count={n} expected={EXPECTED_RACES}')
    print(json.dumps({'status':'PASS','races':n,'output_sha256':sha256_file(out),'numeric_odds_values_included':False},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
