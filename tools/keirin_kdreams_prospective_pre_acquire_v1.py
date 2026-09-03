#!/usr/bin/env python3
"""Research-only KDreams prospective PRE acquirer v1.

Consumes a manifest of exact racedetail hrefs positively observed from a frozen
Day1 racecard before the first-race PIT cutoff. Reuses the pinned HFT v3 PRE
parser, keeps mixed HTML in memory only, and emits the strict PRE allowlist with
a prospective evidence role. No RESULT/payout/odds/forecast surfaces are used.
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, pathlib, re, subprocess
from datetime import datetime, timezone

BASE=pathlib.Path('tools/keirin_kdreams_historical_pre_quarantine_acquire_v3.py')
EXPECTED_BASE_GIT_BLOB='d9ee8186b013b389fc0ae228566de3587b3dbfcc'
ROLE='PROSPECTIVE_PRE_SUPPORT_CANDIDATE_ONLY'
ALLOWED=["race_id","race_date","venue","race_no","car_no","rider_name_raw","class","style","competition_score","S","B","nige","makuri","sashi","mark","source_url","source_file_sha256","evidence_role"]

def base_module():
    got=subprocess.check_output(['git','hash-object',str(BASE)],text=True).strip()
    if got!=EXPECTED_BASE_GIT_BLOB: raise ValueError(f'FAIL_CLOSED_BASE_PARSER_BLOB_{got}')
    spec=importlib.util.spec_from_file_location('hft_acquire_v3',BASE)
    if not spec or not spec.loader: raise ValueError('FAIL_CLOSED_BASE_IMPORT')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m,got

def parse_cutoff(x):
    d=datetime.fromisoformat(str(x).replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('FAIL_CLOSED_CUTOFF_TZ_REQUIRED')
    return d.astimezone(timezone.utc)

def validate_manifest(x):
    e=x.get('event') or {}; cutoff=parse_cutoff(x.get('pit_cutoff_utc'))
    if x.get('day1_confirmed') is not True: raise ValueError('FAIL_CLOSED_DAY1_NOT_CONFIRMED')
    if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}',str(e.get('race_date') or '')): raise ValueError('FAIL_CLOSED_EVENT_DATE')
    if not str(e.get('venue') or '').strip(): raise ValueError('FAIL_CLOSED_EVENT_VENUE')
    if e.get('day')!='Day1': raise ValueError('FAIL_CLOSED_EVENT_DAY')
    try: float(e.get('circumference_m'))
    except Exception: raise ValueError('FAIL_CLOSED_CIRCUMFERENCE') from None
    urls=x.get('detail_urls') or []
    if not 5<=len(urls)<=12 or len(set(urls))!=len(urls): raise ValueError('FAIL_CLOSED_DETAIL_URL_COUNT_OR_DUPLICATE')
    if datetime.now(timezone.utc)>=cutoff: raise ValueError('FAIL_CLOSED_CAPTURE_AT_OR_AFTER_PIT_CUTOFF')
    return e,cutoff,urls

def acquire(manifest,timeout=25):
    e,cutoff,urls=validate_manifest(manifest); base,base_blob=base_module()
    rows=[]; accepted=[]; rejected=[]
    captured=datetime.now(timezone.utc)
    for u in urls:
        try:
            base.validate_detail_url(u)
            raw,final=base.fetch_bytes(u,timeout)
            pr=base.parse_detail_pre(raw,final)
            if not pr: raise ValueError('FAIL_CLOSED_EMPTY_PRE')
            if any(r['race_date']!=e['race_date'] or r['venue']!=e['venue'] for r in pr): raise ValueError('FAIL_CLOSED_EVENT_BINDING_MISMATCH')
            for r in pr:
                r=dict(r); r['evidence_role']=ROLE
                if list(r.keys())!=ALLOWED and set(r)!=set(ALLOWED): raise ValueError('FAIL_CLOSED_OUTPUT_SCHEMA')
                rows.append(r)
            accepted.append({'race_id':pr[0]['race_id'],'race_no':pr[0]['race_no'],'pre_rows':len(pr),'source_file_sha256':pr[0]['source_file_sha256'],'class_tokens':sorted({r['class'] for r in pr})})
        except Exception as exc:
            rejected.append({'url':u,'reason':str(exc)})
    races=sorted(x['race_no'] for x in accepted)
    if rejected: raise ValueError('FAIL_CLOSED_REJECTED_DETAIL_'+str(len(rejected)))
    if races!=list(range(1,max(races)+1)): raise ValueError(f'FAIL_CLOSED_RACE_COVERAGE_{races}')
    keys=[(r['race_no'],r['car_no']) for r in rows]
    if len(keys)!=len(set(keys)): raise ValueError('FAIL_CLOSED_DUPLICATE_RACE_CAR')
    rows.sort(key=lambda r:(r['race_no'],r['car_no']))
    receipt={
      'record':'KEIRIN_KDREAMS_PROSPECTIVE_PRE_ACQUIRE_RECEIPT_v1','status':'WHOLE_DAY_DAY1_PRE_CAPTURED_FAIL_CLOSED_READY_FOR_IDENTITY',
      'captured_utc':captured.isoformat(),'pit_cutoff_utc':cutoff.isoformat(),'captured_before_pit_cutoff':captured<cutoff,
      'event':e,'base_parser_file':str(BASE),'base_parser_git_blob':base_blob,'evidence_role':ROLE,
      'successful_races':len(accepted),'pre_rows':len(rows),'accepted':accepted,'rejected':[],
      'whole_day_race_numbers':races,'raw_html_persisted':False,'raw_html_printed':False,
      'result_fields_emitted':False,'payout_fields_emitted':False,'odds_fields_emitted':False,'forecast_fields_emitted':False,'narabiyoso_fields_emitted':False,
      'race_id_guessed':False,'support_increment_authorized_by_tool':False,'result_join_authorized':False,'model_fit_authorized':False,'main_or_runtime_mutation':False
    }
    return rows,receipt

def write_csv(rows,path):
    pathlib.Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=ALLOWED); w.writeheader(); w.writerows(rows)

def selftest():
    base,blob=base_module(); raw=base.synthetic_detail(['L1']*5)
    rows=base.parse_detail_pre(raw,'https://keirin.kdreams.jp/kawasaki/racedetail/3420260830010006/')
    for r in rows: r['evidence_role']=ROLE
    tests={
      'base_blob_pinned':blob==EXPECTED_BASE_GIT_BLOB,
      'five_rows':len(rows)==5,
      'prospective_role':all(r['evidence_role']==ROLE for r in rows),
      'schema_unchanged':all(set(r)==set(ALLOWED) for r in rows),
      'no_forbidden_mixed_text':not any(x in json.dumps(rows,ensure_ascii=False) for x in ['結果','払戻','オッズ','予想','コメント','並び予想'])
    }
    return {'record':'KEIRIN_KDREAMS_PROSPECTIVE_PRE_ACQUIRE_SELFTEST_v1','status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'network_access':False,'result_accessed':False,'race_id_guessing':False}

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest')
    p=sub.add_parser('acquire'); p.add_argument('--manifest',required=True); p.add_argument('--pre-csv',required=True); p.add_argument('--receipt',required=True); p.add_argument('--timeout',type=int,default=25)
    a=ap.parse_args()
    if a.cmd=='selftest':
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x['status']=='PASS' else 2
    manifest=json.loads(pathlib.Path(a.manifest).read_text(encoding='utf-8'))
    try:
        rows,rec=acquire(manifest,a.timeout); write_csv(rows,a.pre_csv); pathlib.Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:rec[k] for k in ('record','status','successful_races','pre_rows','captured_before_pit_cutoff','race_id_guessed','result_join_authorized')},ensure_ascii=False,sort_keys=True)); return 0
    except Exception as e:
        rec={'record':'KEIRIN_KDREAMS_PROSPECTIVE_PRE_ACQUIRE_RECEIPT_v1','status':'FAIL_CLOSED_PROSPECTIVE_PRE_NOT_CAPTURED','fatal_error':f'{type(e).__name__}: {str(e)[:500]}','raw_html_persisted':False,'raw_html_printed':False,'result_accessed':False,'payout_accessed':False,'odds_accessed':False,'race_id_guessed':False,'support_increment_authorized_by_tool':False,'result_join_authorized':False,'model_fit_authorized':False,'main_or_runtime_mutation':False}
        pathlib.Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps(rec,ensure_ascii=False,sort_keys=True)); return 3
if __name__=='__main__': raise SystemExit(main())
