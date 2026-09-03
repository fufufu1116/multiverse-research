#!/usr/bin/env python3
"""Research-only KEIRIN.JP prospective same-race assignment probe v1.

Generic extraction of the official profile identity + `開催中のレース` section.
Raw HTML remains in memory. No result, payout, odds, forecast, current score,
style, home-bank, preference, or other predictive profile attributes are emitted.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, pathlib, re, unicodedata
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
import requests
from bs4 import BeautifulSoup

MAX_BYTES=2_000_000
LOCATOR=pathlib.Path('v3/prospective_shadow250_v2/keirinjp_identity_locator_v3.py')
CONTRACT='KEIRIN_RIDER_IDENTITY_PRE_ONLY_MAPPING_CONTRACT_20260902_v2.json'
GATE='KEIRIN_RIDER_IDENTITY_PROSPECTIVE_EVENT_ASSIGNMENT_GATE_20260902_v1.json'

def clean(s):
    s=unicodedata.normalize('NFKC',str(s)).replace('\u3000',' ')
    return re.sub(r'\s+',' ',s).strip()

def validate_snum(s):
    s=str(s)
    if not re.fullmatch(r'\d{6}',s): raise ValueError('FAIL_CLOSED_REGISTRATION_NUMBER')
    return s

def profile_url(snum): return f'https://keirin.jp/pc/racerprofile?snum={validate_snum(snum)}'

def extract_current_race_section(content:bytes)->tuple[str,str]:
    soup=BeautifulSoup(content.decode('utf-8','replace'),'html.parser')
    lines=[clean(x) for x in soup.get_text('\n',strip=True).splitlines()]
    lines=[x for x in lines if x]
    starts=[i for i,x in enumerate(lines) if '開催中のレース' in x]
    if len(starts)!=1: raise ValueError(f'FAIL_CLOSED_CURRENT_RACE_HEADING_CARDINALITY_{len(starts)}')
    start=starts[0]
    ends=[i for i,x in enumerate(lines[start+1:],start+1) if '最近の成績' in x]
    if not ends: raise ValueError('FAIL_CLOSED_CURRENT_RACE_SECTION_END_NOT_FOUND')
    section=' | '.join(lines[start:ends[0]])
    if '現在、開催中のレースには出場しておりません' in section:
        raise ValueError('FAIL_CLOSED_OFFICIAL_PROFILE_SAYS_NOT_IN_CURRENT_RACE')
    return section,hashlib.sha256(section.encode('utf-8')).hexdigest()

def verify_event(section:str,venue:str,race_date:str,race_no:int)->dict:
    try: d=datetime.fromisoformat(race_date).date()
    except Exception: raise ValueError('FAIL_CLOSED_RACE_DATE') from None
    display=f'{d.month:02d}/{d.day:02d}'
    if int(race_no)<1 or int(race_no)>12: raise ValueError('FAIL_CLOSED_RACE_NO')
    checks={
        'current_race_heading_present':'開催中のレース' in section,
        'venue_exact_present':clean(venue) in section,
        'race_date_display_exact_present':display in section,
        'race_no_exact_present':re.search(rf'(?<!\d){int(race_no)}R(?!\d)',section) is not None,
    }
    if not all(checks.values()):
        raise ValueError('FAIL_CLOSED_CURRENT_EVENT_MISMATCH_'+'_'.join(k for k,v in checks.items() if not v))
    return checks

def load_locator():
    spec=importlib.util.spec_from_file_location('keirinjp_locator_v3',LOCATOR)
    if not spec or not spec.loader: raise ValueError('FAIL_CLOSED_LOCATOR_IMPORT')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def fetch_profile(url:str)->bytes:
    u=urlparse(url)
    q=parse_qs(u.query)
    if u.scheme!='https' or u.hostname!='keirin.jp' or u.path!='/pc/racerprofile' or set(q)!={'snum'} or len(q['snum'])!=1:
        raise ValueError('FAIL_CLOSED_PROFILE_URL_BINDING')
    r=requests.get(url,timeout=20,allow_redirects=False,headers={'User-Agent':'MultiverseResearch-KEIRIN-SameRaceProbe/1.0','Accept':'text/html','Cache-Control':'no-cache','Pragma':'no-cache'})
    if 300<=r.status_code<400: raise ValueError(f'FAIL_CLOSED_REDIRECT_{r.status_code}')
    if r.status_code in (403,429): raise ValueError(f'FAIL_CLOSED_RATE_HALT_{r.status_code}')
    if r.status_code!=200: raise ValueError(f'FAIL_CLOSED_HTTP_{r.status_code}')
    if len(r.content)>MAX_BYTES: raise ValueError('FAIL_CLOSED_OVERSIZED_RESPONSE')
    if 'text/html' not in r.headers.get('Content-Type','').lower(): raise ValueError('FAIL_CLOSED_CONTENT_TYPE')
    return r.content

def run(args)->dict:
    snum=validate_snum(args.registration_number); url=profile_url(snum)
    cutoff=datetime.fromisoformat(args.pit_cutoff_utc.replace('Z','+00:00'))
    if cutoff.tzinfo is None: raise ValueError('FAIL_CLOSED_CUTOFF_TZ_REQUIRED')
    cutoff=cutoff.astimezone(timezone.utc); captured=datetime.now(timezone.utc)
    base={
      'record':'KEIRINJP_SAME_RACE_ASSIGNMENT_PROBE_v1','generated_utc':captured.isoformat(),
      'status':'FAIL_CLOSED_NOT_EVALUATED','contract':CONTRACT,'assignment_gate':GATE,
      'source':{'organization':'JKA / KEIRIN.JP','interface_field':'開催中のレース','profile_url':url},
      'expected':{'registration_number':snum,'name':args.name,'prefecture':args.prefecture,'term':int(args.term),'venue':args.venue,'race_date':args.race_date,'race_no':int(args.race_no),'circumference_m':float(args.circumference_m),'day':args.day},
      'pit_cutoff_utc':cutoff.isoformat(),'captured_before_pit_cutoff':captured<cutoff,
      'result_accessed':False,'target_result_accessed':False,'payout_accessed':False,'odds_accessed':False,'human_forecast_accessed':False,
      'raw_html_persisted':False,'raw_html_printed':False,'current_profile_nonidentity_fields_persisted_as_features':False,'predictive_features_emitted':False,
      'support_increment_authorized_by_this_probe':0,'formula_fit_authorized':False,'main_or_runtime_mutation':False
    }
    try:
        if captured>=cutoff: raise ValueError('FAIL_CLOSED_CAPTURE_AT_OR_AFTER_PIT_CUTOFF')
        raw=fetch_profile(url); raw_sha=hashlib.sha256(raw).hexdigest()
        locator=load_locator(); ident=locator.parse_identity_profile(raw,url)
        locator.verify_identity(ident,args.name,args.prefecture,int(args.term),snum)
        section,section_sha=extract_current_race_section(raw)
        checks=verify_event(section,args.venue,args.race_date,int(args.race_no))
        base.update({'status':'EXACT_SINGLE_MATCH_EVENT_CORROBORATED','official_identity':ident,
          'observed_current_event':{'venue':args.venue,'race_date':args.race_date,'race_no':int(args.race_no),'circumference_m':float(args.circumference_m),'day':args.day,'same_event_exact_match':True,'same_race_exact_match':True},
          'event_match_checks':checks,'profile_raw_sha256':raw_sha,'current_race_section_sha256':section_sha,'event_assignment_eligible_for_frozen_mapper':True,'fatal_error':None})
    except Exception as e:
        base.update({'status':'FAIL_CLOSED_OFFICIAL_SAME_RACE_ASSIGNMENT_NOT_PROVEN','event_assignment_eligible_for_frozen_mapper':False,'fatal_error':f'{type(e).__name__}: {str(e)[:500]}'})
    return base

def selftest():
    good='''<html><body><h2>開催中のレース</h2><div>奈良 09/10 7R</div><h2>最近の成績</h2></body></html>'''.encode()
    absent='''<html><body><h2>開催中のレース</h2><div>現在、開催中のレースには出場しておりません</div><h2>最近の成績</h2></body></html>'''.encode()
    tests={}
    s,h=extract_current_race_section(good); tests['section_hash']=len(h)==64
    tests['exact_match']=all(verify_event(s,'奈良','2026-09-10',7).values())
    try: verify_event(s,'川崎','2026-09-10',7); tests['venue_mismatch_fail_closed']=False
    except ValueError: tests['venue_mismatch_fail_closed']=True
    try: extract_current_race_section(absent); tests['not_in_race_fail_closed']=False
    except ValueError: tests['not_in_race_fail_closed']=True
    try: validate_snum('15018'); tests['six_digit_required']=False
    except ValueError: tests['six_digit_required']=True
    return {'record':'KEIRINJP_SAME_RACE_ASSIGNMENT_PROBE_SELFTEST_v1','status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'network_access':False,'result_accessed':False}

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest')
    p=sub.add_parser('probe');
    for x in ('registration-number','name','prefecture','term','venue','race-date','race-no','circumference-m','day','pit-cutoff-utc','out'): p.add_argument('--'+x,required=True)
    a=ap.parse_args()
    if a.cmd=='selftest':
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x['status']=='PASS' else 2
    x=run(a); pathlib.Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:x.get(k) for k in ('record','status','generated_utc','captured_before_pit_cutoff','event_assignment_eligible_for_frozen_mapper','fatal_error','raw_html_persisted','result_accessed')},ensure_ascii=False,sort_keys=True))
    return 0 if x['status']=='EXACT_SINGLE_MATCH_EVENT_CORROBORATED' else 3
if __name__=='__main__': raise SystemExit(main())
