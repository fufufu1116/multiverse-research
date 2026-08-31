#!/usr/bin/env python3
import hashlib
import os
import stat
import subprocess
import sys

RC_FAIL = 92
STEP3_ACTION = 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_20_POST_OAUTH_STEP3_ACTION_V1_20260831.txt'
STEP3_ACTION_BYTES = 930
STEP3_ACTION_BLOB = '3bdd412c9da095c8c4077d8a53b8d6ac7fcb4d1b'
STEP3_ACTION_SHA256 = '84d6a772ea09557ae974a59c2f5227536c13144a9fedbd5b0d5039ea7b9b3aee'


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def read_once(repo: str) -> bytes:
    path = os.path.join(repo, STEP3_ACTION)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != os.getuid():
            raise RuntimeError('STEP3_ACTION_FILE_STATE_MISMATCH')
        chunks = []
        while True:
            part = os.read(fd, 1 << 20)
            if not part:
                break
            chunks.append(part)
        data = b''.join(chunks)
    finally:
        os.close(fd)
    if (
        len(data) != STEP3_ACTION_BYTES
        or blob(data) != STEP3_ACTION_BLOB
        or hashlib.sha256(data).hexdigest() != STEP3_ACTION_SHA256
    ):
        raise RuntimeError('STEP3_ACTION_IDENTITY_MISMATCH')
    return data


def main() -> int:
    if len(sys.argv) != 2:
        return RC_FAIL
    repo = os.path.realpath(sys.argv[1])
    if not os.path.isdir(os.path.join(repo, '.git')):
        return RC_FAIL
    data = read_once(repo)
    print('PHASE_C_V19_7_28_STEP3_ACTION_IDENTITY_PASS', flush=True)
    child = subprocess.run(
        ['/bin/bash', '--noprofile', '--norc'],
        input=data,
        check=False,
    )
    print(f'PHASE_C_V19_7_28_STEP3_RETURN_RC={child.returncode}', flush=True)
    return child.returncode if 0 <= child.returncode <= 255 else RC_FAIL


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        os._exit(RC_FAIL)
    raise SystemExit(rc)
