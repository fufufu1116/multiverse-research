#!/usr/bin/env python3
"""Revision-B complete-loader transcript verifier. Review-only/nonlive."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt"
CONTRACT=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_MATRIX_EVIDENCE_V2_20260830.json"
MAP={"PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES":103,"PHASE_C_V19_7_15_FAIL_FRESH_PATHS":104,"PHASE_C_V19_7_15_FAIL_TMPFS_TRUST":105,"PHASE_C_V19_7_15_FAIL_GIT_CONTROL":106,"PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN":107,"PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD":108,"PHASE_C_V19_7_15_FAIL_REPO_STATE":109,"PHASE_C_V19_7_15_FAIL_RUNNER_TRUST":110,"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND":111,"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH":112,"PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH":113,"PHASE_C_V19_7_15_FAIL_RUNNER_RETURN":114}
PASS=["PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES","PHASE_C_V19_7_15_PASS_FRESH_PATHS","PHASE_C_V19_7_15_PASS_TMPFS_TRUST","PHASE_C_V19_7_15_PASS_GIT_CONTROL","PHASE_C_V19_7_15_PASS_CANONICAL_MAIN","PHASE_C_V19_7_15_PASS_RECOVERY_HEAD","PHASE_C_V19_7_15_PASS_REPO_STATE","PHASE_C_V19_7_15_PASS_RUNNER_TRUST","PHASE_C_V19_7_15_PASS_RUNNER_SHA256"]
PREFIX={103:0,104:1,105:2,106:3,107:4,108:5,109:6,110:7,111:8,112:8,113:9,114:9}; START="PHASE_C_V19_7_15_RUNNER_START"
def verify(e):
 cases={x["outer_rc"]:x for x in e["cases"]}; assert set(cases)==set(range(103,116))|{0}
 for marker,code in MAP.items():
  x=cases[code]; out=x["stdout_lines"]; assert out[:PREFIX[code]]==PASS[:PREFIX[code]]; assert x["stderr_lines"]==[marker]
  assert all(p not in out[PREFIX[code]:] for p in PASS) and x["retry_count"]==0 and x["dynamic_prehandoff_lines"]==[]
  if code<114: assert START not in out and x["child_invocations"]==0
  else: assert out[PREFIX[code]:PREFIX[code]+1]==[START] and x["child_invocations"]==1 and x["child_stdout"]==["SYNTHETIC_CHILD_STDOUT"] and x["child_stderr"]==["SYNTHETIC_CHILD_STDERR"]
 assert cases[115]["stderr_lines"]==["PHASE_C_V19_7_15_FAIL_UNKNOWN_SYNTHETIC"] and cases[115]["retry_count"]==0
 assert cases[0]["stdout_lines"][:9]==PASS and cases[0]["stdout_lines"][9:10]==[START] and cases[0]["child_invocations"]==1 and cases[0]["retry_count"]==0
def main():
 b=ACTION.read_bytes(); t=b.decode("ascii"); assert b.count(b"\n")==0 and not b.endswith(b"\n") and t.startswith("{ \\exec /usr/bin/env -i ") and t.endswith("; }")
 for m,c in MAP.items(): assert f"{m}) c={c} ;;" in t
 contract=json.loads(CONTRACT.read_text()); assert contract["action_git_blob"]=="396c5f99c8837b4bc946a76effe1e19cd391b7d0"; verify(contract)
 # PASS evidence requires a second, independently reproduced transcript bundle supplied by Lab.
 if len(sys.argv)!=2: raise SystemExit("INDEPENDENT_REPRODUCED_TRANSCRIPT_REQUIRED")
 reproduced=json.loads(Path(sys.argv[1]).read_text()); assert reproduced["action_git_blob"]==contract["action_git_blob"]; verify(reproduced)
 assert reproduced["cases"]==contract["cases"],"REPRODUCED_TRANSCRIPT_DIFFERS_FROM_FROZEN_CONTRACT"
 print("PHASE_C_V19_7_16_WHOLE_LOADER_HARNESS_V2_PASS")
if __name__=="__main__": main()
