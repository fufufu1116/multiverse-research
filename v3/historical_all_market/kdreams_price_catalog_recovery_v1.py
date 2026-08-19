#!/usr/bin/env python3
"""Multiverse v3.0 All-Market Historical Track — Stage-0 PRICE recovery.

Firewall role: PRICE / MARKET AVAILABILITY ONLY.
NO RESULT, NO PAYOUT, NO REFUND, NO MODEL PROBABILITY, NO EV, NO ROI.
Reads one SHA-bound historical Kdreams showResult HTML payload offline.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, re
from pathlib import Path
from typing import Any
from lxml import html

PARSER_ID = "KDREAMS_PRICE_CATALOG_RECOVERY_v1"
MARKETS = ("3rentan","2shatan","3renhuku","2shahuku","2wakutan","2wakuhuku","wide")

class FailClosed(RuntimeError): pass

def sha256_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def compact(s: Any) -> str: return "".join(str(s).split())
def node_text(n) -> str: return " ".join(" ".join(n.itertext()).split())
def canon_pair(a:int,b:int,ordered:bool)->str:
    a,b=int(a),int(b); return f"{a}-{b}" if ordered else "=".join(map(str,sorted((a,b))))
def canon_triple(a:int,b:int,c:int,ordered:bool)->str:
    x=(int(a),int(b),int(c)); return "-".join(map(str,x)) if ordered else "=".join(map(str,sorted(x)))
def fcell(td):
    s=compact(node_text(td)).replace(',','')
    if not s or s in {'-','—','－','未発売'}: return None
    try: v=float(s)
    except Exception: return None
    return v if math.isfinite(v) and v>0 else None

def _nodes(root,market):
    c=root.xpath(f'//*[@id="JS_ODDSCONTENTS_{market}"]')
    s=root.xpath(f'//*[@id="JS_ODDSSTATUS_{market}"]')
    if len(c)>1 or len(s)>1: raise FailClosed(f"duplicate market DOM {market}: content={len(c)} status={len(s)}")
    if bool(c)!=bool(s): raise FailClosed(f"market content/status mismatch {market}: content={len(c)} status={len(s)}")
    return (c[0],s[0]) if c else (None,None)

def market_presence(root,market): return _nodes(root,market)[0] is not None

def parse_status(root,market):
    _,st=_nodes(root,market)
    if st is None: raise FailClosed(f"status requested for absent market {market}")
    tt=st.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," time ")]')
    if len(tt)!=1: raise FailClosed(f"timestamp cardinality {market}={len(tt)}")
    ts=node_text(tt[0])
    if '現在' not in ts: raise FailClosed(f"timestamp malformed {market}: {ts}")
    return ts

def _container(root,market):
    c,_=_nodes(root,market)
    if c is None: raise FailClosed(f"parse requested for absent market {market}")
    return c

def parse_2way(root,market,ordered):
    c=_container(root,market)
    tbs=c.xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"{market} table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr')
    if not trs: raise FailClosed(f"{market} empty")
    headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
    if not headers: raise FailClosed(f"{market} headers missing")
    out={}
    for tr in trs[2:]:
        ths=tr.xpath('./th')
        if not ths: continue
        rs=compact(node_text(ths[0]))
        if not rs.isdigit(): continue
        row=int(rs)
        for col,td in zip(headers,tr.xpath('./td')[:len(headers)]):
            v=fcell(td)
            if v is None: continue
            key=canon_pair(col,row,True) if ordered else canon_pair(row,col,False)
            if key in out and abs(out[key]-v)>1e-12: raise FailClosed(f"{market} inconsistent duplicate {key}")
            out[key]=v
    if not out: raise FailClosed(f"{market} zero numeric prices")
    return out

def parse_3rentan(root):
    c=_container(root,'3rentan')
    tbs=c.xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    out={}
    for t in tbs:
        trs=t.xpath('.//tr')
        if len(trs)<4: continue
        sp=trs[0].xpath('.//span[contains(@class,"number")]')
        if len(sp)!=1 or not compact(node_text(sp[0])).isdigit(): raise FailClosed('3rentan first-car header')
        first=int(compact(node_text(sp[0])))
        # Kdreams matrix semantics: column header = 2nd-place car; row header = 3rd-place car.
        # This orientation is independently supported by the legacy DEV1000 semantic correction.
        seconds=[int(compact(node_text(x))) for x in trs[1].xpath('./th') if compact(node_text(x)).isdigit()]
        for tr in trs[3:]:
            ths=tr.xpath('./th')
            if not ths: continue
            rr=compact(node_text(ths[0]))
            if not rr.isdigit(): continue
            third=int(rr)
            for second,td in zip(seconds,tr.xpath('./td')[:len(seconds)]):
                v=fcell(td)
                if v is None: continue
                key=canon_triple(first,second,third,True)
                if key in out and abs(out[key]-v)>1e-12: raise FailClosed(f"3rentan inconsistent duplicate {key}")
                out[key]=v
    if not out: raise FailClosed('3rentan zero numeric prices')
    return out

def parse_3renhuku(root):
    c=_container(root,'3renhuku')
    tbs=c.xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    out={}
    for t in tbs:
        trs=t.xpath('.//tr')
        if not trs: continue
        hh=[compact(node_text(x)) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
        if not hh: continue
        first=int(hh[0]); current_second=None
        for tr in trs[2:]:
            nums=[compact(node_text(x)) for x in tr.xpath('./th') if compact(node_text(x)).isdigit()]
            tds=tr.xpath('./td')
            if not tds: continue
            # Rowspan continuation semantics: a two-number row establishes the new
            # second-car group even when that row's price cell is blank. Later
            # one-number rows inherit that second car. Update state before price filtering.
            if len(nums)>=2: current_second=int(nums[0]); third=int(nums[1])
            elif len(nums)==1 and current_second is not None: third=int(nums[0])
            else: continue
            v=fcell(tds[-1])
            if v is None: continue
            if len({first,current_second,third})<3: continue
            key=canon_triple(first,current_second,third,False)
            if key in out and abs(out[key]-v)>1e-12: raise FailClosed(f"3renhuku inconsistent duplicate {key}")
            out[key]=v
    if not out: raise FailClosed('3renhuku zero numeric prices')
    return out

def parse_frame(root,market,ordered):
    c=_container(root,market)
    tbs=c.xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"{market} table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr')
    if len(trs)<3: raise FailClosed(f"{market} rows={len(trs)}")
    headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
    if headers != list(range(1,7)): raise FailClosed(f"{market} frame headers={headers}")
    labels=[node_text(x) for x in trs[1].xpath('./th|./td')][:6] if len(trs)>1 else []
    out={}
    for tr in trs[2:]:
        ths=tr.xpath('./th')
        if not ths: continue
        rs=compact(node_text(ths[0]))
        if not rs.isdigit(): continue
        row=int(rs)
        if row not in range(1,7): continue
        for col,td in zip(headers,tr.xpath('./td')[:len(headers)]):
            v=fcell(td)
            if v is None: continue
            key=canon_pair(col,row,True) if ordered else canon_pair(row,col,False)
            if key in out and abs(out[key]-v)>1e-12: raise FailClosed(f"{market} inconsistent duplicate {key}")
            out[key]=v
    if not out: raise FailClosed(f"{market} zero numeric prices")
    return out,labels

def parse_wide(root):
    c=_container(root,'wide')
    tbs=c.xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"wide table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr'); headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
    out={}
    for tr in trs[2:]:
        ths=tr.xpath('./th')
        if not ths: continue
        rs=compact(node_text(ths[0]))
        if not rs.isdigit(): continue
        row=int(rs)
        for col,td in zip(headers,tr.xpath('./td')[:len(headers)]):
            s=compact(node_text(td)).replace('〜','～').replace('~','～')
            m=re.fullmatch(r'(\d+(?:\.\d+)?)～(\d+(?:\.\d+)?)',s)
            if not m: continue
            lo,hi=map(float,m.groups())
            if not (math.isfinite(lo) and math.isfinite(hi) and 0<lo<=hi): raise FailClosed(f"wide invalid {s}")
            key=canon_pair(row,col,False)
            val={'low':lo,'high':hi}
            if key in out and out[key]!=val: raise FailClosed(f"wide inconsistent duplicate {key}")
            out[key]=val
    if not out: raise FailClosed('wide zero interval prices')
    return out

PARSERS={
 '3rentan':lambda r:parse_3rentan(r),
 '2shatan':lambda r:parse_2way(r,'2shatan',True),
 '3renhuku':lambda r:parse_3renhuku(r),
 '2shahuku':lambda r:parse_2way(r,'2shahuku',False),
 '2wakutan':lambda r:parse_frame(r,'2wakutan',True),
 '2wakuhuku':lambda r:parse_frame(r,'2wakuhuku',False),
 'wide':lambda r:parse_wide(r),
}

def expected_count(m,n):
    return {
      '3rentan':n*(n-1)*(n-2),'2shatan':n*(n-1),
      '3renhuku':math.comb(n,3),'2shahuku':math.comb(n,2),'wide':math.comb(n,2)
    }.get(m)

def parse_payload(payload:bytes, expected_raw_sha256:str|None=None, expected_n_cars:int|None=None):
    dig=sha256_bytes(payload)
    if expected_raw_sha256 and dig!=expected_raw_sha256: raise FailClosed(f"raw SHA mismatch expected={expected_raw_sha256} observed={dig}")
    try: root=html.fromstring(payload)
    except Exception as e: raise FailClosed(f"HTML parse {e}") from e
    if '確定オッズ' not in node_text(root): raise FailClosed('confirmed closing-odds marker missing')
    availability={m:market_presence(root,m) for m in MARKETS}
    sold=[m for m in MARKETS if availability[m]]
    if not sold: raise FailClosed('no sold markets detected')
    catalogs={}; timestamps={}; frame_labels={}
    for m in sold:
        v=PARSERS[m](root)
        if m in ('2wakutan','2wakuhuku'):
            cat,labels=v; catalogs[m]=cat; frame_labels[m]=labels
        else: catalogs[m]=v
        timestamps[m]=parse_status(root,m)
        if expected_n_cars is not None:
            exp=expected_count(m,int(expected_n_cars))
            if exp is not None and len(catalogs[m])!=exp:
                raise FailClosed(f"{m} combo count={len(catalogs[m])} expected={exp} n={expected_n_cars}")
    return {
      'parser_id':PARSER_ID,'raw_sha256':dig,'market_availability':availability,
      'sold_markets':sold,'closing_price_catalogs':catalogs,'odds_timestamps':timestamps,
      'frame_labels_raw':frame_labels,'price_type':'B_CLOSING_PRICE',
      'wide_price_semantics':'INTERVAL_LOW_HIGH_PRESERVED_NO_MIDPOINT',
      'result_fields_emitted':False,'settlement_fields_emitted':False,
      'model_probability_computed':False,'ev_computed':False,'roi_computed':False,
    }

def _read(path:Path):
    b=path.read_bytes();
    if path.suffix=='.gz': b=gzip.decompress(b)
    return b

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('--sha256'); ap.add_argument('--n-cars',type=int); ap.add_argument('--output')
    a=ap.parse_args(); out=parse_payload(_read(Path(a.input)),a.sha256,a.n_cars); text=json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)
    if a.output: Path(a.output).write_text(text,encoding='utf-8')
    else: print(text)
if __name__=='__main__': main()
