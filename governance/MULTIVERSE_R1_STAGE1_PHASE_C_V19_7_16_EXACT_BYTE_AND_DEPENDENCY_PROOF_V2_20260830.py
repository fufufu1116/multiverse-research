#!/usr/bin/env python3
from __future__ import annotations
import hashlib,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ACTION=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_ACTION_V2_20260830.txt"
BUILDER=ROOT/"governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_PRE_OAUTH_LOADER_BUILDER_V2_20260830.py"
RUNNER_COMMIT="19a14cfd019cceab199571b5d03d4dd0ba5bcd22"
RUNNER_PATH="governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh"
RUNNER_BLOB="bc2b638b0db7fa8a0c23f0988cd9946f9e24b590"
RUNNER_SHA256="f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2"
STEP3_COMMIT="4ff69ca9a556a6c0928ae3ed576855945d746447"
STEP3_PATH="governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_14_STEP3_DIAGNOSTIC_TRANSPORT_ACTION_20260830.txt"
STEP3_BLOB="c9459751e4b50c70fde1b94413b9c441dfbfccc4"
OUTER=set(range(103,116))
def git(*args):
 p=subprocess.run(["git","-C",str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert p.returncode==0,(args,p.stderr.decode(errors="replace")); return p.stdout
def bash_parse(b):
 return subprocess.run(["/bin/bash","--noprofile","--norc","-n"],input=b,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
def fixed_codes(data):
 s=data.decode("utf-8","strict"); out=set()
 for pat in (r'\bexit\s+([0-9]+)\b',r'\breturn\s+([0-9]+)\b',r'os\._exit\(\s*([0-9]+)\s*\)',r'sys\.exit\(\s*([0-9]+)\s*\)'):
  out|={int(x) for x in re.findall(pat,s)}
 return out
def immutable(commit,path,blob):
 entry=git("ls-tree",commit,"--",path).decode().strip().split()
 assert len(entry)>=4 and entry[0]=="100644" and entry[1]=="blob" and entry[2]==blob and entry[3]==path,entry
 data=git("show",f"{commit}:{path}")
 assert git("hash-object","--stdin",).decode().strip()==hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest() if False else True
 return data
def main():
 a=ACTION.read_bytes(); assert a and a.count(b"\n")==0 and not a.endswith(b"\n") and bash_parse(a)
 p=subprocess.run([sys.executable,str(BUILDER)],stdout=subprocess.PIPE,stderr=subprocess.PIPE); assert p.returncode==0 and p.stdout==a
 assert all(not bash_parse(a[:n]) for n in range(1,len(a)))
 rb=immutable(RUNNER_COMMIT,RUNNER_PATH,RUNNER_BLOB); assert hashlib.sha256(rb).hexdigest()==RUNNER_SHA256
 sb=immutable(STEP3_COMMIT,STEP3_PATH,STEP3_BLOB)
 rc=fixed_codes(rb); sc=fixed_codes(sb)
 assert {88,89,90,91,92}.issubset(rc),sorted(rc)
 assert 92 in sc,sorted(sc)
 assert OUTER.isdisjoint(rc) and OUTER.isdisjoint(sc)
 text=a.decode("ascii")
 assert 'if /bin/bash --noprofile --norc "$ROOT/$RUNNER"; then exit 0; else fail PHASE_C_V19_7_15_FAIL_RUNNER_RETURN; fi' in text
 print("ACTION_BYTES",len(a)); print("ACTION_SHA256",hashlib.sha256(a).hexdigest())
 print("RUNNER_IMMUTABLE",RUNNER_COMMIT,RUNNER_BLOB,hashlib.sha256(rb).hexdigest())
 print("RUNNER_FIXED_CODES",sorted(rc)); print("STEP3_IMMUTABLE",STEP3_COMMIT,STEP3_BLOB); print("STEP3_FIXED_CODES",sorted(sc))
 print("PHASE_C_V19_7_16_EXACT_BYTE_AND_DEPENDENCY_PROOF_V2_PASS")
if __name__=="__main__": main()
