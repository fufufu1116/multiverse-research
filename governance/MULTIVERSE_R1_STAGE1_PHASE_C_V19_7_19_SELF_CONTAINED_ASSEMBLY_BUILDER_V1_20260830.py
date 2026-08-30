#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_ACTION='governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt'
SOURCE_ACTION_BLOB='396c5f99c8837b4bc946a76effe1e19cd391b7d0'
TRANSFORMED_RUNNER='governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh'
TRANSFORMED_RUNNER_BYTES=5302
TRANSFORMED_RUNNER_BLOB='fe51117fd3fcaa41537b5f92c84841716af27f74'
TRANSFORMED_RUNNER_SHA256='248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e'
HISTORICAL_RUNNER_BYTES=5301
HISTORICAL_RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
HISTORICAL_RUNNER_SHA256='370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
TRANSFORMED_ANCHOR=b"tail=r'''phase_c_bootstrap"
HISTORICAL_ANCHOR=b"tail='''phase_c_bootstrap"
STALE_RUNNER_SHA256='f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2'
OUTPUT_BYTES=6382
OUTPUT_BLOB='01c34b393ae272f9e026fc734560170c076e2fc2'
OUTPUT_SHA256='ce4b53b6b4ccd18fbaeb1c57108d0d2fff6b85deca1c43514648f4f523ba19be'

def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()

def main() -> None:
    action=(ROOT/SOURCE_ACTION).read_bytes()
    if blob(action)!=SOURCE_ACTION_BLOB:
        raise SystemExit('SOURCE_ACTION_BLOB_MISMATCH')
    runner=(ROOT/TRANSFORMED_RUNNER).read_bytes()
    if len(runner)!=TRANSFORMED_RUNNER_BYTES or blob(runner)!=TRANSFORMED_RUNNER_BLOB or hashlib.sha256(runner).hexdigest()!=TRANSFORMED_RUNNER_SHA256:
        raise SystemExit('TRANSFORMED_RUNNER_IDENTITY_MISMATCH')
    if runner.count(TRANSFORMED_ANCHOR)!=1 or runner.count(HISTORICAL_ANCHOR)!=0:
        raise SystemExit('TRANSFORMED_ANCHOR_COUNT_MISMATCH')
    historical=runner.replace(TRANSFORMED_ANCHOR,HISTORICAL_ANCHOR,1)
    if len(historical)!=HISTORICAL_RUNNER_BYTES or blob(historical)!=HISTORICAL_RUNNER_BLOB or hashlib.sha256(historical).hexdigest()!=HISTORICAL_RUNNER_SHA256:
        raise SystemExit('HISTORICAL_RUNNER_RECONSTRUCTION_MISMATCH')
    stale=STALE_RUNNER_SHA256.encode('ascii')
    correct=HISTORICAL_RUNNER_SHA256.encode('ascii')
    if action.count(stale)!=1 or action.count(correct)!=0:
        raise SystemExit('RUNNER_SHA_CONSTANT_MULTIPLICITY_MISMATCH')
    out=action.replace(stale,correct,1)
    if len(out)!=OUTPUT_BYTES or blob(out)!=OUTPUT_BLOB or hashlib.sha256(out).hexdigest()!=OUTPUT_SHA256:
        raise SystemExit('CORRECTED_LOADER_IDENTITY_MISMATCH')
    sys.stdout.buffer.write(out)

if __name__=='__main__':
    main()
