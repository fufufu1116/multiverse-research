#!/usr/bin/env python3
"""
Shadow250-v2 KEIRIN.JP racerprofile parser v2 candidate.

Candidate-only, NOT ACTIVE.

Preserves the frozen v1 predictive semantics/fields while hardening update-time
binding. Instead of assigning the first two unique datetimes found globally,
v2 requires exactly one datetime in the document-order segment between the
nearest preceding semantic section label and each target data table:
- プロフィール -> 氏名/府県/登録番号 table
- 近況成績 -> 勝率/2連対率/3連対率/競走得点 table

If a section label, target table, or bound timestamp is ambiguous, Fail-Closed.
No timestamp is used as a predictive feature; it remains synchronization and
update-boundary metadata only.
"""
import re
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup

class Halt(RuntimeError): pass

DATETIME_RE=re.compile(r'20\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}')

def _clean(s): return re.sub(r'\s+',' ',str(s).replace('\u3000',' ')).strip()

def _table_map_and_node(soup,required_headers):
    req=list(required_headers); found=[]
    for table in soup.find_all('table'):
        rows=table.find_all('tr')
        for idx,row in enumerate(rows[:-1]):
            cells=[_clean(c.get_text(' ',strip=True)) for c in row.find_all(['th','td'])]
            if all(h in cells for h in req):
                vals=[_clean(c.get_text(' ',strip=True)) for c in rows[idx+1].find_all(['th','td'])]
                if len(vals)>=len(cells): found.append(({cells[i]:vals[i] for i in range(len(cells))},table))
    if len(found)!=1: raise Halt(f'QUARANTINE_FAIL_CLOSED table cardinality headers={req} count={len(found)}')
    return found[0]

def _string_stream(soup):
    out=[]
    for node in soup.find_all(string=True):
        txt=_clean(node)
        if txt: out.append((node,txt))
    return out

def _node_inside(node,ancestor):
    cur=getattr(node,'parent',None)
    while cur is not None:
        if cur is ancestor: return True
        cur=cur.parent
    return False

def _table_first_stream_index(stream,table):
    idx=[i for i,(node,_) in enumerate(stream) if _node_inside(node,table)]
    if not idx: raise Halt('QUARANTINE_FAIL_CLOSED target table has no text stream')
    return min(idx)

def _section_bound_timestamp(soup,table,section_label):
    stream=_string_stream(soup); target_idx=_table_first_stream_index(stream,table)
    labels=[i for i,(_,txt) in enumerate(stream[:target_idx]) if txt==section_label]
    if not labels: raise Halt(f'QUARANTINE_FAIL_CLOSED section label missing {section_label}')
    label_idx=max(labels)
    matches=[]
    for _,txt in stream[label_idx+1:target_idx]:
        matches.extend(DATETIME_RE.findall(txt))
    uniq=[]
    for x in matches:
        if x not in uniq: uniq.append(x)
    if len(uniq)!=1:
        raise Halt(f'QUARANTINE_FAIL_CLOSED section timestamp cardinality section={section_label} count={len(uniq)} values={uniq}')
    return uniq[0]

def parse_profile(content:bytes,capture_utc:str,source_url:str,content_sha256:str):
    soup=BeautifulSoup(content,'html.parser')
    basic,basic_table=_table_map_and_node(soup,['氏名','府県','登録番号'])
    profile,profile_table=_table_map_and_node(soup,['期別','級班','脚質'])
    recent,recent_table=_table_map_and_node(soup,['勝率','2連対率','3連対率','競走得点'])
    profile_updated_at=_section_bound_timestamp(soup,basic_table,'プロフィール')
    recent4m_updated_at=_section_bound_timestamp(soup,recent_table,'近況成績')
    result={
      'source_url':source_url,'capture_timestamp_utc':capture_utc,'content_hash':content_sha256,
      'registration_number':_clean(basic['登録番号']),'name':_clean(basic['氏名']),'prefecture':_clean(basic['府県']),
      'term':_clean(profile['期別']),'class':_clean(profile['級班']),'style':_clean(profile['脚質']),
      'profile_updated_at':profile_updated_at,'recent4m_updated_at':recent4m_updated_at,
      'win_rate':_clean(recent['勝率']),'quinella_rate':_clean(recent['2連対率']),
      'trio_rate':_clean(recent['3連対率']),'score':_clean(recent['競走得点']),
      'network_used':True,'raw_html_persisted':False,
      'timestamp_binding':'SECTION_LABEL_TO_TARGET_TABLE_UNIQUE_DATETIME'
    }
    q=parse_qs(urlparse(source_url).query,keep_blank_values=True)
    if set(q)!={'snum'} or len(q['snum'])!=1 or result['registration_number']!=q['snum'][0]: raise Halt('QUARANTINE_FAIL_CLOSED registration mismatch')
    if result['style'] not in {'逃','追','両'}: raise Halt('QUARANTINE_FAIL_CLOSED style')
    for k in ['win_rate','quinella_rate','trio_rate']:
        if not re.fullmatch(r'\d+(?:\.\d+)?%',result[k]): raise Halt(f'QUARANTINE_FAIL_CLOSED {k}')
    if not re.fullmatch(r'\d+(?:\.\d+)?',result['score']): raise Halt('QUARANTINE_FAIL_CLOSED score')
    return result

def synthetic_tests():
    html='''<html><head><meta charset="utf-8"></head><body>
    <h2>プロフィール</h2><div>2026/07/13 02:35 更新</div>
    <table><tr><th>氏名</th><th>府県</th><th>登録番号</th></tr><tr><td>土井 慎二</td><td>岡山県</td><td>015918</td></tr></table>
    <table><tr><th>期別</th><th>級班</th><th>脚質</th></tr><tr><td>127期</td><td>Ａ級２班</td><td>逃</td></tr></table>
    <h2>近況成績</h2><div>2026/07/26 16:32 更新</div>
    <table><tr><th>勝率</th><th>2連対率</th><th>3連対率</th><th>競走得点</th></tr><tr><td>25.0%</td><td>33.3%</td><td>50.0%</td><td>74.50</td></tr></table>
    <h2>通算成績</h2><div>2026/07/13 02:35 更新</div></body></html>'''.encode('utf-8')
    r=parse_profile(html,'2026-08-19T00:00:00+00:00','https://keirin.jp/pc/racerprofile?snum=015918','x'*64)
    assert r['profile_updated_at']=='2026/07/13 02:35' and r['recent4m_updated_at']=='2026/07/26 16:32'
    # Missing recent timestamp must not fall back to profile/global timestamp.
    bad=html.replace('2026/07/26 16:32 更新'.encode('utf-8'),b'')
    try: parse_profile(bad,'x','https://keirin.jp/pc/racerprofile?snum=015918','x'*64); raise AssertionError('missing recent timestamp accepted')
    except Halt: pass
    return {'status':'PASS','network_used':False}

if __name__=='__main__':
    import json,sys
    if len(sys.argv)==2 and sys.argv[1]=='--synthetic': print(json.dumps(synthetic_tests(),ensure_ascii=False,indent=2))
    else: raise SystemExit('usage: --synthetic')
