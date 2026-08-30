#!/usr/bin/env python3
from __future__ import annotations
import hashlib,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_RUNNER_SHA256_CORRECTION_BUILDER_V1_20260830.py'
RUNNER_COMMIT='19a14cfd019cceab199571b5d03d4dd0ba5bcd22'
RUNNER_PATH='governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh'
RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
RUNNER_SHA256='370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
STEP3_COMMIT='4ff69ca9a556a6c0928ae3ed576855945d746447'
STEP3_PATH='governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_14_STEP3_DIAGNOSTIC_TRANSPORT_ACTION_20260830.txt'
STEP3_BLOB='c9459751e4b50c70fde1b94413b9c441dfbfccc4'
OUTER=set(range(103,116))
def git(*args):
 p=subprocess.run(['git','-C',str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode: raise SystemExit('git object access failed')
 return p.stdout
def bash_parse(b): return subprocess.run(['/bin/bash','--noprofile','--norc','-n'],input=b,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
def fixed_codes(data):
 s=data.decode('utf-8','strict'); out=set()
 for pat in (r'\bexit\s+([0-9]+)\b',r'\breturn\s+([0-9]+)\b',r'os\._exit\(\s*([0-9]+)\s*\)',r'sys\.exit\(\s*([0-9]+)\s*\)'): out|={int(x) for x in re.findall(pat,s)}
 return out
def immutable(commit,path,blob):
 entry=git('ls-tree',commit,'--',path).decode().strip().split(None,3)
 if len(entry)!=4 or entry[0]!='100644' or entry[1]!='blob' or entry[2]!=blob or entry[3]!=path: raise SystemExit('immutable tree mismatch')
 return git('show',f'{commit}:{path}')
p=subprocess.run([sys.executable,str(BUILDER)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if p.returncode: raise SystemExit('correction builder failed')
a=p.stdout
if not a or a.count(b'\n')!=0 or a.endswith(b'\n') or not bash_parse(a): raise SystemExit('corrected loader transport shape')
if any(bash_parse(a[:n]) for n in range(1,len(a))): raise SystemExit('strict prefix parses')
rb=immutable(RUNNER_COMMIT,RUNNER_PATH,RUNNER_BLOB)
if hashlib.sha256(rb).hexdigest()!=RUNNER_SHA256: raise SystemExit('runner SHA256 mismatch')
sb=immutable(STEP3_COMMIT,STEP3_PATH,STEP3_BLOB)
rc=fixed_codes(rb); sc=fixed_codes(sb)
if not {88,89,90,91,92}.issubset(rc): raise SystemExit('runner fixed-code drift')
if 92 not in sc: raise SystemExit('Step3 fixed-code drift')
if not OUTER.isdisjoint(rc) or not OUTER.isdisjoint(sc): raise SystemExit('dependency collision')
text=a.decode('ascii')
if 'RUNNER_SHA256="'+RUNNER_SHA256+'"' not in text: raise SystemExit('corrected trust constant missing')
if 'if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi' not in text: raise SystemExit('handoff mapping drift')
print('CORRECTED_ACTION_BYTES',len(a)); print('CORRECTED_ACTION_SHA256',hashlib.sha256(a).hexdigest()); print('RUNNER_IMMUTABLE',RUNNER_COMMIT,RUNNER_BLOB,RUNNER_SHA256); print('RUNNER_FIXED_CODES',sorted(rc)); print('STEP3_IMMUTABLE',STEP3_COMMIT,STEP3_BLOB); print('STEP3_FIXED_CODES',sorted(sc)); print('V7_EXACT_BYTE_AND_DEPENDENCY_PROOF=PASS')
