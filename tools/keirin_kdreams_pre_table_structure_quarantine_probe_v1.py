#!/usr/bin/env python3
"""Sanitized PRE-table structure probe for KDreams racedetail pages.

Research-only. Raw mixed HTML remains in memory and is never printed or
persisted. Emits only race metadata and PRE-table structural facts that are
already within the HFT PRE schema family: field row count, observed class-token
set, style-token set, score/tactical-count shape booleans, and source SHA256.
Never emits rider names, result, payout, odds, forecast, comments, narabiyoso,
or arbitrary page text.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

HOST='keirin.kdreams.jp'; MAX_BYTES=8*1024*1024
UA='Mozilla/5.0 (compatible; MultiverseKeirinResearch/PREStructureProbe1.0)'

def clean(s:str)->str:return re.sub(r'\s+',' ',unescape(s or '')).strip()
def validate(url:str)->str:
    p=urlparse(url)
    if p.scheme!='https' or p.hostname!=HOST or p.query or p.fragment or not re.fullmatch(r'/[^/]+/racedetail/\d+/?',p.path):
        raise ValueError('FAIL-CLOSED:url')
    return url

def fetch(url:str,timeout:int)->tuple[bytes,str]:
    validate(url); req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
    with urlopen(req,timeout=timeout) as r:
        final=r.geturl(); validate(final); ct=(r.headers.get('Content-Type') or '').lower(); data=r.read(MAX_BYTES+1)
    if 'text/html' not in ct and 'application/xhtml' not in ct: raise ValueError('FAIL-CLOSED:non_html')
    if not 500<=len(data)<=MAX_BYTES: raise ValueError('FAIL-CLOSED:size')
    return data,final

def analyze(data:bytes,url:str)->dict:
    s=BeautifulSoup(data.decode('utf-8',errors='replace'),'html.parser')
    title=clean(s.title.get_text(' ',strip=True)) if s.title else ''
    rid=re.search(r'/racedetail/(\d+)/',url); rm=re.search(r'(?:^|\s)(\d{1,2})R(?:\s|$)',title)
    venue=title.split('競輪',1)[0].strip() if '競輪' in title else None
    dm=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',title)
    if not rid or not rm or not venue or not dm: raise ValueError('FAIL-CLOSED:metadata')
    race_date=f'{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}'
    table=None
    for t in s.find_all('table'):
        tt=clean(t.get_text(' ',strip=True))
        if '直近4ヶ月の成績' in tt and '競走得点' in tt and '2連 対率' in tt:
            table=t; break
    if table is None: raise ValueError('FAIL-CLOSED:no_pre_table')
    classes=[]; styles=[]; row_shapes=[]
    for tr in table.find_all('tr'):
        cells=[clean(x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'])]
        # Emit only allowlisted-domain tokens, never arbitrary text.
        class_hits=[c for c in cells if re.fullmatch(r'(?:[SA][123]|L1)',c)]
        if not class_hits: continue
        cls=class_hits[0]; ci=cells.index(cls)
        style_hits=[c for c in cells[ci+1:ci+3] if c in {'逃','追','両'}]
        score_hits=[c for c in cells[ci+1:] if re.fullmatch(r'\d{1,3}\.\d{2}',c)]
        tactical=[]
        if score_hits:
            si=cells.index(score_hits[0],ci+1)
            for c in cells[si+1:]:
                if re.fullmatch(r'\d{1,2}',c): tactical.append(int(c))
                if len(tactical)==6: break
        classes.append(cls); styles.extend(style_hits[:1])
        row_shapes.append({'class_token':cls,'style_token_present':bool(style_hits),'competition_score_token_present':bool(score_hits),'six_tactical_integer_tokens_present':len(tactical)==6})
    return {'race_id':rid.group(1),'race_date':race_date,'venue':venue,'race_no':int(rm.group(1)),'pre_table_found':True,'recognized_structural_rows':len(row_shapes),'class_tokens':sorted(set(classes)),'style_tokens':sorted(set(styles)),'all_rows_have_score_token':bool(row_shapes) and all(x['competition_score_token_present'] for x in row_shapes),'all_rows_have_six_tactical_integer_tokens':bool(row_shapes) and all(x['six_tactical_integer_tokens_present'] for x in row_shapes),'source_file_sha256':hashlib.sha256(data).hexdigest()}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--url',action='append',required=True); ap.add_argument('--out',required=True); ap.add_argument('--timeout',type=int,default=25); a=ap.parse_args()
    records=[]; rejects=[]
    for u in a.url:
        try:
            raw,final=fetch(u,a.timeout); records.append(analyze(raw,final))
        except Exception as e: rejects.append({'url':u,'reason':str(e)})
    out={'record':'KEIRIN_KDREAMS_PRE_TABLE_STRUCTURE_QUARANTINE_PROBE_v1','records':records,'rejects':rejects,'raw_html_persisted':False,'raw_html_printed':False,'rider_names_emitted':False,'result_fields_emitted':False,'payout_fields_emitted':False,'odds_fields_emitted':False,'forecast_fields_emitted':False,'comments_emitted':False,'narabiyoso_emitted':False}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'records':len(records),'rejects':len(rejects)},sort_keys=True)); return 0 if not rejects else 3
if __name__=='__main__': raise SystemExit(main())
