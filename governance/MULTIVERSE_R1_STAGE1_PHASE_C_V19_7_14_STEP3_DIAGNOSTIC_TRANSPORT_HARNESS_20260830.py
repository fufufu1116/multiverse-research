#!/usr/bin/env python3
import builtins
import hashlib
import pathlib
import subprocess
import sys
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACTION_PATH = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_14_STEP3_DIAGNOSTIC_TRANSPORT_ACTION_20260830.txt"
BUILDER_PATH = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_14_STEP3_DIAGNOSTIC_TRANSPORT_BUILDER_20260830.py"
GD_PATH = ROOT / "g/d"

EXPECTED_GD_BLOB = "4f2718f448fc8367775be16bcbb3b06cb59f6047"
EXPECTED_FETCH_COMMIT = "84ec02fcaf79f86e0757ad356d62fb6f9d31e42d"
EXPECTED_CURL = "/usr/bin/curl"
EXPECTED_PYTHON = "/usr/local/python/current/bin/python"


class ExitCalled(BaseException):
    def __init__(self, code):
        self.code = code


class Digest:
    def __init__(self, value):
        self.value = value

    def hexdigest(self):
        return self.value


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def extract_payload(action: bytes) -> str:
    text = action.decode("ascii")
    marker = EXPECTED_PYTHON + " -Bc'"
    start = text.index(marker) + len(marker)
    end = text.index("' 2>/dev/null; }", start)
    payload = text[start:end]
    if "'" in payload:
        raise AssertionError("unexpected single quote in payload")
    return payload


def run_payload(payload: str, fetch_result=None, fetch_exc=None, sha1_value=None):
    payload_code = builtins.compile(payload, "<transport-payload>", "exec")
    compiled_inputs = []
    sentinel = builtins.compile("raise SystemExit(37)", "<fixture>", "exec")

    def fake_compile(obj, filename, mode):
        compiled_inputs.append(obj)
        return sentinel

    def fake_exit(code):
        raise ExitCalled(code)

    patches = [
        mock.patch("subprocess.check_output", return_value=fetch_result, side_effect=fetch_exc),
        mock.patch("builtins.compile", side_effect=fake_compile),
        mock.patch("os._exit", side_effect=fake_exit),
    ]
    if sha1_value is not None:
        patches.append(mock.patch("hashlib.sha1", return_value=Digest(sha1_value)))

    for p in patches:
        p.start()
    try:
        try:
            exec(payload_code, {})
        except (ExitCalled, SystemExit, subprocess.CalledProcessError) as exc:
            return exc, compiled_inputs
        raise AssertionError("payload unexpectedly returned")
    finally:
        for p in reversed(patches):
            p.stop()


def main() -> int:
    action = ACTION_PATH.read_bytes()
    gd = GD_PATH.read_bytes()

    assert b"\n" not in action
    assert not action.endswith(b"\n")
    assert git_blob(gd) == EXPECTED_GD_BLOB
    assert EXPECTED_CURL.encode() in action
    assert EXPECTED_PYTHON.encode() in action
    assert EXPECTED_FETCH_COMMIT.encode() in action
    assert b"raw.githubusercontent.com" in action
    assert b"/usr/bin/env -i" in action
    assert b" 2>/dev/null; }" in action

    complete = subprocess.run(
        ["/bin/bash", "-n", "-c", action.decode("ascii")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert complete.returncode == 0

    for n in range(1, len(action)):
        prefix = action[:n].decode("ascii")
        parsed = subprocess.run(
            ["/bin/bash", "-n", "-c", prefix],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert parsed.returncode != 0, f"strict prefix parsed at length {n}"

    gen1 = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    gen2 = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    assert gen1 == action
    assert gen2 == action
    assert gen1 == gen2

    payload = extract_payload(action)

    exc, compiled = run_payload(payload, fetch_result=gd)
    assert isinstance(exc, SystemExit) and exc.code == 37
    assert len(compiled) == 1 and compiled[0] is gd

    for bad in (gd[:-1], b"x", gd[: max(1, len(gd) // 2)]):
        exc, compiled = run_payload(payload, fetch_result=bad)
        assert isinstance(exc, ExitCalled) and exc.code == 92
        assert compiled == []

    bad_same_len = bytes([gd[0] ^ 1]) + gd[1:]
    exc, compiled = run_payload(
        payload,
        fetch_result=bad_same_len,
        sha1_value=EXPECTED_GD_BLOB,
    )
    assert isinstance(exc, ExitCalled) and exc.code == 92
    assert compiled == []

    exc, compiled = run_payload(
        payload,
        fetch_result=gd,
        sha1_value="0" * 40,
    )
    assert isinstance(exc, ExitCalled) and exc.code == 92
    assert compiled == []

    exc, compiled = run_payload(
        payload,
        fetch_exc=subprocess.CalledProcessError(22, [EXPECTED_CURL]),
    )
    assert isinstance(exc, subprocess.CalledProcessError)
    assert compiled == []

    fail_shape = (
        '{ exec /usr/bin/env -i PATH=/usr/local/bin:/usr/bin:/bin '
        '/definitely/missing-v19-7-14-python -Bc"pass" 2>/dev/null; }'
    )
    started = subprocess.run(
        ["/bin/bash", "-c", fail_shape],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert started.returncode != 0
    assert started.stdout == b""
    assert started.stderr == b""

    print("PHASE_C_V19_7_14_TRANSPORT_HARNESS_PASS")
    print(f"ACTION_BYTES={len(action)}")
    print(f"ACTION_SHA256={hashlib.sha256(action).hexdigest()}")
    print(f"ACTION_GIT_BLOB={git_blob(action)}")
    print(f"STRICT_PREFIXES_TESTED={len(action)-1}")
    print("STRICT_PREFIX_RESULT=ALL_FAIL_PARSE")
    print("DETERMINISTIC_SECOND_GENERATION=PASS")
    print("FAULT_IDENTITY_BEFORE_EXECUTION=PASS")
    print("NO_LIVE_NETWORK_OR_PRODUCTION_MUTATION=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
