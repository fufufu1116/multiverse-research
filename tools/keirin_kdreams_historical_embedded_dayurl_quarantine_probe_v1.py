#!/usr/bin/env python3
"""Research-only sanitized probe for positively embedded KDreams racecard day URLs.

Raw HTML stays in memory. The probe emits only validated racecard day URLs,
race-date/venue metadata, SHA256, and day-status categories. It never opens
race-detail/result/payout pages and never prints or persists raw page content.
"""
from __future__ import annotations
import argparse, hashlib, json, re, unicodedata
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

HOST='keirin.kdreams.jp'; MAX_BYTES=8*1024*1024
UA='Mozilla/5.0 (compatible; MultiverseKeirinResearch/EmbeddedDayURLProbe1.0; PRE-only)'

def clean(s:str)->str:return re.sub(r'\s+',' ',unescape(s or '')).strip()
def norm(s:str)->str:return unicodedata.normalize('NFKC',clean(s))
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def validate(url:str,kind:str)->str:
    p=urlparse(url)
    if p.scheme!='https' or p.hostname!=HOST or p.query or p.fragment: raise ValueError('FAIL-CLOSED:url')
    pat={'index':r'/[^/]+/racecard/?','day':r'/[^/]+/racecard/\d+/?'}[kind]
    if not re.fullmatch(pat,p.path): raise ValueError('FAIL-CLOSED:url_kind')
    return url

def fetch(url:str,kind:str,timeout:int)->tuple[bytes,str]:
    validate(url,kind)
    req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
    with urlopen(req,timeout=timeout) as r:
        final=r.geturl(); validate(final,kind); ct=(r.headers.get('Content-Type') or '').lower(); data=r.read(MAX_BYTES+1)
    if 'text/html' not in ct and 'application/xhtml' not in ct: raise ValueError('FAIL-CLOSED:non_html')
    if not 500<=len(data)<=MAX_BYTES: raise ValueError('FAIL-CLOSED:size')
    return data,final

def soup(data:bytes)->BeautifulSoup:return BeautifulSoup(data.decode('utf-8',errors='replace'),'html.parser')
def parse_date(text:str)->str|None:
    m=re.search(r'(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日',text) or re.search(r'(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})',text)
    if not m:return None
    try:return date(*map(int,m.groups())).isoformat()
    except ValueError:return None

def parse_venue(title:str)->str|None:
    t=clean(title)
    return t.split('競輪',1)[0].strip() if '競輪' in t and t.split('競輪',1)[0].strip() else None

def day_category(text:str)->str:
    t=norm(text)
    if '初日' in t or re.search(r'(^|\D)1日目($|\D)',t) or re.search(r'第1日($|\D)',t): return 'INITIAL_DAY_EXPLICIT'
    if '最終日' in t:return 'FINAL_DAY_EXPLICIT'
    m=re.search(r'([2-9])日目',t)
    return f'DAY_{m.group(1)}_EXPLICIT' if m else 'NO_EXPLICIT_DAY_STATUS'

def active_day_category(s:BeautifulSoup)->str:
    cats=[]
    for e in s.find_all(True):
        classes=' '.join(e.get('class',[])); aria=clean(str(e.get('aria-current','')))
        if not (re.search(r'(?:^|\s)(?:active|current|selected|on)(?:\s|$)',classes,re.I) or aria in {'page','true'}): continue
        c=day_category(e.get_text(' ',strip=True))
        if c!='NO_EXPLICIT_DAY_STATUS':cats.append(c)
    u=sorted(set(cats))
    return u[0] if len(u)==1 else ('AMBIGUOUS_ACTIVE_DAY_STATUS' if len(u)>1 else 'NO_EXPLICIT_DAY_STATUS')

def anchor_day_urls(data:bytes,base:str)->list[str]:
    out=set()
    for a in soup(data).find_all('a',href=True):
        u=urljoin(base,a.get('href'))
        try:validate(u,'day')
        except Exception:continue
        out.add(u)
    return sorted(out)

def embedded_day_urls(data:bytes,base:str)->list[str]:
    text=data.decode('utf-8',errors='replace').replace('\\/','/')
    out=set()
    # Exact observed substrings only; no ID arithmetic or construction.
    for m in re.finditer(r'https://keirin\.kdreams\.jp/[^/\s"\'<>]+/racecard/\d+/?',text):
        u=m.group(0)
        try:validate(u,'day')
        except Exception:continue
        out.add(u)
    for m in re.finditer(r'/[^/\s"\'<>]+/racecard/\d+/?',text):
        u=urljoin(base,m.group(0))
        try:validate(u,'day')
        except Exception:continue
        out.add(u)
    return sorted(out)

def metadata(data:bytes,final:str)->dict:
    s=soup(data); title=clean(s.title.get_text(' ',strip=True)) if s.title else ''; visible=clean(s.get_text(' ',strip=True))
    return {'day_url':final,'race_date':parse_date(title) or parse_date(visible[:10000]),'venue':parse_venue(title),'title_day_category':day_category(title),'active_day_category':active_day_category(s),'source_sha256':sha(data)}

def run(index_urls:list[str],timeout:int)->dict:
    records=[]; failures=[]
    for idx in index_urls:
        try:
            raw_i,final_i=fetch(idx,'index',timeout)
            seeds=anchor_day_urls(raw_i,final_i)
            for seed in seeds:
                try:
                    raw_s,final_s=fetch(seed,'day',timeout); sm=metadata(raw_s,final_s)
                    observed=embedded_day_urls(raw_s,final_s)
                    targets=[]
                    for u in observed:
                        try:
                            raw_t,final_t=fetch(u,'day',timeout); tm=metadata(raw_t,final_t); tm['positively_observed_in_seed_raw']=True; targets.append(tm)
                        except Exception as exc:failures.append({'url':u,'reason':str(exc)})
                    records.append({'archive_index_url':final_i,'seed':sm,'embedded_day_urls':targets,'embedded_day_url_count':len(targets)})
                except Exception as exc:failures.append({'url':seed,'reason':str(exc)})
        except Exception as exc:failures.append({'url':idx,'reason':str(exc)})
    return {'record':'KEIRIN_KDREAMS_HISTORICAL_EMBEDDED_DAYURL_QUARANTINE_PROBE_v1','records':records,'failures':failures[:100],'raw_html_persisted':False,'raw_html_printed':False,'race_detail_opened':False,'target_result_accessed':False,'payout_accessed':False,'odds_emitted':False,'forecast_emitted':False,'comment_emitted':False,'narabiyoso_emitted':False,'race_id_guessed':False}

def selftest()->dict:
    raw=("<html><head><title>川崎競輪 2026年08月30日 1日目</title></head><body>"
         "<script>var x='\\/kawasaki\\/racecard\\/34202608300100\\/';</script>"
         "<div data-url='/kawasaki/racecard/34202608300200/'>x</div></body></html>").encode('utf-8')
    urls=embedded_day_urls(raw,'https://keirin.kdreams.jp/kawasaki/racecard/34202608300300/')
    m=metadata(raw,'https://keirin.kdreams.jp/kawasaki/racecard/34202608300100/')
    tests={'two_exact_observed_urls':len(urls)==2,'title_initial_detected':m['title_day_category']=='INITIAL_DAY_EXPLICIT','no_url_guessing':all('/racecard/' in u for u in urls)}
    return {'record':'KEIRIN_KDREAMS_HISTORICAL_EMBEDDED_DAYURL_QUARANTINE_PROBE_SELFTEST_v1','status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'network_access':False,'race_id_guessing':False}

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest'); p=sub.add_parser('probe'); p.add_argument('--archive-url',action='append',required=True); p.add_argument('--out',required=True); p.add_argument('--timeout',type=int,default=25); a=ap.parse_args()
    if a.cmd=='selftest':
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x['status']=='PASS' else 2
    x=run(a.archive_url,a.timeout); Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'record':x['record'],'records':len(x['records']),'failures':len(x['failures']),'embedded_day_urls':sum(r['embedded_day_url_count'] for r in x['records'])},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
