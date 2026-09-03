#!/usr/bin/env python3
"""Research-only KDreams historical PRE quarantine fetcher v2.

Extends v1 discovery by following only positively observed archive day hrefs and
explicit links whose visible label is exactly "初日". Mixed HTML remains in
memory only. Outputs are limited to strict PRE allowlist fields and sanitized
provenance/receipts. No race-detail ID is derived or guessed.
"""
from __future__ import annotations

import argparse,csv,hashlib,json,re
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any,Iterable
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from bs4 import BeautifulSoup

HOST="keirin.kdreams.jp"
UA="Mozilla/5.0 (compatible; MultiverseKeirinResearch/2.0; PRE-only)"
MAX_BYTES=8*1024*1024
EVIDENCE_ROLE="HISTORICAL_PIT_PRE_SUPPORT_CANDIDATE_ONLY"
ALLOWED_PRE_FIELDS=["race_id","race_date","venue","race_no","car_no","rider_name_raw","class","style","competition_score","S","B","nige","makuri","sashi","mark","source_url","source_file_sha256","evidence_role"]
FORBIDDEN_OUTPUT_KEYS={"result","finish","finish_1","finish_2","finish_3","payout","settlement","odds","forecast","prediction","tips","comment","narabiyoso","roi","ev"}

def clean(s:str)->str:return re.sub(r"\s+"," ",unescape(s or "")).strip()
def sha256_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def validate_url(url:str,allowed:set[str])->str:
 p=urlparse(url)
 if p.scheme!="https" or p.hostname!=HOST:raise ValueError("FAIL-CLOSED:non_kdreams_https_url")
 if p.query or p.fragment:raise ValueError("FAIL-CLOSED:query_or_fragment_forbidden")
 kind=None
 if re.fullmatch(r"/[^/]+/racecard/?",p.path):kind="archive_index"
 elif re.fullmatch(r"/[^/]+/racecard/\d+/?",p.path):kind="day"
 elif re.fullmatch(r"/[^/]+/racedetail/\d+/?",p.path):kind="detail"
 if kind not in allowed:raise ValueError(f"FAIL-CLOSED:url_kind={kind}")
 return url

def fetch_bytes(url:str,timeout:int=25)->tuple[bytes,str]:
 validate_url(url,{"archive_index","day","detail"})
 req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
 with urlopen(req,timeout=timeout) as r:
  final=r.geturl();validate_url(final,{"archive_index","day","detail"})
  ctype=(r.headers.get("Content-Type") or "").lower()
  if "text/html" not in ctype and "application/xhtml" not in ctype:raise ValueError("FAIL-CLOSED:non_html_content_type")
  data=r.read(MAX_BYTES+1)
 if len(data)>MAX_BYTES:raise ValueError("FAIL-CLOSED:html_too_large")
 if len(data)<500:raise ValueError("FAIL-CLOSED:html_too_small")
 return data,final

def soup_from_bytes(data:bytes)->BeautifulSoup:return BeautifulSoup(data.decode("utf-8",errors="replace"),"html.parser")

def parse_date(text:str)->str|None:
 m=re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日",text) or re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})",text)
 if not m:return None
 y,mo,d=map(int,m.groups())
 try:return date(y,mo,d).isoformat()
 except ValueError:return None

def parse_venue(title:str)->str|None:
 t=clean(title)
 if "競輪" not in t:return None
 v=t.split("競輪",1)[0].strip();return v or None

def canonical_url(soup:BeautifulSoup,fallback:str)->str:
 c=soup.find("link",rel="canonical");u=c.get("href") if c else fallback
 validate_url(u,{"archive_index","day","detail"});return u

def detect_day1(soup:BeautifulSoup,current_url:str)->tuple[bool,str]:
 cp=urlparse(current_url).path.rstrip("/")+"/";positives=[]
 for a in soup.find_all("a",href=True):
  if clean(a.get_text(" ",strip=True))!="初日":continue
  u=urljoin(current_url,a.get("href"))
  try:validate_url(u,{"day"})
  except Exception:continue
  if urlparse(u).path.rstrip("/")+"/"==cp:positives.append("CURRENT_HREF_LABEL_INITIAL_DAY")
 for e in soup.find_all(["li","span","div"]):
  if clean(e.get_text(" ",strip=True))!="初日":continue
  classes=" ".join(e.get("class",[]));aria=str(e.get("aria-current",""))
  if re.search(r"(?:^|\s)(?:active|current|selected|on)(?:\s|$)",classes,re.I) or aria in {"page","true"}:positives.append("ACTIVE_TAB_LABEL_INITIAL_DAY")
 return (True,"+".join(sorted(set(positives)))) if positives else (False,"NO_POSITIVE_INITIAL_DAY_ASSOCIATION")

def collect_links(html:bytes,base:str,kind:str)->list[str]:
 soup=soup_from_bytes(html);out=set()
 for a in soup.find_all("a",href=True):
  u=urljoin(base,a.get("href"))
  try:validate_url(u,{kind})
  except Exception:continue
  out.add(u)
 return sorted(out)

def collect_explicit_initial_day_links(html:bytes,base:str)->list[str]:
 soup=soup_from_bytes(html);out=set()
 for a in soup.find_all("a",href=True):
  if clean(a.get_text(" ",strip=True))!="初日":continue
  u=urljoin(base,a.get("href"))
  try:validate_url(u,{"day"})
  except Exception:continue
  out.add(u)
 return sorted(out)

def _build_day1_block(raw_day:bytes,final_day:str,positive_source:str,start_d:date,end_d:date)->dict[str,Any]|None:
 soup=soup_from_bytes(raw_day)
 title=clean(soup.title.get_text(" ",strip=True)) if soup.title else "";full=clean(soup.get_text(" ",strip=True))
 race_date=parse_date(title) or parse_date(full[:10000])
 if not race_date:raise ValueError("FAIL-CLOSED:day_date_missing")
 d=date.fromisoformat(race_date)
 if d<start_d or d>end_d:return None
 venue=parse_venue(title)
 if not venue:raise ValueError("FAIL-CLOSED:day_venue_missing")
 self_day1,self_evidence=detect_day1(soup,final_day)
 externally_positive=positive_source=="EXPLICIT_INITIAL_DAY_HREF_FROM_SEED"
 day1=bool(self_day1 or externally_positive)
 evidence=self_evidence if self_day1 else (positive_source if externally_positive else "NO_POSITIVE_INITIAL_DAY_ASSOCIATION")
 details=collect_links(raw_day,final_day,"detail") if day1 else []
 if day1 and not 5<=len(details)<=12:raise ValueError(f"FAIL-CLOSED:day1_detail_count={len(details)}")
 return {"race_date":race_date,"venue":venue,"day_url":final_day,"day_source_sha256":sha256_bytes(raw_day),"day1_confirmed":day1,"day1_evidence":evidence,"discovery_path":positive_source,"detail_urls":details,"detail_count":len(details)}

def discover_archive(index_urls:Iterable[str],start:str,end:str,timeout:int)->dict[str,Any]:
 start_d,end_d=date.fromisoformat(start),date.fromisoformat(end);blocks=[];failures=[];seen_candidates=set()
 for idx in index_urls:
  try:
   validate_url(idx,{"archive_index"});raw_idx,final_idx=fetch_bytes(idx,timeout)
   seed_urls=collect_links(raw_idx,final_idx,"day")
   for seed_url in seed_urls:
    try:
     raw_seed,final_seed=fetch_bytes(seed_url,timeout)
     candidates=[(final_seed,"ARCHIVE_INDEX_DAY_HREF")]
     for u in collect_explicit_initial_day_links(raw_seed,final_seed):
      candidates.append((u,"EXPLICIT_INITIAL_DAY_HREF_FROM_SEED"))
     for candidate_url,positive_source in candidates:
      key=(candidate_url,positive_source)
      if key in seen_candidates:continue
      seen_candidates.add(key)
      try:
       if candidate_url==final_seed:raw_day,final_day=raw_seed,final_seed
       else:raw_day,final_day=fetch_bytes(candidate_url,timeout)
       block=_build_day1_block(raw_day,final_day,positive_source,start_d,end_d)
       if block is not None:blocks.append(block)
      except Exception as exc:failures.append({"url":candidate_url,"reason":str(exc)})
    except Exception as exc:failures.append({"url":seed_url,"reason":str(exc)})
  except Exception as exc:failures.append({"url":idx,"reason":str(exc)})
 dedup={}
 rank={"EXPLICIT_INITIAL_DAY_HREF_FROM_SEED":2,"ARCHIVE_INDEX_DAY_HREF":1}
 for b in blocks:
  k=b["day_url"]
  old=dedup.get(k)
  if old is None or rank.get(b.get("discovery_path",""),0)>rank.get(old.get("discovery_path",""),0):dedup[k]=b
 blocks=sorted(dedup.values(),key=lambda x:(x["race_date"],x["venue"],x["day_url"]))
 return {"record":"KEIRIN_KDREAMS_HISTORICAL_DAY1_DISCOVERY_v2","start":start,"end":end,"blocks":blocks,"confirmed_day1_blocks":sum(1 for b in blocks if b["day1_confirmed"]),"explicit_initial_day_hrefs_followed":sum(1 for b in blocks if b.get("discovery_path")=="EXPLICIT_INITIAL_DAY_HREF_FROM_SEED"),"failures":failures[:100],"raw_html_emitted":False,"result_fields_emitted":False,"odds_fields_emitted":False,"forecast_fields_emitted":False,"race_id_guessed":False}

def parse_detail_pre(data:bytes,fallback_url:str)->list[dict[str,Any]]:
 soup=soup_from_bytes(data);title=clean(soup.title.get_text(" ",strip=True)) if soup.title else "";url=canonical_url(soup,fallback_url);validate_url(url,{"detail"})
 m=re.search(r"/racedetail/(\d+)/",url);race_date=parse_date(title);rm=re.search(r"(?:^|\s)(\d{1,2})R(?:\s|$)",title);venue=parse_venue(title)
 if not m or not race_date or not rm or not venue:raise ValueError("FAIL-CLOSED:race_metadata")
 rid=m.group(1);race_no=int(rm.group(1));table=None
 for t in soup.find_all("table"):
  tt=clean(t.get_text(" ",strip=True))
  if "直近4ヶ月の成績" in tt and "競走得点" in tt and "2連 対率" in tt:table=t;break
 if table is None:raise ValueError("FAIL-CLOSED:no_pre_table")
 rows=[];seen=set();h=sha256_bytes(data)
 for tr in table.find_all("tr"):
  cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])];ci=next((i for i,c in enumerate(cells) if re.fullmatch(r"[SA][123]",c)),None)
  if ci is None or ci<1:continue
  cars=[int(c) for c in cells[:ci-1] if re.fullmatch(r"[1-9]",c)]
  if not cars:continue
  car=cars[-1]
  if car in seen:raise ValueError(f"FAIL-CLOSED:duplicate_car={car}")
  rider=cells[ci-1]
  if not rider:raise ValueError(f"FAIL-CLOSED:missing_rider={car}")
  style=cells[ci+1] if ci+1<len(cells) and cells[ci+1] in {"逃","追","両"} else None
  si=next((i for i in range(ci+1,len(cells)) if re.fullmatch(r"\d{2,3}\.\d{2}",cells[i])),None)
  if si is None:raise ValueError(f"FAIL-CLOSED:missing_competition_score={car}")
  score=float(cells[si])
  if score==0.0:raise ValueError(f"FAIL-CLOSED:zero_competition_score={car}")
  vals=[]
  for c in cells[si+1:]:
   if re.fullmatch(r"\d{1,2}",c):vals.append(int(c))
   if len(vals)==6:break
  if len(vals)!=6:raise ValueError(f"FAIL-CLOSED:missing_tactical_counts={car}")
  S,B,nige,makuri,sashi,mark=vals
  row={"race_id":rid,"race_date":race_date,"venue":venue,"race_no":race_no,"car_no":car,"rider_name_raw":rider,"class":cells[ci],"style":style,"competition_score":score,"S":S,"B":B,"nige":nige,"makuri":makuri,"sashi":sashi,"mark":mark,"source_url":url,"source_file_sha256":h,"evidence_role":EVIDENCE_ROLE}
  if set(row)!=set(ALLOWED_PRE_FIELDS):raise ValueError("FAIL-CLOSED:output_schema_drift")
  if any(k.lower() in FORBIDDEN_OUTPUT_KEYS for k in row):raise ValueError("FAIL-CLOSED:forbidden_output_key")
  rows.append(row);seen.add(car)
 rows.sort(key=lambda x:x["car_no"])
 if len(rows)<5:raise ValueError(f"FAIL-CLOSED:pre_rows={len(rows)}")
 if [r["car_no"] for r in rows]!=list(range(1,max(r["car_no"] for r in rows)+1)):raise ValueError("FAIL-CLOSED:active_car_continuity")
 return rows

def acquire_manifest(manifest:dict[str,Any],timeout:int)->tuple[list[dict[str,Any]],dict[str,Any]]:
 rows=[];accepted=[];rejected=[]
 for block in manifest.get("blocks",[]):
  if not block.get("day1_confirmed"):continue
  for u in block.get("detail_urls",[]):
   try:
    validate_url(u,{"detail"});raw,final=fetch_bytes(u,timeout);pr=parse_detail_pre(raw,final);rows.extend(pr);accepted.append({"race_id":pr[0]["race_id"],"race_date":pr[0]["race_date"],"venue":pr[0]["venue"],"race_no":pr[0]["race_no"],"pre_rows":len(pr),"source_file_sha256":pr[0]["source_file_sha256"]})
   except Exception as exc:rejected.append({"url":u,"reason":str(exc)})
 keys=[(x["race_date"],x["venue"],x["race_no"]) for x in accepted]
 if len(keys)!=len(set(keys)):raise ValueError("FAIL-CLOSED:duplicate_accepted_race")
 receipt={"record":"KEIRIN_KDREAMS_HISTORICAL_PRE_QUARANTINE_FETCH_RECEIPT_v2","successful_races":len(accepted),"pre_rows":len(rows),"accepted":accepted,"rejected":rejected[:100],"raw_html_written_to_disk":False,"raw_html_printed":False,"result_fields_emitted":False,"payout_fields_emitted":False,"odds_fields_emitted":False,"forecast_fields_emitted":False,"narabiyoso_fields_emitted":False,"race_id_guessed":False,"support_increment_authorized_by_tool":False}
 return rows,receipt

def write_csv(rows:list[dict[str,Any]],path:Path)->None:
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=ALLOWED_PRE_FIELDS);w.writeheader();w.writerows(rows)

def synthetic_detail()->bytes:
 rows=[]
 for i,n in enumerate(["選手一","選手二","選手三","選手四","選手五"],1):rows.append(f"<tr><td>{i}</td><td>{n}</td><td>A1</td><td>逃</td><td>99.{i:02d}</td><td>{i%3}</td><td>{i}</td><td>1</td><td>2</td><td>3</td><td>4</td></tr>")
 return ("<html><head><title>防府競輪 2026年08月31日 1R test</title><link rel='canonical' href='https://keirin.kdreams.jp/hofu/racedetail/6312345678900001/'></head><body><table><tr><th>直近4ヶ月の成績</th><th>競走得点</th><th>2連 対率</th></tr>"+"".join(rows)+"</table><table><tr><th>着 順</th></tr><tr><td>1</td></tr></table><div>予想 オッズ 並び予想 コメント</div></body></html>").encode("utf-8")

def selftest()->dict[str,Any]:
 tests={};r=parse_detail_pre(synthetic_detail(),"https://keirin.kdreams.jp/hofu/racedetail/6312345678900001/")
 tests["pre_rows_5"]=len(r)==5;tests["schema_exact_allowlist"]=all(set(x)==set(ALLOWED_PRE_FIELDS) for x in r);tests["mixed_forbidden_text_not_emitted"]=all(not any(k in json.dumps(x,ensure_ascii=False).lower() for k in ["予想","オッズ","着 順","コメント"]) for x in r)
 try:validate_url("https://keirin.kdreams.jp/hofu/racedetail/6312345678900001/?pageType=result",{"detail"});tests["query_rejected"]=False
 except ValueError:tests["query_rejected"]=True
 seed=("<html><head><title>川崎競輪 2026年09月01日 3日目</title></head><body><a href='/kawasaki/racecard/34202608300100/'>初日</a><a href='/kawasaki/racedetail/3412345678900001/'>1R</a></body></html>").encode("utf-8")
 links=collect_explicit_initial_day_links(seed,"https://keirin.kdreams.jp/kawasaki/racecard/34202608300300/")
 tests["explicit_initial_day_href_collected"]=links==["https://keirin.kdreams.jp/kawasaki/racecard/34202608300100/"]
 try:validate_url("https://evil.example/kawasaki/racecard/34202608300100/",{"day"});tests["foreign_host_rejected"]=False
 except ValueError:tests["foreign_host_rejected"]=True
 return {"record":"KEIRIN_KDREAMS_HISTORICAL_PRE_QUARANTINE_FETCH_SELFTEST_v2","status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"network_access":False,"race_id_guessing":False}

def main()->int:
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True);sub.add_parser("selftest");d=sub.add_parser("discover");d.add_argument("--archive-url",action="append",required=True);d.add_argument("--start",required=True);d.add_argument("--end",required=True);d.add_argument("--out",required=True);d.add_argument("--timeout",type=int,default=25);a=sub.add_parser("acquire");a.add_argument("--manifest",required=True);a.add_argument("--pre-csv",required=True);a.add_argument("--receipt",required=True);a.add_argument("--timeout",type=int,default=25);args=ap.parse_args()
 if args.cmd=="selftest":out=selftest();print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2));return 0 if out["status"]=="PASS" else 2
 if args.cmd=="discover":out=discover_archive(args.archive_url,args.start,args.end,args.timeout);Path(args.out).write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8");print(json.dumps({k:v for k,v in out.items() if k!="blocks"},ensure_ascii=False,sort_keys=True));return 0
 manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"));rows,receipt=acquire_manifest(manifest,args.timeout);write_csv(rows,Path(args.pre_csv));Path(args.receipt).write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8");print(json.dumps({k:v for k,v in receipt.items() if k not in {"accepted","rejected"}},ensure_ascii=False,sort_keys=True));return 0 if not receipt["rejected"] else 3

if __name__=="__main__":raise SystemExit(main())
