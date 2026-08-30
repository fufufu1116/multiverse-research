#!/usr/bin/env python3
"""Revision-C V7 103..112 corrected-loader transcript verifier. Review-only/nonlive."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_CASE_RUN_V3_20260830.py'
CONTRACT=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_MATRIX_EVIDENCE_V3_20260830.json'
SOURCE_ACTION_BLOB='396c5f99c8837b4bc946a76effe1e19cd391b7d0'
BUILDER_BLOB='a21aee9a91bc23d17dbe1fa44e4794b315d17c0c'
RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
RUNNER_SHA='370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
PASS=["PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES","PHASE_C_V19_7_15_PASS_FRESH_PATHS","PHASE_C_V19_7_15_PASS_TMPFS_TRUST","PHASE_C_V19_7_15_PASS_GIT_CONTROL","PHASE_C_V19_7_15_PASS_CANONICAL_MAIN","PHASE_C_V19_7_15_PASS_RECOVERY_HEAD","PHASE_C_V19_7_15_PASS_REPO_STATE","PHASE_C_V19_7_15_PASS_RUNNER_TRUST"]
PREFIX={103:0,104:1,105:2,106:3,107:4,108:5,109:6,110:7,111:8,112:8}
MARK={103:'PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES',104:'PHASE_C_V19_7_15_FAIL_FRESH_PATHS',105:'PHASE_C_V19_7_15_FAIL_TMPFS_TRUST',106:'PHASE_C_V19_7_15_FAIL_GIT_CONTROL',107:'PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN',108:'PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD',109:'PHASE_C_V19_7_15_FAIL_REPO_STATE',110:'PHASE_C_V19_7_15_FAIL_RUNNER_TRUST',111:'PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND',112:'PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH'}
contract=json.loads(CONTRACT.read_text())
if contract.get('source_action_git_blob')!=SOURCE_ACTION_BLOB: raise SystemExit('source action blob drift')
if contract.get('correction_builder_blob')!=BUILDER_BLOB: raise SystemExit('builder blob drift')
if contract.get('runner_blob')!=RUNNER_BLOB or contract.get('runner_sha256')!=RUNNER_SHA: raise SystemExit('runner identity drift')
rows=contract.get('byte_identical_complete_loader_cases')
if not isinstance(rows,list) or len(rows)!=10: raise SystemExit('contract schema drift')
if any(set(x)!= {'outer_rc','stderr_marker','pass_prefix'} for x in rows): raise SystemExit('contract row schema drift')
frozen={}
for x in rows:
 c=x['outer_rc']
 if c in frozen: raise SystemExit('duplicate outer class')
 frozen[c]=x
if set(frozen)!=set(range(103,113)): raise SystemExit('contract class drift')
for code in range(103,113):
 exp=frozen[code]
 if exp['pass_prefix']!=PASS[:PREFIX[code]]: raise SystemExit(f'frozen PASS prefix schema mismatch {code}')
 if exp['stderr_marker']!=MARK[code]: raise SystemExit(f'frozen stderr marker schema mismatch {code}')
 p=subprocess.run([sys.executable,str(CASE),str(code)],text=True,capture_output=True)
 if p.returncode: raise SystemExit(f'case-run infrastructure failure {code}: {p.stderr}')
 try: got=json.loads(p.stdout)
 except Exception as e: raise SystemExit(f'case-run JSON failure {code}: {e}')
 if set(got)!= {'outer_rc','stdout_lines','stderr_lines','child_invocations','retry_count','dynamic_prehandoff_lines'}: raise SystemExit(f'case-run schema drift {code}')
 if got['outer_rc']!=code: raise SystemExit(f'outer rc mismatch {code}: {got["outer_rc"]}')
 if got['stdout_lines']!=exp['pass_prefix']: raise SystemExit(f'PASS prefix mismatch {code}')
 if got['stderr_lines']!=[exp['stderr_marker']]: raise SystemExit(f'stderr marker mismatch {code}')
 if got['child_invocations']!=0 or got['retry_count']!=0 or got['dynamic_prehandoff_lines']!=[]: raise SystemExit(f'control leakage {code}')
print('EVIDENCE_CLASS=BYTE_IDENTICAL_COMPLETE_LOADER')
print('V7_CORRECTED_LOADER_CLOSED_WORLD_CASES_103_112=PASS')
