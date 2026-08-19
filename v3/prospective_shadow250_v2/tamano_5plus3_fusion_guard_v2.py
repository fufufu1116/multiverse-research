#!/usr/bin/env python3
"""Shadow250-v2 5+3 fusion guard candidate. Candidate-only, NOT ACTIVE.
Implements the already-frozen `exact canonical match` duplicate-consistency semantics.
"""
import hashlib,re,unicodedata
from decimal import Decimal,ROUND_HALF_UP
class FailClosed(RuntimeError):pass
CANON_CLASSES={'SS','S1','S2','A1','A2','A3','L1'}
PROFILE_CLASS_MAP={'S級S班':'SS','S級1班':'S1','S級2班':'S2','A級1班':'A1','A級2班':'A2','A級3班':'A3','L級1班':'L1'}
def norm(s):
    s=unicodedata.normalize('NFKC',str(s));s=unicodedata.normalize('NFC',s);return ''.join(ch for ch in s if not ch.isspace())
def canon_pref(s):
    s=norm(s)
    for suf in ('都','道','府','県'):
        if s.endswith(suf) and len(s)>1:return s[:-1]
    return s
def rider_key(name,pref,term):return hashlib.sha256(f'{norm(name)}|{canon_pref(pref)}|{int(term)}'.encode()).hexdigest()
def canon_racecard_class(v):
    x=norm(v)
    if x not in CANON_CLASSES:raise FailClosed(f'QUARANTINE_FAIL_CLOSED racecard class={x}')
    return x
def canon_profile_class(v):
    x=norm(v)
    if x in CANON_CLASSES:return x
    if x not in PROFILE_CLASS_MAP:raise FailClosed(f'QUARANTINE_FAIL_CLOSED profile class={x}')
    return PROFILE_CLASS_MAP[x]
def pct_fraction(v):
    x=norm(v)
    if not re.fullmatch(r'\d+(?:\.\d+)?%',x):raise FailClosed(f'QUARANTINE_FAIL_CLOSED percent={x}')
    return Decimal(x[:-1])/Decimal(100)
def dec(v):
    try:return Decimal(str(v))
    except Exception:raise FailClosed(f'QUARANTINE_FAIL_CLOSED decimal={v}') from None
def qscore(v):return dec(v).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
def qrate(v):return dec(v).quantize(Decimal('0.001'),rounding=ROUND_HALF_UP)
def fuse_race(race_rows,batch_profiles):
    if len(race_rows)!=7 or len(batch_profiles)!=7:raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP require 7+7 rows')
    rc={int(x['car_no']):x for x in race_rows};sp={int(x['car_no']):x for x in batch_profiles}
    if set(rc)!=set(range(1,8)) or set(sp)!=set(range(1,8)):raise FailClosed('QUARANTINE_FAIL_CLOSED car set')
    out=[]
    for car in range(1,8):
        r=rc[car];p=sp[car]
        rk=r.get('rider_id') or rider_key(r['rider_name'],r['prefecture'],r['term'])
        if str(p.get('rider_key'))!=str(rk):raise FailClosed(f'QUARANTINE_FAIL_CLOSED rider_key car={car}')
        rc_cls=canon_racecard_class(r['class']);pf_cls=canon_profile_class(p['duplicate_class'])
        if rc_cls!=pf_cls:raise FailClosed(f'QUARANTINE_FAIL_CLOSED class car={car} racecard={rc_cls} profile={pf_cls}')
        if qscore(r['score'])!=qscore(p['duplicate_score']):raise FailClosed(f'QUARANTINE_FAIL_CLOSED score car={car}')
        if qrate(r['quinella_rate'])!=qrate(pct_fraction(p['duplicate_quinella_rate'])):raise FailClosed(f'QUARANTINE_FAIL_CLOSED quinella_rate car={car}')
        style=norm(p['style'])
        if style not in {'逃','追','両'}:raise FailClosed(f'QUARANTINE_FAIL_CLOSED style car={car}')
        out.append({'race_id':r['race_id'],'car_no':car,'rider_id':rk,
                    'score':float(qscore(r['score'])),'quinella_rate':float(qrate(r['quinella_rate'])),'S':int(r['S']),'B':int(r['B']),'class':rc_cls,
                    'style':style,'win_rate':float(qrate(pct_fraction(p['win_rate']))),'trio_rate':float(qrate(pct_fraction(p['trio_rate']))),
                    'profile_updated_at':p['profile_updated_at'],'recent4m_updated_at':p['recent4m_updated_at'],'capture_timestamp_utc':p['capture_timestamp_utc']})
    return out
def synthetic_tests():
    expected={'Ｓ級Ｓ班':'SS','Ｓ級１班':'S1','Ｓ級２班':'S2','Ａ級１班':'A1','Ａ級２班':'A2','Ａ級３班':'A3','Ｌ級１班':'L1'}
    for raw,want in expected.items():assert canon_profile_class(raw)==want
    try:canon_profile_class('Ａ級４班');raise AssertionError('unknown class accepted')
    except FailClosed:pass
    rows=[];profiles=[]
    for i in range(1,8):
        k=rider_key(f'選手{i}','岡山',127);rows.append({'race_id':'R','car_no':i,'rider_id':k,'rider_name':f'選手{i}','prefecture':'岡山','term':127,'class':'A2','score':77.11,'quinella_rate':0.333,'S':1,'B':2});profiles.append({'car_no':i,'rider_key':k,'duplicate_class':'Ａ級２班','duplicate_score':'77.11','duplicate_quinella_rate':'33.3%','style':'逃','win_rate':'27.7%','trio_rate':'50.0%','profile_updated_at':'2026/08/14 02:36','recent4m_updated_at':'2026/08/19 02:35','capture_timestamp_utc':'x'})
    assert len(fuse_race(rows,profiles))==7
    return {'status':'PASS','network_used':False,'canonical_class_map':expected}
if __name__=='__main__':
    import json,sys
    if len(sys.argv)==2 and sys.argv[1]=='--synthetic':print(json.dumps(synthetic_tests(),ensure_ascii=False,indent=2))
    else:raise SystemExit('usage: --synthetic')
