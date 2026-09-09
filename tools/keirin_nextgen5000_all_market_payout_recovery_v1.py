#!/usr/bin/env python3
"""All-car-market payout-only recovery for burned NEXTGEN5000 diagnostics.

Runs only after PRE predictions are frozen and primary outcome gate has opened.
Emits winning tickets/payouts for 2shahuku, 3renhuku, wide, 2shatan, 3rentan.
No odds/PRE/model fields; raw HTML is never persisted.
"""
from __future__ import annotations
import argparse,csv,json,re,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
from bs4 import BeautifulSoup

spec=spec_from_file_location("base","tools/keirin_nextgen5000_3renhuku_payout_bulk_recovery_v1.py")
base=module_from_spec(spec); spec.loader.exec_module(base)

FIELDS=['race_id','race_date','market','winning_ticket','payout_yen_per_100','source_url','source_file_sha256','evidence_role']
ROLE='RETROSPECTIVE_ALL_CAR_MARKET_PAYOUT_ONLY_AFTER_PRE_FREEZE'

def clean(s): return re.sub(r'\s+',' ',s or '').strip()
def compact(s): return re.sub(r'\s+','',s or '')

def one(text,pat,label):
    m=re.fullmatch(pat,compact(text))
    if not m: raise ValueError(f'FAIL-CLOSED:{label}:{compact(text)!r}')
    return m.groups()

def parse_all_market(b,url,expected_date):
    soup=BeautifulSoup(b.decode('utf-8','replace'),'html.parser')
    title=clean(soup.title.get_text(' ',strip=True)) if soup.title else ''
    ridm=re.search(r'/racedetail/(\d+)/',url)
    dm=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',title)
    if not ridm or not dm: raise ValueError('FAIL-CLOSED:meta')
    rid=ridm.group(1)
    rdate=f'{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}'
    if rdate!=expected_date: raise ValueError('FAIL-CLOSED:date_mismatch')
    matches=[]
    for t in soup.find_all('table'):
        rows=t.find_all('tr')
        if len(rows)<2: continue
        c0=[clean(x.get_text(' ',strip=True)) for x in rows[0].find_all(['th','td'])]
        c1=[clean(x.get_text(' ',strip=True)) for x in rows[1].find_all(['th','td'])]
        if len(c0)>=11 and len(c1)>=6 and compact(c0[0])=='2枠連' and compact(c0[3])=='2車連' and compact(c0[6])=='3連勝' and compact(c0[9])=='ワイド':
            matches.append((c0,c1))
    if len(matches)!=1: raise ValueError(f'FAIL-CLOSED:payout_table_count={len(matches)}')
    c0,c1=matches[0]
    out=[]
    h=base.sha256_bytes(b)
    def add(market,ticket,pay):
        out.append({'race_id':rid,'race_date':rdate,'market':market,'winning_ticket':ticket,
                    'payout_yen_per_100':int(pay.replace(',','')),'source_url':url,
                    'source_file_sha256':h,'evidence_role':ROLE})
    # 2車複
    a,b,pay=one(c0[5],r'([1-9])=([1-9])([0-9,]+)円\([^)]*\)','2shahuku')
    add('2shahuku','='.join(map(str,sorted([int(a),int(b)]))),pay)
    # 3連複
    a,b,c,pay=one(c0[8],r'([1-9])=([1-9])=([1-9])([0-9,]+)円\([^)]*\)','3renhuku')
    add('3renhuku','='.join(map(str,sorted([int(a),int(b),int(c)]))),pay)
    # wide: exactly three winning pairs in standard top3
    wides=re.findall(r'([1-9])=([1-9])([0-9,]+)円\([^)]*\)',compact(c0[10]))
    if len(wides)!=3: raise ValueError(f'FAIL-CLOSED:wide_count={len(wides)}')
    for a,b,pay in wides: add('wide','='.join(map(str,sorted([int(a),int(b)]))),pay)
    # row1: 2枠単 value at 1 (ignored), 2車単 at 3, 3連単 at 5
    a,b,pay=one(c1[3],r'([1-9])-([1-9])([0-9,]+)円\([^)]*\)','2shatan')
    add('2shatan',f'{a}-{b}',pay)
    a,b,c,pay=one(c1[5],r'([1-9])-([1-9])-([1-9])([0-9,]+)円\([^)]*\)','3rentan')
    add('3rentan',f'{a}-{b}-{c}',pay)
    return out

def acquire(pos,row,timeout):
    rid,rdate,_,_,url,_=row; last=None
    for attempt in range(3):
        try:
            b,final=base.fetch(url,timeout)
            if final.rstrip('/')!=url.rstrip('/'): raise ValueError('FAIL-CLOSED:redirect')
            rows=parse_all_market(b,url,rdate)
            if any(x['race_id']!=rid for x in rows): raise ValueError('FAIL-CLOSED:identity')
            return {'ok':True,'position':pos,'rows':rows}
        except Exception as e:
            last=str(e); time.sleep(.5*(attempt+1))
    return {'ok':False,'position':pos,'reject':{'position':pos,'race_id':rid,'race_date':rdate,'reason':last}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--start-position',type=int,required=True)
    ap.add_argument('--end-position',type=int,required=True)
    ap.add_argument('--workers',type=int,default=10)
    ap.add_argument('--timeout',type=int,default=25)
    ap.add_argument('--out-csv',required=True)
    ap.add_argument('--receipt',required=True)
    a=ap.parse_args()
    if not 2001<=a.start_position<=a.end_position<=5000: raise SystemExit('bad range')
    locked=base.rediscover_locked(a.timeout)
    selected=[(i+1,locked[i]) for i in range(a.start_position-1,a.end_position)]
    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,16))) as ex:
        fut=[ex.submit(acquire,pos,row,a.timeout) for pos,row in selected]
        for f in as_completed(fut): got.append(f.result())
    got.sort(key=lambda x:x['position'])
    rows=[r for g in got if g['ok'] for r in g['rows']]
    rejects=[g['reject'] for g in got if not g['ok']]
    Path(a.out_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    ok_races=len([g for g in got if g['ok']])
    rec={'record':'KEIRIN_NEXTGEN5000_ALL_CAR_MARKET_PAYOUT_RECEIPT_v1',
         'start_position':a.start_position,'end_position':a.end_position,'requested_races':len(selected),
         'successful_races':ok_races,'rejected_races':len(rejects),'output_rows':len(rows),'rejects':rejects,
         'markets':['2shahuku','3renhuku','wide','2shatan','3rentan'],
         'odds_fields_emitted':False,'pre_fields_emitted':False,'model_fields_emitted':False,
         'raw_mixed_html_written':False,'evidence_role':ROLE}
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in rec.items() if k!='rejects'},ensure_ascii=False,sort_keys=True))
    return 0 if ok_races>=.90*len(selected) else 3

if __name__=='__main__':
    raise SystemExit(main())
