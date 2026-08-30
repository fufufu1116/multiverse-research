#!/usr/bin/env python3
import hashlib
import sys

SOURCE_LOADER_BYTES = 6382
SOURCE_LOADER_GIT_BLOB = "01c34b393ae272f9e026fc734560170c076e2fc2"
SOURCE_LOADER_SHA256 = "ce4b53b6b4ccd18fbaeb1c57108d0d2fff6b85deca1c43514648f4f523ba19be"
OLD = b'/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START; if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
NEW = b'export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START; if /usr/bin/python3 - "$ROOT/$RUNNER" <<\'"\'"\'PY\'"\'"\'\nimport fcntl, hashlib, os, subprocess, sys\nsrc_path=sys.argv[1]\nwith open(src_path,"rb",buffering=0) as f:\n    src=f.read()\nif len(src)!=5301 or hashlib.sha256(src).hexdigest()!="370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c":\n    raise SystemExit(113)\nanchor=b"tail=\'\'\'phase_c_bootstrap"\nif src.count(anchor)!=1:\n    raise SystemExit(113)\nout=src.replace(anchor,b"tail=r\'\'\'phase_c_bootstrap",1)\nif len(out)!=5302 or hashlib.sha256(out).hexdigest()!="248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e":\n    raise SystemExit(113)\nfd=os.memfd_create("mv-r1-stage1-phase-c-v19-7-17-runner",os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)\nif os.write(fd,out)!=len(out):\n    raise SystemExit(113)\nos.lseek(fd,0,os.SEEK_SET)\nseals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE\nfcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)\nif fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=seals:\n    raise SystemExit(113)\nsnap=os.pread(fd,5303,0)\nif len(snap)!=5302 or hashlib.sha256(snap).hexdigest()!="248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e":\n    raise SystemExit(113)\nhdr=b"blob "+str(len(snap)).encode("ascii")+b"\\0"\nif hashlib.sha1(hdr+snap).hexdigest()!="fe51117fd3fcaa41537b5f92c84841716af27f74":\n    raise SystemExit(113)\nos.set_inheritable(fd,True)\np=f"/proc/self/fd/{fd}"\nparse=subprocess.run(["/bin/bash","--noprofile","--norc","-n",p],pass_fds=(fd,),check=False)\nif parse.returncode:\n    raise SystemExit(113)\nrun=subprocess.run(["/bin/bash","--noprofile","--norc",p],pass_fds=(fd,),check=False)\nraise SystemExit(run.returncode)\nPY\nthen exit 0; else rc=$?; if test "$rc" -eq 113; then fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi; fi'

def git_blob_sha1(data):
    hdr=b"blob "+str(len(data)).encode("ascii")+b"\0"
    return hashlib.sha1(hdr+data).hexdigest()

def main():
    src=sys.stdin.buffer.read()
    if len(src)!=SOURCE_LOADER_BYTES:
        raise SystemExit("SOURCE_LOADER_LENGTH_MISMATCH")
    if git_blob_sha1(src)!=SOURCE_LOADER_GIT_BLOB:
        raise SystemExit("SOURCE_LOADER_BLOB_MISMATCH")
    if hashlib.sha256(src).hexdigest()!=SOURCE_LOADER_SHA256:
        raise SystemExit("SOURCE_LOADER_SHA256_MISMATCH")
    if src.count(OLD)!=1:
        raise SystemExit("OLD_ANCHOR_COUNT_MISMATCH")
    out=src.replace(OLD,NEW,1)
    sys.stdout.buffer.write(out)

if __name__=="__main__":
    main()
