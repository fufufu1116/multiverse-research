from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

SCHEMA = "MULTIVERSE_REPOSITORY_HYGIENE_AUDIT_v1"
CURRENT_RE = re.compile(r"(?:^|[_-])CURRENT(?:[_-]|$)|CURRENT_STATE", re.I)
VERSION_RE = re.compile(r"(?P<stem>.*?)(?:[_-]v(?P<ver>\d+))(?:\.[^.]+)?$", re.I)
TEMP_RE = re.compile(r"(?:^|/)(?:tmp|temp|scratch|cache)(?:/|$)|(?:proof|diagnostic|probe|candidate|draft)", re.I)
PROTECTED_RE = re.compile(r"ECON_HOLDOUT|HOLDOUT|SEALED|PROTECTED", re.I)
EVIDENCE_RE = re.compile(r"RECEIPT|AUDIT|LEDGER|POSTMORTEM|PREREG|EXPERIMENT|DECISION|MANIFEST|FREEZE", re.I)


def git_ls_files(root: Path) -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    return [p for p in out.decode().split("\0") if p]


def blob_digest(root: Path, rel: str) -> str:
    h = hashlib.sha256()
    with (root / rel).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_name(path: str) -> str:
    if PROTECTED_RE.search(path):
        return "PROTECTED_SEALED"
    if EVIDENCE_RE.search(path):
        return "EVIDENCE_IMMUTABLE"
    if CURRENT_RE.search(Path(path).name):
        return "CURRENT_POINTER_CANDIDATE"
    if TEMP_RE.search(path):
        return "TEMPORARY_OR_CANDIDATE_REVIEW"
    return "UNCLASSIFIED_REQUIRES_INDEX"


def audit(paths: list[str], root: Path | None = None, hash_duplicates: bool = False) -> dict:
    findings: list[dict] = []
    by_dir_current: dict[str, list[str]] = defaultdict(list)
    versions: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    class_counts: dict[str, int] = defaultdict(int)

    for path in sorted(paths):
        cls = classify_name(path)
        class_counts[cls] += 1
        name = Path(path).name
        parent = str(Path(path).parent)
        if CURRENT_RE.search(name):
            by_dir_current[parent].append(path)
        m = VERSION_RE.match(name)
        if m:
            suffix = Path(name).suffix.lower()
            stem = m.group("stem").lower()
            versions[(parent, stem + suffix)].append((int(m.group("ver")), path))

    if any(p.startswith(".github/workflows/.github/workflows/") for p in paths):
        findings.append({
            "code": "NESTED_WORKFLOW_TREE",
            "severity": "HIGH_REVIEW",
            "decision": "CONSOLIDATION_CANDIDATE",
            "paths": sorted(p for p in paths if p.startswith(".github/workflows/.github/workflows/")),
        })

    for parent, members in sorted(by_dir_current.items()):
        if len(members) > 1:
            findings.append({
                "code": "MULTIPLE_CURRENT_LIKE_FILES_SAME_DIRECTORY",
                "severity": "REVIEW",
                "decision": "RETIRE_FROM_ACTIVE_VIEW",
                "directory": parent,
                "paths": members,
            })

    for (parent, family), members in sorted(versions.items()):
        if len(members) > 1:
            findings.append({
                "code": "VERSION_SIBLINGS_REQUIRE_LIFECYCLE_INDEX",
                "severity": "REVIEW",
                "decision": "CONSOLIDATION_CANDIDATE",
                "directory": parent,
                "family": family,
                "paths": [p for _, p in sorted(members)],
            })

    duplicate_groups = []
    if hash_duplicates:
        if root is None:
            raise ValueError("root required when hash_duplicates=True")
        digest_map: dict[str, list[str]] = defaultdict(list)
        for path in sorted(paths):
            full = root / path
            if full.is_file():
                digest_map[blob_digest(root, path)].append(path)
        duplicate_groups = [
            {"sha256": digest, "paths": members}
            for digest, members in sorted(digest_map.items())
            if len(members) > 1
        ]

    return {
        "schema": SCHEMA,
        "mode": "READ_ONLY",
        "runtime": "OFF",
        "tracked_file_count": len(paths),
        "classification_counts": dict(sorted(class_counts.items())),
        "findings": findings,
        "exact_content_duplicate_groups": duplicate_groups,
        "deletion_authority": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--output", default="repository_hygiene_audit.json")
    p.add_argument("--hash-duplicates", action="store_true")
    args = p.parse_args()
    root = Path(args.repo_root).resolve()
    result = audit(git_ls_files(root), root=root, hash_duplicates=args.hash_duplicates)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "schema": result["schema"],
        "tracked_file_count": result["tracked_file_count"],
        "finding_count": len(result["findings"]),
        "duplicate_group_count": len(result["exact_content_duplicate_groups"]),
        "mode": result["mode"],
        "runtime": result["runtime"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
