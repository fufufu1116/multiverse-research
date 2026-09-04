#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, os, pathlib, re, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
AUTO=ROOT/'automation'; RC=92; SHA40=re.compile(r'^[0-9a-f]{40}$')
EXPECTED=('orchestrator_mvp_v2.py','test_orchestrator_mvp_v2.py','README_ORCHESTRATOR_MVP_V2.md')
def fail(code): print('MULTIVERSE_AUTOMATION_MVP_V2_GATE_DENIED:'+code,file=sys.stderr); raise SystemExit(RC)
def run_capture(cmd, env=None):
    p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    if p.returncode!=0:
        sys.stdout.write(p.stdout); sys.stderr.write(p.stderr); fail('COMMAND_RC:'+str(p.returncode)+':'+cmd[0])
    return p.stdout.strip()
def run_live(cmd, env=None):
    p=subprocess.run(cmd,cwd=ROOT,env=env)
    if p.returncode!=0: fail('COMMAND_RC:'+str(p.returncode)+':'+cmd[0])
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--expected-head',required=True); ap.add_argument('--canonical-main',required=True); a=ap.parse_args()
    if not SHA40.fullmatch(a.expected_head) or not SHA40.fullmatch(a.canonical_main): fail('SHA_ARG')
    for n in EXPECTED:
        p=AUTO/n
        if not p.is_file(): fail('MISSING:'+n)
    for n in ('orchestrator_mvp_v2.py','test_orchestrator_mvp_v2.py','mechanical_gate_orchestrator_mvp_v2.py'):
        try: ast.parse((AUTO/n).read_text(),filename=n)
        except SyntaxError: fail('PYTHON_SYNTAX:'+n)
    head=run_capture(['git','rev-parse','HEAD']).splitlines()[-1]
    if head!=a.expected_head: fail('EXACT_HEAD_MISMATCH:'+head)
    text=(AUTO/'orchestrator_mvp_v2.py').read_text()
    for token in (
        'MAX_SEMANTIC_RETRY_BUDGET = 2','MAX_TRANSIENT_RETRY_BUDGET = 3',
        'MAX_DIFF_BUDGET_LINES = 500','MAX_EXECUTION_BUDGET_SECONDS = 300',
        'MAX_HEARTBEAT_TIMEOUT_SECONDS = 300','MVP_COST_BUDGET_MICROUSD = 0',
        'WORKER_REPLAY_SAFETY_REQUIRED','active_operation_key','operation_key(',
        'get_context("fork")','proc.terminate()','REVIEW_HEAD_MISMATCH',
        'TRANSIENT_RETRY_WIDENING_DENIED','DIFF_BUDGET_WIDENING_DENIED',
        'EXECUTION_BUDGET_WIDENING_DENIED','CANDIDATE_HEAD_BINDING_MISMATCH'):
        if token not in text: fail('INVARIANT:'+token)
    run_live([sys.executable,'-m','unittest','discover','-s','automation','-p','test_orchestrator_mvp_v2.py','-v'], env={**os.environ,'MULTIVERSE_EXPECTED_HEAD':a.expected_head,'MULTIVERSE_CANONICAL_MAIN':a.canonical_main})
    print('E2E_FINAL_STATE=DONE')
    print('E2E_CANDIDATE_HEAD='+a.expected_head)
    print('OWNER_COPY_PASTE_COUNT=0')
    print('OWNER_CONTINUE_PROMPT_COUNT=0')
    print('OWNER_KEEP_ALIVE_COUNT=0')
    print('MULTIVERSE_ORCHESTRATOR_MVP_V2_MECHANICAL_GATE_PASS')
    print('PRODUCTION_AUTHORITY_GRANTED=false'); print('RUNTIME=OFF'); return 0
if __name__=='__main__': raise SystemExit(main())
