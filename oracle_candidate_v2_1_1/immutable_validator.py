from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ZERO_AUDIT_ORACLE_V2_1_1_MANIFEST.json"

POISON_NAMES = {
    "conftest.py",
    "pytest.py",
    "sitecustomize.py",
    "usercustomize.py",
}
POISON_SUFFIXES = {".pth"}

def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def verify_candidate_surface(stage: str):
    base = ROOT / "candidate/security_v3_3"
    if not base.is_dir():
        raise SystemExit(f"FAIL_CLOSED: {stage}: candidate directory missing")
    for p in base.rglob("*"):
        if p.is_symlink():
            raise SystemExit(f"FAIL_CLOSED: {stage}: candidate symlink forbidden: {p}")
        if p.is_file() and (p.name in POISON_NAMES or p.suffix in POISON_SUFFIXES):
            raise SystemExit(f"FAIL_CLOSED: {stage}: candidate poisoning surface forbidden: {p.name}")

def verify_manifest(stage: str, require_head_anchor: bool = True):
    m = load_manifest()
    if require_head_anchor:
        committed = subprocess.run(
            ["git", "show", "HEAD:ZERO_AUDIT_ORACLE_V2_1_1_MANIFEST.json"],
            cwd=ROOT,
            capture_output=True,
        )
        if committed.returncode != 0 or hashlib.sha256(committed.stdout).hexdigest() != h(MANIFEST):
            raise SystemExit(f"FAIL_CLOSED: {stage}: manifest differs from committed root anchor")
    for rel, expected in m["protected_components"].items():
        p = ROOT / rel
        if not p.is_file() or h(p) != expected:
            raise SystemExit(f"FAIL_CLOSED: {stage}: protected component mismatch: {rel}")
    verify_candidate_surface(stage)
    print(f"MANIFEST_{stage}_OK")

def one_result(xml_path: Path):
    root = ET.parse(xml_path).getroot()
    cases = list(root.iter("testcase"))
    if len(cases) != 1:
        return False, f"expected exactly 1 testcase, got {len(cases)}"
    c = cases[0]
    if c.find("failure") is not None or c.find("error") is not None or c.find("skipped") is not None:
        return False, "failure/error/skipped present"
    return True, "PASS"

def isolated_pytest_command(node: str, xml_path: Path):
    user = os.environ.get("MV33_TEST_USER", "").strip()
    require = os.environ.get("MV33_REQUIRE_ISOLATION", "") == "1"

    if require and not user:
        raise SystemExit("FAIL_CLOSED: MV33_REQUIRE_ISOLATION=1 but MV33_TEST_USER missing")

    base = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        node,
        f"--junitxml={xml_path}",
        "-p",
        "no:cacheprovider",
    ]

    if not user:
        return base

    probe = subprocess.run(["id", user], capture_output=True)
    if probe.returncode != 0:
        raise SystemExit(f"FAIL_CLOSED: isolated test user missing: {user}")

    return [
        "sudo", "-n", "-u", user, "-H", "env",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONNOUSERSITE=1",
        "MV33_REQUIRE_ISOLATION=1",
        f"MV33_REPO_ROOT={ROOT}",
        f"PYTHONPATH={ROOT}",
        f"PATH={os.environ.get('PATH', '')}",
        *base,
    ]

def run_suite(evidence_dir: Path, report_path: Path) -> int:
    m = load_manifest()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    seen = set()

    for i, node in enumerate(m["mandatory_node_ids"], 1):
        if node in seen:
            raise SystemExit(f"FAIL_CLOSED: duplicate mandatory node id: {node}")
        seen.add(node)

        verify_manifest(f"PRE_TEST_{i:02d}")

        with tempfile.TemporaryDirectory(prefix=f"mv33_junit_{i:02d}_") as td:
            td_path = Path(td)
            os.chmod(td_path, 0o777)
            xml = td_path / "result.xml"

            env = os.environ.copy()
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONNOUSERSITE"] = "1"

            try:
                cp = subprocess.run(
                    isolated_pytest_command(node, xml),
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=120,
                )
            except subprocess.TimeoutExpired:
                results.append({
                    "node_id": node,
                    "passed": False,
                    "reason": "timeout",
                    "pytest_exit": 124,
                })
                verify_manifest(f"POST_TEST_{i:02d}")
                continue

            (evidence_dir / f"test_{i:02d}.stdout.txt").write_text(cp.stdout, encoding="utf-8")
            (evidence_dir / f"test_{i:02d}.stderr.txt").write_text(cp.stderr, encoding="utf-8")

            verify_manifest(f"POST_TEST_{i:02d}")

            ok = False
            reason = f"pytest_exit={cp.returncode}"

            if cp.returncode == 0 and xml.exists():
                try:
                    ok, reason = one_result(xml)
                    (evidence_dir / f"test_{i:02d}.xml").write_bytes(xml.read_bytes())
                except Exception as e:
                    reason = f"invalid_junit:{type(e).__name__}:{e}"

            results.append({
                "node_id": node,
                "passed": bool(ok),
                "reason": reason,
                "pytest_exit": cp.returncode,
            })

    expected = len(m["mandatory_node_ids"])
    passed = len(results) == expected and all(r["passed"] for r in results)

    report = {
        "status": "PASS" if passed else "FAIL_CLOSED",
        "mandatory_count": len(results),
        "passed_count": sum(r["passed"] for r in results),
        "results": results,
        "runtime_isolation_required": os.environ.get("MV33_REQUIRE_ISOLATION", "") == "1",
        "runtime_test_user": os.environ.get("MV33_TEST_USER", ""),
        "freeze": False,
        "security_audit_passed": False,
    }

    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if passed else 2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-manifest")
    ap.add_argument("--no-head-anchor", action="store_true")
    ap.add_argument("--evidence-dir")
    ap.add_argument("--report")
    a = ap.parse_args()

    if a.verify_manifest:
        verify_manifest(a.verify_manifest, require_head_anchor=not a.no_head_anchor)
        return

    if not a.evidence_dir or not a.report:
        raise SystemExit(2)

    raise SystemExit(run_suite(ROOT / a.evidence_dir, ROOT / a.report))

if __name__ == "__main__":
    main()
