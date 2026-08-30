#!/usr/bin/env python3
import hashlib
import sys

SOURCE_BYTES = 7945
SOURCE_GIT_BLOB = "882ef767bfd816348f07e183258fcaa0490a6e6c"
SOURCE_SHA256 = "67c3e1024795d8bf65024d309fd19e5903d0105f5e3b57e48764c028182c6d2d"
OLD1 = b'anchor=b"tail=\'\'\'phase_c_bootstrap"'
OLD2 = b'b"tail=r\'\'\'phase_c_bootstrap"'
SPLICE3 = b'\'"\'"\'\'"\'"\'\'"\'"\''
NEW1 = b'anchor=b"tail=' + SPLICE3 + b'phase_c_bootstrap"'
NEW2 = b'b"tail=r' + SPLICE3 + b'phase_c_bootstrap"'
OUTPUT_BYTES = 7969

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def main() -> None:
    src = sys.stdin.buffer.read()
    if len(src) != SOURCE_BYTES:
        raise SystemExit("SOURCE_LENGTH_MISMATCH")
    if git_blob(src) != SOURCE_GIT_BLOB:
        raise SystemExit("SOURCE_BLOB_MISMATCH")
    if hashlib.sha256(src).hexdigest() != SOURCE_SHA256:
        raise SystemExit("SOURCE_SHA256_MISMATCH")
    if src.count(OLD1) != 1 or src.count(OLD2) != 1:
        raise SystemExit("FOCUS_ANCHOR_COUNT_MISMATCH")
    if src.count(NEW1) != 0 or src.count(NEW2) != 0:
        raise SystemExit("PROTECTED_FOCUS_PREEXISTS")
    out = src.replace(OLD1, NEW1, 1).replace(OLD2, NEW2, 1)
    if len(out) != OUTPUT_BYTES:
        raise SystemExit("OUTPUT_LENGTH_MISMATCH")
    if out.count(OLD1) != 0 or out.count(OLD2) != 0:
        raise SystemExit("UNPROTECTED_FOCUS_REMAINS")
    if out.count(NEW1) != 1 or out.count(NEW2) != 1:
        raise SystemExit("PROTECTED_FOCUS_COUNT_MISMATCH")
    sys.stdout.buffer.write(out)

if __name__ == "__main__":
    main()
