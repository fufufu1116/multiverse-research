#!/usr/bin/env python3
"""Sanitized KDreams historical racecard day-navigation probe.

Research-only transport diagnostic. Raw HTML stays in memory and is never
printed or written. The only emitted page-derived values are validated KDreams
racecard day URLs, race date/venue metadata, and tightly categorized short day
navigation labels. No result, payout, odds, forecasts, comments, line text, or
race-detail content is emitted.
"""
from __future__ import annotations
import argparse,hashlib,json,re,unicodedata
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup

HOST='keirin.kdreams.jp'; MAX_BYTES=8*1024*1024
UA='Mozilla/5.0 (compatible; MultiverseKeirinResearch/DayNavProbe1.0; PRE-only)'

def clean(s:str)->str:return re.sub(r'\s+',' ',unescape(s or '')).strip()
def norm(s:str)->str:return unicodedata.normalize('NFKC',clean(s))
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def validate(url:str,kind:str)->str:
 p=urlparse(url)
 if p.scheme!='https' or p.hostname!=HOST or p.query or p.fragment:raise ValueError('FAIL-CLOSED:url')
 ok={'index':r'/[^/]+/racecard/?','day':r'/[^/]+/racecard/\d+/?'}[kind]
 if not re.fullmatch(ok,p.path):raise ValueError('FAIL-CLOSED:url_kind')
 return url

def fetch(url:str,kind:str,timeout:int)->tuple[bytes,str]:
 validate(url,kind); req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
 with urlopen(req,timeout=timeout) as r:
  final=r.geturl(); validate(final,kind); ct=(r.headers.get('Content-Type') or '').lower(); data=r.read(MAX_BYTES+1)
 if 'text/html' not in ct and 'application/xhtml' not in ct:raise ValueError('FAIL-CLOSED:non_html')
 if not 500<=len(data)<=MAX_BYTES:raise ValueError('FAIL-CLOSED:size')
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

def category(text:str)->str:
 t=norm(text)
 if '初日' in t:return 'INITIAL_DAY_EXPLICIT'
 if re.search(r'(^|\D)1日目($|\D)',t) or re.search(r'第1日($|\D)',t):return 'INITIAL_DAY_EXPLICIT'
 if '最終日' in t:return 'FINAL_DAY_EXPLICIT'
 m=re.search(r'([2-9])日目',t)
 if m:return f'DAY_{m.group(1)}_EXPLICIT'
 if re.fullmatch(r'\d{1,2}月\d{1,2}日',t) or re.fullmatch(r'\d{1,2}/\d{1,2}',t):return 'DATE_LABEL_ONLY'
 return 'OTHER_OR_EMPTY'

def day_links(data:bytes,base:str)->list[dict]:
 s=soup(data); out=[]; seen=set()
 for pos,a in enumerate(s.find_all('a',href=True)):
  u=urljoin(base,a.get('href'))
  try:validate(u,'day')
  except Exception:continue
  if u in seen:continue
  seen.add(u)
  txt=clean(a.get_text(' ',strip=True)); aria=clean(str(a.get('aria-label',''))); title=clean(str(a.get('title','')))
  cats=sorted(set([category(txt),category(aria),category(title)])-{'OTHER_OR_EMPTY'})
  out.append({'position':pos,'target_day_url':u,'label_categories':cats or ['OTHER_OR_EMPTY']})
 return out

def run(index_urls:list[str],timeout:int)->dict:
 records=[]; failures=[]
 for idx in index_urls:
  try:
   raw_idx,final_idx=fetch(idx,'index',timeout)
   for seed in day_links(raw_idx,final_idx):
    su=seed['target_day_url']
    try:
     raw_seed,final_seed=fetch(su,'day',timeout); ss=soup(raw_seed); title=clean(ss.title.get_text(' ',strip=True)) if ss.title else ''
     seed_date=parse_date(title) or parse_date(clean(ss.get_text(' ',strip=True))[:10000]); venue=parse_venue(title)
     nav=[]
     for link in day_links(raw_seed,final_seed):
      tu=link['target_day_url']
      td=None;tv=None;th=None
      try:
       raw_t,final_t=fetch(tu,'day',timeout); ts=soup(raw_t); tt=clean(ts.title.get_text(' ',strip=True)) if ts.title else ''
       td=parse_date(tt) or parse_date(clean(ts.get_text(' ',strip=True))[:10000]); tv=parse_venue(tt); th=sha(raw_t)
      except Exception as exc:
       failures.append({'url':tu,'reason':str(exc)})
      nav.append({**link,'target_race_date':td,'target_venue':tv,'target_source_sha256':th})
     records.append({'archive_index_url':final_idx,'seed_day_url':final_seed,'seed_race_date':seed_date,'seed_venue':venue,'seed_source_sha256':sha(raw_seed),'navigation':nav})
    except Exception as exc:failures.append({'url':su,'reason':str(exc)})
  except Exception as exc:failures.append({'url':idx,'reason':str(exc)})
 return {'record':'KEIRIN_KDREAMS_HISTORICAL_DAYNAV_QUARANTINE_PROBE_v1','records':records,'failures':failures[:100],'raw_html_persisted':False,'raw_html_printed':False,'race_detail_opened':False,'target_result_accessed':False,'payout_accessed':False,'odds_emitted':False,'forecast_emitted':False,'comment_emitted':False,'narabiyoso_emitted':False}

def selftest()->dict:
 html=b"<html><body><a href='/kawasaki/racecard/34202608300100/'>1\xe6\x97\xa5\xe7\x9b\xae</a><a href='/kawasaki/racecard/34202608300300/'>\xe6\x9c\x80\xe7\xb5\x82\xe6\x97\xa5</a><a href='https://evil.example/x'>\xe5\x88\x9d\xe6\x97\xa5</a></body></html>"
 x=day_links(html,'https://keirin.kdreams.jp/kawasaki/racecard/34202608300300/')
 tests={'two_valid_day_links':len(x)==2,'initial_category':x[0]['label_categories']==['INITIAL_DAY_EXPLICIT'],'final_category':x[1]['label_categories']==['FINAL_DAY_EXPLICIT']}
 return {'record':'KEIRIN_KDREAMS_HISTORICAL_DAYNAV_QUARANTINE_PROBE_SELFTEST_v1','status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'network_access':False}

def main()->int:
 ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest'); p=sub.add_parser('probe'); p.add_argument('--archive-url',action='append',required=True); p.add_argument('--out',required=True); p.add_argument('--timeout',type=int,default=25); a=ap.parse_args()
 if a.cmd=='selftest':
  x=selftest();print(json.dumps(x,ensure_ascii=False,sort_keys=True));return 0 if x['status']=='PASS' else 2
 x=run(a.archive_url,a.timeout);Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');print(json.dumps({'record':x['record'],'records':len(x['records']),'failures':len(x['failures'])},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
