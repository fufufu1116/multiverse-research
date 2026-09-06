#!/usr/bin/env python3
"""Research-only KEIRIN.JP same-race assignment probe v2.

Hardens v1 by pinning both the v1 probe and its identity-locator dependency,
and by requiring venue/date/race-no to co-occur in one official current-race
text fragment. No RESULT/payout/odds/forecast use; fail closed on ambiguity.
"""
from __future__ import annotations
import importlib.util, json, pathlib, re, subprocess

BASE=pathlib.Path('tools/keirinjp_same_race_assignment_probe_v1.py')
BASE_BLOB='01b6a024e190142bab3bd8bc723193e145899459'
LOCATOR=pathlib.Path('v3/prospective_shadow250_v2/keirinjp_identity_locator_v3.py')
LOCATOR_BLOB='c97d1d7c736e8cd778029446ffc704a684d4938e'

def git_blob(p): return subprocess.check_output(['git','hash-object',str(p)],text=True).strip()

def _load(path,name,expected):
    got=git_blob(path)
    if got!=expected: raise ValueError(f'FAIL_CLOSED_PIN_DRIFT_{name}_{got}')
    s=importlib.util.spec_from_file_location(name,path)
    if not s or not s.loader: raise ValueError(f'FAIL_CLOSED_IMPORT_{name}')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m,got

def load_locator_v2():
    m,_=_load(LOCATOR,'keirinjp_identity_locator_v3_pinned',LOCATOR_BLOB); return m

def verify_event_v2(section,venue,race_date,race_no):
    from datetime import datetime
    d=datetime.fromisoformat(race_date).date(); display=f'{d.month:02d}/{d.day:02d}'; rn=int(race_no)
    if rn<1 or rn>12: raise ValueError('FAIL_CLOSED_RACE_NO')
    # Preserve official text order but require all three tokens inside one bounded fragment.
    fragments=[re.sub(r'\s+',' ',x).strip() for x in re.split(r'[|\n\r]+',section) if x.strip()]
    hits=[]
    for f in fragments:
        if venue in f and display in f and re.search(rf'(?<!\d){rn}R(?!\d)',f): hits.append(f)
    if len(hits)!=1: raise ValueError(f'FAIL_CLOSED_EVENT_FRAGMENT_CARDINALITY_{len(hits)}')
    return {'current_race_heading_present':'開催中のレース' in section,'venue_date_race_cooccurrence_exact':True,'matched_fragment_sha256':__import__('hashlib').sha256(hits[0].encode()).hexdigest()}

def base_module():
    b,bb=_load(BASE,'same_race_probe_v1_pinned',BASE_BLOB)
    # Transitive dependency must also match before any run.
    _,lb=_load(LOCATOR,'identity_locator_v3_pincheck',LOCATOR_BLOB)
    b.load_locator=load_locator_v2; b.verify_event=verify_event_v2
    return b,bb,lb

def run(args):
    b,bb,lb=base_module(); out=b.run(args); out['record']='KEIRINJP_SAME_RACE_ASSIGNMENT_PROBE_v2'; out['base_probe_git_blob']=bb; out['identity_locator_git_blob']=lb; out['event_binding_policy']='SINGLE_FRAGMENT_VENUE_DATE_RACE_COOCCURRENCE'; return out

def selftest():
    b,bb,lb=base_module(); tests={'base_probe_blob_pinned':bb==BASE_BLOB,'locator_blob_pinned':lb==LOCATOR_BLOB}
    good='開催中のレース | 奈良 09/10 7R'; split='開催中のレース | 奈良 09/10 | 別記 7R'
    try: verify_event_v2(good,'奈良','2026-09-10',7); tests['same_fragment_pass']=True
    except Exception: tests['same_fragment_pass']=False
    try: verify_event_v2(split,'奈良','2026-09-10',7); tests['split_tokens_rejected']=False
    except ValueError: tests['split_tokens_rejected']=True
    tests['v1_selftest_pass']=b.selftest().get('status')=='PASS'
    return {'record':'KEIRINJP_SAME_RACE_ASSIGNMENT_PROBE_SELFTEST_v2','status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'network_access':False,'result_accessed':False,'support_increment_authorized_now':0}

def main():
    import argparse
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest'); p=sub.add_parser('probe')
    for x in ('registration-number','name','prefecture','term','venue','race-date','race-no','circumference-m','day','pit-cutoff-utc','out'): p.add_argument('--'+x,required=True)
    a=ap.parse_args()
    if a.cmd=='selftest':
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x['status']=='PASS' else 2
    from types import SimpleNamespace
    ns=SimpleNamespace(registration_number=a.registration_number,name=a.name,prefecture=a.prefecture,term=a.term,venue=a.venue,race_date=a.race_date,race_no=a.race_no,circumference_m=a.circumference_m,day=a.day,pit_cutoff_utc=a.pit_cutoff_utc)
    x=run(ns); pathlib.Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:x.get(k) for k in ('record','status','event_assignment_eligible_for_frozen_mapper','fatal_error')},ensure_ascii=False,sort_keys=True)); return 0 if x.get('status')=='EXACT_SINGLE_MATCH_EVENT_CORROBORATED' else 3
if __name__=='__main__': raise SystemExit(main())
