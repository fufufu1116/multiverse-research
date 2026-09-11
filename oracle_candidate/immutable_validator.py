from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ZERO_AUDIT_ORACLE_MANIFEST.json"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verify_manifest(stage: str):
    m = load_manifest()
    committed = subprocess.run(["git", "show", "HEAD:ZERO_AUDIT_ORACLE_MANIFEST.json"], cwd=ROOT, capture_output=True)
    if committed.returncode != 0 or hashlib.sha256(committed.stdout).hexdigest() != h(MANIFEST):
        raise SystemExit(f"FAIL_CLOSED: {stage}: manifest differs from committed root anchor")
    for rel, expected in m["protected_components"].items():
        p = ROOT / rel
        if not p.is_file() or h(p) != expected:
            raise SystemExit(f"FAIL_CLOSED: {stage}: protected component mismatch: {rel}")
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


def run_suite(evidence_dir: Path, report_path: Path) -> int:
    m = load_manifest(); evidence_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy(); env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    results = []
    for i, node in enumerate(m["mandatory_node_ids"], 1):
        xml = evidence_dir / f"test_{i:02d}.xml"
        cp = subprocess.run([sys.executable, "-m", "pytest", "-q", node, f"--junitxml={xml}", "-p", "no:cacheprovider"], cwd=ROOT, env=env, text=True, capture_output=True, timeout=120)
        (evidence_dir / f"test_{i:02d}.stdout.txt").write_text(cp.stdout, encoding="utf-8")
        (evidence_dir / f"test_{i:02d}.stderr.txt").write_text(cp.stderr, encoding="utf-8")
        ok = False; reason = f"pytest_exit={cp.returncode}"
        if cp.returncode == 0 and xml.exists():
            try: ok, reason = one_result(xml)
            except Exception as e: reason = f"invalid_junit:{type(e).__name__}:{e}"
        results.append({"node_id": node, "passed": bool(ok), "reason": reason, "pytest_exit": cp.returncode})
    passed = all(r["passed"] for r in results)
    report = {"status": "PASS" if passed else "FAIL_CLOSED", "mandatory_count": len(results), "passed_count": sum(r["passed"] for r in results), "results": results, "freeze": False, "security_audit_passed": False}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return 0 if passed else 2


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--verify-manifest"); ap.add_argument("--evidence-dir"); ap.add_argument("--report")
    a = ap.parse_args()
    if a.verify_manifest: verify_manifest(a.verify_manifest); return
    if not a.evidence_dir or not a.report: raise SystemExit(2)
    raise SystemExit(run_suite(ROOT/a.evidence_dir, ROOT/a.report))

if __name__ == "__main__": main()
