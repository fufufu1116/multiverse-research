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
SHM = '/dev/shm'
EXEC_NAME = 'multiverse-r1-stage1-phase-c-execution'
STALE_NAME = 'multiverse-r1-stage1-phase-c-execution-v19-7-29-stale'
TEMPLATE_NAME = 'multiverse-r1-stage1-phase-c-v19-7-29-empty-git-template'
STEP3_ACTION = 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_20_POST_OAUTH_STEP3_ACTION_V1_20260831.txt'
STEP3_ACTION_BYTES = 930
STEP3_ACTION_BLOB = '3bdd412c9da095c8c4077d8a53b8d6ac7fcb4d1b'
STEP3_ACTION_SHA256 = '84d6a772ea09557ae974a59c2f5227536c13144a9fedbd5b0d5039ea7b9b3aee'


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def clean_git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
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
    return subprocess.run(['git', *args], cwd=cwd, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def require_ok(cp: subprocess.CompletedProcess[str]) -> str:
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
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
        data = b''.join(chunks)
    finally:
        os.close(fd)
    if len(data) != STEP3_ACTION_BYTES or blob(data) != STEP3_ACTION_BLOB or hashlib.sha256(data).hexdigest() != STEP3_ACTION_SHA256:
        raise RuntimeError('STEP3_IDENTITY')
    return data


def rebootstrap_current_main() -> None:
    if os.environ.get('CODESPACES') != 'true' or not os.environ.get('CODESPACE_NAME'):
        raise RuntimeError('CODESPACES_REQUIRED')
    fs = subprocess.run(['/usr/bin/stat', '-f', '-c', '%T', SHM], text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if fs.returncode != 0 or fs.stdout.strip() not in {'tmpfs', 'ramfs'}:
        raise RuntimeError('SHM_NOT_MEMORY_BACKED')
    pfd = os.open(SHM, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        if os.path.exists(os.path.join(SHM, STALE_NAME)) or os.path.islink(os.path.join(SHM, STALE_NAME)):
            raise RuntimeError('STALE_QUARANTINE_PREEXISTS')
        os.rename(EXEC_NAME, STALE_NAME, src_dir_fd=pfd, dst_dir_fd=pfd)
        st = os.stat(STALE_NAME, dir_fd=pfd, follow_symlinks=False)
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o700:
            raise RuntimeError('STALE_ROOT_STATE')
        if os.path.exists(os.path.join(SHM, TEMPLATE_NAME)) or os.path.islink(os.path.join(SHM, TEMPLATE_NAME)):
            raise RuntimeError('TEMPLATE_PREEXISTS')
        os.mkdir(TEMPLATE_NAME, 0o700, dir_fd=pfd)
        os.mkdir(EXEC_NAME, 0o700, dir_fd=pfd)
        for name in (TEMPLATE_NAME, EXEC_NAME):
            now = os.stat(name, dir_fd=pfd, follow_symlinks=False)
            if not stat.S_ISDIR(now.st_mode) or now.st_uid != os.getuid() or stat.S_IMODE(now.st_mode) != 0o700:
                raise RuntimeError('FRESH_ROOT_STATE')
    finally:
        os.close(pfd)

    stale_root = os.path.join(SHM, STALE_NAME)
    if require_ok(clean_git(['rev-parse', '--verify', 'HEAD^{commit}'], stale_root)) != STALE_MAIN:
        raise RuntimeError('STALE_HEAD_MISMATCH')
    if require_ok(clean_git(['rev-parse', '--verify', 'HEAD^{tree}'], stale_root)) != STALE_TREE:
        raise RuntimeError('STALE_TREE_MISMATCH')
    stale_symbolic = clean_git(['symbolic-ref', '-q', 'HEAD'], stale_root)
    if stale_symbolic.returncode != 1:
        raise RuntimeError('STALE_NOT_DETACHED')
    if require_ok(clean_git(['remote'], stale_root)) != 'origin':
        raise RuntimeError('STALE_REMOTE_SET')
    if require_ok(clean_git(['config', '--local', '--get', 'remote.origin.url'], stale_root)) != ORIGIN:
        raise RuntimeError('STALE_ORIGIN_MISMATCH')
    if require_ok(clean_git(['status', '--porcelain=v1', '--untracked-files=all'], stale_root)):
        raise RuntimeError('STALE_WORKTREE_DIRTY')

    exec_root = os.path.join(SHM, EXEC_NAME)
    template = os.path.join(SHM, TEMPLATE_NAME)
    cp = clean_git(['clone', '--no-checkout', '--no-recurse-submodules', '--template=' + template, ORIGIN, exec_root], SHM)
    require_ok(cp)
    require_ok(clean_git(['config', '--local', 'core.hooksPath', '/dev/null'], exec_root))
    require_ok(clean_git(['checkout', '--detach', CURRENT_MAIN], exec_root))
    if os.path.lexists(os.path.join(exec_root, '.devcontainer')) or os.path.lexists(os.path.join(exec_root, '.devcontainer.json')):
        raise RuntimeError('STARTUP_PATH_PRESENT')
    if require_ok(clean_git(['rev-parse', '--verify', 'HEAD^{commit}'], exec_root)) != CURRENT_MAIN:
        raise RuntimeError('HEAD_MISMATCH')
    if require_ok(clean_git(['rev-parse', '--verify', 'HEAD^{tree}'], exec_root)) != CURRENT_TREE:
        raise RuntimeError('TREE_MISMATCH')
    symbolic = clean_git(['symbolic-ref', '-q', 'HEAD'], exec_root)
    if symbolic.returncode != 1:
        raise RuntimeError('NOT_DETACHED')
    if require_ok(clean_git(['remote'], exec_root)) != 'origin':
        raise RuntimeError('REMOTE_SET')
    if require_ok(clean_git(['config', '--local', '--get', 'remote.origin.url'], exec_root)) != ORIGIN:
        raise RuntimeError('ORIGIN_MISMATCH')
    if require_ok(clean_git(['status', '--porcelain=v1', '--untracked-files=all'], exec_root)):
        raise RuntimeError('WORKTREE_DIRTY')
    print('PHASE_C_V19_7_29_CURRENT_MAIN_REBOOTSTRAP_PASS', flush=True)


def main() -> int:
    if len(sys.argv) != 2:
        return RC_FAIL
    repo = os.path.realpath(sys.argv[1])
    if not os.path.isdir(os.path.join(repo, '.git')):
        return RC_FAIL
    data = read_step3_once(repo)
    print('PHASE_C_V19_7_29_STEP3_ACTION_IDENTITY_PASS', flush=True)
    rebootstrap_current_main()
    child = subprocess.run(['/bin/bash', '--noprofile', '--norc'], input=data, check=False)
    print(f'PHASE_C_V19_7_29_STEP3_RETURN_RC={child.returncode}', flush=True)
    return child.returncode if 0 <= child.returncode <= 255 else RC_FAIL


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        os._exit(RC_FAIL)
    raise SystemExit(rc)
