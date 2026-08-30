#!/usr/bin/env python3
"""Revision-C integrated complete-loader transcript verifier for 103..112 only. Review-only/nonlive."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt"
CONTRACT=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_MATRIX_EVIDENCE_V2_20260830.json"
MAP={"PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES":103,"PHASE_C_V19_7_15_FAIL_FRESH_PATHS":104,"PHASE_C_V19_7_15_FAIL_TMPFS_TRUST":105,"PHASE_C_V19_7_15_FAIL_GIT_CONTROL":106,"PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN":107,"PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD":108,"PHASE_C_V19_7_15_FAIL_REPO_STATE":109,"PHASE_C_V19_7_15_FAIL_RUNNER_TRUST":110,"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND":111,"PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH":112}
START="PHASE_C_V19_7_15_RUNNER_START"
def die(x): raise SystemExit(x)
def verify_reproduced(contract,reproduced):
 expected={x['outer_rc']:x for x in contract['byte_identical_complete_loader_cases']}
 if set(expected)!=set(range(103,113)): die('contract case set')
 got={x['outer_rc']:x for x in reproduced['cases']}
 if set(got)!=set(range(103,113)): die('reproduced case set')
 for code in range(103,113):
  e=expected[code]; x=got[code]
  if x['stdout_lines']!=e['pass_prefix']: die(f'{code} PASS prefix')
  if x['stderr_lines']!=[e['stderr_marker']]: die(f'{code} stderr marker')
  if x.get('child_invocations',0)!=0 or x.get('retry_count',0)!=0: die(f'{code} retry/child')
  if x.get('dynamic_prehandoff_lines',[])!=[] or START in x['stdout_lines']: die(f'{code} dynamic leakage')
def main():
 b=ACTION.read_bytes(); t=b.decode('ascii')
 if b.count(b'\n')!=0 or b.endswith(b'\n') or not t.startswith('{ \\exec /usr/bin/env -i ') or not t.endswith('; }'): die('action shape')
 for m,c in MAP.items():
  if f'{m}) c={c} ;;' not in t: die(f'map drift {c}')
 contract=json.loads(CONTRACT.read_text())
 if contract['action_git_blob']!='396c5f99c8837b4bc946a76effe1e19cd391b7d0': die('action blob contract')
 if contract['runner_return_114_and_success']['evidence_class']!='GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT': die('114 class drift')
 if contract['fallback115']['evidence_class']!='SYNTHETIC_FALLBACK_EQUIVALENT': die('115 class drift')
 if len(sys.argv)!=2: die('INDEPENDENT_REPRODUCED_103_112_TRANSCRIPT_REQUIRED')
 reproduced=json.loads(Path(sys.argv[1]).read_text())
 if reproduced.get('action_git_blob')!=contract['action_git_blob']: die('reproduced action blob')
 verify_reproduced(contract,reproduced)
 print('EVIDENCE_CLASS=BYTE_IDENTICAL_COMPLETE_LOADER')
 print('CASES_103_112=PASS')
 print('REVISION_C_CLASS_SEPARATION=PASS')
if __name__=='__main__': main()
