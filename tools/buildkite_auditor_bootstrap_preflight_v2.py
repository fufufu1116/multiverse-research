from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_TOKENS = (
    'queue: "independent-auditor"',
    'git fetch origin main:refs/remotes/origin/main',
    'git rev-parse --verify refs/remotes/origin/main^{commit}',
    'git archive refs/remotes/origin/main automation/review_dispatcher_v1',
    'origin main:refs/remotes/origin/main',
    'PYTHONPATH=.mv_dispatcher',
    "python3 -c 'import automation.review_dispatcher_v1.dispatcher'",
    "python3 -c 'import automation.review_dispatcher_v1.publisher'",
    "python3 -c 'import automation.review_dispatcher_v1.t2'",
    '--head "$$BUILDKITE_COMMIT"',
    'publisher.py',
    't2.py',
    'review_publish_receipt.json',
    't2_publish_receipt.json',
    'MULTIVERSE_INDEPENDENT_AUDITOR_PRIVATE_KEY',
)

FORBIDDEN_PATTERNS = (
    ("FETCH_HEAD_DEPENDENCY", re.compile(r"FETCH_HEAD", re.IGNORECASE)),
    (
        "SINGLE_DOLLAR_RUNTIME_VARIABLE",
        re.compile(r'(?<!\$)\$[A-Z_][A-Z0-9_]*'),
    ),
    (
        "AMBIENT_PWD_PYTHONPATH",
        re.compile(r'export\s+PYTHONPATH=.*\$+PWD', re.IGNORECASE),
    ),
)


def inspect_pipeline_text(text: str) -> dict[str, object]:
    findings: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            findings.append(f"MISSING_REQUIRED_TOKEN:{token}")

    if text.count('queue: "independent-auditor"') != 3:
        findings.append("AUDITOR_QUEUE_STAGE_COUNT_NOT_3")

    if text.count("PYTHONPATH=.mv_dispatcher") < 7:
        findings.append("INLINE_PYTHONPATH_COUNT_LT_7")

    if text.count("  - wait") != 2:
        findings.append("WAIT_STAGE_COUNT_NOT_2")

    for code, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            findings.append(code)

    return {
        "ok": not findings,
        "findings": findings,
        "runtime_effect": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    result = inspect_pipeline_text(Path(args.path).read_text())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
