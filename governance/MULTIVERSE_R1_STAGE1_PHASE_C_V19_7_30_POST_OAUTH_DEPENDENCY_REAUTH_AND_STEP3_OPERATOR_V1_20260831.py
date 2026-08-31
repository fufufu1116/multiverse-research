#!/usr/bin/env python3
"""V19.7.30 post-OAuth review candidate. NONCANONICAL; NONMUTATING Step3 only."""
import hashlib, json, os, pathlib, stat, subprocess, sys
PY="/usr/local/python/current/bin/python"
ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-pydeps"); SITE=ROOT/"site"; MAN=ROOT/"MANIFEST.sha256"
GH_CONFIG_DIR="/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
EXEC_ROOT="/dev/shm/multiverse-r1-stage1-phase-c-execution"
PREFLIGHT="tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py"
PYNACL="22de65bb9010a725b0dac248f353bb072969c94fa8d6b1f34b87d7953cf7bbe4"
PYCPARSER="e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934"
CFFI={(3,11):"34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632",(3,12):"c1453022f490d2459a11819d83ad1d586e9ff65a12ac3e705ffebd46d3685dcf",(3,13):"a931079504ecc49efed7744c476a5c343a92fabf66dec2db95edb1b2fdc770e2",(3,14):"b0431303acaea1089ad4b3e9ce4e6518193def1118d4073ca848635ee4ea2e96"}
V29="governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_29_POST_OAUTH_CURRENT_MAIN_REBOOTSTRAP_STEP3_OPERATOR_V3_20260831.py"; V29_BYTES=8227; V29_BLOB="61e302d9ef3f70b82301dec0b0fdffb3a677adef"; V29_SHA="aaf6acfb863228c174fcfb10678f346d3297a740918a79becc6aad0cb485aac0"
def die(x): print("PHASE_C_V19_7_30_POST_OAUTH_DENIED:"+x,flush=True); raise SystemExit(92)
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def read_once(p):
 fd=os.open(p,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.getuid(): die("FILE_STATE")
  a=[]
  while True:
   b=os.read(fd,1048576)
   if not b: break
   a.append(b)
  return b"".join(a)
 finally: os.close(fd)
def main():
 if os.environ.get("CODESPACES")!="true" or not os.environ.get("CODESPACE_NAME") or sys.executable!=PY or len(sys.argv)!=2 or sys.version_info[:2] not in CFFI: die("ENTRY")
 if os.environ.get("GH_CONFIG_DIR")!=GH_CONFIG_DIR: die("GH_CONFIG_DIR")
 if subprocess.check_output(["stat","-f","-c","%T",str(ROOT)],text=True).strip() not in {"tmpfs","ramfs"}: die("PYDEPS_FS")
 st=os.lstat(ROOT)
 if st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700 or len(pathlib.Path("/proc/swaps").read_text().splitlines())>1: die("PYDEPS_STATE")
 rows=MAN.read_text(encoding="ascii").splitlines(); got={}
 for row in rows:
  h,n=row.split("  wheels/",1)
  if n in got: die("MANIFEST_DUPLICATE")
  got[n]=h
 expected={"pynacl.whl":PYNACL,"pycparser.whl":PYCPARSER,"cffi.whl":CFFI[sys.version_info[:2]]}
 if got!=expected: die("MANIFEST")
 for n,h in expected.items():
  p=ROOT/"wheels"/n
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h: die("WHEEL_REAUTH")
 code='import sys; p=sys.argv[1]; sys.path[:]=[p]+[x for x in sys.path if x!=p and "site-packages" not in x and ".local" not in x]; from nacl.public import PrivateKey,SealedBox; import nacl; assert nacl.__version__=="1.6.2"; k=PrivateKey.generate(); m=b"post-oauth"; assert SealedBox(k).decrypt(SealedBox(k.public_key).encrypt(m))==m'
 if subprocess.run([PY,"-I","-B","-c",code,str(SITE)],env={"PATH":"/usr/local/bin:/usr/bin:/bin","PYTHONNOUSERSITE":"1"}).returncode: die("PYNACL_REAUTH")
 repo=os.path.realpath(sys.argv[1]); v29=read_once(os.path.join(repo,V29))
 if len(v29)!=V29_BYTES or blob(v29)!=V29_BLOB or hashlib.sha256(v29).hexdigest()!=V29_SHA: die("V19_7_29_IDENTITY")
 ns={"__name__":"_multiverse_v19_7_29_same_memory_"}
 exec(compile(v29,"<v19.7.29-same-memory>","exec"),ns,ns)
 rebootstrap=ns.get("rebootstrap_current_main")
 if not callable(rebootstrap): die("V19_7_29_REBOOTSTRAP_ENTRY")
 print("PHASE_C_V19_7_30_POST_OAUTH_DEPENDENCY_REAUTH_PASS",flush=True)
 rebootstrap()
 env={"PATH":"/usr/local/bin:/usr/bin:/bin","LANG":"C","LC_ALL":"C","CODESPACES":os.environ["CODESPACES"],"CODESPACE_NAME":os.environ["CODESPACE_NAME"],"GH_CONFIG_DIR":GH_CONFIG_DIR,"PYTHONPATH":str(SITE),"PYTHONNOUSERSITE":"1"}
 cp=subprocess.run([PY,"-B",PREFLIGHT],cwd=EXEC_ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if cp.returncode!=0:
  try:
   d=json.loads(cp.stdout); reason=d.get("reason","UNCLASSIFIED") if isinstance(d,dict) else "UNCLASSIFIED"
  except Exception: reason="UNCLASSIFIED"
  print("PHASE_C_V19_7_30_STEP3_PREFLIGHT_DENIED:"+str(reason)[:220].replace("\n","_").replace("\r","_"),flush=True)
  return 92
 try: d=json.loads(cp.stdout)
 except Exception: die("STEP3_JSON")
 if not isinstance(d,dict) or d.get("status")!="PHASE_C_NONMUTATING_PREFLIGHT_PASS" or d.get("production_mutation_performed") is not False or d.get("runtime_activation_performed") is not False: die("STEP3_RESULT")
 print("PHASE_C_V19_7_30_STEP3_PREFLIGHT_PASS",flush=True)
 print("PRODUCTION_MUTATION_PERFORMED=false",flush=True); print("RUNTIME_ACTIVATION_PERFORMED=false",flush=True)
 return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except SystemExit: raise
 except BaseException: os._exit(92)
