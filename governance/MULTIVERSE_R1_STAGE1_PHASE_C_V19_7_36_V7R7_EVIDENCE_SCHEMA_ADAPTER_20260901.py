#!/usr/bin/env python3
"""Deterministic review-only v7r7 evidence-schema adapter for the exact inherited v7r6 gate.

This adapter is intentionally narrow: it accepts exactly one reviewed inherited source blob
and changes only the external GitHub evidence schema literals. All gate control logic remains
byte-for-byte inherited apart from those mechanically counted literal substitutions.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

RC = 92
EXPECTED_INHERITED_GIT_BLOB = "f2c3f1023a453bfe5ee43c7d978de9728c5a2dc8"
SUCCESSOR_VERSION = "V19.7.36-v7r7"

REPLACEMENTS = (
    ("MULTIVERSE_V7R6_CANDIDATE_FREEZE ", "MULTIVERSE_V7R7_CANDIDATE_FREEZE ", 1),
    ("MULTIVERSE_V7R6_SESSION_BINDING ", "MULTIVERSE_V7R7_SESSION_BINDING ", 1),
    ("MULTIVERSE_V7R6_OWNER_APPROVAL_RECEIPT ", "MULTIVERSE_V7R7_OWNER_APPROVAL_RECEIPT ", 1),
    ("V19.7.36-v7r6", "V19.7.36-v7r7", 6),
    ("FREEZE V19.7.36 v7r6 CANDIDATE", "FREEZE V19.7.36 v7r7 CANDIDATE", 2),
    ("APPROVE V19.7.36 v7r6 ONE-SHOT LIVE", "APPROVE V19.7.36 v7r7 ONE-SHOT LIVE", 2),
)

LEGACY_EVIDENCE_LITERALS = tuple(old for old, _, _ in REPLACEMENTS)
SUCCESSOR_EVIDENCE_LITERALS = tuple(new for _, new, _ in REPLACEMENTS)


def deny(code: str, detail: str = "") -> "NoReturn":
    suffix = f":{detail}" if detail else ""
    print(f"PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_DENIED:{code}{suffix}", file=sys.stderr)
    raise SystemExit(RC)


def git_blob_sha1(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def adapt_bytes(raw: bytes) -> bytes:
    actual = git_blob_sha1(raw)
    if actual != EXPECTED_INHERITED_GIT_BLOB:
        deny("INHERITED_GATE_BLOB", actual)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        deny("INHERITED_GATE_UTF8")

    for old, new, expected_count in REPLACEMENTS:
        count = text.count(old)
        if count != expected_count:
            deny("REPLACEMENT_COUNT", f"{old!r}:got={count}:expected={expected_count}")
        text = text.replace(old, new)

    for legacy in LEGACY_EVIDENCE_LITERALS:
        if legacy in text:
            deny("LEGACY_EVIDENCE_LITERAL_REMAINS", repr(legacy))
    for successor in SUCCESSOR_EVIDENCE_LITERALS:
        if successor not in text:
            deny("SUCCESSOR_EVIDENCE_LITERAL_MISSING", repr(successor))

    required_logic = (
        "apiHardBudget = 40",
        "apiReserveRemaining = 8",
        "pollInterval = 30 * time.Second",
        "approvalWindow = 10 * time.Minute",
        "cursorOverlap = 2 * time.Second",
        "c.CreatedAt.After(approvalDeadline)",
        "requiredApp = \"chatgpt-codex-connector\"",
        "ownerBound(c comment)",
        "evidenceBound(c comment)",
        "findFreeze(cs []comment",
        "selectReceipt(cs []comment",
        "STRICT_APPROVAL_WINDOW_SELFTEST_PASS",
        "RATE_HEADERS_FAIL_CLOSED_SELFTEST_PASS",
        "PAGINATION_RACE_SELFTEST_PASS",
    )
    for needle in required_logic:
        if needle not in text:
            deny("INHERITED_SECURITY_LOGIC_MISSING", needle)

    return text.encode("utf-8")


def selftest(src: pathlib.Path) -> None:
    out = adapt_bytes(src.read_bytes()).decode("utf-8")
    successor_checks = (
        'const freezePrefix = "MULTIVERSE_V7R7_CANDIDATE_FREEZE "',
        'const receiptPrefix = "MULTIVERSE_V7R7_SESSION_BINDING "',
        'const approvalPrefix = "MULTIVERSE_V7R7_OWNER_APPROVAL_RECEIPT "',
        'f.Version != "V19.7.36-v7r7"',
        'a.Version == "V19.7.36-v7r7"',
        's.Version != "V19.7.36-v7r7"',
        '"FREEZE V19.7.36 v7r7 CANDIDATE"',
        '"APPROVE V19.7.36 v7r7 ONE-SHOT LIVE"',
        'freezeReceipt{"V19.7.36-v7r7"',
        'approvalReceipt{"V19.7.36-v7r7"',
        'sessionReceipt{"V19.7.36-v7r7"',
    )
    for needle in successor_checks:
        if needle not in out:
            deny("SUCCESSOR_SELFTEST_WIRING", needle)
    print(
        "PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_SELFTEST_PASS "
        f"inherited_git_blob={EXPECTED_INHERITED_GIT_BLOB} successor_version={SUCCESSOR_VERSION} runtime=OFF"
    )
    print("SECURITY_AUTHORITY_GRANTED=false")
    print("RUNTIME=OFF")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        selftest(pathlib.Path(sys.argv[2]))
        return
    if len(sys.argv) != 3:
        deny("ARGS")
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2])
    if not src.is_file():
        deny("SOURCE_MISSING", str(src))
    if dst.exists():
        deny("DESTINATION_PREEXISTS", str(dst))
    adapted = adapt_bytes(src.read_bytes())
    dst.write_bytes(adapted)
    print(
        "PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_PASS "
        f"inherited_git_blob={EXPECTED_INHERITED_GIT_BLOB} successor_version={SUCCESSOR_VERSION} runtime=OFF"
    )


if __name__ == "__main__":
    main()
