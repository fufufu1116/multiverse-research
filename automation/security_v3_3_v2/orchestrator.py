from __future__ import annotations
import json, os, random, subprocess, sys, time
from pathlib import Path
from google import genai
from automation.security_v3_3_v2.patch_guard import apply_patch, candidate_sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / os.environ.get("AUTOPILOT_OUTPUT_DIR", "autopilot_v2_output")
MAX_REPAIRS = int(os.environ.get("MAX_REPAIRS", "8"))
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

PATCH_SCHEMA = {
  "type":"object", "additionalProperties":False,
  "required":["schema_version","attempt","base_candidate_sha256","changes","reason","expected_fixed_tests"],
  "properties":{
    "schema_version":{"type":"string","enum":["mv33-patch-v1"]},
    "attempt":{"type":"integer","minimum":1,"maximum":8},
    "base_candidate_sha256":{"type":"string"},
    "changes":{"type":"array","minItems":1,"maxItems":5,"items":{"type":"object","additionalProperties":False,"required":["path","operation","content"],"properties":{"path":{"type":"string"},"operation":{"type":"string","enum":["create","replace"]},"content":{"type":"string"}}}},
    "reason":{"type":"string"},
    "expected_fixed_tests":{"type":"array","items":{"type":"string"}}
  }
}

def receipt(status: str, detail: str = ""):
    obj={"status":status,"detail":detail,"freeze":False,"security_audit_passed":False,"ECON_HOLDOUT1000":{"state":"SEALED","Price_accessed":False,"PAYOUT_accessed":False,"scored":False}}
    (OUT/"BUILD_RECEIPT.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def verify(stage):
    cp=subprocess.run([sys.executable,"oracle_candidate/immutable_validator.py","--verify-manifest",stage],cwd=ROOT,text=True,capture_output=True)
    (OUT/f"manifest_{stage}.txt").write_text(cp.stdout+"\n"+cp.stderr,encoding="utf-8")
    if cp.returncode: raise RuntimeError(f"manifest {stage} failed")

def run_tests(label: str):
    d=OUT/label; d.mkdir(parents=True,exist_ok=True); report=d/"validator_report.json"
    cp=subprocess.run([sys.executable,"oracle_candidate/immutable_validator.py","--evidence-dir",str(d.relative_to(ROOT)),"--report",str(report.relative_to(ROOT))],cwd=ROOT,text=True,capture_output=True)
    (d/"validator.stdout.txt").write_text(cp.stdout,encoding="utf-8"); (d/"validator.stderr.txt").write_text(cp.stderr,encoding="utf-8")
    data=json.loads(report.read_text(encoding="utf-8")) if report.exists() else {"status":"FAIL_CLOSED","results":[],"error":"missing report"}
    return cp.returncode, data

def compact_failure(report):
    bad=[{"node_id":r.get("node_id"),"reason":r.get("reason")} for r in report.get("results",[]) if not r.get("passed")]
    return {"status":report.get("status"),"failed_tests":bad[:13]}

def call_gemini(client, attempt, failure):
    tests=(ROOT/"oracle_candidate/test_security_oracle.py").read_text(encoding="utf-8")
    spec=(ROOT/"oracle_candidate/ORACLE_SPEC.json").read_text(encoding="utf-8")
    prompt=("Implement only candidate/security_v3_3/ so the immutable synthetic security oracle passes. "
            "Do not modify tests/oracle/validator/workflow/evidence. Do not invent ROI, profit, races, PRICE or PAYOUT data. "
            "Use only synthetic state. Return only the requested structured patch.\n\nORACLE SPEC:\n"+spec+"\n\nIMMUTABLE TEST SOURCE:\n"+tests+"\n\nCURRENT FAILURE:\n"+json.dumps(failure,ensure_ascii=False)+"\nCURRENT CANDIDATE SHA256:\n"+candidate_sha()+f"\nATTEMPT:{attempt}")
    last=None
    for n in range(5):
        try:
            r=client.models.generate_content(model=MODEL,contents=prompt,config={"response_mime_type":"application/json","response_json_schema":PATCH_SCHEMA})
            return r.text
        except Exception as e:
            last=e; code=getattr(e,"status_code",None) or getattr(e,"code",None)
            text=str(e)
            transient = code in {429,500,502,503,504} or any(x in text for x in ["429","500","502","503","504","UNAVAILABLE","RESOURCE_EXHAUSTED"])
            if not transient or n==4: raise
            time.sleep(min(2**n,16)+random.random())
    raise last

def main():
    OUT.mkdir(parents=True,exist_ok=True); receipt("FAIL_CLOSED","not completed")
    try:
        verify("START")
        code, report=run_tests("baseline")
        if code==0:
            verify("END"); receipt("ZERO_AUDIT_LOCAL_TESTED","baseline passed; pending independent Oracle audit"); return 0
        client=genai.Client()
        failure=compact_failure(report)
        for attempt in range(1,MAX_REPAIRS+1):
            ad=OUT/f"attempt_{attempt:02d}"; ad.mkdir(parents=True,exist_ok=True)
            try: raw=call_gemini(client,attempt,failure)
            except Exception as e:
                (ad/"gemini_api_error.txt").write_text(type(e).__name__+": "+str(e),encoding="utf-8"); receipt("FAIL_CLOSED","Gemini API failure"); return 2
            (ad/"gemini_patch.json").write_text(raw,encoding="utf-8")
            try: pr=apply_patch(raw); (ad/"patch_result.json").write_text(json.dumps(pr,indent=2)+"\n",encoding="utf-8")
            except Exception as e:
                failure={"status":"PATCH_REJECTED","failed_tests":[],"patch_error":str(e)}; (ad/"patch_rejected.txt").write_text(str(e),encoding="utf-8"); continue
            code, report=run_tests(f"attempt_{attempt:02d}/tests")
            if code==0:
                verify("END"); receipt("ZERO_AUDIT_LOCAL_TESTED",f"passed after {attempt} repair attempts; pending independent Oracle audit"); return 0
            failure=compact_failure(report)
        verify("END"); receipt("FAIL_CLOSED",f"no candidate passed after {MAX_REPAIRS} repairs"); return 2
    except Exception as e:
        receipt("FAIL_CLOSED",type(e).__name__+": "+str(e)); print("FAIL_CLOSED:",e,file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
