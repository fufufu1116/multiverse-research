#!/usr/bin/env python3
from __future__ import annotations
import os,re,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V1_20260830.txt"
MAP={"PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES":90,"PHASE_C_V19_7_15_FAIL_FRESH_PATHS":91,"PHASE_C_V19_7_15_FAIL_TMPFS_TRUST":92,"PHASE_C_V19_7_15_FAIL_GIT_CONTROL":93,"PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN":94,"PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD":95,"PHASE_C_V19_7_15_FAIL_REPO_STATE":96,"PHASE_C_V19_7_15_FAIL_RUNNER_TRUST":97,"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND":98,"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH":99,"PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH":100,"PHASE_C_V19_7_15_FAIL_RUNNER_RETURN":101}

def run(s,env=None):
 e=dict(os.environ); e.update(env or {})
 return subprocess.run(["/bin/bash","--noprofile","--norc","-c",s],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e)

def main():
 t=ACTION.read_text("ascii")
 m=re.search(r"fail\(\)\{.*?\}; mark\(\)\{",t); assert m
 fail=m.group(0)[:-9]
 for marker,code in MAP.items():
  p=run(f"set -u; {fail} fail {marker}")
  assert p.returncode==code and p.stdout=="" and p.stderr==marker+"\n",(marker,p.returncode,p.stdout,p.stderr)
 p=run(f"set -u; {fail} fail PHASE_C_V19_7_15_FAIL_UNKNOWN_SYNTHETIC")
 assert p.returncode==102 and p.stdout=="" and p.stderr=="PHASE_C_V19_7_15_FAIL_UNKNOWN_SYNTHETIC\n"
 gate='test "$(git_clean -C "$ROOT" rev-parse --verify "refs/remotes/origin/main^{commit}")" = "$CANONICAL_MAIN" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN; test "$(git_clean -C "$ROOT" rev-parse --verify "$CANONICAL_MAIN^{tree}")" = "$CANONICAL_TREE" || fail PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN;'
 assert t.count(gate)==1
 setup='ROOT=x; CANONICAL_MAIN=good; CANONICAL_TREE=tree; git_clean(){ if [[ "$*" == *"refs/remotes/origin/main"* ]]; then echo bad; else echo tree; fi; }; '
 p=run("set -u; "+fail+setup+gate); assert p.returncode==94 and p.stderr.endswith("PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN\n")
 setup='ROOT=x; CANONICAL_MAIN=good; CANONICAL_TREE=tree; git_clean(){ if [[ "$*" == *"refs/remotes/origin/main"* ]]; then echo good; else echo badtree; fi; }; '
 p=run("set -u; "+fail+setup+gate); assert p.returncode==94 and p.stderr.endswith("PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN\n")
 with tempfile.TemporaryDirectory() as td:
  q=Path(td); bad=q/"bad.sh"; count=q/"count"
  bad.write_text('printf "%s\\n" SYNTHETIC_RUNNER_STDOUT\nprintf "%s\\n" SYNTHETIC_RUNNER_STDERR >&2\nprintf x >>"$FIX/count"\nexit 7\n'); bad.chmod(0o644)
  mark='mark(){ command printf "%s\\n" "$1"; }; '
  frag='mark PHASE_C_V19_7_15_RUNNER_START; if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
  p=run('set -u; '+fail+mark+'ROOT="$FIX"; RUNNER=bad.sh; '+frag,{"FIX":td})
  assert p.returncode==101
  assert p.stdout=="PHASE_C_V19_7_15_RUNNER_START\nSYNTHETIC_RUNNER_STDOUT\n"
  assert p.stderr=="SYNTHETIC_RUNNER_STDERR\nPHASE_C_V19_7_15_FAIL_RUNNER_RETURN\n"
  assert count.read_text()=="x"
 print("PHASE_C_V19_7_16_EXIT_CODE_HARNESS_V1_PASS")
if __name__=="__main__": main()
