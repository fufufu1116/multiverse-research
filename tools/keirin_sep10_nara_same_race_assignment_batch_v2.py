#!/usr/bin/env python3
"""Research-only Sep10 Nara same-race assignment batch v2.

Pins the existing v1 batch and swaps its child probe to hardened same-race
assignment probe v2. Support remains unauthorized until separate receipt
assembly and frozen-gate revalidation.
"""
from __future__ import annotations
import importlib.util, json, pathlib, subprocess

BASE=pathlib.Path('tools/keirin_sep10_nara_same_race_assignment_batch_v1.py')
BASE_BLOB='f59a266a9d0382baf65891c8e61e96e52c8acc04'
CHILD=pathlib.Path('tools/keirinjp_same_race_assignment_probe_v2.py')
CHILD_BLOB='71849c756c90365a1942c3af205b3a61fddbb0e1'

def git_blob(p): return subprocess.check_output(['git','hash-object',str(p)],text=True).strip()

def load_base():
    bb=git_blob(BASE); cb=git_blob(CHILD)
    if bb!=BASE_BLOB: raise ValueError(f'FAIL_CLOSED_BASE_BATCH_BLOB_{bb}')
    if cb!=CHILD_BLOB: raise ValueError(f'FAIL_CLOSED_PROBE_V2_BLOB_{cb}')
    s=importlib.util.spec_from_file_location('nara_batch_v1_pinned',BASE)
    if not s or not s.loader: raise ValueError('FAIL_CLOSED_BASE_BATCH_IMPORT')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    m.CHILD=CHILD; m.EXPECTED_CHILD_BLOB=CHILD_BLOB
    return m,bb,cb

def selftest():
    m,bb,cb=load_base(); x=m.selftest(); tests={'base_batch_blob_pinned':bb==BASE_BLOB,'probe_v2_blob_pinned':cb==CHILD_BLOB,'base_selftest_with_v2_child_pass':x.get('status')=='PASS'}
    return {'record':'KEIRIN_SEP10_NARA_SAME_RACE_ASSIGNMENT_BATCH_SELFTEST_v2','status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'network_access':False,'result_accessed':False,'support_increment_authorized_now':0}

def main():
    import argparse
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('selftest'); p=sub.add_parser('run'); p.add_argument('--resolver',required=True); p.add_argument('--out',required=True); p.add_argument('--spacing-seconds',type=float,default=5.2); a=ap.parse_args()
    m,_,_=load_base()
    if a.cmd=='selftest':
        x=selftest(); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 0 if x['status']=='PASS' else 2
    try:
        resolver=json.loads(pathlib.Path(a.resolver).read_text(encoding='utf-8')); x=m.run_batch(resolver,a.spacing_seconds); x['record']='KEIRIN_SEP10_NARA_SAME_RACE_ASSIGNMENT_BATCH_v2'; x['child_probe_path']=str(CHILD); x['child_probe_git_blob']=CHILD_BLOB; pathlib.Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:x.get(k) for k in ('record','status','official_assignment_pass_count','support_increment_authorized_now')},ensure_ascii=False,sort_keys=True)); return 0 if x['status'].startswith('BATCH_COMPLETED') else 3
    except Exception as e:
        x={'record':'KEIRIN_SEP10_NARA_SAME_RACE_ASSIGNMENT_BATCH_v2','status':'FAIL_CLOSED_ASSIGNMENT_BATCH_INCOMPLETE','fatal_error':f'{type(e).__name__}: {str(e)[:500]}','support_increment_authorized_now':0,'support_receipt_authorized_now':False,'result_accessed':False,'result_join_authorized':False,'main_or_runtime_mutation':False}; pathlib.Path(a.out).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps(x,ensure_ascii=False,sort_keys=True)); return 3
if __name__=='__main__': raise SystemExit(main())
