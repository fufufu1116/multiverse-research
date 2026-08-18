#!/usr/bin/env python3
"""
Shadow250-v2 race-level KEIRIN identity + supplement batch candidate.

Candidate-only, NOT ACTIVE.

Why this exists:
- a seven-rider race must obey one provider-wide >=5s request spacing invariant;
- per-rider locator instances must not reset the limiter between riders;
- the official racerprofile response used for four-field identity verification is
  parsed ONCE by the already-frozen racerprofile parser, avoiding a duplicate
  network fetch for predictive supplement fields;
- total KEIRIN batch time <=90s and total source window from Tamano capture
  start <=120s are mandatory fail-closed gates.

The search-result page is identity-routing only. Only name+snum are consumed
from it. Predictive supplement fields come only from the frozen
keirinjp_racerprofile_hardlimit_adapter_v1.parse_profile() semantics applied to
that same official racerprofile response.
"""
from __future__ import annotations
import hashlib, importlib.util, json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import requests

HERE=Path(__file__).resolve().parent
LOCATOR_PATH=HERE/'keirinjp_identity_locator_v2.py'
SUPPLEMENT_PATH=HERE.parent/'prospective'/'keirinjp_racerprofile_hardlimit_adapter_v1.py'
EXPECTED_LOCATOR_GIT_BLOB='41517a604bb0c23200cb4d0878d8459f9379d63f'
EXPECTED_SUPPLEMENT_GIT_BLOB='a73a28e9568c326b8cd10b4cfa70bcb573f0f852'
REQUIRED_RIDERS=7
MAX_BATCH_ELAPSED_SECONDS=90.0
MAX_SOURCE_WINDOW_SECONDS=120.0

class FailClosed(RuntimeError): pass

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise FailClosed(f'FAIL_CLOSED import {path}')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _git_blob_bytes(path):
    raw=Path(path).read_bytes()
    header=f'blob {len(raw)}\0'.encode()
    return hashlib.sha1(header+raw).hexdigest()

def _wait_between_requests(): time.sleep(5.0)

def _elapsed_guard(started,source_window_started_monotonic):
    batch=time.monotonic()-started
    window=time.monotonic()-float(source_window_started_monotonic)
    if batch>MAX_BATCH_ELAPSED_SECONDS: raise FailClosed(f'QUARANTINE_FAIL_CLOSED batch elapsed={batch:.3f}')
    if window>MAX_SOURCE_WINDOW_SECONDS: raise FailClosed(f'QUARANTINE_FAIL_CLOSED source window elapsed={window:.3f}')
    return batch,window

def _validate_entrants(entrants,loc):
    if not isinstance(entrants,list) or len(entrants)!=REQUIRED_RIDERS: raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP require exactly 7 entrants')
    out=[]; cars=set(); keys=set()
    for e in entrants:
        if not isinstance(e,dict): raise FailClosed('FAIL_CLOSED entrant type')
        if set(['car_no','rider_name','prefecture','term'])-set(e): raise FailClosed('FAIL_CLOSED missing entrant identity field')
        car=int(e['car_no']); name=loc.norm(e['rider_name']); pref=loc.canon_pref(e['prefecture']); term=int(e['term'])
        if car<1 or car>7 or car in cars or not name: raise FailClosed('FAIL_CLOSED entrant identity/cardinality')
        key=loc.rider_key(name,pref,term)
        if key in keys: raise FailClosed('QUARANTINE_FAIL_CLOSED duplicate rider identity key')
        cars.add(car);keys.add(key);out.append({'car_no':car,'rider_name':name,'prefecture':pref,'term':term,'rider_key':key})
    if cars!=set(range(1,8)): raise FailClosed('PRE_INELIGIBLE_SOURCE_GAP car set')
    return sorted(out,key=lambda x:x['car_no'])

def resolve_race(entrants,source_window_started_monotonic):
    if source_window_started_monotonic is None: raise FailClosed('FAIL_CLOSED source-window start required')
    loc=_load('shadow250_locator_v2_batch',LOCATOR_PATH); sup=_load('shadow250_supplement_parser',SUPPLEMENT_PATH)
    if _git_blob_bytes(LOCATOR_PATH)!=EXPECTED_LOCATOR_GIT_BLOB: raise FailClosed('FAIL_CLOSED locator blob mismatch')
    if _git_blob_bytes(SUPPLEMENT_PATH)!=EXPECTED_SUPPLEMENT_GIT_BLOB: raise FailClosed('FAIL_CLOSED supplement blob mismatch')
    es=_validate_entrants(entrants,loc); started=time.monotonic(); s=requests.Session(); limiter=loc.RuntimeLimiter()

    landing=loc._request(s,limiter,'get',loc.SEARCH_URL); _elapsed_guard(started,source_window_started_monotonic)
    groups={}
    for e in es: groups.setdefault((e['prefecture'],e['term']),[]).append(e)
    resolved={}; search_receipts=[]
    for idx,((pref,term),members) in enumerate(sorted(groups.items(),key=lambda kv:(kv[0][0],kv[0][1]))):
        action,payload=loc._verify_search_landing(landing.content,pref,term)
        _wait_between_requests(); result=loc._request(s,limiter,'get',action,params=payload); _elapsed_guard(started,source_window_started_monotonic)
        candidates=loc.extract_identity_candidates(result.content)
        for e in members:
            matches=[c for c in candidates if loc.norm(c['name'])==loc.norm(e['rider_name'])]
            if len(matches)!=1: raise FailClosed(f"QUARANTINE_FAIL_CLOSED name match car={e['car_no']} count={len(matches)}")
            snum=matches[0]['snum']
            if snum in resolved.values(): raise FailClosed('QUARANTINE_FAIL_CLOSED duplicate snum assignment')
            resolved[e['car_no']]=snum
        search_receipts.append({'prefecture':pref,'term':term,'member_cars':[e['car_no'] for e in members],
                                'candidate_count':len(candidates),'content_sha256':hashlib.sha256(result.content).hexdigest(),
                                'identity_fields_used':['name','snum']})

    profiles=[]
    for e in es:
        snum=resolved[e['car_no']]; _wait_between_requests()
        url=f"https://{loc.ALLOWED_HOST}{loc.PROFILE_PATH}?"+urlencode({'snum':snum})
        r=loc._request(s,limiter,'get',url); batch_elapsed,window_elapsed=_elapsed_guard(started,source_window_started_monotonic)
        raw_hash=hashlib.sha256(r.content).hexdigest(); capture=datetime.now(timezone.utc).isoformat()
        ident=loc.parse_identity_profile(r.content,url); loc.verify_identity(ident,e['rider_name'],e['prefecture'],e['term'],snum)
        try: parsed=sup.parse_profile(r.content,capture,url,raw_hash)
        except Exception as ex: raise FailClosed(f'QUARANTINE_FAIL_CLOSED frozen supplement parse: {type(ex).__name__}: {ex}') from None
        if loc.norm(parsed['name'])!=loc.norm(e['rider_name']) or loc.canon_pref(parsed['prefecture'])!=loc.canon_pref(e['prefecture']): raise FailClosed('QUARANTINE_FAIL_CLOSED supplement identity mismatch')
        pterm=''.join(ch for ch in str(parsed['term']) if ch.isdigit())
        if pterm!=str(e['term']) or str(parsed['registration_number'])!=str(snum): raise FailClosed('QUARANTINE_FAIL_CLOSED supplement term/registration mismatch')
        profiles.append({'car_no':e['car_no'],'rider_key':e['rider_key'],'snum':snum,
                         'style':parsed['style'],'win_rate':parsed['win_rate'],'trio_rate':parsed['trio_rate'],
                         'duplicate_class':parsed['class'],'duplicate_score':parsed['score'],'duplicate_quinella_rate':parsed['quinella_rate'],
                         'profile_updated_at':parsed['profile_updated_at'],'recent4m_updated_at':parsed['recent4m_updated_at'],
                         'capture_timestamp_utc':capture,'profile_raw_sha256':raw_hash})

    batch_elapsed,window_elapsed=_elapsed_guard(started,source_window_started_monotonic)
    return {'status':'PASS_RACE_BATCH_IDENTITY_AND_SUPPLEMENT','rider_count':len(profiles),'group_count':len(groups),
            'request_count':1+len(groups)+len(profiles),'batch_elapsed_seconds':round(batch_elapsed,3),
            'source_window_elapsed_seconds':round(window_elapsed,3),'max_batch_elapsed_seconds':MAX_BATCH_ELAPSED_SECONDS,
            'max_source_window_seconds':MAX_SOURCE_WINDOW_SECONDS,'search_result_identity_fields_used':['name','snum'],
            'predictive_fields_from_search_result':[], 'predictive_fields_from_racerprofile':['style','win_rate','trio_rate'],
            'raw_html_persisted':False,'search_receipts':search_receipts,'profiles':profiles}

def synthetic_tests():
    loc=_load('shadow250_locator_v2_synth',LOCATOR_PATH)
    good=[{'car_no':i,'rider_name':f'選手{i}','prefecture':'岡山','term':127} for i in range(1,8)]
    es=_validate_entrants(good,loc); assert len(es)==7 and [e['car_no'] for e in es]==list(range(1,8))
    bad=good[:-1]
    try: _validate_entrants(bad,loc); raise AssertionError('six riders not rejected')
    except FailClosed: pass
    return {'status':'PASS','network_used':False,'race_batch_required':True}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--synthetic',action='store_true');args=ap.parse_args()
    if args.synthetic: print(json.dumps(synthetic_tests(),ensure_ascii=False,indent=2))
    else: raise SystemExit('FAIL_CLOSED only --synthetic is allowed; live race use requires upstream Tamano source-window start')
