#!/usr/bin/env python3
"""Multiverse v3.0 All-Market Historical Track — Stage-0 offline raw parser candidate.

NO NETWORK. NO MODEL PROBABILITIES. NO EV. NO SCORING.
Reads SHA-bound historical Kdreams showResult HTML(.gz), detects only markets actually
present/sold in that raw page, and emits market availability, complete closing-odds
catalogs, official refund catalogs, market timestamps, and raw provenance.
"""
from __future__ import annotations

import argparse, gzip, hashlib, json, math, re
from pathlib import Path
from typing import Any
from lxml import html

PARSER_ID = "KDREAMS_ALL_MARKET_OFFLINE_PARSER_v1"
MARKETS = (
    "3rentan", "2shatan", "3renhuku", "2shahuku",
    "2wakutan", "2wakuhuku", "wide",
)
POINT_MARKETS = ("3rentan","2shatan","3renhuku","2shahuku","2wakutan","2wakuhuku")
INTERVAL_MARKETS = ("wide",)

class FailClosed(RuntimeError):
    pass

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def compact(s: Any) -> str:
    return "".join(str(s).split())

def node_text(n) -> str:
    return " ".join(" ".join(n.itertext()).split())

def canon_pair(a: int, b: int, ordered: bool) -> str:
    a,b=int(a),int(b)
    return f"{a}-{b}" if ordered else "=".join(map(str, sorted((a,b))))

def canon_triple(a: int,b: int,c: int,ordered: bool) -> str:
    vals=(int(a),int(b),int(c))
    return "-".join(map(str,vals)) if ordered else "=".join(map(str,sorted(vals)))

def fcell(td):
    s=compact(node_text(td))
    if not s or s in {"-","—"}: return None
    try:
        v=float(s)
    except Exception:
        return None
    return v if math.isfinite(v) and v>0 else None

def parse_status(root, market: str) -> str:
    st=root.xpath(f'//*[@id="JS_ODDSSTATUS_{market}"]')
    if len(st)!=1:
        raise FailClosed(f"status cardinality market={market} count={len(st)}")
    tt=st[0].xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," time ")]')
    if len(tt)!=1:
        raise FailClosed(f"status timestamp cardinality market={market} count={len(tt)}")
    ts=node_text(tt[0])
    if "現在" not in ts:
        raise FailClosed(f"status timestamp malformed market={market}: {ts}")
    return ts

def market_presence(root, market: str) -> bool:
    c=root.xpath(f'//*[@id="JS_ODDSCONTENTS_{market}"]')
    s=root.xpath(f'//*[@id="JS_ODDSSTATUS_{market}"]')
    if bool(c) != bool(s):
        raise FailClosed(f"content/status presence mismatch market={market} content={len(c)} status={len(s)}")
    if len(c)>1 or len(s)>1:
        raise FailClosed(f"content/status duplicate market={market} content={len(c)} status={len(s)}")
    return len(c)==1

def parse_2shatan(root):
    c=root.xpath('//*[@id="JS_ODDSCONTENTS_2shatan"]')
    tbs=c[0].xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"2shatan table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr')
    headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
    out={}
    for tr in trs[2:]:
        ths=tr.xpath('./th')
        if not ths: continue
        rs=compact(node_text(ths[0]))
        if not rs.isdigit(): continue
        second=int(rs)
        for first,td in zip(headers,tr.xpath('./td')[:len(headers)]):
            v=fcell(td)
            if v is not None: out[canon_pair(first,second,True)]=v
    return out

def parse_2shahuku(root):
    c=root.xpath('//*[@id="JS_ODDSCONTENTS_2shahuku"]')
    tbs=c[0].xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"2shahuku table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr')
    headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
    out={}
    for tr in trs[2:]:
        ths=tr.xpath('./th')
        if not ths: continue
        rs=compact(node_text(ths[0]))
        if not rs.isdigit(): continue
        row=int(rs)
        for col,td in zip(headers,tr.xpath('./td')[:len(headers)]):
            v=fcell(td)
            if v is not None: out[canon_pair(row,col,False)]=v
    return out

def parse_3rentan(root):
    c=root.xpath('//*[@id="JS_ODDSCONTENTS_3rentan"]')
    tbs=c[0].xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    out={}
    for t in tbs:
        trs=t.xpath('.//tr')
        if len(trs)<4: continue
        sp=trs[0].xpath('.//span[contains(@class,"number")]')
        if len(sp)!=1 or not compact(node_text(sp[0])).isdigit(): raise FailClosed('3rentan first-car header')
        first=int(compact(node_text(sp[0])))
        thirds=[int(compact(node_text(x))) for x in trs[1].xpath('./th') if compact(node_text(x)).isdigit()]
        for tr in trs[3:]:
            ths=tr.xpath('./th')
            if not ths: continue
            ss=compact(node_text(ths[0]))
            if not ss.isdigit(): continue
            second=int(ss)
            for third,td in zip(thirds,tr.xpath('./td')[:len(thirds)]):
                v=fcell(td)
                if v is not None: out[canon_triple(first,second,third,True)]=v
    return out

def parse_3renhuku(root):
    c=root.xpath('//*[@id="JS_ODDSCONTENTS_3renhuku"]')
    tbs=c[0].xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
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
            v=fcell(tds[-1])
            if v is None: continue
            if len(nums)>=2:
                current_second=int(nums[0]); third=int(nums[1])
            elif len(nums)==1 and current_second is not None:
                third=int(nums[0])
            else: continue
            out[canon_triple(first,current_second,third,False)]=v
    return out

def parse_frame_point(root, market: str, ordered: bool):
    c=root.xpath(f'//*[@id="JS_ODDSCONTENTS_{market}"]')
    tbs=c[0].xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"{market} table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr')
    if len(trs)<3: raise FailClosed(f"{market} rows={len(trs)}")
    headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
    if headers != list(range(1,7)): raise FailClosed(f"{market} frame headers={headers}")
    # Retain raw rider-group labels as metadata for later independently-audited car->frame mapping.
    labels=[]
    if len(trs)>1:
        labels=[node_text(x) for x in trs[1].xpath('./th|./td')][:6]
    out={}
    for tr in trs[2:]:
        ths=tr.xpath('./th')
        if not ths: continue
        rs=compact(node_text(ths[0]))
        if not rs.isdigit(): continue
        row=int(rs)
        if row not in range(1,7): continue
        vals=tr.xpath('./td')[:len(headers)]
        for col,td in zip(headers,vals):
            v=fcell(td)
            if v is None: continue
            if ordered:
                # Exact frame ticket. Same-frame is legitimate when page publishes it.
                key=canon_pair(col,row,True)  # Kdreams matrix: column=1st frame, row=2nd frame.
            else:
                key=canon_pair(row,col,False)
            if key in out and abs(out[key]-v)>1e-12:
                raise FailClosed(f"{market} duplicate inconsistent key={key}")
            out[key]=v
    return out, labels

def parse_wide(root):
    c=root.xpath('//*[@id="JS_ODDSCONTENTS_wide"]')
    tbs=c[0].xpath(".//div[contains(@class,'odds_table_wrapper')]//table[contains(@class,'odds_table')]")
    if len(tbs)!=1: raise FailClosed(f"wide table count={len(tbs)}")
    trs=tbs[0].xpath('.//tr')
    headers=[int(compact(node_text(x))) for x in trs[0].xpath('./th') if compact(node_text(x)).isdigit()]
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
            out[canon_pair(row,col,False)]={'low':lo,'high':hi}
    return out

def _refund_dls(cell):
    vals=[]
    for dl in cell.xpath('.//dl'):
        dt=dl.xpath('./dt'); dd=dl.xpath('./dd')
        if not dt or not dd: continue
        combo=compact(node_text(dt[0]))
        if combo=='未発売': continue
        m=re.search(r'([\d,]+)円',compact(node_text(dd[0])))
        if combo and m: vals.append((combo,int(m.group(1).replace(',',''))))
    return vals

def normalize_refund_combo(raw: str, market: str) -> str:
    nums=[int(x) for x in re.findall(r'[1-9]',raw)]
    if market in ('2shatan','2wakutan') and len(nums)==2: return canon_pair(nums[0],nums[1],True)
    if market in ('2shahuku','2wakuhuku','wide') and len(nums)==2: return canon_pair(nums[0],nums[1],False)
    if market=='3rentan' and len(nums)==3: return canon_triple(nums[0],nums[1],nums[2],True)
    if market=='3renhuku' and len(nums)==3: return canon_triple(nums[0],nums[1],nums[2],False)
    raise FailClosed(f"refund combo malformed market={market} raw={raw}")

def parse_refunds(root):
    tabs=root.xpath('//table[contains(concat(" ",normalize-space(@class)," ")," refund_table ")]')
    if len(tabs)!=1: raise FailClosed(f"refund table count={len(tabs)}")
    trs=tabs[0].xpath('./tr')
    if len(trs)<2: raise FailClosed(f"refund rows={len(trs)}")
    r0=trs[0].xpath('./th|./td'); r1=trs[1].xpath('./th|./td')
    out={m:{} for m in MARKETS}
    # Row0 group headers: 2枠連 [複,payout], 2車連 [複,payout], 3連勝 [複,payout], ワイド [payout]
    for i,c in enumerate(r0):
        lab=compact(node_text(c))
        target=None; off=None
        if lab=='2枠連': target,off='2wakuhuku',2
        elif lab=='2車連': target,off='2shahuku',2
        elif lab=='3連勝': target,off='3renhuku',2
        elif lab=='ワイド': target,off='wide',1
        if target and i+off < len(r0):
            for raw,pay in _refund_dls(r0[i+off]):
                out[target][normalize_refund_combo(raw,target)]=pay
    # Row1 is ordered payouts aligned as: frame exacta, car exacta, trifecta.
    cells=[c for c in r1 if c.tag=='td']
    ordered_markets=('2wakutan','2shatan','3rentan')
    payout_cells=[]
    # actual structure alternates label=単 then payout cell; identify cells containing yen/refund dls.
    for c in cells:
        vals=_refund_dls(c)
        if vals: payout_cells.append(c)
    if len(payout_cells) not in (2,3):
        raise FailClosed(f"ordered refund payout cell count={len(payout_cells)}")
    # If frame market unsold, its cell can be absent; distinguish by combo format / row0 frame presence.
    idx=0
    frame_sold=bool(out['2wakuhuku'])
    if frame_sold:
        c=payout_cells[idx]; idx+=1
        for raw,pay in _refund_dls(c): out['2wakutan'][normalize_refund_combo(raw,'2wakutan')]=pay
    c=payout_cells[idx]; idx+=1
    for raw,pay in _refund_dls(c): out['2shatan'][normalize_refund_combo(raw,'2shatan')]=pay
    c=payout_cells[idx]
    for raw,pay in _refund_dls(c): out['3rentan'][normalize_refund_combo(raw,'3rentan')]=pay
    return out

def parse_payload(payload: bytes, expected_raw_sha256: str|None=None, expected_n_cars: int|None=None):
    dig=sha256_bytes(payload)
    if expected_raw_sha256 is not None and dig!=expected_raw_sha256:
        raise FailClosed(f"raw SHA mismatch expected={expected_raw_sha256} observed={dig}")
    try: root=html.fromstring(payload)
    except Exception as e: raise FailClosed(f"HTML parse {e}") from e
    if '確定オッズ' not in node_text(root): raise FailClosed('confirmed-odds marker missing')
    availability={m:market_presence(root,m) for m in MARKETS}
    # Core car markets and wide should be present on standard sold page.
    for m in ('3rentan','2shatan','3renhuku','2shahuku','wide'):
        if not availability[m]: raise FailClosed(f"core market absent {m}")
    # Frame exacta/quinella must appear together or neither.
    if availability['2wakutan'] != availability['2wakuhuku']:
        raise FailClosed('frame-market availability mismatch')
    odds={}; metadata={}
    odds['3rentan']=parse_3rentan(root)
    odds['2shatan']=parse_2shatan(root)
    odds['3renhuku']=parse_3renhuku(root)
    odds['2shahuku']=parse_2shahuku(root)
    odds['wide']=parse_wide(root)
    if availability['2wakutan']:
        odds['2wakutan'],labels1=parse_frame_point(root,'2wakutan',True)
        odds['2wakuhuku'],labels2=parse_frame_point(root,'2wakuhuku',False)
        if labels1!=labels2: raise FailClosed('frame header label mismatch between markets')
        metadata['frame_header_labels']=labels1
    timestamps={m:parse_status(root,m) for m in MARKETS if availability[m]}
    refunds=parse_refunds(root)
    for m in MARKETS:
        if availability[m] and not refunds[m]: raise FailClosed(f"sold market missing refund {m}")
        if not availability[m] and refunds[m]: raise FailClosed(f"unsold market has refund {m}")
    # Count invariants for car-number markets if field size is supplied.
    if expected_n_cars is not None:
        n=int(expected_n_cars)
        exp={
            '3rentan':n*(n-1)*(n-2), '2shatan':n*(n-1),
            '3renhuku':math.comb(n,3), '2shahuku':math.comb(n,2), 'wide':math.comb(n,2),
        }
        for m,k in exp.items():
            if len(odds[m])!=k: raise FailClosed(f"combo count {m}={len(odds[m])} expected={k}")
    # Point odds are finite positive; wide interval validated in parser.
    for m in POINT_MARKETS:
        if availability[m]:
            if not odds.get(m): raise FailClosed(f"empty sold market {m}")
            if not all(math.isfinite(float(v)) and float(v)>0 for v in odds[m].values()): raise FailClosed(f"invalid odds {m}")
    return {
        'parser':PARSER_ID,
        'raw_sha256':dig,
        'market_availability':availability,
        'market_semantics':{m:('INTERVAL_ODDS' if m=='wide' else 'POINT_ODDS') for m in MARKETS if availability[m]},
        'odds':odds,
        'refunds_yen_per_100':{m:refunds[m] for m in MARKETS if availability[m]},
        'timestamps':timestamps,
        'metadata':metadata,
        'network_used':False,
        'probabilities_computed':False,
        'ev_computed':False,
        'scoring_performed':False,
    }

def read_raw(path: Path) -> bytes:
    b=path.read_bytes()
    if path.suffix=='.gz': return gzip.decompress(b)
    return b

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('path',type=Path)
    ap.add_argument('--sha256')
    ap.add_argument('--n-cars',type=int)
    ap.add_argument('--summary-only',action='store_true')
    args=ap.parse_args()
    x=parse_payload(read_raw(args.path),args.sha256,args.n_cars)
    if args.summary_only:
        x={
            'parser':x['parser'],'raw_sha256':x['raw_sha256'],
            'market_availability':x['market_availability'],
            'odds_counts':{m:len(v) for m,v in x['odds'].items()},
            'refund_counts':{m:len(v) for m,v in x['refunds_yen_per_100'].items()},
            'timestamps':x['timestamps'],'metadata':x['metadata'],
            'network_used':False,'probabilities_computed':False,'ev_computed':False,'scoring_performed':False,
        }
    print(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2))

if __name__=='__main__': main()
