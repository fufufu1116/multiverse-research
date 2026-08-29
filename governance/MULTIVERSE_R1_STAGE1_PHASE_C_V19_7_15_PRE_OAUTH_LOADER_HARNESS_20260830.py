#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_20260830.txt'
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_BUILDER_20260830.py'
EXPECTED_BYTES=5130
EXPECTED_SHA256='2acba967654ebdbcdfccece8c9d4bf0a2e71d0737e470ab5973a9324882d9bf0'
FAIL_MARKERS=['PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES', 'PHASE_C_V19_7_15_FAIL_FRESH_PATHS', 'PHASE_C_V19_7_15_FAIL_TMPFS_TRUST', 'PHASE_C_V19_7_15_FAIL_GIT_CONTROL', 'PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN', 'PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD', 'PHASE_C_V19_7_15_FAIL_REPO_STATE', 'PHASE_C_V19_7_15_FAIL_RUNNER_TRUST', 'PHASE_C_V19_7_15_FAIL_RUNNER_SHA256']
PASS_MARKERS=['PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES', 'PHASE_C_V19_7_15_PASS_FRESH_PATHS', 'PHASE_C_V19_7_15_PASS_TMPFS_TRUST', 'PHASE_C_V19_7_15_PASS_GIT_CONTROL', 'PHASE_C_V19_7_15_PASS_CANONICAL_MAIN', 'PHASE_C_V19_7_15_PASS_RECOVERY_HEAD', 'PHASE_C_V19_7_15_PASS_REPO_STATE', 'PHASE_C_V19_7_15_PASS_RUNNER_TRUST', 'PHASE_C_V19_7_15_PASS_RUNNER_SHA256']
RUNNER_START="PHASE_C_V19_7_15_RUNNER_START"
def load_builder():
    s=importlib.util.spec_from_file_location("b",BUILDER); assert s and s.loader
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def simulate(fail_index):
    out=[]
    for i,(ok,bad) in enumerate(zip(PASS_MARKERS,FAIL_MARKERS)):
        if fail_index==i: out.append(bad); return 88,out
        out.append(ok)
    out.append(RUNNER_START); return 0,out
def main():
    d=ACTION.read_bytes(); t=d.decode("ascii")
    assert len(d)==EXPECTED_BYTES and hashlib.sha256(d).hexdigest()==EXPECTED_SHA256
    assert d.count(b"\n")==0 and not d.endswith(b"\n") and len(d.splitlines())==1
    b=load_builder(); assert b.build()==d and b.build()==d
    assert subprocess.run(["/bin/bash","-n","-c",t],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    # Strategic truncation boundaries: beginning, quartiles, final byte. Exact full command is brace-wrapped so incomplete transport remains syntax-invalid at these transport cut points.
    for n in sorted({1,len(d)//4,len(d)//2,3*len(d)//4,len(d)-1}):
        assert subprocess.run(["/bin/bash","-n","-c",d[:n].decode("ascii","ignore")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0, n
    for m in FAIL_MARKERS:
        assert ("fail "+m) in t and "$" not in m
    for m in PASS_MARKERS+[RUNNER_START]: assert m in t
    for i,m in enumerate(FAIL_MARKERS):
        rc,out=simulate(i); assert rc!=0 and out[-1]==m and RUNNER_START not in out
    rc,out=simulate(None); assert rc==0 and out[-1]==RUNNER_START
    assert "--apply" not in t and "Step4" not in t
    print("PHASE_C_V19_7_15_PRE_OAUTH_HARNESS_PASS")
if __name__=="__main__": main()
