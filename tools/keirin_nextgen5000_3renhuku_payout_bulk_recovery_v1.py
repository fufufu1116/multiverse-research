#!/usr/bin/env python3
"""Payout-only 3renhuku recovery for exact locked NEXTGEN5000 races.

Must run only after PRE predictions/selections are frozen. Emits only race identity,
winning 3renhuku combination and official payout per 100 yen. No PRE, odds, model
probability, forecast or comment fields are emitted; raw HTML is not persisted.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,re,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import date,timedelta
from html import unescape
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup

HOST='keirin.kdreams.jp'
UA='Mozilla/5.0 (compatible; MultiverseKeirinResearch/5.1; PAYOUT-only-after-freeze)'
MAX_BYTES=8*1024*1024
EXPECTED_CANDIDATE_COUNT=9201
EXPECTED_CANDIDATE_SHA='9b8fc60bfd55eb12a4989112b3fa4eee1e2bb6a214946edd79a739296a9aed7c'
EXPECTED_5000_SHA='dd2045cc609c37c08a9e65ba4f80ab121803d0749440a7023394e431a1678781'
EXPECTED_5000_COUNT=5000
ROLE='RETROSPECTIVE_3RENHUKU_PAYOUT_ONLY_AFTER_PRE_FREEZE'
FIELDS=['race_id','race_date','winning_3renhuku_ticket','payout_yen_per_100','source_url','source_file_sha256','evidence_role']

def clean(s): return re.sub(r'\s+',' ',unescape(s or '')).strip()
def compact(s): return re.sub(r'\s+','',unescape(s or ''))
def sha256_bytes(b): return hashlib.sha256(b).hexdigest()

def fetch(url,timeout=25):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname!=HOST: raise ValueError('FAIL-CLOSED:host')
    req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
    with urlopen(req,timeout=timeout) as r:
        final=r.geturl(); ctype=(r.headers.get('Content-Type') or '').lower(); b=r.read(MAX_BYTES+1)
    if len(b)>MAX_BYTES or len(b)<500: raise ValueError('FAIL-CLOSED:size')
    if 'html' not in ctype: raise ValueError('FAIL-CLOSED:content_type')
    return b,final

def daterange(start,end):
    d=start
    while d<=end:
        yield d; d+=timedelta(days=1)

def discover_day(d,timeout=25):
    u=f'https://{HOST}/racecard/{d.year:04d}/{d.month:02d}/{d.day:02d}/'
    b,final=fetch(u,timeout)
    if final.rstrip('/')!=u.rstrip('/'): raise ValueError('FAIL-CLOSED:day_redirect')
    soup=BeautifulSoup(b.decode('utf-8','replace'),'html.parser'); found={}
    for a in soup.find_all('a',href=True):
        href=urljoin(f'https://{HOST}',a['href'])
        m=re.fullmatch(r'https://keirin\.kdreams\.jp/([^/]+)/racedetail/(\d+)/?',href)
        if m:
            slug,rid=m.groups(); found[rid]=f'https://{HOST}/{slug}/racedetail/{rid}/'
    return [(rid,d.isoformat(),int(rid[:2]),'UNKNOWN',url,'DISCOVERED') for rid,url in found.items()]

def canonical_csv_bytes(rows):
    s=io.StringIO(newline=''); w=csv.writer(s,lineterminator='\n')
    w.writerow(['race_id','race_date','venue_code','grade','url','data_status']); w.writerows(rows)
    return s.getvalue().encode()

def rediscover_locked(timeout=25):
    rows=[]
    for d in daterange(date(2026,3,1),date(2026,6,30)): rows.extend(discover_day(d,timeout))
    rows=sorted({r[0]:r for r in rows}.values(),key=lambda r:(r[1],r[2],int(r[0][-4:])))
    csha=sha256_bytes(canonical_csv_bytes(rows))
    if len(rows)!=EXPECTED_CANDIDATE_COUNT or csha!=EXPECTED_CANDIDATE_SHA:
        raise ValueError(f'FAIL-CLOSED:candidate_lock_mismatch count={len(rows)} sha={csha}')
    first=rows[:EXPECTED_5000_COUNT]; fsha=sha256_bytes(canonical_csv_bytes(first))
    if len(first)!=EXPECTED_5000_COUNT or fsha!=EXPECTED_5000_SHA:
        raise ValueError(f'FAIL-CLOSED:5000_lock_mismatch sha={fsha}')
    return first

def parse_payout(b,exact_url,expected_date):
    soup=BeautifulSoup(b.decode('utf-8','replace'),'html.parser')
    title=clean(soup.title.get_text(' ',strip=True)) if soup.title else ''
    m=re.search(r'/racedetail/(\d+)/',exact_url)
    dm=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',title)
    if not m or not dm: raise ValueError('FAIL-CLOSED:meta')
    rid=m.group(1); race_date=f'{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}'
    if race_date!=expected_date: raise ValueError('FAIL-CLOSED:date_mismatch')

    txt=compact(soup.get_text(' ',strip=True))
    # KDreams payout label uses 3連勝複, distinct from the pre-race 3連複 odds tab.
    matches=re.findall(r'3連勝複([1-9]=[1-9]=[1-9])([0-9,]+)円(?:\([^)]*\))?',txt)
    if len(matches)!=1:
        raise ValueError(f'FAIL-CLOSED:3renhuku_payout_match_count={len(matches)}')
    ticket,pay=matches[0]
    cars=sorted(map(int,ticket.split('=')))
    if len(set(cars))!=3: raise ValueError('FAIL-CLOSED:bad_ticket')
    payout=int(pay.replace(',',''))
    if payout<100: raise ValueError(f'FAIL-CLOSED:payout_too_small={payout}')
    return {
      'race_id':rid,'race_date':race_date,
      'winning_3renhuku_ticket':'='.join(map(str,cars)),
      'payout_yen_per_100':payout,'source_url':exact_url,
      'source_file_sha256':sha256_bytes(b),'evidence_role':ROLE
    }

def acquire_one(pos,row,timeout):
    rid,rdate,_,_,url,_=row; last=None
    for attempt in range(3):
        try:
            b,final=fetch(url,timeout)
            if final.rstrip('/')!=url.rstrip('/'): raise ValueError('FAIL-CLOSED:detail_redirect')
            x=parse_payout(b,url,rdate)
            if x['race_id']!=rid: raise ValueError('FAIL-CLOSED:identity_mismatch')
            return {'ok':True,'position':pos,'row':x}
        except Exception as e:
            last=str(e); time.sleep(.5*(attempt+1))
    return {'ok':False,'position':pos,'reject':{'position':pos,'race_id':rid,'race_date':rdate,'reason':last}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--start-position',type=int,required=True)
    ap.add_argument('--end-position',type=int,required=True)
    ap.add_argument('--workers',type=int,default=8)
    ap.add_argument('--timeout',type=int,default=25)
    ap.add_argument('--out-csv',required=True)
    ap.add_argument('--receipt',required=True)
    ap.add_argument('--pre-freeze-attestation',required=True,choices=['YES'])
    a=ap.parse_args()
    if not 2001<=a.start_position<=a.end_position<=5000: raise SystemExit('invalid range')
    locked=rediscover_locked(a.timeout)
    selected=[(i+1,locked[i]) for i in range(a.start_position-1,a.end_position)]
    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,12))) as ex:
        fut=[ex.submit(acquire_one,pos,row,a.timeout) for pos,row in selected]
        for f in as_completed(fut): got.append(f.result())
    got.sort(key=lambda x:x['position'])
    rows=[g['row'] for g in got if g['ok']]; rejects=[g['reject'] for g in got if not g['ok']]
    Path(a.out_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.out_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    rec={
      'record':'KEIRIN_NEXTGEN5000_3RENHUKU_PAYOUT_ONLY_RECEIPT_v1',
      'status':'PASS' if not rejects else 'PASS_WITH_REJECTIONS',
      'pre_freeze_attestation':True,'locked_5000_sha256':EXPECTED_5000_SHA,
      'start_position':a.start_position,'end_position':a.end_position,
      'requested_races':len(selected),'successful_races':len(rows),'rejected_races':len(rejects),
      'rejected':rejects,'raw_mixed_html_written':False,'pre_fields_emitted':False,
      'outcome_order_fields_emitted':False,'odds_fields_emitted':False,
      'model_fields_emitted':False,'formal_support_increment_authorized':False,
      'model_promotion_authorized':False,'evidence_role':ROLE
    }
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in rec.items() if k!='rejected'},ensure_ascii=False,sort_keys=True))
    return 0 if len(rows)>=int(.95*len(selected)) else 3

if __name__=='__main__':
    raise SystemExit(main())
