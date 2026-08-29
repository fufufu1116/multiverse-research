#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_V5_20260830.txt"

PASS = [
    "PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES",
    "PHASE_C_V19_7_15_PASS_FRESH_PATHS",
    "PHASE_C_V19_7_15_PASS_TMPFS_TRUST",
    "PHASE_C_V19_7_15_PASS_GIT_CONTROL",
    "PHASE_C_V19_7_15_PASS_CANONICAL_MAIN",
    "PHASE_C_V19_7_15_PASS_RECOVERY_HEAD",
    "PHASE_C_V19_7_15_PASS_REPO_STATE",
    "PHASE_C_V19_7_15_PASS_RUNNER_TRUST",
    "PHASE_C_V19_7_15_PASS_RUNNER_SHA256",
]

FAIL = [
    "PHASE_C_V19_7_15_FAIL_PLATFORM_CODESPACES",
    "PHASE_C_V19_7_15_FAIL_FRESH_PATHS",
    "PHASE_C_V19_7_15_FAIL_TMPFS_TRUST",
    "PHASE_C_V19_7_15_FAIL_GIT_CONTROL",
    "PHASE_C_V19_7_15_FAIL_CANONICAL_MAIN",
    "PHASE_C_V19_7_15_FAIL_RECOVERY_HEAD",
    "PHASE_C_V19_7_15_FAIL_REPO_STATE",
    "PHASE_C_V19_7_15_FAIL_RUNNER_TRUST",
    "PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_COMMAND",
    "PHASE_C_V19_7_15_FAIL_RUNNER_SHA256_MISMATCH",
    "PHASE_C_V19_7_15_FAIL_RUNNER_LAUNCH",
]

RUNNER_START = "PHASE_C_V19_7_15_RUNNER_START"

# For each failure class, this is the number of completed fixed success gates
# whose PASS markers may already have been emitted to stdout.
EXPECTED_PASS_PREFIX_LEN = {
    FAIL[0]: 0,
    FAIL[1]: 1,
    FAIL[2]: 2,
    FAIL[3]: 3,
    FAIL[4]: 4,
    FAIL[5]: 5,
    FAIL[6]: 6,
    FAIL[7]: 7,
    FAIL[8]: 8,
    FAIL[9]: 8,
    FAIL[10]: 9,
}


def main() -> None:
    text = ACTION.read_text("ascii")
    assert "\n" not in text
    start_token = "mark " + RUNNER_START
    assert text.count(start_token) == 1
    pre = text[: text.index(start_token)]

    # Whole-source order proof: every reviewed PASS marker exists exactly once,
    # is emitted through mark(), and appears in the frozen order before handoff.
    positions = []
    for marker in PASS:
        token = "mark " + marker
        assert pre.count(token) == 1, marker
        positions.append(pre.index(token))
    assert positions == sorted(positions)

    # No other loader PASS marker exists before the handoff.
    words = [w.strip(";'\"{}()") for w in pre.replace(";", " ").split()]
    discovered = sorted({w for w in words if w.startswith("PHASE_C_V19_7_15_PASS_")})
    assert discovered == sorted(PASS)

    # Every reviewed pre-handoff failure marker exists before RUNNER_START and
    # is wired to fail(), whose frozen definition exits immediately.
    assert "fail(){ command printf" in pre
    assert "exit 88; };" in pre
    for marker in FAIL:
        assert marker in pre, marker
        assert pre.index(marker) < len(pre)

    # The exact stdout contract is an ordered prefix of fixed PASS markers,
    # never an arbitrary/dynamic string. This explicitly corrects the previous
    # over-strong `stdout == empty` claim for later pre-handoff failures.
    for failure, n in EXPECTED_PASS_PREFIX_LEN.items():
        assert 0 <= n <= len(PASS)
        transcript = "".join(m + "\n" for m in PASS[:n])
        assert all(line.startswith("PHASE_C_V19_7_15_PASS_") for line in transcript.splitlines())
        assert failure.startswith("PHASE_C_V19_7_15_FAIL_")

    # Handoff itself occurs only after all nine fixed PASS markers.
    assert all(pre.index("mark " + marker) < len(pre) for marker in PASS)
    assert text.index(start_token) > positions[-1]

    # No production/live authority is present in this proof target.
    assert "--apply" not in text
    assert "Step4" not in text

    print("PHASE_C_V19_7_15_PRE_HANDOFF_WHOLE_LOADER_TRANSCRIPT_PROOF_V5C_PASS")


if __name__ == "__main__":
    main()
