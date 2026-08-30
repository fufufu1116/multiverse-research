#!/usr/bin/env python3
"""Revision-C V7 103..112 corrected-loader reproducer; review-only/nonlive."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_RUNNER_SHA256_CORRECTION_BUILDER_V1_20260830.py'
FIX=ROOT/'governance/v19_7_16_fixtures'
RECOVERY_HEAD='19a14cfd019cceab199571b5d03d4dd0ba5bcd22'
RUNNER='governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh'
RUNNER_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
RUNNER_SHA='370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
BUILDER_BLOB='a21aee9a91bc23d17dbe1fa44e4794b315d17c0c'
GIT_SHIM_BLOB='d50661c0658ce4f62cbe49192e878e45e913fece'
SHA_SHIM_BLOB='d6fbf5d85301446e1086295487b168189515e8b2'
STAT_SHIM_BLOB='e880e1206c468fd13618da2b048ea800679608df'
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def die(x): raise SystemExit(x)
def git_bytes(*args):
 p=subprocess.run(['git','-C',str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode: die('git object access failed')
 return p.stdout
if len(sys.argv)!=2: die('usage: case-run CODE')
code=int(sys.argv[1])
if code not in range(103,113): die('supported closed-world cases are 103..112')
if blob(BUILDER.read_bytes())!=BUILDER_BLOB: die('correction builder blob drift')
pbuild=subprocess.run([sys.executable,str(BUILDER)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if pbuild.returncode: die('correction builder failed')
action=pbuild.stdout
if action.count(b'370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c')!=1: die('corrected loader trust constant drift')
git_shim=(FIX/'bin/git').read_bytes(); sha_shim=(FIX/'bin/sha256sum').read_bytes(); stat_shim=(FIX/'bin/stat').read_bytes()
if blob(git_shim)!=GIT_SHIM_BLOB: die('git shim blob drift')
if blob(sha_shim)!=SHA_SHIM_BLOB: die('sha shim blob drift')
if blob(stat_shim)!=STAT_SHIM_BLOB: die('stat shim blob drift')
entry=git_bytes('ls-tree',RECOVERY_HEAD,'--',RUNNER).decode().strip().split(None,3)
if len(entry)!=4 or entry[0]!='100644' or entry[1]!='blob' or entry[2]!=RUNNER_BLOB or entry[3]!=RUNNER: die('immutable runner tree mismatch')
runner=git_bytes('show',f'{RECOVERY_HEAD}:{RUNNER}')
if blob(runner)!=RUNNER_BLOB or hashlib.sha256(runner).hexdigest()!=RUNNER_SHA: die('immutable runner bytes drift')
bwrap=shutil.which('bwrap')
if not bwrap: die('BUBBLEWRAP_REQUIRED')
with tempfile.TemporaryDirectory() as td:
 t=Path(td); fixture=t/'fixture'; fixture.mkdir(); (fixture/'SCENARIO').write_text(str(code)+'\n')
 (fixture/'runner').write_bytes(runner); os.chmod(fixture/'runner',0o644)
 (fixture/'git').write_bytes(git_shim); os.chmod(fixture/'git',0o755)
 (fixture/'sha256sum').write_bytes(sha_shim); os.chmod(fixture/'sha256sum',0o755)
 (fixture/'stat').write_bytes(stat_shim); os.chmod(fixture/'stat',0o755)
 cmd=[bwrap,'--unshare-all','--die-with-parent','--ro-bind','/','/','--ro-bind',str(fixture),'/review-fixture','--tmpfs','/dev/shm']
 if code==104: cmd += ['--dir','/dev/shm/multiverse-r1-stage1-phase-c-recovery-control']
 cmd += ['--ro-bind',str(fixture/'git'),'/usr/local/bin/git']
 if code==105: cmd += ['--ro-bind',str(fixture/'stat'),'/usr/local/bin/stat']
 if code in (111,112): cmd += ['--ro-bind',str(fixture/'sha256sum'),'/usr/bin/sha256sum']
 if code==103: cs=''; name=''
 else: cs='true'; name='mv-review-fixture'
 cmd += ['--setenv','CODESPACES',cs,'--setenv','CODESPACE_NAME',name,'/bin/bash','--noprofile','--norc','-c',action.decode('ascii')]
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 result={'outer_rc':p.returncode,'stdout_lines':p.stdout.decode('utf-8','strict').splitlines(),'stderr_lines':p.stderr.decode('utf-8','strict').splitlines(),'child_invocations':0,'retry_count':0,'dynamic_prehandoff_lines':[]}
 print(json.dumps(result,separators=(',',':'),sort_keys=True))
