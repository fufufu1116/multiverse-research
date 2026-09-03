#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, os, pathlib, subprocess, sys

from orchestrator_provider_idempotency_v8 import V8_CANONICAL_MAIN, V8_MANIFEST_SHA256, V8_SOURCE_BRANCH, V8Manifest
from orchestrator_role_relay_policy_source_v5 import ReviewedPolicySource

ROOT=pathlib.Path(__file__).resolve().parent.parent
HERE=ROOT/"automation"
MANIFEST=HERE/"MULTIVERSE_AUTOMATION_PROVIDER_IDEMPOTENCY_V8.json"
POLICY=HERE/"MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json"
V5_HEAD="e803723309a045086287e613f924a90a880b5a3b"
V5_BRANCH="agent/automation-orchestrator-policy-source-v5-20260903-v1"
FILES=[HERE/"orchestrator_provider_idempotency_v8.py",HERE/"test_orchestrator_provider_idempotency_v8.py",HERE/"test_orchestrator_provider_idempotency_v8_integration.py"]
FORBIDDEN={"anthropic","boto3","http.client","httpx","openai","requests","socket","urllib","urllib.request"}
FORBIDDEN_TEXT=("OPENAI_API_KEY","ANTHROPIC_API_KEY","os.environ","getenv(","urlopen(","requests.","httpx.","socket.")

def run(cmd,env=None): return subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env)
def run_test(pattern,env):
    p=run([sys.executable,"-m","unittest","discover","-s","automation","-p",pattern,"-v"],env); print(p.stdout,end=""); print(p.stderr,end="")
    if p.returncode: print("PROVIDER_IDEMPOTENCY_V8_TESTS_FAIL:"+pattern); return False
    return True

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--expected-head",required=True); ap.add_argument("--canonical-main",required=True); ap.add_argument("--candidate-branch",required=True); ns=ap.parse_args()
    if len(ns.expected_head)!=40 or len(ns.canonical_main)!=40: return 2
    if ns.canonical_main!=V8_CANONICAL_MAIN: print("CURRENT_MAIN_NOT_REVIEWED_V8_MAIN"); return 2
    if ns.candidate_branch!=V8_SOURCE_BRANCH: print("WRONG_V8_BRANCH"); return 2
    for path in FILES:
        text=path.read_text(); tree=ast.parse(text,filename=str(path))
        if path.name=="orchestrator_provider_idempotency_v8.py":
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for name in node.names:
                        if name.name in FORBIDDEN: print("FORBIDDEN_IMPORT:"+name.name); return 3
                if isinstance(node,ast.ImportFrom) and node.module in FORBIDDEN: print("FORBIDDEN_IMPORT:"+str(node.module)); return 3
            for token in FORBIDDEN_TEXT:
                if token in text: print("FORBIDDEN_CAPABILITY_TEXT:"+token); return 3
    h=run(["git","rev-parse","HEAD"])
    if h.returncode or h.stdout.strip()!=ns.expected_head: print("EXACT_HEAD_BINDING_FAIL"); return 4
    m=V8Manifest(MANIFEST)
    if m.sha256!=V8_MANIFEST_SHA256: print("V8_MANIFEST_SHA_MISMATCH"); return 5
    source=ReviewedPolicySource.load(POLICY)
    if source.canonical_main!=ns.canonical_main: print("V5_POLICY_SOURCE_MAIN_MISMATCH"); return 5
    env=os.environ.copy(); env["MULTIVERSE_V8_CODE_HEAD"]=ns.expected_head; env["MULTIVERSE_V7_CODE_HEAD"]=ns.expected_head; env["MULTIVERSE_CANONICAL_MAIN"]=ns.canonical_main
    patterns=["test_orchestrator_role_relay_v3.py","test_orchestrator_role_relay_policy_v4.py","test_orchestrator_role_relay_policy_source_v5.py","test_orchestrator_policy_change_control_v6.py","test_orchestrator_provider_adapter_v7.py","test_orchestrator_provider_adapter_v7_integration.py","test_orchestrator_provider_idempotency_v8.py","test_orchestrator_provider_idempotency_v8_integration.py"]
    for pat in patterns:
        if not run_test(pat,env): return 6
    v5env=env.copy(); v5env["MULTIVERSE_EXPECTED_HEAD"]=V5_HEAD; v5env["MULTIVERSE_V5_CANDIDATE_BRANCH"]=V5_BRANCH
    if not run_test("test_orchestrator_role_relay_policy_source_v5_integration.py",v5env): return 6
    print("PROVIDER_IDEMPOTENCY_V8_MECHANICAL_GATE_PASS=true"); print("PROVIDER_IDEMPOTENCY_V8_EXACT_HEAD="+ns.expected_head); print("PROVIDER_IDEMPOTENCY_V8_CANONICAL_MAIN="+ns.canonical_main); print("PROVIDER_IDEMPOTENCY_V8_SOURCE_BRANCH="+ns.candidate_branch); print("PROVIDER_IDEMPOTENCY_V8_MANIFEST_SHA256="+m.sha256)
    print("PROVIDER_IDEMPOTENCY_V8_PREPARE_COMMIT_BEFORE_REMOTE=true"); print("PROVIDER_IDEMPOTENCY_V8_LOCAL_TX_ACROSS_REMOTE=false"); print("PROVIDER_IDEMPOTENCY_V8_RESPONSE_LOST_RECONCILIATION=true"); print("PROVIDER_IDEMPOTENCY_V8_SIMULATED_REMOTE_EFFECT=true"); print("PROVIDER_IDEMPOTENCY_V8_REAL_EXTERNAL_EFFECT=false"); print("PROVIDER_IDEMPOTENCY_V8_NETWORK=false"); print("PROVIDER_IDEMPOTENCY_V8_LIVE_PROVIDER=false"); print("PROVIDER_IDEMPOTENCY_V8_CREDENTIAL=false"); print("PROVIDER_IDEMPOTENCY_V8_SPEND=false"); print("PROVIDER_IDEMPOTENCY_V8_EXISTING_V5_POLICY_ONLY=true"); print("PROVIDER_IDEMPOTENCY_V8_ARBITRARY_PROVIDER_EXACTLY_ONCE_PROVEN=false"); print("OWNER_COPY_PASTE_COUNT=0"); print("OWNER_CONTINUE_PROMPT_COUNT=0"); print("OWNER_KEEP_ALIVE_COUNT=0"); print("PRODUCTION_AUTHORITY_GRANTED=false"); print("CORE_KEIRIN_ADOPTION_AUTHORITY=false"); print("PROVIDER_IDEMPOTENCY_V8_RUNTIME=OFF")
    return 0
if __name__=="__main__": raise SystemExit(main())
