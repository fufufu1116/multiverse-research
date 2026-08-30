#!/usr/bin/env python3
"""Revision-B complete exact-loader namespace executor.
Review-only. Scenario selection is a filesystem path chosen before loader entry; no MV_CASE_CODE
or other selector is expected to survive the loader's env -i boundaries.
"""
from __future__ import annotations
import os,shutil,subprocess,sys
from pathlib import Path
if len(sys.argv)!=4: raise SystemExit("usage: case-run CODE ACTION SCENARIO_ROOT")
code=int(sys.argv[1]); action=Path(sys.argv[2]).resolve(); scenario=Path(sys.argv[3]).resolve(); data=action.read_bytes()
if code not in set(range(103,115))|{0}: raise SystemExit("unsupported byte-identical case")
if not scenario.is_dir(): raise SystemExit("SCENARIO_ROOT_REQUIRED")
bwrap=shutil.which("bwrap")
if not bwrap: raise SystemExit("BUBBLEWRAP_REQUIRED")
# Scenario roots are complete frozen filesystem fixtures. They contain only reviewed boundary
# objects (command shims/repository image/synthetic runner metadata) and never replacement loader flow.
manifest=scenario/"MANIFEST.sha256"
if not manifest.is_file(): raise SystemExit("SCENARIO_MANIFEST_REQUIRED")
check=subprocess.run(["sha256sum","-c",str(manifest)],cwd=scenario,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if check.returncode: raise SystemExit("SCENARIO_MANIFEST_MISMATCH")
cmd=[bwrap,"--unshare-all","--die-with-parent","--ro-bind","/","/","--tmpfs","/dev/shm","--ro-bind",str(scenario),"/review-fixture","--ro-bind",str(action),"/tmp/exact-action.txt","--setenv","CODESPACES","true","--setenv","CODESPACE_NAME","mv-review-fixture","/bin/bash","--noprofile","--norc","-c",data.decode("ascii")]
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr)
raise SystemExit(0 if p.returncode==code else 1)
