#!/usr/bin/env python3
from pathlib import Path
import hashlib,subprocess,tempfile,os
L=Path('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt').read_text()
START='export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START;'
END='if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
assert L.count(START)==1 and L.count(END)==1
a=L.index(START); z=L.index(END,a)+len(END); R=L[a:z]
needle='/bin/bash --noprofile --norc "$ROOT/$RUNNER"'
assert R.count(needle)==1
T=R.replace(needle,'"$SYNTH_CHILD"',1)
# Only test the generated post-trust equivalent. Never claim byte-identical complete-loader evidence here.
PREFIX='set -eu -o pipefail; fail(){ c=115; case "$1" in PHASE_C_V19_7_15_FAIL_RUNNER_RETURN) c=114 ;; esac; command printf "%s\\n" "$1" >&2; exit "$c"; }; mark(){ command printf "%s\\n" "$1"; }; ROOT=/tmp/revision-c-root; RUNNER=synthetic; '
def run(rc):
  with tempfile.TemporaryDirectory() as d:
    child=Path(d)/'child'; count=Path(d)/'count'
    child.write_text('#!/bin/bash\necho SYNTH_CHILD_STDOUT\necho SYNTH_CHILD_STDERR >&2\necho x >>"$COUNT_FILE"\nexit '+str(rc)+'\n')
    child.chmod(0o700)
    env=os.environ.copy(); env['SYNTH_CHILD']=str(child); env['COUNT_FILE']=str(count)
    p=subprocess.run(['/bin/bash','--noprofile','--norc','-c',PREFIX+T],text=True,capture_output=True,env=env)
    n=count.read_text().count('x') if count.exists() else 0
    return p,n
p,n=run(0)
assert p.returncode==0 and n==1 and p.stdout.count('PHASE_C_V19_7_15_RUNNER_START')==1
assert 'SYNTH_CHILD_STDOUT' in p.stdout and 'SYNTH_CHILD_STDERR' in p.stderr
assert 'PHASE_C_V19_7_15_FAIL_RUNNER_RETURN' not in p.stderr
p,n=run(37)
assert p.returncode==114 and n==1 and p.stdout.count('PHASE_C_V19_7_15_RUNNER_START')==1
assert 'SYNTH_CHILD_STDOUT' in p.stdout and 'SYNTH_CHILD_STDERR' in p.stderr
assert p.stderr.count('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN')==1
print('EVIDENCE_CLASS=GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT')
print('SUCCESS_CASE=PASS')
print('RUNNER_RETURN_114_CASE=PASS')
print('NO_RETRY_CHILD_ONCE=PASS')
print('BOUNDARY_TEMPLATE_SHA256='+hashlib.sha256(T.encode()).hexdigest())
