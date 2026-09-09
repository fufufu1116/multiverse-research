#!/usr/bin/env python3
"""Discover a result-blind July-August 2026 KDreams race universe.

Only date-level racecard index pages are fetched. Detail pages are not fetched.
Emits race identity + URL only, for a later PRE-only freeze.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,re
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup

HOST='keirin.kdreams.jp'
UA='Mozilla/5.0 (compatible; MultiverseKeirinResearch/6.0; UNIVERSE-DISCOVERY-ONLY)'
MAX_BYTES=8*1024*1024
FIELDS=['race_id','race_date','venue_code','grade','url','data_status']

def fetch(url,timeout=25):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname!=HOST: raise ValueError('FAIL-CLOSED:host')
    with urlopen(Request(url,headers={'User-Agent':UA,'Accept':'text/html'}),timeout=timeout) as r:
        final=r.geturl();ctype=(r.headers.get('Content-Type') or '').lower();b=r.read(MAX_BYTES+1)
    if len(b)>MAX_BYTES or len(b)<500 or 'html' not in ctype: raise ValueError('FAIL-CLOSED:response')
    return b,final

def days(a,b):
    d=a
    while d<=b:
        yield d;d+=timedelta(days=1)

def discover_day(d,timeout):
    u=f'https://{HOST}/racecard/{d.year:04d}/{d.month:02d}/{d.day:02d}/'
    b,final=fetch(u,timeout)
    if final.rstrip('/')!=u.rstrip('/'): raise ValueError('FAIL-CLOSED:redirect')
    soup=BeautifulSoup(b.decode('utf-8','replace'),'html.parser')
    found={}
    for a in soup.find_all('a',href=True):
        href=urljoin(f'https://{HOST}',a['href'])
        m=re.fullmatch(r'https://keirin\.kdreams\.jp/([^/]+)/racedetail/(\d+)/?',href)
        if m:
            slug,rid=m.groups()
            found[rid]=(rid,d.isoformat(),int(rid[:2]),'UNKNOWN',f'https://{HOST}/{slug}/racedetail/{rid}/','DISCOVERED')
    return list(found.values())

def canonical(rows):
    s=io.StringIO(newline='');w=csv.writer(s,lineterminator='\n');w.writerow(FIELDS);w.writerows(rows);return s.getvalue().encode()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out-csv',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--timeout',type=int,default=25)
    a=ap.parse_args()
    rows=[]
    for d in days(date(2026,7,1),date(2026,8,31)): rows.extend(discover_day(d,a.timeout))
    rows=sorted({r[0]:r for r in rows}.values(),key=lambda r:(r[1],r[2],int(r[0][-4:])))
    b=canonical(rows);sha=hashlib.sha256(b).hexdigest()
    Path(a.out_csv).parent.mkdir(parents=True,exist_ok=True);Path(a.out_csv).write_bytes(b)
    rec={
      'record':'KEIRIN_JULAUG2026_RESULT_BLIND_UNIVERSE_DISCOVERY_v1',
      'status':'DISCOVERY_ONLY_NO_DETAIL_PAGE_ACCESS',
      'date_start':'2026-07-01','date_end':'2026-08-31',
      'candidate_races':len(rows),'canonical_csv_sha256':sha,
      'detail_pages_fetched':False,'result_fields_accessed':False,'payout_fields_accessed':False,
      'odds_fields_accessed':False,'model_fields_accessed':False,
      'formal_support_increment_authorized':False,'model_promotion_authorized':False,'runtime':False
    }
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('PASS_DISCOVERY',json.dumps(rec,sort_keys=True))
if __name__=='__main__':main()
