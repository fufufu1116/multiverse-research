#!/usr/bin/env python3
"""Shadow250-v2 race-level KEIRIN identity + supplement batch v3 candidate. Candidate-only, NOT ACTIVE."""
from __future__ import annotations
import hashlib,importlib.util,json,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
import requests
HERE=Path(__file__).resolve().parent
LOCATOR_PATH=HERE/'keirinjp_identity_locator_v3.py';SUPPLEMENT_PARSER_PATH=HERE/'keirinjp_racerprofile_parser_v4.py'
EXPECTED_LOCATOR_GIT_BLOB='c97d1d7c736e8cd778029446ffc704a684d4938e';EXPECTED_SUPPLEMENT_PARSER_GIT_BLOB='d8ce951abd1f008f872bc093d6bb12a50d62ca16'
REQUIRED_RIDERS=7;MAX_BATCH_ELAPSED_SECONDS=90.0;MAX_SOURCE_WINDOW_SECONDS=120.0
class FailClosed(RuntimeError):pass
def _load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None:raise FailClosed(f'FAIL_CLOSED import {path}')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def _git_blob_bytes(path):
    raw=Path(path).read_bytes();return hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
def _wait():time.sleep(5.0)
def _elapsed_guard(started,source_start):
    b=time.monotonic()-started;w=time.monotonic()-float(source_start)
    if b>MAX_BATCH_ELAPSED_SECONDS:raise FailClosed(f'QUARANTINE_FAIL_CLOSED batch elapsed={b:.3f}')
    if w>MAX_SOURCE_WINDOW_SECONDS:raise FailClosed(f'QUARANTINE_FAIL_CLOSED source window elapsed={w:.3f}')
    return b,w
def _validate_entrants(entrants,loc):
    if not isinstance(entrants,list) or len(entrants)!=7:raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP require exactly 7 entrants')
    out=[];cars=set();keys=set()
    for e in entrants:
        if not isinstance(e,dict) or set(['car_no','rider_name','prefecture','term'])-set(e):raise FailClosed('FAIL_CLOSED entrant identity fields')
        car=int(e['car_no']);name=loc.norm(e['rider_name']);pref=loc.canon_pref(e['prefecture']);term=int(e['term']);key=loc.rider_key(name,pref,term)
        if car not in range(1,8) or car in cars or not name or key in keys:raise FailClosed('FAIL_CLOSED entrant identity/cardinality')
        cars.add(car);keys.add(key);out.append({'car_no':car,'rider_name':name,'prefecture':pref,'term':term,'rider_key':key})
    if cars!=set(range(1,8)):raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP car set')
    return sorted(out,key=lambda x:x['car_no'])
def resolve_race(entrants,source_window_started_monotonic):
    if source_window_started_monotonic is None:raise FailClosed('FAIL_CLOSED source-window start required')
    loc=_load('locator_v3_batch3',LOCATOR_PATH);sup=_load('profile_parser_v4_batch3',SUPPLEMENT_PARSER_PATH)
    if _git_blob_bytes(LOCATOR_PATH)!=EXPECTED_LOCATOR_GIT_BLOB:raise FailClosed('FAIL_CLOSED locator blob mismatch')
    if _git_blob_bytes(SUPPLEMENT_PARSER_PATH)!=EXPECTED_SUPPLEMENT_PARSER_GIT_BLOB:raise FailClosed('FAIL_CLOSED supplement parser blob mismatch')
    es=_validate_entrants(entrants,loc);started=time.monotonic();s=requests.Session();lim=loc.RuntimeLimiter();landing=loc._request(s,lim,'get',loc.SEARCH_URL);_elapsed_guard(started,source_window_started_monotonic)
    groups={}
    for e in es:groups.setdefault((e['prefecture'],e['term']),[]).append(e)
    resolved={};search_receipts=[]
    for (pref,term),members in sorted(groups.items(),key=lambda kv:(kv[0][0],kv[0][1])):
        action,payload=loc._verify_search_landing(landing.content,pref,term);_wait();result=loc._request(s,lim,'get',action,params=payload);_elapsed_guard(started,source_window_started_monotonic);cands=loc.extract_identity_candidates(result.content)
        for e in members:
            ms=[c for c in cands if loc.norm(c['name'])==loc.norm(e['rider_name'])]
            if len(ms)!=1:raise FailClosed(f"QUARANTINE_FAIL_CLOSED name match car={e['car_no']} count={len(ms)}")
            snum=ms[0]['snum']
            if snum in resolved.values():raise FailClosed('QUARANTINE_FAIL_CLOSED duplicate snum assignment')
            resolved[e['car_no']]=snum
        search_receipts.append({'prefecture':pref,'term':term,'member_cars':[e['car_no'] for e in members],'candidate_count':len(cands),'content_sha256':hashlib.sha256(result.content).hexdigest(),'identity_fields_used':['name','snum']})
    profiles=[]
    for e in es:
        snum=resolved[e['car_no']];_wait();url=f"https://{loc.ALLOWED_HOST}{loc.PROFILE_PATH}?"+urlencode({'snum':snum});r=loc._request(s,lim,'get',url);_elapsed_guard(started,source_window_started_monotonic);raw_hash=hashlib.sha256(r.content).hexdigest();capture=datetime.now(timezone.utc).isoformat();ident=loc.parse_identity_profile(r.content,url);loc.verify_identity(ident,e['rider_name'],e['prefecture'],e['term'],snum)
        try:parsed=sup.parse_profile(r.content,capture,url,raw_hash)
        except Exception as ex:raise FailClosed(f'QUARANTINE_FAIL_CLOSED supplement parser v4: {type(ex).__name__}: {ex}') from None
        if loc.norm(parsed['name'])!=loc.norm(e['rider_name']) or loc.canon_pref(parsed['prefecture'])!=loc.canon_pref(e['prefecture']):raise FailClosed('QUARANTINE_FAIL_CLOSED supplement identity mismatch')
        pterm=''.join(ch for ch in str(parsed['term']) if ch.isdigit())
        if pterm!=str(e['term']) or str(parsed['registration_number'])!=str(snum):raise FailClosed('QUARANTINE_FAIL_CLOSED supplement term/registration mismatch')
        profiles.append({'car_no':e['car_no'],'rider_key':e['rider_key'],'snum':snum,'style':parsed['style'],'win_rate':parsed['win_rate'],'trio_rate':parsed['trio_rate'],'duplicate_class':parsed['class'],'duplicate_score':parsed['score'],'duplicate_quinella_rate':parsed['quinella_rate'],'profile_updated_at':parsed['profile_updated_at'],'recent4m_updated_at':parsed['recent4m_updated_at'],'capture_timestamp_utc':capture,'profile_raw_sha256':raw_hash,'timestamp_binding':parsed['timestamp_binding'],'table_binding':parsed['table_binding']})
    b,w=_elapsed_guard(started,source_window_started_monotonic)
    return {'status':'PASS_RACE_BATCH_IDENTITY_AND_SUPPLEMENT_V3','rider_count':len(profiles),'group_count':len(groups),'request_count':1+len(groups)+len(profiles),'batch_elapsed_seconds':round(b,3),'source_window_elapsed_seconds':round(w,3),'max_batch_elapsed_seconds':90.0,'max_source_window_seconds':120.0,'search_result_identity_fields_used':['name','snum'],'predictive_fields_from_search_result':[],'predictive_fields_from_racerprofile':['style','win_rate','trio_rate'],'raw_html_persisted':False,'search_receipts':search_receipts,'profiles':profiles}
def synthetic_tests():
    loc=_load('loc_synth_b3',LOCATOR_PATH);assert loc.synthetic_tests()['status']=='PASS';good=[{'car_no':i,'rider_name':f'選手{i}','prefecture':'岡山','term':127} for i in range(1,8)];assert len(_validate_entrants(good,loc))==7
    return {'status':'PASS','network_used':False,'race_batch_required':True,'locator_blob':EXPECTED_LOCATOR_GIT_BLOB,'supplement_parser_blob':EXPECTED_SUPPLEMENT_PARSER_GIT_BLOB}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--synthetic',action='store_true');a=ap.parse_args()
    if a.synthetic:print(json.dumps(synthetic_tests(),ensure_ascii=False,indent=2))
    else:raise SystemExit('FAIL_CLOSED only --synthetic; live use requires upstream source-window start')
