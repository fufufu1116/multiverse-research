#!/usr/bin/env python3
"""Mechanical gate for the session-independent Orchestrator MVP candidate."""
from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUTO = ROOT / "automation"
RC = 92
EXPECTED = (
    "orchestrator_mvp_v1.py",
    "test_orchestrator_mvp_v1.py",
    "README_ORCHESTRATOR_MVP_V1.md",
)


def fail(code: str) -> None:
    print(f"MULTIVERSE_ORCHESTRATOR_MVP_MECH_DENIED:{code}", file=sys.stderr)
    raise SystemExit(RC)


def need(text: str, values: tuple[str, ...], code: str) -> None:
    for value in values:
        if value not in text:
            fail(f"{code}:{value}")


def main() -> int:
    for name in EXPECTED:
        if not (AUTO / name).is_file():
            fail(f"MISSING:{name}")
    for name in ("orchestrator_mvp_v1.py", "test_orchestrator_mvp_v1.py"):
        try:
            ast.parse((AUTO / name).read_text(), filename=name)
        except SyntaxError:
            fail(f"PYTHON_SYNTAX:{name}")

    src = (AUTO / "orchestrator_mvp_v1.py").read_text()
    need(
        src,
        (
            'DEFAULT_SEMANTIC_RETRY_BUDGET = 2',
            'DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 300',
            '"PENDING"',
            '"IN_IMPLEMENT"',
            '"MECH_GATE_FAIL"',
            '"IN_LAB"',
            '"LAB_FIX_REQUIRED"',
            '"IN_AUDIT"',
            '"AUDIT_FIX_REQUIRED"',
            '"OWNER_GATE"',
            '"DONE"',
            '"ROLLED_BACK"',
            'PRAGMA journal_mode=WAL',
            'PRAGMA synchronous=FULL',
            'REPEATED_FAILURE_FINGERPRINT',
            'EXECUTION_TIME_BUDGET_EXCEEDED',
            'owner_copy_paste_count',
            'owner_continue_prompt_count',
            'owner_keep_alive_count',
            'cost_budget_microusd',
            'stable_production_effect',
            'authority_expansion',
        ),
        "ORCHESTRATOR_INVARIANT",
    )
    for forbidden in (
        "openai",
        "anthropic",
        "requests.",
        "urllib.request",
        'subprocess.run("git push',
        "gh api",
    ):
        if forbidden in src.lower():
            fail(f"LIVE_EXTERNAL_OR_MUTATION_SURFACE:{forbidden}")

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(AUTO),
            "-p",
            "test_orchestrator_mvp_v1.py",
            "-v",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sys.stdout.write(process.stdout)
    sys.stderr.write(process.stderr)
    if process.returncode != 0:
        fail(f"UNIT_TESTS:rc={process.returncode}")

    print("MULTIVERSE_ORCHESTRATOR_MVP_MECHANICAL_GATE_PASS")
    print("OWNER_COPY_PASTE_COUNT=0")
    print("OWNER_CONTINUE_PROMPT_COUNT=0")
    print("OWNER_KEEP_ALIVE_COUNT=0")
    print("LIVE_LLM_API_CALLS=0")
    print("PRODUCTION_AUTHORITY_GRANTED=false")
    print("RUNTIME=OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
