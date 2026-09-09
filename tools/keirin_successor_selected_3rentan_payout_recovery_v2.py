#!/usr/bin/env python3
"""Recover all official winning 3rentan settlements for PRE-frozen successor races.

Supports dead-heat/multiple winning 3rentan combinations. Selection is never
changed: scorer later matches the frozen ticket against this complete settlement set.
"""
from __future__ import annotations
import argparse,csv,json,re,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from bs4 import BeautifulSoup
from importlib.util import spec_from_file_location,module_from_spec

spec=spec_from_file_location("pre","tools/keirin_successor9201_pre_bulk_recovery_v1.py")
pre=module_from_spec(spec);spec.loader.exec_module(pre)
FIELDS=['race_id','race_date','winning_3rentan_settlements_json','source_url','source_file_sha256','evidence_role']
ROLE='SUCCESSOR_SELECTED_3RENTAN_ALL_SETTLEMENTS_AFTER_PREOUTCOME_FREEZE'

def clean(s):return re.sub(r'\s+',' ',s or '').strip()
def compact(s):return re.sub(r'\s+','',s or '')

def parse(body,url,expected_date):
    soup=BeautifulSoup(body.decode('utf-8','replace'),'html.parser')
    title=clean(soup.title.get_text(' ',strip=True)) if soup.title else ''
    ridm=re.search(r'/racedetail/(\d+)/',url)
    dm=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',title)
    if not ridm or not dm:raise ValueError('FAIL-CLOSED:meta')
    rid=ridm.group(1);rdate=f'{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}'
    if rdate!=expected_date:raise ValueError('FAIL-CLOSED:date')
    matches=[]
    for t in soup.find_all('table'):
        rows=t.find_all('tr')
        if len(rows)<2:continue
        c0=[clean(x.get_text(' ',strip=True)) for x in rows[0].find_all(['th','td'])]
        c1=[clean(x.get_text(' ',strip=True)) for x in rows[1].find_all(['th','td'])]
        if len(c0)>=11 and len(c1)>=6 and compact(c0[0])=='2枠連' and compact(c0[3])=='2車連' and compact(c0[6])=='3連勝' and compact(c0[9])=='ワイド':
            matches.append((c0,c1))
    if len(matches)!=1:raise ValueError(f'FAIL-CLOSED:payout_table_count={len(matches)}')
    txt=compact(matches[0][1][5])
    found=re.findall(r'([1-9])-([1-9])-([1-9])([0-9,]+)円\(([^)]*)\)',txt)
    if not found:raise ValueError(f'FAIL-CLOSED:no_3rentan_settlement:{txt!r}')
    settlements=[]
    consumed=''
    for car1,car2,car3,pay,pop in found:
        settlements.append({'ticket':f'{car1}-{car2}-{car3}','payout_yen_per_100':int(pay.replace(',','')),'popularity_raw':pop})
        consumed+=f'{car1}-{car2}-{car3}{pay}円({pop})'
    # Require every compact character in the cell to be explained by parsed settlements.
    if consumed!=txt:raise ValueError(f'FAIL-CLOSED:unparsed_3rentan_tail parsed={consumed!r} actual={txt!r}')
    if len({x['ticket'] for x in settlements})!=len(settlements):raise ValueError('FAIL-CLOSED:duplicate_ticket')
    return {'race_id':rid,'race_date':rdate,
      'winning_3rentan_settlements_json':json.dumps(settlements,ensure_ascii=False,separators=(',',':'),sort_keys=True),
      'source_url':url,'source_file_sha256':pre.sha256_bytes(body),'evidence_role':ROLE}

def acquire(rid,rdate,url,timeout):
    last=None
    for attempt in range(3):
        try:
            body,final=pre.fetch(url,timeout)
            if final.rstrip('/')!=url.rstrip('/'):raise ValueError('FAIL-CLOSED:redirect')
            r=parse(body,url,rdate)
            if r['race_id']!=rid:raise ValueError('FAIL-CLOSED:identity')
            return {'ok':True,'row':r}
        except Exception as e:
            last=str(e);time.sleep(.5*(attempt+1))
    return {'ok':False,'reject':{'race_id':rid,'race_date':rdate,'reason':last}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--out-csv',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--workers',type=int,default=12);ap.add_argument('--timeout',type=int,default=25)
    a=ap.parse_args()
    fr=json.loads(Path(a.freeze).read_text(encoding='utf-8'))
    if fr.get('status')!='SUCCESSOR_OUTCOME_GATE_READY_AFTER_THIS_FREEZE':raise SystemExit('FAIL-CLOSED:freeze_status')
    s=fr.get('safeguards',{})
    if any(s.get(k) is not False for k in ['result_accessed','payout_accessed','odds_accessed','model_refit']):raise SystemExit('FAIL-CLOSED:freeze_not_blind')
    sel=fr['selected'];ids={r['race_id'] for r in sel}
    locked=pre.rediscover_locked(a.timeout);mapu={r[0]:{'date':r[1],'url':r[4]} for r in locked if r[0] in ids}
    missing=ids-set(mapu)
    if missing:raise SystemExit(f'FAIL-CLOSED:selected_not_locked:{sorted(missing)[:5]}')
    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,16))) as ex:
        fut=[ex.submit(acquire,rid,mapu[rid]['date'],mapu[rid]['url'],a.timeout) for rid in sorted(ids)]
        for f in as_completed(fut):got.append(f.result())
    rows=[g['row'] for g in got if g['ok']];rows.sort(key=lambda r:(r['race_date'],r['race_id']))
    rejects=[g['reject'] for g in got if not g['ok']]
    Path(a.out_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    multi=sum(len(json.loads(r['winning_3rentan_settlements_json']))>1 for r in rows)
    rec={'record':'KEIRIN_SUCCESSOR_SELECTED_3RENTAN_ALL_SETTLEMENTS_RECEIPT_v2','freeze_record':fr['record'],
      'selected_requested':len(sel),'successful_races':len(rows),'multiple_settlement_races':multi,'rejected':len(rejects),'rejects':rejects,
      'selection_changed':False,'raw_mixed_html_written':False,'pre_fields_emitted':False,'odds_fields_emitted':False,'model_fields_emitted':False}
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_PAYOUT_V2',json.dumps({k:v for k,v in rec.items() if k!='rejects'},sort_keys=True))
    return 0 if len(rows)==len(sel) else 3
if __name__=='__main__':raise SystemExit(main())
