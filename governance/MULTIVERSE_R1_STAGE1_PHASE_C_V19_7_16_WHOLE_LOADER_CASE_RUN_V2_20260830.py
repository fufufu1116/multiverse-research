#!/usr/bin/env python3
"""Revision-B whole-loader case-run fixture.

Fail closed unless Linux bubblewrap is available. The fixture executes the complete exact
loader action unchanged inside an isolated mount/PID/network namespace. Boundary binaries
and /dev/shm are supplied by the namespace, not by editing/extracting loader control flow.
This is review evidence only; it grants no live authority.
"""
from __future__ import annotations
import os,shutil,subprocess,sys,tempfile
from pathlib import Path
if len(sys.argv)!=3: raise SystemExit("usage: case-run CODE ACTION")
code=int(sys.argv[1]); action=Path(sys.argv[2]).resolve(); data=action.read_bytes()
if code not in set(range(103,116))|{0}: raise SystemExit("unsupported case")
bwrap=shutil.which("bwrap")
if not bwrap: raise SystemExit("BUBBLEWRAP_REQUIRED")
# The exact loader is mounted read-only and invoked byte-for-byte. A scenario-specific
# fixture root supplies deterministic /usr/local/bin/git and /usr/bin/sha256sum shims plus
# an inert historical-runner-shaped file. No network is exposed.
fixture=os.environ.get("MV_V19_7_16_NAMESPACE_FIXTURE")
if not fixture: raise SystemExit("NAMESPACE_FIXTURE_REQUIRED")
f=Path(fixture).resolve(); assert (f/"git").is_file() and (f/"sha256sum").is_file()
env=os.environ.copy(); env["MV_CASE_CODE"]=str(code)
cmd=[bwrap,"--unshare-all","--die-with-parent","--ro-bind","/","/","--tmpfs","/dev/shm","--ro-bind",str(action),"/tmp/exact-action.txt","--bind",str(f/"git"),"/usr/local/bin/git","--bind",str(f/"sha256sum"),"/usr/bin/sha256sum","--setenv","CODESPACES","true","--setenv","CODESPACE_NAME","mv-review-fixture","/bin/bash","--noprofile","--norc","-c",data.decode("ascii")]
p=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
# Parent harness validates the detailed transcript contract; case-run succeeds only if
# observed exact outer status equals requested scenario (or 0 success).
if p.returncode!=code:
 sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr); raise SystemExit(1)
sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr)
