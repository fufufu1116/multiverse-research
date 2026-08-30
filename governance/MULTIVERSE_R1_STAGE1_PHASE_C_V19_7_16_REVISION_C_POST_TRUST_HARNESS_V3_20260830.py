#!/usr/bin/env python3
from __future__ import annotations
import hashlib, os, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_RUNNER_SHA256_CORRECTION_BUILDER_V1_20260830.py'
BUILDER_BLOB='a21aee9a91bc23d17dbe1fa44e4794b315d17c0c'
EXPECTED_ACTION_BLOB='01c34b393ae272f9e026fc734560170c076e2fc2'
EXPECTED_ACTION_SHA256='ce4b53b6b4ccd18fbaeb1c57108d0d2fff6b85deca1c43514648f4f523ba19be'
EXPECTED_ACTION_BYTES=6382
START='export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START;'
END='if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
FAIL_START='fail(){ c=115;'
AFTER_FAIL_MARK=' ORIGIN="https://github.com/fufufu1116/multiverse-research.git";'
EXPECTED_T_SHA='6e5d69ada53d1a7903aa3aa25213540f18cc67ca794aebd219d07b14712a2817'
EXPECTED_FAIL_MARK_SHA='407b2274a6bacb29fb9f9418ce18864058767256b8292c5c914263aec13814cf'
EXPECTED_SCRIPT_SHA='8ffd84b3004be6528a81015a3ddcc69ee3dffaaf2dc19b3d7d5a52e48893c0e0'

def die(msg: str) -> None:
    raise SystemExit(msg)

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

builder_bytes=BUILDER.read_bytes()
if git_blob(builder_bytes)!=BUILDER_BLOB:
    die('correction builder blob drift')
pb=subprocess.run([sys.executable,str(BUILDER)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if pb.returncode:
    die('correction builder failed')
action=pb.stdout
if len(action)!=EXPECTED_ACTION_BYTES:
    die('corrected loader byte-length drift')
if git_blob(action)!=EXPECTED_ACTION_BLOB:
    die('corrected loader Git-blob drift')
if hashlib.sha256(action).hexdigest()!=EXPECTED_ACTION_SHA256:
    die('corrected loader SHA-256 drift')
if action.count(b'\n')!=0 or action.endswith(b'\n'):
    die('corrected loader transport drift')
L=action.decode('ascii')
if L.count(START)!=1 or L.count(END)!=1:
    die('boundary anchor multiplicity')
a=L.index(START)
z=L.index(END,a)+len(END)
R=L[a:z]
needle='/bin/bash --noprofile --norc "$ROOT/$RUNNER"'
if R.count(needle)!=1:
    die('runner invocation multiplicity')
T=R.replace(needle,'"$SYNTH_CHILD"',1)
if L.count(FAIL_START)!=1 or L.count(AFTER_FAIL_MARK)!=1:
    die('fail/mark anchor multiplicity')
fa=L.index(FAIL_START)
fz=L.index(AFTER_FAIL_MARK,fa)
FAIL_MARK=L[fa:fz]
if not FAIL_MARK.startswith('fail(){ c=115;'):
    die('fail region start drift')
if not FAIL_MARK.endswith('};'):
    die('mark region end drift')
if FAIL_MARK.count('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN) c=114 ;;')!=1:
    die('runner-return mapping drift')
if FAIL_MARK.count('exit "$c"')!=1:
    die('fail termination drift')
if FAIL_MARK.count('mark(){')!=1:
    die('mark function multiplicity')
SETUP='set -eu -o pipefail; ROOT=/tmp/revision-c-root; RUNNER=synthetic; '
SCRIPT=SETUP+FAIL_MARK+' '+T
if sha(T)!=EXPECTED_T_SHA:
    die('boundary template expected-byte drift')
if sha(FAIL_MARK)!=EXPECTED_FAIL_MARK_SHA:
    die('fail/mark expected-byte drift')
if sha(SCRIPT)!=EXPECTED_SCRIPT_SHA:
    die('generated script expected-byte drift')

def run_child(rc: int):
    with tempfile.TemporaryDirectory() as d:
        child=Path(d)/'child'
        count=Path(d)/'count'
        child.write_text('#!/bin/bash\necho SYNTH_CHILD_STDOUT\necho SYNTH_CHILD_STDERR >&2\necho x >>"$COUNT_FILE"\nexit '+str(rc)+'\n')
        child.chmod(0o700)
        env=os.environ.copy()
        env['SYNTH_CHILD']=str(child)
        env['COUNT_FILE']=str(count)
        p=subprocess.run(['/bin/bash','--noprofile','--norc','-c',SCRIPT],text=True,capture_output=True,env=env)
        n=count.read_text().count('x') if count.exists() else 0
        return p,n

p,n=run_child(0)
if not (p.returncode==0 and n==1 and p.stdout.count('PHASE_C_V19_7_15_RUNNER_START')==1):
    die('success control flow')
if 'SYNTH_CHILD_STDOUT' not in p.stdout or 'SYNTH_CHILD_STDERR' not in p.stderr:
    die('success child transcript')
if 'PHASE_C_V19_7_15_FAIL_RUNNER_RETURN' in p.stderr:
    die('success emitted RETURN marker')

p,n=run_child(37)
if not (p.returncode==114 and n==1 and p.stdout.count('PHASE_C_V19_7_15_RUNNER_START')==1):
    die('114 control flow')
if 'SYNTH_CHILD_STDOUT' not in p.stdout or 'SYNTH_CHILD_STDERR' not in p.stderr:
    die('114 child transcript')
if p.stderr.count('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN')!=1:
    die('114 RETURN marker count')

print('EVIDENCE_CLASS=GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT')
print('CORRECTED_ACTION_BLOB='+EXPECTED_ACTION_BLOB)
print('BOUNDARY_TEMPLATE_SHA256='+EXPECTED_T_SHA)
print('FAIL_MARK_SHA256='+EXPECTED_FAIL_MARK_SHA)
print('GENERATED_SCRIPT_SHA256='+EXPECTED_SCRIPT_SHA)
print('EXPECTED_TRANSFORMATION_FAIL_CLOSED=PASS')
print('SUCCESS_CASE=PASS')
print('RUNNER_RETURN_114_CASE=PASS')
print('NO_RETRY_CHILD_ONCE=PASS')
