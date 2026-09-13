from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_TOKENS = (
    'git fetch origin main:refs/remotes/origin/main',
    'git rev-parse --verify refs/remotes/origin/main^{commit}',
    'git archive refs/remotes/origin/main automation/review_dispatcher_v1',
    '--head "$BUILDKITE_COMMIT"',
    'queue: "independent-auditor"',
)

FORBIDDEN_PATTERNS = (
    re.compile(r'git\s+archive\s+"?\$?DISPATCHER_REF"?.*FETCH_HEAD', re.IGNORECASE),
    re.compile(r'DISPATCHER_REF=.*FETCH_HEAD', re.IGNORECASE),
    re.compile(r'git\s+archive\s+FETCH_HEAD', re.IGNORECASE),
)


def inspect_pipeline_text(text: str) -> dict[str, object]:
    findings: list[str] = []
    for token in REQUIRED_TOKENS:
        if token not in text:
            findings.append(f"MISSING_REQUIRED_TOKEN:{token}")
    if "FETCH_HEAD" in text:
        findings.append("FORBIDDEN_FETCH_HEAD_DEPENDENCY")
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            findings.append("FORBIDDEN_FETCH_HEAD_ARCHIVE_PATTERN")
            break
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
