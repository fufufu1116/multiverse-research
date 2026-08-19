#!/usr/bin/env python3
"""Multiverse v3.0 All-Market Historical Track — SETTLEMENT recovery.

Firewall role: OFFICIAL REFUND SETTLEMENT ONLY.
Operational use is forbidden until Stage 1-6 decision rules are frozen.
NO PRICE CATALOG, NO MODEL PROBABILITY, NO EV, NO ROI/STRATEGY SEARCH.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,re
from pathlib import Path
from lxml import html

PARSER_ID='KDREAMS_SETTLEMENT_RECOVERY_v1'
MARKETS=('3rentan','2shatan','3renhuku','2shahuku','2wakutan','2wakuhuku','wide')
class FailClosed(RuntimeError): pass

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def compact(s): return ''.join(str(s).split())
def node_text(n): return ' '.join(' '.join(n.itertext()).split())
def pair(a,b,ordered):
    a,b=int(a),int(b); return f'{a}-{b}' if ordered else '='.join(map(str,sorted((a,b))))
def triple(a,b,c,ordered):
    x=(int(a),int(b),int(c)); return '-'.join(map(str,x)) if ordered else '='.join(map(str,sorted(x)))
def normalize_combo(raw,market):
    nums=[int(x) for x in re.findall(r'[1-9]',raw)]
    if market in ('2shatan','2wakutan') and len(nums)==2:return pair(*nums,True)
    if market in ('2shahuku','2wakuhuku','wide') and len(nums)==2:return pair(*nums,False)
    if market=='3rentan' and len(nums)==3:return triple(*nums,True)
    if market=='3renhuku' and len(nums)==3:return triple(*nums,False)
    raise FailClosed(f'malformed settlement combo market={market} raw={raw!r}')
def dl_entries(cell,market):
    out={}
    for dl in cell.xpath('.//dl'):
        dt=dl.xpath('./dt'); dd=dl.xpath('./dd')
        if not dt or not dd: continue
        raw=compact(node_text(dt[0]))
        if not raw or raw=='未発売': continue
        money=re.search(r'([\d,]+)円',compact(node_text(dd[0])))
        if not money: raise FailClosed(f'missing yen amount market={market} combo={raw}')
        key=normalize_combo(raw,market); pay=int(money.group(1).replace(',',''))
        if pay<=0: raise FailClosed(f'nonpositive refund {market}/{key}={pay}')
        if key in out and out[key]!=pay: raise FailClosed(f'conflicting duplicate refund {market}/{key}: {out[key]} vs {pay}')
        out[key]=pay
    return out

def parse_payload(payload:bytes,expected_raw_sha256:str|None=None):
    dig=sha256_bytes(payload)
    if expected_raw_sha256 and dig!=expected_raw_sha256: raise FailClosed(f'raw SHA mismatch expected={expected_raw_sha256} observed={dig}')
    try: root=html.fromstring(payload)
    except Exception as e: raise FailClosed(f'HTML parse {e}') from e
    tabs=root.xpath('//table[contains(concat(" ",normalize-space(@class)," ")," refund_table ")]')
    if len(tabs)!=1: raise FailClosed(f'refund_table count={len(tabs)}')
    trs=tabs[0].xpath('./tr')
    if len(trs)<2: raise FailClosed(f'refund rows={len(trs)}')
    out={m:{} for m in MARKETS}
    row0=trs[0].xpath('./th|./td')
    # unordered rows plus Wide are identified by visible semantic group labels.
    for i,c in enumerate(row0):
        lab=compact(node_text(c))
        if lab=='2枠連' and i+2<len(row0): out['2wakuhuku'].update(dl_entries(row0[i+2],'2wakuhuku'))
        elif lab=='2車連' and i+2<len(row0): out['2shahuku'].update(dl_entries(row0[i+2],'2shahuku'))
        elif lab=='3連勝' and i+2<len(row0): out['3renhuku'].update(dl_entries(row0[i+2],'3renhuku'))
        elif lab=='ワイド' and i+1<len(row0): out['wide'].update(dl_entries(row0[i+1],'wide'))
    # Ordered row is fixed semantic layout: frame exacta, car exacta, trifecta.
    # Each group is ["単", settlement cell]. Explicit 未発売 remains a semantic cell.
    row1=trs[1].xpath('./th|./td')
    if len(row1) != 6:
        raise FailClosed(f'ordered settlement row cell count={len(row1)}')
    if [compact(node_text(row1[i])) for i in (0,2,4)] != ['単','単','単']:
        raise FailClosed('ordered settlement semantic labels drifted')
    ordered_specs=((1,'2wakutan'),(3,'2shatan'),(5,'3rentan'))
    for idx,market in ordered_specs:
        cell=row1[idx]
        txt=compact(node_text(cell))
        if txt=='未発売':
            continue
        vals=dl_entries(cell,market)
        if not vals:
            raise FailClosed(f'sold ordered settlement has no entries market={market}')
        out[market].update(vals)
    sold={m:bool(out[m]) for m in MARKETS}
    if not any(sold.values()): raise FailClosed('no settlement entries parsed')
    return {'parser_id':PARSER_ID,'raw_sha256':dig,'settlements_yen_per_100':out,'settled_market_presence':sold,
            'multi_refund_supported':True,'price_fields_emitted':False,'result_order_fields_emitted':False,
            'model_probability_computed':False,'ev_computed':False,'roi_computed':False,
            'operational_stage':'POST_RULE_FREEZE_SETTLEMENT_ONLY'}
def _read(p):
    b=Path(p).read_bytes(); return gzip.decompress(b) if str(p).endswith('.gz') else b
def main():
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('--sha256');ap.add_argument('--output');a=ap.parse_args()
    x=parse_payload(_read(a.input),a.sha256);t=json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)
    Path(a.output).write_text(t,encoding='utf-8') if a.output else print(t)
if __name__=='__main__':main()
