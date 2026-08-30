#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile

INPUT_BYTES = 7969
PAYLOAD_BYTES = 1579
PAYLOAD_GIT_BLOB = "497047a1545df84c1f05b5a31b3390ac7b528373"
PAYLOAD_SHA256 = "c411ca57fc04130fa11f45997d21dff70992fa684f803606524a4802f2a02275"
SPLICE3 = b'\'"\'"\'\'"\'"\'\'"\'"\''
FOCUS1 = b'anchor=b"tail=' + SPLICE3 + b'phase_c_bootstrap"'
FOCUS2 = b'b"tail=r' + SPLICE3 + b'phase_c_bootstrap"'

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def main() -> None:
    transport = sys.stdin.buffer.read()
    if len(transport) != INPUT_BYTES:
        raise SystemExit("INPUT_LENGTH_MISMATCH")
    if transport.count(FOCUS1) != 1 or transport.count(FOCUS2) != 1:
        raise SystemExit("PROTECTED_FOCUS_COUNT_MISMATCH")

    parse = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-n"],
        input=transport,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if parse.returncode != 0 or parse.stderr != b"":
        raise SystemExit("OUTER_BASH_PARSE_OR_WARNING_FAILURE")

    with tempfile.TemporaryDirectory(prefix="mv-v19-7-18-boundary-") as td:
        out_path = os.path.join(td, "argv.json")
        sink_path = os.path.join(td, "sink.py")
        sink = (
            "#!/usr/bin/env python3\n"
            "import base64,json,os,sys\n"
            f"p={out_path!r}\n"
            "v=[base64.b64encode(os.fsencode(x)).decode('ascii') for x in sys.argv]\n"
            "open(p,'w',encoding='ascii').write(json.dumps(v,separators=(',',':')))\n"
        ).encode("utf-8")
        fd = os.open(sink_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        try:
            if os.write(fd, sink) != len(sink):
                raise SystemExit("SINK_SHORT_WRITE")
        finally:
            os.close(fd)
        st = os.lstat(sink_path)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_nlink != 1:
            raise SystemExit("SINK_METADATA_FAILURE")

        target = b"/bin/bash"
        if transport.count(target) < 1:
            raise SystemExit("OUTER_TARGET_MISSING")
        capture = transport.replace(target, os.fsencode(sink_path), 1)
        run = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-c", capture.decode("utf-8")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if run.returncode != 0 or run.stderr != b"":
            raise SystemExit("OUTER_LEXICAL_CAPTURE_FAILURE")
        args = [base64.b64decode(x) for x in json.loads(open(out_path, encoding="ascii").read())]
        if len(args) < 5 or args[-2] != b"-c":
            raise SystemExit("CAPTURED_ARGV_SHAPE_FAILURE")
        inner = args[-1]

    opener = b"<<'PY'\n"
    terminator = b"\nPY\n"
    if inner.count(opener) != 1 or inner.count(terminator) != 1:
        raise SystemExit("HEREDOC_MULTIPLICITY_FAILURE")
    start = inner.index(opener) + len(opener)
    stop_marker = inner.index(terminator, start)
    payload = inner[start:stop_marker + 1]
    if len(payload) != PAYLOAD_BYTES:
        raise SystemExit("POST_OUTER_PAYLOAD_LENGTH_MISMATCH")
    if git_blob(payload) != PAYLOAD_GIT_BLOB:
        raise SystemExit("POST_OUTER_PAYLOAD_BLOB_MISMATCH")
    if hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256:
        raise SystemExit("POST_OUTER_PAYLOAD_SHA256_MISMATCH")
    try:
        compile(payload.decode("utf-8"), "<stdin>", "exec")
    except SyntaxError as exc:
        raise SystemExit(f"POST_OUTER_PAYLOAD_COMPILE_FAILURE_LINE_{exc.lineno}_OFFSET_{exc.offset}")

    mini = (
        b"/bin/bash --noprofile --norc -c '"
        b"/usr/bin/python3 - <<'\"'\"'PY'\"'\"'\n"
        b"anchor=b\"tail=" + SPLICE3 + b"phase_c_bootstrap\"\n"
        b"out=anchor.replace(b\"tail=\",b\"tail=r\",1)\n"
        b"assert anchor==b\"tail=\\x27\\x27\\x27phase_c_bootstrap\"\n"
        b"assert out==b\"tail=r\\x27\\x27\\x27phase_c_bootstrap\"\n"
        b"print(\"V19_7_18_NESTED_SHELL_QUOTE_BOUNDARY_PASS\")\n"
        b"PY\n"
        b"'"
    )
    mini_run = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-c", mini.decode("utf-8")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if mini_run.returncode != 0 or mini_run.stderr != b"":
        raise SystemExit("NESTED_SHELL_HARNESS_FAILURE")
    if mini_run.stdout != b"V19_7_18_NESTED_SHELL_QUOTE_BOUNDARY_PASS\n":
        raise SystemExit("NESTED_SHELL_HARNESS_MARKER_MISMATCH")

    print("V19_7_18_POST_OUTER_PAYLOAD_HARNESS_PASS")

if __name__ == "__main__":
    main()
