#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

CONTROLLED_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/local/python/current/bin"
CANONICAL_SHA = "74ea95e59ac0654e1a0c1f811a178b3eef7b073c"
CANONICAL_ORIGIN = "https://github.com/fufufu1116/multiverse-research.git"
EXEC_ROOT = Path("/dev/shm/multiverse-r1-stage1-phase-c-execution")
GH_CONFIG_DIR = "/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
CRITICAL_PATHS = (
    "tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py",
    "tools/multiverse_r1_stage1_writer_key_provisioner_v1.py",
    "tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py",
)
FAIL = "PHASE_C_V19_7_7_STEP3_STANDALONE_STOP_DELETE_CODESPACE"
SUCCESS = "PHASE_C_V19_7_7_NONMUTATING_STEP3_PASS"


def stop(stage: str, detail: str = "") -> None:
    suffix = f":{stage}" + (f":{detail}" if detail else "")
    print(FAIL + suffix, file=sys.stderr, flush=True)
    raise SystemExit(92)


def run_clean_git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    cp = subprocess.run(
        ["/usr/bin/git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    if check and cp.returncode != 0:
        stop("GIT_COMMAND")
    return cp


def require_env() -> None:
    if os.environ.get("PATH") != CONTROLLED_PATH:
        stop("PATH")
    if os.environ.get("GH_CONFIG_DIR") != GH_CONFIG_DIR:
        stop("GH_CONFIG_DIR")
    if os.environ.get("CODESPACES") != "true" or not os.environ.get("CODESPACE_NAME"):
        stop("CODESPACE_BINDING")
    if sys.executable != "/usr/local/python/current/bin/python":
        stop("TRUSTED_PYTHON")


def require_memory_root(path: Path, stage: str) -> None:
    try:
        st = path.lstat()
    except OSError:
        stop(stage, "MISSING")
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        stop(stage, "TYPE")
    if stat.S_IMODE(st.st_mode) != 0o700:
        stop(stage, "MODE")
    if st.st_uid != os.getuid():
        stop(stage, "OWNER")
    cp = subprocess.run(["/usr/bin/stat", "-f", "-c", "%T", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if cp.returncode != 0 or cp.stdout.strip() not in {"tmpfs", "ramfs"}:
        stop(stage, "NOT_MEMORY_BACKED")


def verify_checkout() -> None:
    require_memory_root(Path(os.environ.get("HOME", "")), "HOME")
    require_memory_root(Path(GH_CONFIG_DIR), "GH_MEMORY")
    require_memory_root(EXEC_ROOT, "EXEC_ROOT")

    swaps = Path("/proc/swaps").read_text(encoding="utf-8").splitlines()
    if len(swaps) != 1:
        stop("SWAP")

    git_dir = EXEC_ROOT / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink():
        stop("GIT_DIR")

    head = run_clean_git("-C", str(EXEC_ROOT), "rev-parse", "--verify", "HEAD^{commit}", check=True).stdout.strip()
    if head != CANONICAL_SHA:
        stop("HEAD")

    symbolic = run_clean_git("-C", str(EXEC_ROOT), "symbolic-ref", "-q", "HEAD")
    if symbolic.returncode != 1:
        stop("DETACHED_HEAD")

    remotes = run_clean_git("-C", str(EXEC_ROOT), "remote", check=True).stdout.strip()
    if remotes != "origin":
        stop("REMOTE_SET")
    origin = run_clean_git("-C", str(EXEC_ROOT), "config", "--local", "--get", "remote.origin.url", check=True).stdout.strip()
    if origin != CANONICAL_ORIGIN:
        stop("ORIGIN")

    ls_v = run_clean_git("-C", str(EXEC_ROOT), "ls-files", "-v", check=True).stdout.splitlines()
    if any(line and line[0].islower() for line in ls_v):
        stop("INDEX_FLAGS")
    ls_t = run_clean_git("-C", str(EXEC_ROOT), "ls-files", "-t", check=True).stdout.splitlines()
    if any(line.startswith("S ") for line in ls_t):
        stop("SKIP_WORKTREE")

    for rel in CRITICAL_PATHS:
        tree_line = run_clean_git("-C", str(EXEC_ROOT), "ls-tree", CANONICAL_SHA, "--", rel, check=True).stdout.rstrip("\n")
        if not tree_line:
            stop("CRITICAL_TREE", rel)
        try:
            meta, listed = tree_line.split("\t", 1)
            mode, obj_type, oid = meta.split(" ", 2)
        except ValueError:
            stop("CRITICAL_TREE_PARSE", rel)
        if mode != "100644" or obj_type != "blob" or listed != rel:
            stop("CRITICAL_TREE_META", rel)
        p = EXEC_ROOT / rel
        try:
            st = p.lstat()
        except OSError:
            stop("CRITICAL_FILE_MISSING", rel)
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or (st.st_mode & 0o111):
            stop("CRITICAL_FILE_TYPE", rel)
        if st.st_nlink != 1 or st.st_uid != os.getuid() or (stat.S_IMODE(st.st_mode) & 0o022):
            stop("CRITICAL_FILE_META", rel)
        actual = run_clean_git("-C", str(EXEC_ROOT), "hash-object", "--no-filters", "--", rel, check=True).stdout.strip()
        if actual != oid:
            stop("CRITICAL_FILE_BLOB", rel)

    status_out = run_clean_git("-C", str(EXEC_ROOT), "status", "--porcelain=v1", "--untracked-files=all", check=True).stdout
    if status_out:
        stop("WORKTREE_DIRTY")


def run_preflight() -> dict:
    cp = subprocess.run(
        ["/usr/local/python/current/bin/python", "-B", "tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py"],
        cwd=str(EXEC_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    if cp.returncode != 0:
        stop("PREFLIGHT_NONZERO", str(cp.returncode))
    try:
        data = json.loads(cp.stdout)
    except Exception:
        stop("PREFLIGHT_JSON")
    if not isinstance(data, dict):
        stop("PREFLIGHT_TYPE")
    if data.get("status") != "PHASE_C_NONMUTATING_PREFLIGHT_PASS":
        stop("PREFLIGHT_STATUS")
    if data.get("production_mutation_performed") is not False:
        stop("PRODUCTION_MUTATION_FLAG")
    if data.get("runtime_activation_performed") is not False:
        stop("RUNTIME_ACTIVATION_FLAG")
    return data


def main() -> None:
    require_env()
    verify_checkout()
    run_preflight()
    print(SUCCESS, flush=True)


if __name__ == "__main__":
    main()
