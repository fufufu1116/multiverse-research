#!/usr/bin/env python3
import fcntl
import hashlib
import os
import stat
import subprocess
import sys

RC_FAIL = 92
SOURCE_ACTION = 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt'
TRANSFORMED_RUNNER = 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh'
SOURCE_ACTION_BLOB = '396c5f99c8837b4bc946a76effe1e19cd391b7d0'
TRANSFORMED_RUNNER_BYTES = 5302
TRANSFORMED_RUNNER_BLOB = 'fe51117fd3fcaa41537b5f92c84841716af27f74'
TRANSFORMED_RUNNER_SHA256 = '248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e'
HISTORICAL_RUNNER_BYTES = 5301
HISTORICAL_RUNNER_BLOB = 'bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
HISTORICAL_RUNNER_SHA256 = '370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
TRANSFORMED_ANCHOR = b"tail=r'''phase_c_bootstrap"
HISTORICAL_ANCHOR = b"tail='''phase_c_bootstrap"
STALE_RUNNER_SHA256 = b'f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2'
CORRECTED_LOADER_BYTES = 6382
CORRECTED_LOADER_BLOB = '01c34b393ae272f9e026fc734560170c076e2fc2'
CORRECTED_LOADER_SHA256 = 'ce4b53b6b4ccd18fbaeb1c57108d0d2fff6b85deca1c43514648f4f523ba19be'
GEN_OLD = b'/bin/bash --noprofile --norc -n "$ROOT/$RUNNER" >/dev/null 2>&1 || fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START; if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi'
GEN_NEW = b'export RECOVERY_ROOT="$ROOT"; mark PHASE_C_V19_7_15_RUNNER_START; if /usr/bin/python3 - "$ROOT/$RUNNER" <<\'"\'"\'PY\'"\'"\'\nimport fcntl, hashlib, os, subprocess, sys\nsrc_path=sys.argv[1]\nwith open(src_path,"rb",buffering=0) as f:\n    src=f.read()\nif len(src)!=5301 or hashlib.sha256(src).hexdigest()!="370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c":\n    raise SystemExit(113)\nanchor=b"tail=\'\'\'phase_c_bootstrap"\nif src.count(anchor)!=1:\n    raise SystemExit(113)\nout=src.replace(anchor,b"tail=r\'\'\'phase_c_bootstrap",1)\nif len(out)!=5302 or hashlib.sha256(out).hexdigest()!="248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e":\n    raise SystemExit(113)\nfd=os.memfd_create("mv-r1-stage1-phase-c-v19-7-17-runner",os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)\nif os.write(fd,out)!=len(out):\n    raise SystemExit(113)\nos.lseek(fd,0,os.SEEK_SET)\nseals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE\nfcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)\nif fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=seals:\n    raise SystemExit(113)\nsnap=os.pread(fd,5303,0)\nif len(snap)!=5302 or hashlib.sha256(snap).hexdigest()!="248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e":\n    raise SystemExit(113)\nhdr=b"blob "+str(len(snap)).encode("ascii")+b"\\0"\nif hashlib.sha1(hdr+snap).hexdigest()!="fe51117fd3fcaa41537b5f92c84841716af27f74":\n    raise SystemExit(113)\nos.set_inheritable(fd,True)\np=f"/proc/self/fd/{fd}"\nparse=subprocess.run(["/bin/bash","--noprofile","--norc","-n",p],pass_fds=(fd,),check=False)\nif parse.returncode:\n    raise SystemExit(113)\nrun=subprocess.run(["/bin/bash","--noprofile","--norc",p],pass_fds=(fd,),check=False)\nraise SystemExit(run.returncode)\nPY\nthen exit 0; else rc=$?; if test "$rc" -eq 113; then fail PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi; fi'
GEN_OUTPUT_BYTES = 7945
GEN_OUTPUT_BLOB = '882ef767bfd816348f07e183258fcaa0490a6e6c'
GEN_OUTPUT_SHA256 = '67c3e1024795d8bf65024d309fd19e5903d0105f5e3b57e48764c028182c6d2d'
FILTER_OLD1 = b'anchor=b"tail=\'\'\'phase_c_bootstrap"'
FILTER_OLD2 = b'b"tail=r\'\'\'phase_c_bootstrap"'
SPLICE3 = b'\'"\'"\'\'"\'"\'\'"\'"\''
FILTER_NEW1 = b'anchor=b"tail=' + SPLICE3 + b'phase_c_bootstrap"'
FILTER_NEW2 = b'b"tail=r' + SPLICE3 + b'phase_c_bootstrap"'
FINAL_BYTES = 7969
FINAL_BLOB = '90369186f103e192674a711f58460b05fd0d8bee'
FINAL_SHA256 = 'c7f4f15f3f2e5b29b495c42c86e39774e577cbf484ae4555d3262fb96b299136'


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def read_once(repo: str, rel: str, expected_blob: str) -> bytes:
    path = os.path.join(repo, rel)
    flags = os.O_RDONLY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != os.getuid():
            raise RuntimeError('INPUT_FILE_STATE_MISMATCH')
        chunks = []
        while True:
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
        data = b''.join(chunks)
    finally:
        os.close(fd)
    if blob(data) != expected_blob:
        raise RuntimeError('INPUT_BLOB_MISMATCH')
    return data


def require_identity(data: bytes, n: int, git_blob: str, sha256: str) -> None:
    if len(data) != n or blob(data) != git_blob or hashlib.sha256(data).hexdigest() != sha256:
        raise RuntimeError('IDENTITY_MISMATCH')


def main() -> int:
    if len(sys.argv) != 2:
        return RC_FAIL
    repo = os.path.realpath(sys.argv[1])
    if not os.path.isdir(os.path.join(repo, '.git')):
        return RC_FAIL

    action = read_once(repo, SOURCE_ACTION, SOURCE_ACTION_BLOB)
    runner = read_once(repo, TRANSFORMED_RUNNER, TRANSFORMED_RUNNER_BLOB)
    require_identity(runner, TRANSFORMED_RUNNER_BYTES, TRANSFORMED_RUNNER_BLOB, TRANSFORMED_RUNNER_SHA256)

    if runner.count(TRANSFORMED_ANCHOR) != 1 or runner.count(HISTORICAL_ANCHOR) != 0:
        return RC_FAIL
    historical = runner.replace(TRANSFORMED_ANCHOR, HISTORICAL_ANCHOR, 1)
    require_identity(historical, HISTORICAL_RUNNER_BYTES, HISTORICAL_RUNNER_BLOB, HISTORICAL_RUNNER_SHA256)

    correct = HISTORICAL_RUNNER_SHA256.encode('ascii')
    if action.count(STALE_RUNNER_SHA256) != 1 or action.count(correct) != 0:
        return RC_FAIL
    loader = action.replace(STALE_RUNNER_SHA256, correct, 1)
    require_identity(loader, CORRECTED_LOADER_BYTES, CORRECTED_LOADER_BLOB, CORRECTED_LOADER_SHA256)

    if loader.count(GEN_OLD) != 1 or loader.count(GEN_NEW) != 0:
        return RC_FAIL
    generated = loader.replace(GEN_OLD, GEN_NEW, 1)
    require_identity(generated, GEN_OUTPUT_BYTES, GEN_OUTPUT_BLOB, GEN_OUTPUT_SHA256)

    if generated.count(FILTER_OLD1) != 1 or generated.count(FILTER_OLD2) != 1:
        return RC_FAIL
    if generated.count(FILTER_NEW1) != 0 or generated.count(FILTER_NEW2) != 0:
        return RC_FAIL
    final = generated.replace(FILTER_OLD1, FILTER_NEW1, 1).replace(FILTER_OLD2, FILTER_NEW2, 1)
    require_identity(final, FINAL_BYTES, FINAL_BLOB, FINAL_SHA256)

    fd = os.memfd_create('mv-r1-stage1-phase-c-v19-7-27-transport', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        if os.write(fd, final) != len(final):
            return RC_FAIL
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        if fcntl.fcntl(fd, fcntl.F_GET_SEALS) != seals:
            return RC_FAIL
        snap = os.pread(fd, FINAL_BYTES + 1, 0)
        require_identity(snap, FINAL_BYTES, FINAL_BLOB, FINAL_SHA256)
        os.set_inheritable(fd, True)
        p = f'/proc/self/fd/{fd}'
        parse = subprocess.run(['/bin/bash', '--noprofile', '--norc', '-n', p], pass_fds=(fd,), check=False)
        if parse.returncode != 0:
            print(f'PHASE_C_V19_7_27_SEALED_TRANSPORT_PARSE_FAILED_RC={parse.returncode}')
            return 0
        print('PHASE_C_V19_7_19_WRAPPER_TRANSPORT_IDENTITY_PASS', flush=True)
        print('PHASE_C_V19_7_19_LIVE_CHILD_START', flush=True)
        child = subprocess.run(['/bin/bash', '--noprofile', '--norc', p], pass_fds=(fd,), check=False)
        print(f'PHASE_C_V19_7_19_LIVE_CHILD_RETURN_RC={child.returncode}', flush=True)
        print('PHASE_C_V19_7_19_WRAPPER_RETURNING_TO_PARENT_SHELL', flush=True)
        return 0
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        os._exit(RC_FAIL)
    raise SystemExit(rc)
