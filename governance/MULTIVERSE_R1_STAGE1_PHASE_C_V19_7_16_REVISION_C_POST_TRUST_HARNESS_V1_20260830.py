#!/usr/bin/env python3
from pathlib import Path
import hashlib,subprocess,tempfile,os
L=Path('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt').read_text()
START='export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START;'
END='if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
FAIL_START='fail(){ c=115; case "$1" in '
FAIL_END='}; mark(){ command printf '\''%s\\n'\'' "$1"; };'
def die(x): raise SystemExit(x)
if L.count(START)!=1 or L.count(END)!=1: die('boundary anchor multiplicity')
a=L.index(START); z=L.index(END,a)+len(END); R=L[a:z]
needle='/bin/bash --noprofile --norc "$ROOT/$RUNNER"'
if R.count(needle)!=1: die('runner invocation multiplicity')
T=R.replace(needle,'"$SYNTH_CHILD"',1)
# Mechanically extract proof-relevant fail()+mark() semantics from exact frozen loader bytes.
if L.count(FAIL_START)!=1 or L.count(FAIL_END)!=1: die('fail/mark anchor multiplicity')
fa=L.index(FAIL_START); fz=L.index(FAIL_END,fa)+len(FAIL_END)
FAIL_MARK=L[fa:fz]
if 'PHASE_C_V19_7_15_FAIL_RUNNER_RETURN) c=114 ;;' not in FAIL_MARK: die('114 mapping absent')
if FAIL_MARK.count('exit "$c"')!=1: die('fail termination drift')
# Hand-authored setup is non-semantic plumbing only; fail/mark and boundary behavior are exact-source generated.
SETUP='set -eu -o pipefail; ROOT=/tmp/revision-c-root; RUNNER=synthetic; '
SCRIPT=SETUP+FAIL_MARK+' '+T
def run(rc):
  with tempfile.TemporaryDirectory() as d:
    child=Path(d)/'child'; count=Path(d)/'count'
    child.write_text('#!/bin/bash\necho SYNTH_CHILD_STDOUT\necho SYNTH_CHILD_STDERR >&2\necho x >>"$COUNT_FILE"\nexit '+str(rc)+'\n')
    child.chmod(0o700)
    env=os.environ.copy(); env['SYNTH_CHILD']=str(child); env['COUNT_FILE']=str(count)
    p=subprocess.run(['/bin/bash','--noprofile','--norc','-c',SCRIPT],text=True,capture_output=True,env=env)
    n=count.read_text().count('x') if count.exists() else 0
    return p,n
p,n=run(0)
if not (p.returncode==0 and n==1 and p.stdout.count('PHASE_C_V19_7_15_RUNNER_START')==1): die('success control flow')
if not ('SYNTH_CHILD_STDOUT' in p.stdout and 'SYNTH_CHILD_STDERR' in p.stderr): die('success child transcript')
if 'PHASE_C_V19_7_15_FAIL_RUNNER_RETURN' in p.stderr: die('success return marker leakage')
p,n=run(37)
if not (p.returncode==114 and n==1 and p.stdout.count('PHASE_C_V19_7_15_RUNNER_START')==1): die('114 control flow')
if not ('SYNTH_CHILD_STDOUT' in p.stdout and 'SYNTH_CHILD_STDERR' in p.stderr): die('114 child transcript')
if p.stderr.count('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN')!=1: die('114 return marker')
print('EVIDENCE_CLASS=GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT')
print('SUCCESS_CASE=PASS')
print('RUNNER_RETURN_114_CASE=PASS')
print('NO_RETRY_CHILD_ONCE=PASS')
print('BOUNDARY_TEMPLATE_SHA256='+hashlib.sha256(T.encode()).hexdigest())
print('FAIL_MARK_SOURCE_SHA256='+hashlib.sha256(FAIL_MARK.encode()).hexdigest())
print('GENERATED_SCRIPT_SHA256='+hashlib.sha256(SCRIPT.encode()).hexdigest())
