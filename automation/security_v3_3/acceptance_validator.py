from pathlib import Path
import hashlib, json, re, subprocess, sys, os

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def collect_count(output):
    m = re.search(r"(\d+)\s+tests?\s+collected", output)
    if m:
        return int(m.group(1))
    m = re.search(r"collected\s+(\d+)\s+items?", output)
    if m:
        return int(m.group(1))
    raise ValueError("cannot parse collected test count")

def run(cmd, cwd):
    env = os.environ.copy(); env["PYTHONPATH"] = str(cwd.parent) + os.pathsep + env.get("PYTHONPATH", ""); p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=env)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

def verify_manifest(candidate):
    mf = candidate / "FILE_MANIFEST_SHA256.json"
    if not mf.exists():
        return {"ok": False, "error": "manifest_missing"}
    data = json.loads(mf.read_text(encoding="utf-8"))
    mismatches = []
    for rel, expected in data.items():
        p = candidate / rel
        if not p.is_file():
            mismatches.append({"path": rel, "reason": "missing"})
        elif sha256_file(p) != expected:
            mismatches.append({"path": rel, "reason": "sha_mismatch"})
    return {"ok": not mismatches, "mismatches": mismatches, "entries": len(data)}

def verify_receipt(candidate, cr, pr, rr, count):
    rp = candidate / "BUILD_RECEIPT.json"
    if not rp.exists():
        return {"ok": False, "error": "receipt_missing"}
    r = json.loads(rp.read_text(encoding="utf-8"))
    checks = {
        "compileall_exit_0": cr["returncode"] == 0 and r.get("compileall_exit_code") == 0,
        "pytest_exit_0": pr["returncode"] == 0 and r.get("pytest_exit_code") == 0,
        "collect_exit_0": rr["returncode"] == 0 and r.get("collect_exit_code") == 0,
        "test_count_match": r.get("collected_test_count") == count,
        "max_status": r.get("status") == "LOCAL_TESTED — pending independent re-audit",
        "holdout_sealed": (r.get("ECON_HOLDOUT1000") if isinstance(r.get("ECON_HOLDOUT1000"), dict) else {}).get("state") == "SEALED",
        "price_unaccessed": (r.get("ECON_HOLDOUT1000") if isinstance(r.get("ECON_HOLDOUT1000"), dict) else {}).get("Price_accessed") is False,
        "payout_unaccessed": (r.get("ECON_HOLDOUT1000") if isinstance(r.get("ECON_HOLDOUT1000"), dict) else {}).get("PAYOUT_accessed") is False,
        "unscored": (r.get("ECON_HOLDOUT1000") if isinstance(r.get("ECON_HOLDOUT1000"), dict) else {}).get("scored") is False,
        "not_frozen": r.get("Freeze") in (None, False),
        "no_security_audit_passed": r.get("SECURITY_AUDIT_PASSED") in (None, False),
    }
    return {"ok": all(checks.values()), "checks": checks}

def validate(candidate):
    cr = run([sys.executable, "-m", "compileall", "-q", "."], candidate)
    pr = run([sys.executable, "-m", "pytest", "-q"], candidate)
    rr = run([sys.executable, "-m", "pytest", "--collect-only", "-q"], candidate)
    count = collect_count(rr["stdout"] + "\n" + rr["stderr"]) if rr["returncode"] == 0 else -1
    manifest = verify_manifest(candidate)
    receipt = verify_receipt(candidate, cr, pr, rr, count)
    xfail = "XFAIL" in (pr["stdout"] + pr["stderr"]).upper() or "XPASS" in (pr["stdout"] + pr["stderr"]).upper()
    ok = cr["returncode"] == pr["returncode"] == rr["returncode"] == 0 and count >= 1 and manifest["ok"] and receipt["ok"] and not xfail
    return {"ok": ok, "compileall": cr, "pytest": pr, "collect": rr, "count": count, "manifest": manifest, "receipt": receipt, "xfail": xfail}

if __name__ == "__main__":
    candidate = Path(sys.argv[1]).resolve()
    out = validate(candidate)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["ok"] else 1)
