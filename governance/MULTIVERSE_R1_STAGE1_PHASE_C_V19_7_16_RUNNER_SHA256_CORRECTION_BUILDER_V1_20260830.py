#!/usr/bin/env python3
from __future__ import annotations
import hashlib, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_HEAD='9786e87dbc2534f10e3343e2644ec089d88a302b'
SOURCE_ACTION='governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt'
SOURCE_ACTION_BLOB='396c5f99c8837b4bc946a76effe1e19cd391b7d0'
RECOVERY_HEAD='19a14cfd019cceab199571b5d03d4dd0ba5bcd22'
RUNNER_PATH='governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh'
RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
STALE_RUNNER_SHA256='f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2'
CORRECT_RUNNER_SHA256='370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'

def blob(b: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def git_bytes(*args: str) -> bytes:
    p=subprocess.run(['git','-C',str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise SystemExit('git object access failed')
    return p.stdout

def build() -> bytes:
    action=git_bytes('show',f'{SOURCE_HEAD}:{SOURCE_ACTION}')
    if blob(action)!=SOURCE_ACTION_BLOB:
        raise SystemExit('source action blob drift')
    runner=git_bytes('show',f'{RECOVERY_HEAD}:{RUNNER_PATH}')
    if blob(runner)!=RUNNER_BLOB:
        raise SystemExit('runner blob drift')
    actual=hashlib.sha256(runner).hexdigest()
    if actual!=CORRECT_RUNNER_SHA256:
        raise SystemExit('immutable runner SHA256 drift')
    stale=STALE_RUNNER_SHA256.encode()
    correct=CORRECT_RUNNER_SHA256.encode()
    if action.count(stale)!=1:
        raise SystemExit('stale trust constant multiplicity')
    if action.count(correct)!=0:
        raise SystemExit('correct trust constant unexpectedly preexists')
    out=action.replace(stale,correct,1)
    if len(out)!=len(action):
        raise SystemExit('length drift')
    if out.count(stale)!=0 or out.count(correct)!=1:
        raise SystemExit('replacement drift')
    if out.count(b'\n')!=0 or out.endswith(b'\n'):
        raise SystemExit('transport shape drift')
    return out

if __name__=='__main__':
    out=build()
    if len(sys.argv)==2 and sys.argv[1]=='--meta':
        print('SOURCE_ACTION_BLOB',SOURCE_ACTION_BLOB)
        print('RUNNER_BLOB',RUNNER_BLOB)
        print('CORRECT_RUNNER_SHA256',CORRECT_RUNNER_SHA256)
        print('GENERATED_ACTION_BYTES',len(out))
        print('GENERATED_ACTION_GIT_BLOB',blob(out))
        print('GENERATED_ACTION_SHA256',hashlib.sha256(out).hexdigest())
    elif len(sys.argv)==1:
        sys.stdout.buffer.write(out)
    else:
        raise SystemExit('usage: builder [--meta]')
