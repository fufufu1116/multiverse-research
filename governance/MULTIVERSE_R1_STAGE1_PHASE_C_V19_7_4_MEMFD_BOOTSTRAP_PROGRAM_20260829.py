#!/usr/bin/env python3
import fcntl
import hashlib
import os
import subprocess
import sys

SPEC = [
    ("https://raw.githubusercontent.com/fufufu1116/multiverse-research/6b140d458812c84598ed3fcb3528f9b5e6176c86/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_3_STEP2_6_PAYLOAD_20260829.sh", 3692, "5fd32b4eeb7152170de17048e6a88206b411aca230833e0dccd04a86aa5a1066", "543d64387aa73e3ac14ba9819d6a33b0a82efe15", "step26"),
    ("https://raw.githubusercontent.com/fufufu1116/multiverse-research/03a816c86af992bef24ac73d842cc420e3fc8d17/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_3_STEP3_NONMUTATING_PAYLOAD_20260829.sh", 1309, "1fb3f574b77e03092e6b7ed00b3f02bd6960c7ecf1091b9ac0795abc2523a3c5", "2bdf758e534cd6cea30a59e185681937168bdd04", "step3"),
]
SEAL = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
FAIL = "PHASE_C_V19_7_4_MEMFD_BOOTSTRAP_STOP_DELETE_CODESPACE"

def stop(reason):
    print(f"{FAIL}:{reason}", file=sys.stderr)
    raise SystemExit(93)

def fetch(u):
    r = subprocess.run(["/usr/bin/curl", "--fail", "--silent", "--show-error", "--location", "--proto", "=https", "--tlsv1.2", u], stdout=subprocess.PIPE)
    if r.returncode != 0:
        stop("FETCH")
    return r.stdout

def git_blob(d):
    return hashlib.sha1(b"blob " + str(len(d)).encode() + b"\0" + d).hexdigest()

def sealed_pair(data, name):
    original = os.memfd_create("phase-c-v19-7-4-" + name, os.MFD_ALLOW_SEALING)
    high = None
    try:
        pos = 0
        while pos < len(data):
            n = os.write(original, data[pos:])
            if n <= 0:
                stop("WRITE")
            pos += n
        if os.pread(original, len(data) + 1, 0) != data:
            stop("PREAD")
        fcntl.fcntl(original, fcntl.F_ADD_SEALS, SEAL)
        if fcntl.fcntl(original, fcntl.F_GET_SEALS) != SEAL:
            stop("SEAL")
        os.lseek(original, 0, os.SEEK_SET)
        high = fcntl.fcntl(original, fcntl.F_DUPFD_CLOEXEC, 10)
        if high < 10:
            stop("HIGH_FD")
        return original, high
    except BaseException:
        if high is not None:
            try:
                os.close(high)
            except OSError:
                pass
        try:
            os.close(original)
        except OSError:
            pass
        raise

def main():
    originals = []
    highs = []
    fixed = False
    try:
        for u, expected_len, expected_sha, expected_blob, name in SPEC:
            d = fetch(u)
            if len(d) != expected_len or hashlib.sha256(d).hexdigest() != expected_sha or git_blob(d) != expected_blob:
                stop("PAYLOAD_IDENTITY")
            original, high = sealed_pair(d, name)
            originals.append(original)
            highs.append(high)
        if len(originals) != 2 or len(highs) != 2 or len(set(originals + highs)) != 4:
            stop("FD_SET")
        for fd in originals:
            os.close(fd)
        originals.clear()
        os.dup2(highs[0], 3, inheritable=True)
        os.dup2(highs[1], 4, inheritable=True)
        fixed = True
    finally:
        for fd in highs:
            try:
                os.close(fd)
            except OSError:
                pass
        for fd in originals:
            try:
                os.close(fd)
            except OSError:
                pass
        if not fixed:
            for fd in (3, 4):
                try:
                    os.close(fd)
                except OSError:
                    pass
    if not os.get_inheritable(3) or not os.get_inheritable(4):
        stop("INHERITABLE")
    if os.lseek(3, 0, os.SEEK_CUR) != 0 or os.lseek(4, 0, os.SEEK_CUR) != 0:
        stop("OFFSET")
    if fcntl.fcntl(3, fcntl.F_GET_SEALS) != SEAL or fcntl.fcntl(4, fcntl.F_GET_SEALS) != SEAL:
        stop("FIXED_SEAL")
    os.execve("/bin/bash", ["/bin/bash", "--noprofile", "--rcfile", "/dev/fd/3", "-i"], os.environ.copy())

if __name__ == "__main__":
    main()
