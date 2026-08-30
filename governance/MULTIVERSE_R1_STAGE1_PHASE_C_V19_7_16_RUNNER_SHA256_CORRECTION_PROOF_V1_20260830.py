#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_RUNNER_SHA256_CORRECTION_BUILDER_V1_20260830.py'
SOURCE_HEAD='9786e87dbc2534f10e3343e2644ec089d88a302b'
SOURCE_ACTION='governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt'
OLD=b'f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2'
NEW=b'370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
def git(*a):
 p=subprocess.run(['git','-C',str(ROOT),*a],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode: raise SystemExit('git object access failed')
 return p.stdout
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
spec=importlib.util.spec_from_file_location('corr',BUILDER); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
src=git('show',f'{SOURCE_HEAD}:{SOURCE_ACTION}')
out=m.build()
if len(src)!=len(out): raise SystemExit('length changed')
if src.count(OLD)!=1 or src.count(NEW)!=0 or out.count(OLD)!=0 or out.count(NEW)!=1: raise SystemExit('literal multiplicity drift')
i=src.index(OLD)
if src[:i]!=out[:i] or src[i+len(OLD):]!=out[i+len(NEW):]: raise SystemExit('bytes changed outside trust constant')
if subprocess.run(['/bin/bash','--noprofile','--norc','-n'],input=out,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: raise SystemExit('generated loader parse failure')
print('SOURCE_ACTION_BLOB',blob(src))
print('CORRECTED_ACTION_BLOB',blob(out))
print('CORRECTED_ACTION_SHA256',hashlib.sha256(out).hexdigest())
print('CORRECTED_ACTION_BYTES',len(out))
print('ONLY_RUNNER_SHA256_LITERAL_CHANGED=PASS')
print('V7_CORRECTION_PROOF=PASS')
