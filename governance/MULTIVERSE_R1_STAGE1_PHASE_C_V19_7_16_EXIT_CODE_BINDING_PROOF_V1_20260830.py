#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V1_20260830.txt"
BUILDER = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_BUILDER_V1_20260830.py"
RUNNER = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh"
STEP3 = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_14_STEP3_DIAGNOSTIC_TRANSPORT_ACTION_20260830.txt"
EXPECTED_BYTES = 6372
EXPECTED_SHA256 = "434f4b1a733466cf8d9998361917f3ecf5177c02c2e72fa26b164136f6f14eae"
MAP = {
"PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES":90,
"PHASE_C_V19_7_15_FAIL_FRESH_PATHS":91,
"PHASE_C_V19_7_15_FAIL_TMPFS_TRUST":92,
"PHASE_C_V19_7_15_FAIL_GIT_CONTROL":93,
"PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN":94,
"PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD":95,
"PHASE_C_V19_7_15_FAIL_REPO_STATE":96,
"PHASE_C_V19_7_15_FAIL_RUNNER_TRUST":97,
"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND":98,
"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH":99,
"PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH":100,
"PHASE_C_V19_7_15_FAIL_RUNNER_RETURN":101,
}
FALLBACK = 102
PREFIX = {
"PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES":0,
"PHASE_C_V19_7_15_FAIL_FRESH_PATHS":1,
"PHASE_C_V19_7_15_FAIL_TMPFS_TRUST":2,
"PHASE_C_V19_7_15_FAIL_GIT_CONTROL":3,
"PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN":4,
"PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD":5,
"PHASE_C_V19_7_15_FAIL_REPO_STATE":6,
"PHASE_C_V19_7_15_FAIL_RUNNER_TRUST":7,
"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND":8,
"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH":8,
"PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH":9,
}
PASSES = [
"PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES","PHASE_C_V19_7_15_PASS_FRESH_PATHS","PHASE_C_V19_7_15_PASS_TMPFS_TRUST","PHASE_C_V19_7_15_PASS_GIT_CONTROL","PHASE_C_V19_7_15_PASS_CANONICAL_MAIN","PHASE_C_V19_7_15_PASS_RECOVERY_HEAD","PHASE_C_V19_7_15_PASS_REPO_STATE","PHASE_C_V19_7_15_PASS_RUNNER_TRUST","PHASE_C_V19_7_15_PASS_RUNNER_SHA256"]

def load_builder():
    s=importlib.util.spec_from_file_location("b",BUILDER); assert s and s.loader
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def main():
    d=ACTION.read_bytes(); t=d.decode("ascii")
    assert len(d)==EXPECTED_BYTES and hashlib.sha256(d).hexdigest()==EXPECTED_SHA256
    assert d.count(b"\n")==0 and not d.endswith(b"\n")
    assert load_builder().build()==d
    assert subprocess.run(["/bin/bash","-n","-c",t],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    assert set(MAP.values())==set(range(90,102)) and FALLBACK==102 and FALLBACK not in MAP.values()
    assert all(x not in set(range(64,79))|{126,127} and x<128 for x in list(MAP.values())+[FALLBACK])
    for marker,code in MAP.items():
        assert t.count(f"{marker}) c={code} ;;")==1, (marker,code)
    assert t.count('fail(){ c=102; case "$1" in ')==1
    assert 'CANONICAL_MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"' in t
    assert 'CANONICAL_TREE="3d47741b4863411e5c36cb4c28925ac455ab6441"' in t
    assert 'CANONICAL_MAIN="74ea95e59ac0654e1a0c1f811a178b3eef7b073c"' not in t
    start=t.index("PHASE_C_V19_7_15_RUNNER_START")
    pre=t[:start]
    pass_pos=[]
    for p in PASSES:
        needle="mark "+p
        assert pre.count(needle)==1
        pass_pos.append(pre.index(needle))
    assert pass_pos==sorted(pass_pos)
    callsites=re.findall(r"fail (PHASE_C_V19_7_15_FAIL_[A-Z0-9_]+)",t)
    assert set(callsites)==set(MAP)
    for marker,n in PREFIX.items():
        positions=[m.start() for m in re.finditer(re.escape("fail "+marker),pre)]
        assert positions
        actual={sum(pp<pos for pp in pass_pos) for pos in positions}
        assert actual=={n}, (marker,actual,n)
    post=t[start:]
    assert "fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN" in post
    # Project-local collision check on exact interactive chain dependencies.
    pat=re.compile(r"\b(?:exit|return)\s+(9[0-9]|10[0-2])\b")
    for p in (RUNNER,STEP3):
        assert not pat.search(p.read_text("utf-8")), ("project-local exit collision",p)
    assert "--apply" not in t and "Step4" not in t
    print("PHASE_C_V19_7_16_EXIT_CODE_BINDING_PROOF_V1_PASS")

if __name__=="__main__": main()
