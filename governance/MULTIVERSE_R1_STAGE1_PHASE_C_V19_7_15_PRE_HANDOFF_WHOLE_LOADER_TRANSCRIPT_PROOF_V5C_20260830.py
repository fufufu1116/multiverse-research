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


def all_positions(haystack: str, needle: str) -> list[int]:
    out: list[int] = []
    start = 0
    while True:
        i = haystack.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + len(needle)


def main() -> None:
    text = ACTION.read_text("ascii")
    assert "\n" not in text
    start_token = "mark " + RUNNER_START
    assert text.count(start_token) == 1
    runner_start_pos = text.index(start_token)
    pre = text[:runner_start_pos]

    # Whole-source order proof: every reviewed PASS marker exists exactly once,
    # is emitted through mark(), and appears in the frozen order before handoff.
    pass_positions = []
    for marker in PASS:
        token = "mark " + marker
        assert pre.count(token) == 1, marker
        pass_positions.append(pre.index(token))
    assert pass_positions == sorted(pass_positions)

    # No other loader PASS marker exists before the handoff.
    words = [w.strip(";'\"{}()") for w in pre.replace(";", " ").split()]
    discovered = sorted({w for w in words if w.startswith("PHASE_C_V19_7_15_PASS_")})
    assert discovered == sorted(PASS)

    # Every reviewed pre-handoff failure class must be attached to literal fail()
    # call sites in the exact source. For every actual call-site occurrence, derive
    # the number of preceding PASS markers from source positions and mechanically
    # bind it to EXPECTED_PASS_PREFIX_LEN. Any failure moved across a PASS boundary,
    # or any incorrect expected prefix length, makes this proof fail.
    assert "fail(){ command printf" in pre
    assert "exit 88; };" in pre
    for failure, expected_n in EXPECTED_PASS_PREFIX_LEN.items():
        token = "fail " + failure
        occurrences = all_positions(pre, token)
        assert occurrences, failure
        assert all(pos < runner_start_pos for pos in occurrences)
        actual_counts = {
            sum(1 for pass_pos in pass_positions if pass_pos < fail_pos)
            for fail_pos in occurrences
        }
        assert actual_counts == {expected_n}, (failure, expected_n, sorted(actual_counts))
        assert 0 <= expected_n <= len(PASS)
        transcript = "".join(marker + "\n" for marker in PASS[:expected_n])
        assert all(line.startswith("PHASE_C_V19_7_15_PASS_") for line in transcript.splitlines())

    # Every reviewed failure class is covered by the mechanical binding table.
    assert set(EXPECTED_PASS_PREFIX_LEN) == set(FAIL)

    # Handoff itself occurs only after all nine fixed PASS markers.
    assert runner_start_pos > pass_positions[-1]

    # No production/live authority is present in this proof target.
    assert "--apply" not in text
    assert "Step4" not in text

    print("PHASE_C_V19_7_15_PRE_HANDOFF_WHOLE_LOADER_TRANSCRIPT_PROOF_V5D_PASS")


if __name__ == "__main__":
    main()
