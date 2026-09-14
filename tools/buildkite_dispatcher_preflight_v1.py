from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HARD_PIN_RE = re.compile(r'test\s+"?\$BUILDKITE_COMMIT"?\s*=\s*"?[0-9a-f]{40}"?', re.IGNORECASE)
REQUIRED_TOKENS = (
    "git fetch origin main",
    "dispatcher.py",
    '--head "$BUILDKITE_COMMIT"',
)


def inspect_pipeline_text(text: str) -> dict[str, object]:
    findings: list[str] = []
    if HARD_PIN_RE.search(text):
        findings.append("CANDIDATE_SPECIFIC_BUILDKITE_COMMIT_HARD_PIN")
    for token in REQUIRED_TOKENS:
        if token not in text:
            findings.append(f"MISSING_REQUIRED_TOKEN:{token}")
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
