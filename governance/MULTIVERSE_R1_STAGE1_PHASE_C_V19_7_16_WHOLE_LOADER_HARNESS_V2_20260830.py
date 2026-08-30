#!/usr/bin/env python3
"""Independent-review harness specification/executor for v19.7.16 executable-v2.

This harness is intentionally source-bound to the complete exact action. It rejects the
old v1 testing pattern (direct fail() or copied gate fragments). The controlled fixture
backend is required to execute the complete loader entrypoint for every case.
"""
from __future__ import annotations
import hashlib,re,subprocess,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt"
MAP={
"PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES":103,
"PHASE_C_V19_7_15_FAIL_FRESH_PATHS":104,
"PHASE_C_V19_7_15_FAIL_TMPFS_TRUST":105,
"PHASE_C_V19_7_15_FAIL_GIT_CONTROL":106,
"PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN":107,
"PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD":108,
"PHASE_C_V19_7_15_FAIL_REPO_STATE":109,
"PHASE_C_V19_7_15_FAIL_RUNNER_TRUST":110,
"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND":111,
"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH":112,
"PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH":113,
"PHASE_C_V19_7_15_FAIL_RUNNER_RETURN":114,
}
PASS=[
"PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES","PHASE_C_V19_7_15_PASS_FRESH_PATHS",
"PHASE_C_V19_7_15_PASS_TMPFS_TRUST","PHASE_C_V19_7_15_PASS_GIT_CONTROL",
"PHASE_C_V19_7_15_PASS_CANONICAL_MAIN","PHASE_C_V19_7_15_PASS_RECOVERY_HEAD",
"PHASE_C_V19_7_15_PASS_REPO_STATE","PHASE_C_V19_7_15_PASS_RUNNER_TRUST",
"PHASE_C_V19_7_15_PASS_RUNNER_SHA256"]
EXPECTED_PREFIX={103:0,104:1,105:2,106:3,107:4,108:5,109:6,110:7,111:8,112:8,113:9,114:9}
def source_checks(t:str):
 assert "c=115;" in t
 for m,c in MAP.items(): assert f"{m}) c={c} ;;" in t
 assert "CANONICAL_MAIN=\"5c1403c1f5aabb80d29e8c868440aede8888ce61\"" in t
 assert "CANONICAL_TREE=\"3d47741b4863411e5c36cb4c28925ac455ab6441\"" in t
 # complete loader has one outer env entrypoint and one runner invocation site
 assert t.startswith("{ \\exec /usr/bin/env -i ") and t.endswith("; }")
 assert t.count('/bin/bash --noprofile --norc "$ROOT/$RUNNER"')==2 # parse check + execution
 # prohibit old harness technique in this harness source itself
 me=Path(__file__).read_text()
 assert "re.search(r\"fail" not in me and "gate='" not in me and "frag='" not in me

def run_complete(action:bytes,env:dict[str,str]):
 # Complete exact entrypoint only. Fixtures must be supplied outside action bytes.
 return subprocess.run(["/bin/bash","--noprofile","--norc","-c",action.decode("ascii")],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def main():
 b=ACTION.read_bytes(); t=b.decode("ascii"); source_checks(t)
 assert b.count(b"\n")==0 and not b.endswith(b"\n")
 # A real review run must provide MV_WHOLE_LOADER_FIXTURE_ROOT containing controlled
 # command shims capable of taking the complete loader through every gate. Without
 # that fixture this harness fails closed rather than pretending fragments are proof.
 fixture=os.environ.get("MV_WHOLE_LOADER_FIXTURE_ROOT")
 if not fixture:
  raise SystemExit("WHOLE_LOADER_FIXTURE_REQUIRED")
 # Fixture protocol: one executable 'case-run' receives target code and exact action path,
 # invokes the complete action in its isolated namespace, and writes stdout/stderr/rc.
 cr=Path(fixture)/"case-run"
 assert cr.is_file() and os.access(cr,os.X_OK)
 for marker,code in MAP.items():
  p=subprocess.run([str(cr),str(code),str(ACTION)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  assert p.returncode==0,(marker,p.returncode,p.stdout,p.stderr)
 for code in (115,0):
  p=subprocess.run([str(cr),str(code),str(ACTION)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  assert p.returncode==0,(code,p.returncode,p.stdout,p.stderr)
 print("PHASE_C_V19_7_16_WHOLE_LOADER_HARNESS_V2_PASS")
if __name__=="__main__": main()
