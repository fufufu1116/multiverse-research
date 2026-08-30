#!/usr/bin/env python3
"""Revision-B complete exact-loader namespace executor; review-only/nonlive."""
from __future__ import annotations
import shutil,subprocess,sys
from pathlib import Path
if len(sys.argv)!=4: raise SystemExit("usage: case-run CODE ACTION SCENARIO_ROOT")
code=int(sys.argv[1]); action=Path(sys.argv[2]).resolve(); scenario=Path(sys.argv[3]).resolve(); data=action.read_bytes()
if code not in set(range(103,115))|{0}: raise SystemExit("unsupported byte-identical case")
if not scenario.is_dir() or not (scenario/"MANIFEST.sha256").is_file(): raise SystemExit("FROZEN_SCENARIO_REQUIRED")
if subprocess.run(["/usr/bin/sha256sum","-c","MANIFEST.sha256"],cwd=scenario,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode: raise SystemExit("SCENARIO_MANIFEST_MISMATCH")
bwrap=shutil.which("bwrap");
if not bwrap: raise SystemExit("BUBBLEWRAP_REQUIRED")
cmd=[bwrap,"--unshare-all","--die-with-parent","--ro-bind","/","/","--tmpfs","/dev/shm","--ro-bind",str(scenario),"/review-fixture"]
# Wire fixture command shims into paths the unchanged loader actually resolves. The loader PATH
# includes /usr/local/bin before /usr/bin; its nested git_clean PATH does too.
for name in ("git",):
 p=scenario/"bin"/name
 if p.is_file(): cmd += ["--ro-bind",str(p),f"/usr/local/bin/{name}"]
# sha256sum is absolute in the loader, so wire that exact observed path when supplied.
p=scenario/"bin"/"sha256sum"
if p.is_file(): cmd += ["--ro-bind",str(p),"/usr/bin/sha256sum"]
# Scenario-specific filesystem preconditions are mapped to exact loader-observed locations.
for rel,target in (("preexisting-root","/dev/shm/multiverse-r1-stage1-phase-c-recovery-control"),("repo-seed","/review-fixture/repo-seed")):
 p=scenario/rel
 if p.exists(): cmd += ["--ro-bind",str(p),target]
if code==103: codespaces=""; name=""
else: codespaces="true"; name="mv-review-fixture"
cmd += ["--setenv","CODESPACES",codespaces,"--setenv","CODESPACE_NAME",name,"/bin/bash","--noprofile","--norc","-c",data.decode("ascii")]
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr)
raise SystemExit(0 if p.returncode==code else 1)
