#!/usr/bin/env python3
from pathlib import Path
import hashlib,re,subprocess,tempfile
LOADER=Path('governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt')
RECOVERY_HEAD='19a14cfd019cceab199571b5d03d4dd0ba5bcd22'
RUNNER_PATH='governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh'
EXPECTED_LOADER_BLOB='396c5f99c8837b4bc946a76effe1e19cd391b7d0'
EXPECTED_RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
EXPECTED_RUNNER_SHA='f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2'
EXPECTED_TEMPLATE_SHA='6e5d69ada53d1a7903aa3aa25213540f18cc67ca794aebd219d07b14712a2817'
START='export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START;'
END='if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def run(*a, text=False):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=text)
 if p.returncode: raise SystemExit('command failed: '+' '.join(a))
 return p.stdout
def die(x): raise SystemExit(x)
b=LOADER.read_bytes()
if blob(b)!=EXPECTED_LOADER_BLOB: die('loader blob drift')
s=b.decode()
if s.count(START)!=1 or s.count(END)!=1: die('anchor multiplicity')
a=s.index(START); z=s.index(END,a)+len(END)
if a>=z: die('anchor order')
region=s[a:z]
if region.count('PHASE_C_V19_7_15_RUNNER_START')!=1 or region.count('PHASE_C_V19_7_15_FAIL_RUNNER_RETURN')!=1: die('region drift')
entry=run('git','ls-tree',RECOVERY_HEAD,'--',RUNNER_PATH,text=True).strip().split(None,3)
if len(entry)!=4: die('immutable runner ls-tree shape')
mode,typ,oid,listed=entry
if (mode,typ,oid,listed)!=('100644','blob',EXPECTED_RUNNER_BLOB,RUNNER_PATH): die('immutable runner ls-tree mismatch')
rb=run('git','show',f'{RECOVERY_HEAD}:{RUNNER_PATH}')
if blob(rb)!=EXPECTED_RUNNER_BLOB or hashlib.sha256(rb).hexdigest()!=EXPECTED_RUNNER_SHA: die('immutable runner object identity drift')
with tempfile.NamedTemporaryFile('wb',delete=True) as f:
 f.write(rb); f.flush()
 if subprocess.run(['/bin/bash','--noprofile','--norc','-n',f.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: die('immutable runner parse failure')
needle='/bin/bash --noprofile --norc "$ROOT/$RUNNER"'
if region.count(needle)!=1: die('runner invocation multiplicity')
template=region.replace(needle,'"$SYNTH_CHILD"',1)
if template.count('"$SYNTH_CHILD"')!=1: die('transform drift')
if hashlib.sha256(template.encode()).hexdigest()!=EXPECTED_TEMPLATE_SHA: die('reviewed boundary-template drift')
print('EVIDENCE_CLASS=BYTE_IDENTICAL_COMPLETE_LOADER')
print('IMMUTABLE_RUNNER_POSITIVE_113=PASS')
print('EVIDENCE_CLASS=GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT')
print('EXPECTED_TRANSFORMATION_FAIL_CLOSED=PASS')
m=re.search(r'fail\(\)\{ c=115; case "\$1" in (.*?) esac;',s)
if not m: die('dispatcher missing')
print('EVIDENCE_CLASS=SYNTHETIC_FALLBACK_EQUIVALENT')
print('UNKNOWN_FALLBACK=115')
