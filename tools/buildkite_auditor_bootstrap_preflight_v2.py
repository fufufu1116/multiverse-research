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
    'PYTHONPATH=.mv_dispatcher',
    "python3 -c 'import automation.review_dispatcher_v1.dispatcher'",
    '--head "$$BUILDKITE_COMMIT"',
)

FORBIDDEN_PATTERNS = (
    ("FETCH_HEAD_DEPENDENCY", re.compile(r"FETCH_HEAD", re.IGNORECASE)),
    (
        "SINGLE_DOLLAR_BUILDKITE_COMMIT",
        re.compile(r'(?<!\$)\$BUILDKITE_COMMIT'),
    ),
    (
        "AMBIENT_PWD_PYTHONPATH",
        re.compile(r'export\s+PYTHONPATH=.*\$PWD', re.IGNORECASE),
    ),
)


def inspect_pipeline_text(text: str) -> dict[str, object]:
    findings: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            findings.append(f"MISSING_REQUIRED_TOKEN:{token}")

    if text.count("PYTHONPATH=.mv_dispatcher") < 3:
        findings.append("INLINE_PYTHONPATH_COUNT_LT_3")

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
