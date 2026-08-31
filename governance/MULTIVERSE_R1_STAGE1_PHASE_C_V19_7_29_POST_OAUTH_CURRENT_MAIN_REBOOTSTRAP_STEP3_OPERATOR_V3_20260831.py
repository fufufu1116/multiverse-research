#!/usr/bin/env python3
import hashlib
import os
import stat
import subprocess
import sys

RC_FAIL = 92

ORIGIN = "https://github.com/fufufu1116/multiverse-research.git"
CANONICAL_MAIN = "5c1403c1f5aabb80d29e8c868440aede8888ce61"
CANONICAL_TREE = "3d47741b4863411e5c36cb4c28925ac455ab6441"
STALE_MAIN = "74ea95e59ac0654e1a0c1f811a178b3eef7b073c"

EXEC_ROOT = "/dev/shm/multiverse-r1-stage1-phase-c-execution"
NEW_ROOT = "/dev/shm/multiverse-r1-stage1-phase-c-execution-v19-7-29-new"
STALE_ROOT = "/dev/shm/multiverse-r1-stage1-phase-c-execution-v19-7-29-stale"
TEMPLATE = "/dev/shm/multiverse-r1-stage1-phase-c-v19-7-29-empty-template"
GIT_HOME = "/dev/shm/multiverse-r1-stage1-phase-c-v19-7-29-git-home"

STEP3_ACTION = "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_20_POST_OAUTH_STEP3_ACTION_V1_20260831.txt"
STEP3_ACTION_BYTES = 930
STEP3_ACTION_BLOB = "3bdd412c9da095c8c4077d8a53b8d6ac7fcb4d1b"
STEP3_ACTION_SHA256 = "84d6a772ea09557ae974a59c2f5227536c13144a9fedbd5b0d5039ea7b9b3aee"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def clean_env() -> dict[str, str]:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": GIT_HOME,
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }


def run_git(args: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=clean_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def must_git(args: list[str], *, cwd: str | None = None) -> str:
    cp = run_git(args, cwd=cwd)
    if cp.returncode != 0:
        raise RuntimeError("GIT_COMMAND_FAILED")
    return cp.stdout.strip()


def assert_tmpfs_dir(path: str, mode: int = 0o700) -> None:
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise RuntimeError("DIR_IDENTITY_MISMATCH")
    if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != mode:
        raise RuntimeError("DIR_PERMISSIONS_MISMATCH")
    cp = subprocess.run(
        ["stat", "-f", "-c", "%T", path],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
    )
    if cp.returncode != 0 or cp.stdout.strip() not in {"tmpfs", "ramfs"}:
        raise RuntimeError("DIR_NOT_MEMORY_BACKED")


def assert_repo(root: str, expected_head: str) -> None:
    assert_tmpfs_dir(root)
    dotgit = os.path.join(root, ".git")
    st = os.lstat(dotgit)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise RuntimeError("GITDIR_IDENTITY_MISMATCH")
    if must_git(["-C", root, "rev-parse", "--verify", "HEAD^{commit}"]) != expected_head:
        raise RuntimeError("HEAD_MISMATCH")
    if must_git(["-C", root, "rev-parse", "--verify", "HEAD^{tree}"]) != CANONICAL_TREE:
        raise RuntimeError("TREE_MISMATCH")
    sym = run_git(["-C", root, "symbolic-ref", "-q", "HEAD"])
    if sym.returncode != 1:
        raise RuntimeError("HEAD_NOT_DETACHED")
    if must_git(["-C", root, "remote"]) != "origin":
        raise RuntimeError("REMOTE_SET_MISMATCH")
    if must_git(["-C", root, "config", "--local", "--get", "remote.origin.url"]) != ORIGIN:
        raise RuntimeError("ORIGIN_MISMATCH")
    if must_git(["-C", root, "status", "--porcelain=v1", "--untracked-files=all"]):
        raise RuntimeError("WORKTREE_NOT_CLEAN")


def mkdir_fresh(path: str) -> None:
    if os.path.lexists(path):
        raise RuntimeError("FRESH_PATH_PREEXISTS")
    os.mkdir(path, 0o700)
    assert_tmpfs_dir(path)


def fresh_remote_main() -> None:
    cp = run_git(["ls-remote", "--heads", ORIGIN, "refs/heads/main"])
    if cp.returncode != 0:
        raise RuntimeError("LS_REMOTE_FAILED")
    rows = [line.split() for line in cp.stdout.splitlines() if line.strip()]
    if rows != [[CANONICAL_MAIN, "refs/heads/main"]]:
        raise RuntimeError("REMOTE_MAIN_DRIFT")


def rebootstrap_current_main() -> None:
    assert_repo(EXEC_ROOT, STALE_MAIN)
    stale_before = os.lstat(EXEC_ROOT)
    for path in (NEW_ROOT, STALE_ROOT, TEMPLATE, GIT_HOME):
        if os.path.lexists(path):
            raise RuntimeError("REBOOTSTRAP_PATH_PREEXISTS")

    mkdir_fresh(GIT_HOME)
    mkdir_fresh(TEMPLATE)
    fresh_remote_main()

    cp = run_git([
        "clone",
        "--no-checkout",
        "--no-recurse-submodules",
        f"--template={TEMPLATE}",
        ORIGIN,
        NEW_ROOT,
    ])
    if cp.returncode != 0:
        raise RuntimeError("CLONE_FAILED")
    assert_tmpfs_dir(NEW_ROOT)

    cp = run_git(["-C", NEW_ROOT, "config", "--local", "core.hooksPath", "/dev/null"])
    if cp.returncode != 0:
        raise RuntimeError("HOOKS_DISABLE_FAILED")

    if must_git(["-C", NEW_ROOT, "rev-parse", "--verify", "refs/remotes/origin/main^{commit}"]) != CANONICAL_MAIN:
        raise RuntimeError("CLONED_MAIN_DRIFT")

    cp = run_git(["-C", NEW_ROOT, "checkout", "--detach", CANONICAL_MAIN])
    if cp.returncode != 0:
        raise RuntimeError("CHECKOUT_FAILED")
    assert_repo(NEW_ROOT, CANONICAL_MAIN)

    assert_repo(EXEC_ROOT, STALE_MAIN)
    stale_now = os.lstat(EXEC_ROOT)
    if (stale_now.st_dev, stale_now.st_ino) != (stale_before.st_dev, stale_before.st_ino):
        raise RuntimeError("STALE_ROOT_CHANGED_BEFORE_SWITCH")

    new_before = os.lstat(NEW_ROOT)
    os.rename(EXEC_ROOT, STALE_ROOT)
    stale_after = os.lstat(STALE_ROOT)
    if (stale_after.st_dev, stale_after.st_ino) != (stale_before.st_dev, stale_before.st_ino):
        raise RuntimeError("STALE_ROOT_SWITCH_IDENTITY_MISMATCH")
    try:
        os.rename(NEW_ROOT, EXEC_ROOT)
    except Exception:
        raise RuntimeError("EXEC_ROOT_SWITCH_FAILED")

    current_after = os.lstat(EXEC_ROOT)
    if (current_after.st_dev, current_after.st_ino) != (new_before.st_dev, new_before.st_ino):
        raise RuntimeError("CURRENT_ROOT_SWITCH_IDENTITY_MISMATCH")
    assert_repo(EXEC_ROOT, CANONICAL_MAIN)
    print("PHASE_C_V19_7_29_CURRENT_MAIN_REBOOTSTRAP_PASS", flush=True)


def read_step3_once(repo: str) -> bytes:
    path = os.path.join(repo, STEP3_ACTION)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_uid != os.getuid():
            raise RuntimeError("STEP3_ACTION_FILE_STATE_MISMATCH")
        chunks = []
        while True:
            part = os.read(fd, 1 << 20)
            if not part:
                break
            chunks.append(part)
        data = b"".join(chunks)
    finally:
        os.close(fd)

    if (
        len(data) != STEP3_ACTION_BYTES
        or git_blob(data) != STEP3_ACTION_BLOB
        or hashlib.sha256(data).hexdigest() != STEP3_ACTION_SHA256
    ):
        raise RuntimeError("STEP3_ACTION_IDENTITY_MISMATCH")
    return data


def main() -> int:
    os.umask(0o077)
    if os.environ.get("CODESPACES") != "true" or not os.environ.get("CODESPACE_NAME"):
        return RC_FAIL
    if len(sys.argv) != 2:
        return RC_FAIL
    review_repo = os.path.realpath(sys.argv[1])
    if not os.path.isdir(os.path.join(review_repo, ".git")):
        return RC_FAIL

    step3 = read_step3_once(review_repo)
    print("PHASE_C_V19_7_29_STEP3_ACTION_IDENTITY_PASS", flush=True)

    rebootstrap_current_main()

    child = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc"],
        input=step3,
        check=False,
    )
    print(f"PHASE_C_V19_7_29_STEP3_RETURN_RC={child.returncode}", flush=True)
    return child.returncode if 0 <= child.returncode <= 255 else RC_FAIL


if __name__ == "__main__":
    try:
        rc = main()
    except Exception:
        try:
            print("PHASE_C_V19_7_29_FAIL_CLOSED", flush=True)
        except Exception:
            pass
        os._exit(RC_FAIL)
    raise SystemExit(rc)
