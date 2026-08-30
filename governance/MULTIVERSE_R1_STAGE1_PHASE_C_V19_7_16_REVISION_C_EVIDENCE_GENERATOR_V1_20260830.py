#!/usr/bin/env python3
from pathlib import Path
import hashlib,re,subprocess,sys
LOADER=Path('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt')
RUNNER=Path('governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh')
EXPECTED_LOADER_BLOB='396c5f99c8837b4bc946a76effe1e19cd391b7d0'
EXPECTED_RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
EXPECTED_RUNNER_SHA='f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2'
START='export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START;'
END='if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def die(x): raise SystemExit(x)
b=LOADER.read_bytes()
if blob(b)!=EXPECTED_LOADER_BLOB: die('loader blob drift')
s=b.decode()
if s.count(START)!=1 or s.count(END)!=1: die('anchor multiplicity')
a=s.index(START); z=s.index(END,a)+len(END)
if a>=z: die('anchor order')
region=s[a:z]
if region.count('PHASE_C_V19_7_15_RUNNER_START')!=1 or region.count('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN')!=1: die('region drift')
rb=RUNNER.read_bytes()
if blob(rb)!=EXPECTED_RUNNER_BLOB or hashlib.sha256(rb).hexdigest()!=EXPECTED_RUNNER_SHA: die('runner identity drift')
if subprocess.run(['/bin/bash','--noprofile','--norc','-n',str(RUNNER)]).returncode: die('immutable runner parse failure')
print('EVIDENCE_CLASS=BYTE_IDENTICAL_COMPLETE_LOADER')
print('LOADER_BLOB='+blob(b))
print('RUNNER_BLOB='+blob(rb))
print('RUNNER_SHA256='+hashlib.sha256(rb).hexdigest())
print('IMMUTABLE_RUNNER_BASH_PARSE=PASS')
print('EVIDENCE_CLASS=GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT')
print('BOUNDARY_SOURCE_SHA256='+hashlib.sha256(region.encode()).hexdigest())
print('BOUNDARY_SOURCE_BYTES='+str(len(region.encode())))
# Mechanically derive only the child invocation token; outer statements remain exact.
needle='/bin/bash --noprofile --norc "$ROOT/$RUNNER"'
if region.count(needle)!=1: die('runner invocation multiplicity')
template=region.replace(needle,'"$SYNTH_CHILD"',1)
if template.count('"$SYNTH_CHILD"')!=1: die('transform drift')
print('BOUNDARY_TEMPLATE_SHA256='+hashlib.sha256(template.encode()).hexdigest())
# fallback dispatcher is explicitly synthetic-equivalent; mapping is parsed from exact loader source.
m=re.search(r'fail\(\)\{ c=115; case "\$1" in (.*?) esac;',s)
if not m: die('dispatcher missing')
print('EVIDENCE_CLASS=SYNTHETIC_FALLBACK_EQUIVALENT')
print('UNKNOWN_FALLBACK=115')
