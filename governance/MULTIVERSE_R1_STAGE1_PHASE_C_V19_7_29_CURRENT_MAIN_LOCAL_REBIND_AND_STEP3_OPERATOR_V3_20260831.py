#!/usr/bin/env python3
import hashlib
import os
import stat
import subprocess
import sys

RC_FAIL = 92
ORIGIN = 'https://github.com/fufufu1116/multiverse-research.git'
CURRENT_MAIN = '5c1403c1f5aabb80d29e8c868440aede8888ce61'
CURRENT_TREE = '3d47741b4863411e5c36cb4c28925ac455ab6441'
STALE_MAIN = '74ea95e59ac0654e1a0c1f811a178b3eef7b073c'
STALE_TREE = '3d47741b4863411e5c36cb4c28925ac455ab6441'
EXEC_ROOT = '/dev/shm/multiverse-r1-stage1-phase-c-execution'
STEP3_ACTION = 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_20_POST_OAUTH_STEP3_ACTION_V1_20260831.txt'
STEP3_ACTION_BYTES = 930
STEP3_ACTION_BLOB = '3bdd412c9da095c8c4077d8a53b8d6ac7fcb4d1b'
STEP3_ACTION_SHA256 = '84d6a772ea09557ae974a59c2f5227536c13144a9fedbd5b0d5039ea7b9b3aee'


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def clean_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = {
        'PATH': '/usr/local/bin:/usr/bin:/bin',
        'HOME': '/dev/shm/multiverse-r1-stage1-phase-c-recovery-control-home',
        'LANG': 'C',
        'LC_ALL': 'C',
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_CONFIG_SYSTEM': '/dev/null',
        'GIT_CONFIG_GLOBAL': '/dev/null',
        'GIT_ATTR_NOSYSTEM': '1',
        'GIT_NO_REPLACE_OBJECTS': '1',
        'GIT_TERMINAL_PROMPT': '0',
    }
    return subprocess.run(['git', *args], cwd=EXEC_ROOT, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def out(args: list[str]) -> str:
    cp = clean_git(args)
    if cp.returncode != 0:
        raise RuntimeError('GIT_FAILED')
    return cp.stdout.strip()


def read_step3_once(repo: str) -> bytes:
    path = os.path.join(repo, STEP3_ACTION)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != os.getuid():
            raise RuntimeError('STEP3_FILE_STATE')
        chunks = []
        while True:
            part = os.read(fd, 1 << 20)
            if not part:
                break
            chunks.append(part)
        data = b''.join(chunks)
    finally:
        os.close(fd)
    if len(data) != STEP3_ACTION_BYTES or blob(data) != STEP3_ACTION_BLOB or hashlib.sha256(data).hexdigest() != STEP3_ACTION_SHA256:
        raise RuntimeError('STEP3_IDENTITY')
    return data


def bind_and_recheckout_current_main() -> None:
    if os.environ.get('CODESPACES') != 'true' or not os.environ.get('CODESPACE_NAME'):
        raise RuntimeError('CODESPACES_REQUIRED')
    st = os.lstat(EXEC_ROOT)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o700:
        raise RuntimeError('EXEC_ROOT_STATE')
    fs = subprocess.run(['/usr/bin/stat', '-f', '-c', '%T', EXEC_ROOT], text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if fs.returncode != 0 or fs.stdout.strip() not in {'tmpfs', 'ramfs'}:
        raise RuntimeError('EXEC_ROOT_NOT_MEMORY_BACKED')
    if out(['rev-parse', '--verify', 'HEAD^{commit}']) != STALE_MAIN:
        raise RuntimeError('STALE_HEAD_MISMATCH')
    if out(['rev-parse', '--verify', 'HEAD^{tree}']) != STALE_TREE:
        raise RuntimeError('STALE_TREE_MISMATCH')
    if out(['rev-parse', '--verify', 'refs/remotes/origin/main^{commit}']) != CURRENT_MAIN:
        raise RuntimeError('REMOTE_MAIN_MISMATCH')
    if out(['rev-parse', '--verify', CURRENT_MAIN + '^{tree}']) != CURRENT_TREE:
        raise RuntimeError('CURRENT_TREE_MISMATCH')
    symbolic = clean_git(['symbolic-ref', '-q', 'HEAD'])
    if symbolic.returncode != 1:
        raise RuntimeError('STALE_NOT_DETACHED')
    if out(['remote']) != 'origin':
        raise RuntimeError('REMOTE_SET')
    if out(['config', '--local', '--get', 'remote.origin.url']) != ORIGIN:
        raise RuntimeError('ORIGIN_MISMATCH')
    if out(['status', '--porcelain=v1', '--untracked-files=all']):
        raise RuntimeError('STALE_WORKTREE_DIRTY')
    if STALE_TREE != CURRENT_TREE:
        raise RuntimeError('TREE_EQUIVALENCE_REQUIRED')
    cp = clean_git(['config', '--local', 'core.hooksPath', '/dev/null'])
    if cp.returncode != 0:
        raise RuntimeError('HOOKS_DISABLE_FAILED')
    cp = clean_git(['checkout', '--detach', CURRENT_MAIN])
    if cp.returncode != 0:
        raise RuntimeError('CURRENT_CHECKOUT_FAILED')
    if out(['rev-parse', '--verify', 'HEAD^{commit}']) != CURRENT_MAIN:
        raise RuntimeError('CURRENT_HEAD_MISMATCH')
    if out(['rev-parse', '--verify', 'HEAD^{tree}']) != CURRENT_TREE:
        raise RuntimeError('CURRENT_HEAD_TREE_MISMATCH')
    symbolic = clean_git(['symbolic-ref', '-q', 'HEAD'])
    if symbolic.returncode != 1:
        raise RuntimeError('CURRENT_NOT_DETACHED')
    if out(['status', '--porcelain=v1', '--untracked-files=all']):
        raise RuntimeError('CURRENT_WORKTREE_DIRTY')
    if os.path.lexists(os.path.join(EXEC_ROOT, '.devcontainer')) or os.path.lexists(os.path.join(EXEC_ROOT, '.devcontainer.json')):
        raise RuntimeError('STARTUP_PATH_PRESENT')
    print('PHASE_C_V19_7_29_CURRENT_MAIN_LOCAL_REBIND_PASS', flush=True)


def main() -> int:
    if len(sys.argv) != 2:
        return RC_FAIL
    repo = os.path.realpath(sys.argv[1])
    if not os.path.isdir(os.path.join(repo, '.git')):
        return RC_FAIL
    data = read_step3_once(repo)
    print('PHASE_C_V19_7_29_STEP3_ACTION_IDENTITY_PASS', flush=True)
    bind_and_recheckout_current_main()
    child = subprocess.run(['/bin/bash', '--noprofile', '--norc'], input=data, check=False)
    print(f'PHASE_C_V19_7_29_STEP3_RETURN_RC={child.returncode}', flush=True)
    return child.returncode if 0 <= child.returncode <= 255 else RC_FAIL


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        os._exit(RC_FAIL)
    raise SystemExit(rc)
