#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt"
BUILDER=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_BUILDER_V2_20260830.py"
RUNNER=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh"
STEP3=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_14_STEP3_DIAGNOSTIC_TRANSPORT_ACTION_20260830.txt"
OUTER=set(range(103,116))
def bash_parse(b:bytes)->bool:
 p=subprocess.run(["/bin/bash","--noprofile","--norc","-n"],input=b,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 return p.returncode==0
def fixed_codes(data:bytes):
 s=data.decode("utf-8","strict"); out=set()
 for pat in (r'\bexit\s+([0-9]+)\b',r'\breturn\s+([0-9]+)\b',r'os\._exit\(\s*([0-9]+)\s*\)',r'sys\.exit\(\s*([0-9]+)\s*\)'):
  out|={int(x) for x in re.findall(pat,s)}
 return out
def main():
 a=ACTION.read_bytes(); assert a and a.count(b"\n")==0 and not a.endswith(b"\n")
 assert bash_parse(a)
 p=subprocess.run(["python3",str(BUILDER)],stdout=subprocess.PIPE,stderr=subprocess.PIPE); assert p.returncode==0 and p.stdout==a
 # exhaustive strict-prefix parse property, exact changed bytes
 bad=[]
 for n in range(1,len(a)):
  if bash_parse(a[:n]): bad.append(n)
 assert not bad,("STRICT_PREFIX_PARSEABLE",bad[:20])
 # Dependency proof is valid only when these local bytes are independently established as
 # exact immutable dependency blobs by Git review. We do not assert candidate-branch blob equality.
 if not RUNNER.exists() or not STEP3.exists(): raise SystemExit("IMMUTABLE_DEPENDENCY_BYTES_REQUIRED")
 rc=fixed_codes(RUNNER.read_bytes()); sc=fixed_codes(STEP3.read_bytes())
 assert OUTER.isdisjoint(rc),sorted(OUTER & rc)
 assert OUTER.isdisjoint(sc),sorted(OUTER & sc)
 print("ACTION_BYTES",len(a)); print("ACTION_SHA256",hashlib.sha256(a).hexdigest())
 print("RUNNER_FIXED_CODES",sorted(rc)); print("STEP3_FIXED_CODES",sorted(sc))
 print("PHASE_C_V19_7_16_EXACT_BYTE_AND_DEPENDENCY_PROOF_V2_PASS")
if __name__=="__main__": main()
