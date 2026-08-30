#!/usr/bin/env python3
"""Revision-C 103..112 closed-world transcript verifier. Review-only/nonlive."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_CASE_RUN_V2_20260830.py'
CONTRACT=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_MATRIX_EVIDENCE_V2_20260830.json'
PASS=["PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES","PHASE_C_V19_7_15_PASS_FRESH_PATHS","PHASE_C_V19_7_15_PASS_TMPFS_TRUST","PHASE_C_V19_7_15_PASS_GIT_CONTROL","PHASE_C_V19_7_15_PASS_CANONICAL_MAIN","PHASE_C_V19_7_15_PASS_RECOVERY_HEAD","PHASE_C_V19_7_15_PASS_REPO_STATE","PHASE_C_V19_7_15_PASS_RUNNER_TRUST"]
PREFIX={103:0,104:1,105:2,106:3,107:4,108:5,109:6,110:7,111:8,112:8}
MARK={103:'PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES',104:'PHASE_C_V19_7_15_FAIL_FRESH_PATHS',105:'PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',106:'PHASE_C_V19_7_15_FAIL_GIT_CONTROL',107:'PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN',108:'PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',109:'PHASE_C_V19_7_15_FAIL_REPO_STATE',110:'PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',111:'PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND',112:'PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH'}
contract=json.loads(CONTRACT.read_text()); frozen={x['outer_rc']:x for x in contract['cases'] if 103<=x['outer_rc']<=112}
if set(frozen)!=set(range(103,113)): raise SystemExit('contract class drift')
for code in range(103,113):
 p=subprocess.run([sys.executable,str(CASE),str(code)],text=True,capture_output=True)
 if p.returncode: raise SystemExit(f'case-run infrastructure failure {code}: {p.stderr}')
 got=json.loads(p.stdout)
 if got['outer_rc']!=code: raise SystemExit(f'outer rc mismatch {code}: {got["outer_rc"]}')
 if got['stdout_lines']!=PASS[:PREFIX[code]]: raise SystemExit(f'PASS prefix mismatch {code}')
 if got['stderr_lines']!=[MARK[code]]: raise SystemExit(f'stderr marker mismatch {code}')
 if got['child_invocations']!=0 or got['retry_count']!=0 or got['dynamic_prehandoff_lines']!=[]: raise SystemExit(f'control leakage {code}')
 exp=frozen[code]
 for k in ('outer_rc','stdout_lines','stderr_lines','child_invocations','retry_count','dynamic_prehandoff_lines'):
  if got[k]!=exp[k]: raise SystemExit(f'frozen transcript mismatch {code}:{k}')
print('EVIDENCE_CLASS=BYTE_IDENTICAL_COMPLETE_LOADER')
print('CLOSED_WORLD_CASES_103_112=PASS')
