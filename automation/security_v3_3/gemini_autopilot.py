from pathlib import Path
import json, os, re, shutil, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
PROMPT = (HERE / "FINAL_ACCEPTANCE_PROMPT.txt").read_text(encoding="utf-8")
MAX_ATTEMPTS = 3

def sanitize(text):
    return re.sub(r'(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+', r'\1=[REDACTED]', text)[-24000:]

def call_gemini(instruction):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY required")
    from google import genai
    client = genai.Client(api_key=key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    resp = client.models.generate_content(model=model, contents=instruction, config={"response_mime_type":"application/json","response_schema":{"type":"object","properties":{"build_script":{"type":"string"}},"required":["build_script"]}})
    if not getattr(resp, "text", None):
        raise RuntimeError("Gemini returned no text")
    return resp.text

def parse_output(text):
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    obj = json.loads(t)
    if set(obj.keys()) != {"build_script"} or not isinstance(obj["build_script"], str):
        raise ValueError("Gemini output contract violated")
    return obj["build_script"]

def main():
    outroot = Path(os.environ.get("AUTOPILOT_OUTPUT_DIR", "autopilot_output")).resolve()
    outroot.mkdir(parents=True, exist_ok=True)
    failure = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        instruction = PROMPT
        if failure:
            instruction += "\n\nPrevious sanitized failure:\n" + failure + "\nRepair root cause without weakening tests."
        script_text = parse_output(call_gemini(instruction))
        with tempfile.TemporaryDirectory(prefix=f"mv33_{attempt}_") as td:
            work = Path(td)
            script = work / "build_candidate.py"
            script.write_text(script_text, encoding="utf-8")

            # Preserve exactly what Gemini generated before execution.
            evidence_script = outroot / f"attempt_{attempt}_build_candidate.py"
            evidence_script.write_text(script_text, encoding="utf-8")

            # Syntax-only preflight: do not execute malformed generated Python.
            cp = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script)],
                cwd=work,
                text=True,
                capture_output=True,
                timeout=120,
            )
            (outroot / f"attempt_{attempt}_py_compile.txt").write_text(
                cp.stdout + "\n" + cp.stderr,
                encoding="utf-8",
            )

            if cp.returncode != 0:
                failure = sanitize(
                    "PY_COMPILE_FAILED\n"
                    + cp.stdout
                    + "\n"
                    + cp.stderr
                    + "\nRepair syntax/indentation only. "
                      "Do not weaken tests, receipt checks, or fail-closed semantics."
                )
                (outroot / "FAILURE_CONTEXT.json").write_text(
                    json.dumps(
                        {
                            "attempt": attempt,
                            "stage": "py_compile",
                            "sanitized_failure": failure,
                            "ECON_HOLDOUT1000": {
                                "state": "SEALED",
                                "Price_accessed": False,
                                "PAYOUT_accessed": False,
                                "scored": False,
                            },
                            "Freeze": False,
                            "SECURITY_AUDIT_PASSED": False,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ) + "\n",
                    encoding="utf-8",
                )
                continue

            bp = subprocess.run(
                [sys.executable, str(script)],
                cwd=work,
                text=True,
                capture_output=True,
                timeout=600,
            )
            candidate = work / "candidate"
            if bp.returncode == 0 and candidate.is_dir():
                vp = subprocess.run([sys.executable, str(HERE / "acceptance_validator.py"), str(candidate)],
                                    text=True, capture_output=True, timeout=600)
                if vp.returncode == 0:
                    final = outroot / "LOCAL_TESTED_candidate"
                    if final.exists():
                        shutil.rmtree(final)
                    shutil.copytree(candidate, final)
                    (outroot / "AUTOPILOT_STATUS.json").write_text(json.dumps({
                        "status": "LOCAL_TESTED — pending independent re-audit",
                        "attempt": attempt,
                        "ECON_HOLDOUT1000": {"state":"SEALED","Price_accessed":False,"PAYOUT_accessed":False,"scored":False},
                        "Freeze": False,
                        "SECURITY_AUDIT_PASSED": False
                    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print("LOCAL_TESTED — pending independent re-audit")
                    return 0
                failure = sanitize(vp.stdout + "\n" + vp.stderr)
            else:
                failure = sanitize(bp.stdout + "\n" + bp.stderr + ("\nHARD_FAILURE: required ./candidate directory was not created" if bp.returncode == 0 and not candidate.is_dir() else ""))
            (outroot / "FAILURE_CONTEXT.json").write_text(json.dumps({"attempt":attempt,"sanitized_failure":failure}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"FAIL_CLOSED: no candidate passed after {MAX_ATTEMPTS} attempts", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
