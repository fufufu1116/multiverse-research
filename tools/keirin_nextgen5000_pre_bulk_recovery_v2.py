#!/usr/bin/env python3
"""Strict PRE-only recovery v2 for the exact locked NEXTGEN5000 universe.

v2 fixes the v1 semantic bug that confused KDreams gear ratio with competition
score. It parses the current "直近4ヶ月の成績" table by semantic position:
class -> style -> gear ratio -> competition score -> S/B/逃/捲/差/マ ->
1着/2着/3着/着外 counts -> 勝率/2連対率/3連対率.

Raw mixed HTML is never persisted. RESULT/PAYOUT/ODDS/FORECAST/COMMENT fields
are not emitted. Research role only.
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
UA='Mozilla/5.0 (compatible; MultiverseKeirinResearch/5.0; PRE-only-v2)'
MAX_BYTES=8*1024*1024
EXPECTED_CANDIDATE_COUNT=9201
EXPECTED_CANDIDATE_SHA='9b8fc60bfd55eb12a4989112b3fa4eee1e2bb6a214946edd79a739296a9aed7c'
EXPECTED_5000_SHA='dd2045cc609c37c08a9e65ba4f80ab121803d0749440a7023394e431a1678781'
EXPECTED_5000_COUNT=5000
ROLE='RETROSPECTIVE_PRE_DEVELOPMENT_ONLY_UNPROVEN_PIT_V2'
CLASS_RE=re.compile(r'(?:SS|S1|S2|A1|A2|A3|L1)')
INT_RE=re.compile(r'\d{1,3}')
DEC_RE=re.compile(r'\d{1,3}(?:\.\d{1,3})?')
FIELDS=[
 'race_id','race_date','venue','race_no','car_no','rider_name_raw','class','style',
 'gear_ratio','competition_score','S','B','nige','makuri','sashi','mark',
 'win_rate','quinella_rate','trio_rate',
 'source_url','source_file_sha256','evidence_role'
]

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
        yield d
        d+=timedelta(days=1)

def discover_day(d,timeout=25):
    u=f'https://{HOST}/racecard/{d.year:04d}/{d.month:02d}/{d.day:02d}/'
    b,final=fetch(u,timeout)
    if final.rstrip('/')!=u.rstrip('/'): raise ValueError('FAIL-CLOSED:day_redirect')
    soup=BeautifulSoup(b.decode('utf-8','replace'),'html.parser')
    found={}
    for a in soup.find_all('a',href=True):
        href=urljoin(f'https://{HOST}',a['href'])
        m=re.fullmatch(r'https://keirin\.kdreams\.jp/([^/]+)/racedetail/(\d+)/?',href)
        if not m: continue
        slug,rid=m.groups()
        found[rid]=f'https://{HOST}/{slug}/racedetail/{rid}/'
    return [(rid,d.isoformat(),int(rid[:2]),'UNKNOWN',url,'DISCOVERED') for rid,url in found.items()]

def canonical_csv_bytes(rows):
    s=io.StringIO(newline='')
    w=csv.writer(s,lineterminator='\n')
    w.writerow(['race_id','race_date','venue_code','grade','url','data_status'])
    w.writerows(rows)
    return s.getvalue().encode()

def rediscover_locked(timeout=25):
    rows=[]
    for d in daterange(date(2026,3,1),date(2026,6,30)):
        rows.extend(discover_day(d,timeout))
    rows=sorted({r[0]:r for r in rows}.values(),key=lambda r:(r[1],r[2],int(r[0][-4:])))
    csha=sha256_bytes(canonical_csv_bytes(rows))
    if len(rows)!=EXPECTED_CANDIDATE_COUNT or csha!=EXPECTED_CANDIDATE_SHA:
        raise ValueError(f'FAIL-CLOSED:candidate_lock_mismatch count={len(rows)} sha={csha}')
    first=rows[:EXPECTED_5000_COUNT]
    fsha=sha256_bytes(canonical_csv_bytes(first))
    if len(first)!=EXPECTED_5000_COUNT or fsha!=EXPECTED_5000_SHA:
        raise ValueError(f'FAIL-CLOSED:5000_lock_mismatch sha={fsha}')
    return first

def parse_float_token(x,label):
    x=clean(x)
    if not DEC_RE.fullmatch(x): raise ValueError(f'FAIL-CLOSED:{label}_token={x!r}')
    return float(x)

def parse_int_token(x,label):
    x=clean(x)
    if not INT_RE.fullmatch(x): raise ValueError(f'FAIL-CLOSED:{label}_token={x!r}')
    return int(x)

def find_pre_table(soup):
    matches=[]
    for t in soup.find_all('table'):
        tt=compact(t.get_text(' ',strip=True))
        if all(k in tt for k in ('直近4ヶ月の成績','競走得点','勝率','2連対率','3連対率')):
            matches.append(t)
    if len(matches)!=1:
        raise ValueError(f'FAIL-CLOSED:pre_table_count={len(matches)}')
    return matches[0]

def parse_pre(b,exact_url):
    soup=BeautifulSoup(b.decode('utf-8','replace'),'html.parser')
    title=clean(soup.title.get_text(' ',strip=True)) if soup.title else ''
    m=re.search(r'/racedetail/(\d+)/',exact_url)
    dm=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',title)
    rm=re.search(r'(?:^|\s)(\d{1,2})R(?:\s|$)',title)
    venue=title.split('競輪',1)[0].strip() if '競輪' in title else ''
    if not m or not dm or not rm or not venue: raise ValueError('FAIL-CLOSED:meta')
    rid=m.group(1)
    race_date=f'{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}'
    race_no=int(rm.group(1))
    table=find_pre_table(soup)

    table_compact=compact(table.get_text(' ',strip=True))
    semantic_order=['脚質','ギヤ倍数','直近4ヶ月の成績','競走得点','S','B','逃','捲','差','マ','勝率','2連対率','3連対率']
    # Coarse header firewall: all labels must exist. Row parsing below supplies strict positions.
    for label in semantic_order:
        if label not in table_compact:
            raise ValueError(f'FAIL-CLOSED:missing_header_semantic={label}')

    out=[]; seen=set(); h=sha256_bytes(b)
    for tr in table.find_all('tr'):
        els=tr.find_all(['th','td'])
        cells=[clean(x.get_text(' ',strip=True)) for x in els]
        ci=next((i for i,c in enumerate(cells) if CLASS_RE.fullmatch(c)),None)
        if ci is None or ci<1: continue

        cars=[int(c) for c in cells[:ci-1] if re.fullmatch(r'[1-9]',c)]
        if not cars: continue
        car=cars[-1]
        if car in seen: raise ValueError('FAIL-CLOSED:duplicate_car')

        if ci+3>=len(cells): raise ValueError('FAIL-CLOSED:short_identity_prefix')
        rider=cells[ci-1]
        style=cells[ci+1]
        if style not in {'逃','追','両'}: raise ValueError(f'FAIL-CLOSED:style={style!r}')

        gear=parse_float_token(cells[ci+2],'gear_ratio')
        score=parse_float_token(cells[ci+3],'competition_score')
        if not (2.0 <= gear <= 5.0):
            raise ValueError(f'FAIL-CLOSED:gear_range={gear}')
        if not (40.0 <= score <= 130.0):
            raise ValueError(f'FAIL-CLOSED:score_range={score}')
        # Explicit anti-regression: a gear-like score is never accepted.
        if score < 40.0 or abs(score-gear)<1e-12:
            raise ValueError('FAIL-CLOSED:gear_score_semantic_collision')

        tail=cells[ci+4:]
        if len(tail)<13:
            raise ValueError(f'FAIL-CLOSED:stats_tail_len={len(tail)}')
        counts=[parse_int_token(tail[i],f'count_{i}') for i in range(10)]
        S,B,nige,makuri,sashi,mark=counts[:6]
        # counts[6:10] are 1着/2着/3着/着外, intentionally not emitted.
        rates=[parse_float_token(x,f'rate_{j}') for j,x in enumerate(tail[-3:])]
        if any(not (0.0<=x<=100.0) for x in rates):
            raise ValueError(f'FAIL-CLOSED:rate_range={rates}')
        # Require the three rates to follow the ten count columns with no unknown semantic drift.
        middle=tail[10:-3]
        if any(clean(x) for x in middle):
            raise ValueError(f'FAIL-CLOSED:unexpected_mid_tail={middle!r}')

        out.append({
          'race_id':rid,'race_date':race_date,'venue':venue,'race_no':race_no,
          'car_no':car,'rider_name_raw':rider,'class':cells[ci],'style':style,
          'gear_ratio':gear,'competition_score':score,'S':S,'B':B,
          'nige':nige,'makuri':makuri,'sashi':sashi,'mark':mark,
          'win_rate':rates[0],'quinella_rate':rates[1],'trio_rate':rates[2],
          'source_url':exact_url,'source_file_sha256':h,'evidence_role':ROLE
        })
        seen.add(car)

    out.sort(key=lambda x:x['car_no'])
    if len(out)<5: raise ValueError('FAIL-CLOSED:too_few_rows')
    if [r['car_no'] for r in out]!=list(range(1,max(r['car_no'] for r in out)+1)):
        raise ValueError('FAIL-CLOSED:car_continuity')
    return out

def acquire_one(pos,row,timeout):
    rid,rdate,_,_,url,_=row
    last=None
    for attempt in range(3):
        try:
            b,final=fetch(url,timeout)
            if final.rstrip('/')!=url.rstrip('/'): raise ValueError('FAIL-CLOSED:detail_redirect')
            pr=parse_pre(b,url)
            if pr[0]['race_id']!=rid or pr[0]['race_date']!=rdate:
                raise ValueError('FAIL-CLOSED:identity_mismatch')
            return {'ok':True,'position':pos,'rows':pr,'summary':{
              'position':pos,'race_id':rid,'race_date':rdate,'pre_rows':len(pr),
              'source_file_sha256':pr[0]['source_file_sha256']
            }}
        except Exception as e:
            last=str(e); time.sleep(0.5*(attempt+1))
    return {'ok':False,'position':pos,'summary':{
      'position':pos,'race_id':rid,'race_date':rdate,'reason':last
    }}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--start-position',type=int,default=2001)
    ap.add_argument('--end-position',type=int,default=2500)
    ap.add_argument('--workers',type=int,default=8)
    ap.add_argument('--timeout',type=int,default=25)
    ap.add_argument('--pre-csv',required=True)
    ap.add_argument('--receipt',required=True)
    a=ap.parse_args()
    if not 1<=a.start_position<=a.end_position<=5000: raise SystemExit('invalid position range')

    locked=rediscover_locked(a.timeout)
    selected=[(i+1,locked[i]) for i in range(a.start_position-1,a.end_position)]
    got=[]
    with ThreadPoolExecutor(max_workers=max(1,min(a.workers,12))) as ex:
        fut=[ex.submit(acquire_one,pos,row,a.timeout) for pos,row in selected]
        for f in as_completed(fut): got.append(f.result())
    got.sort(key=lambda x:x['position'])
    rows=[r for g in got if g['ok'] for r in g['rows']]

    Path(a.pre_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(a.pre_csv,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)

    accepted=[g['summary'] for g in got if g['ok']]
    rejected=[g['summary'] for g in got if not g['ok']]
    receipt={
      'record':'KEIRIN_NEXTGEN5000_PRE_ONLY_BULK_RECOVERY_RECEIPT_v2',
      'status':'PASS' if not rejected else 'PASS_WITH_REJECTIONS',
      'locked_5000_sha256':EXPECTED_5000_SHA,
      'start_position':a.start_position,'end_position':a.end_position,
      'requested_races':len(selected),'successful_races':len(accepted),
      'rejected_races':len(rejected),'pre_rows':len(rows),
      'accepted':accepted,'rejected':rejected,
      'parser_semantics':'class/style/gear/score + exact S,B,逃,捲,差,マ + win/quinella/trio rates',
      'v1_gear_score_bug_fixed':True,
      'raw_mixed_html_written':False,'result_fields_emitted':False,
      'payout_fields_emitted':False,'odds_fields_emitted':False,
      'forecast_or_comment_fields_emitted':False,
      'formal_support_increment_authorized':False,'model_promotion_authorized':False,
      'evidence_role':ROLE
    }
    Path(a.receipt).write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in {'accepted','rejected'}},ensure_ascii=False,sort_keys=True))
    return 0 if len(accepted)>=int(0.95*len(selected)) else 3

if __name__=='__main__':
    raise SystemExit(main())
