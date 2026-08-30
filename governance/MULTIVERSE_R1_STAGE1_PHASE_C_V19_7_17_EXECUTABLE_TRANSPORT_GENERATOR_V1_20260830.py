#!/usr/bin/env python3
import hashlib
import sys

SOURCE_LOADER_SHA256 = "ce4b53b6b4ccd18fbaeb1c57108d0d2fff6b85deca1c43514648f4f523ba19be"
OLD = b'/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START; if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
NEW = b'''export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START; /usr/bin/python3 - "$ROOT/$RUNNER" <<'"'"'PY'"'"'
import fcntl, hashlib, os, subprocess, sys
src_path=sys.argv[1]
src=open(src_path,"rb").read()
if len(src)!=5301 or hashlib.sha256(src).hexdigest()!="370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c":
    raise SystemExit(113)
anchor=b"tail=\'\'\'phase_c_bootstrap"
if src.count(anchor)!=1:
    raise SystemExit(113)
out=src.replace(anchor,b"tail=r\'\'\'phase_c_bootstrap",1)
if len(out)!=5302 or hashlib.sha256(out).hexdigest()!="248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e":
    raise SystemExit(113)
fd=os.memfd_create("mv-r1-stage1-phase-c-v19-7-17-runner", os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
if os.write(fd,out)!=len(out):
    raise SystemExit(113)
os.lseek(fd,0,os.SEEK_SET)
required_seals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
fcntl.fcntl(fd,fcntl.F_ADD_SEALS,required_seals)
if fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=required_seals:
    raise SystemExit(113)
os.set_inheritable(fd,True)
p=f"/proc/self/fd/{fd}"
with open(p,"rb",buffering=0) as r:
    snap=r.read()
if len(snap)!=5302 or hashlib.sha256(snap).hexdigest()!="248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e":
    raise SystemExit(113)
check=subprocess.run(["/usr/bin/git","hash-object","--no-filters","--stdin"],input=snap,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=False)
if check.returncode or check.stdout.strip()!=b"fe51117fd3fcaa41537b5f92c84841716af27f74":
    raise SystemExit(113)
parse=subprocess.run(["/bin/bash","--noprofile","--norc","-n",p],pass_fds=(fd,),check=False)
if parse.returncode:
    raise SystemExit(113)
run=subprocess.run(["/bin/bash","--noprofile","--norc",p],pass_fds=(fd,),check=False)
raise SystemExit(run.returncode)
PY
rc=$?; test "$rc" -eq 0 || fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; exit 0'''

def main():
    src=sys.stdin.buffer.read()
    if hashlib.sha256(src).hexdigest()!=SOURCE_LOADER_SHA256:
        raise SystemExit("SOURCE_LOADER_SHA256_MISMATCH")
    if src.count(OLD)!=1:
        raise SystemExit("OLD_ANCHOR_COUNT_MISMATCH")
    out=src.replace(OLD,NEW,1)
    sys.stdout.buffer.write(out)

if __name__=="__main__":
    main()
