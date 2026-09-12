from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HIGH_RISK_PATTERNS = {
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GITHUB_TOKEN": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "AWS_ACCESS_KEY_ID": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GENERIC_BEARER": re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "GENERIC_SECRET_ASSIGNMENT": re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{24,}"),
}

SENSITIVE_PATH_HINTS = re.compile(r"(?i)(secret|credential|private[_-]?key|\.env(?:\.|$)|token)")

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}
TEXT_SUFFIX_ALLOW = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".csv", ".tsv", ".sh"
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIX_ALLOW:
        return True
    return path.suffix == ""


def redact_match(value: str) -> str:
    if len(value) <= 8:
        return "<REDACTED>"
    return value[:4] + "…" + value[-4:]


def audit(root: Path, registry_path: Path | None = None) -> dict:
    findings: list[dict] = []
    scanned = 0
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        if SENSITIVE_PATH_HINTS.search(rel):
            findings.append({"severity": "REVIEW", "type": "SENSITIVE_PATH_NAME", "path": rel})
        if not is_probably_text(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for pattern_id, pattern in HIGH_RISK_PATTERNS.items():
            match = pattern.search(text)
            if match:
                findings.append({
                    "severity": "CRITICAL",
                    "type": pattern_id,
                    "path": rel,
                    "sample": redact_match(match.group(0)),
                })
    registry_state = "NOT_PROVIDED"
    if registry_path:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        required = {"GITHUB_CANONICAL", "GOOGLE_DRIVE_RECOVERY", "BUILDKITE_REVIEW", "NETLIFY", "TALLY", "AI_PROVIDERS_AND_PLUGINS", "LOCAL_MAC", "FUTURE_CLOUD_RUNTIME"}
        seen = {item["id"] for item in data.get("services", [])}
        missing = sorted(required - seen)
        if missing:
            findings.append({"severity": "CRITICAL", "type": "MISSING_TRUST_BOUNDARY", "services": missing})
            registry_state = "FAIL_CLOSED"
        else:
            registry_state = "COMPLETE_FOR_V1_DECLARED_SURFACES"
        for item in data.get("services", []):
            if item.get("credential_scope") in {None, ""}:
                findings.append({"severity": "CRITICAL", "type": "UNKNOWN_CREDENTIAL_SCOPE_UNMARKED", "service": item.get("id")})
            observed = item.get("observed_state") or {}
            if observed.get("chatgpt_plugin_permission") == "FULL_ACCESS_OBSERVED":
                findings.append({
                    "severity": "CRITICAL",
                    "type": "OVERBROAD_CHATGPT_PLUGIN_PERMISSION",
                    "service": item.get("id"),
                    "observed": "FULL_ACCESS_OBSERVED",
                    "required_action": "OWNER_REVIEW_AND_PERMISSION_REDUCTION_OR_EXPLICIT_EXCEPTION",
                })
    critical = [f for f in findings if f["severity"] == "CRITICAL"]
    return {
        "schema": "MULTIVERSE_REPOSITORY_SECURITY_AUDIT_v1",
        "mode": "READ_ONLY",
        "write_effects": False,
        "runtime": "OFF",
        "scanned_text_files": scanned,
        "registry_state": registry_state,
        "critical_count": len(critical),
        "finding_count": len(findings),
        "findings": findings,
        "decision": "FAIL_CLOSED" if critical else "PASS_NO_CRITICAL_PATTERN_FOUND",
        "warning": "Pattern scan and declared posture checks are defense-in-depth only; they do not prove that no secret exists and never grant mutation authority.",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--registry")
    p.add_argument("--output")
    args = p.parse_args()
    result = audit(Path(args.root), Path(args.registry) if args.registry else None)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 2 if result["critical_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
