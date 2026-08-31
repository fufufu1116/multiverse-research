#!/usr/bin/env python3
"""V19.7.30 post-OAuth review candidate. NONCANONICAL; NONMUTATING Step3 only."""
import hashlib, os, pathlib, stat, subprocess, sys
PY="/usr/local/python/current/bin/python"; ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-pydeps"); SITE=ROOT/"site"; MAN=ROOT/"MANIFEST.sha256"
EXPECTED={"pynacl.whl":"22de65bb9010a725b0dac248f353bb072969c94fa8d6b1f34b87d7953cf7bbe4","pycparser.whl":"e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934"}
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
 if os.environ.get("CODESPACES")!="true" or not os.environ.get("CODESPACE_NAME") or sys.executable!=PY or len(sys.argv)!=2: die("ENTRY")
 if subprocess.check_output(["stat","-f","-c","%T",str(ROOT)],text=True).strip() not in {"tmpfs","ramfs"}: die("PYDEPS_FS")
 st=os.lstat(ROOT)
 if st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700: die("PYDEPS_PERMISSIONS")
 if len(pathlib.Path("/proc/swaps").read_text().splitlines())>1: die("ACTIVE_SWAP")
 rows=MAN.read_text(encoding="ascii").splitlines(); got={}
 for row in rows:
  h,n=row.split("  wheels/",1); got[n]=h
 if got.get("pynacl.whl")!=EXPECTED["pynacl.whl"] or got.get("pycparser.whl")!=EXPECTED["pycparser.whl"]: die("MANIFEST")
 for n,h in got.items():
  p=ROOT/"wheels"/n
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h: die("WHEEL_REAUTH")
 code='import sys; p=sys.argv[1]; sys.path[:]=[p]+[x for x in sys.path if x!=p and "site-packages" not in x and ".local" not in x]; from nacl.public import PrivateKey,SealedBox; import nacl; assert nacl.__version__=="1.6.2"; k=PrivateKey.generate(); m=b"post-oauth"; assert SealedBox(k).decrypt(SealedBox(k.public_key).encrypt(m))==m'
 if subprocess.run([PY,"-I","-B","-c",code,str(SITE)],env={"PATH":"/usr/local/bin:/usr/bin:/bin","PYTHONNOUSERSITE":"1"}).returncode: die("PYNACL_REAUTH")
 repo=os.path.realpath(sys.argv[1]); v29=read_once(os.path.join(repo,V29))
 if len(v29)!=V29_BYTES or blob(v29)!=V29_BLOB or hashlib.sha256(v29).hexdigest()!=V29_SHA: die("V19_7_29_IDENTITY")
 print("PHASE_C_V19_7_30_POST_OAUTH_DEPENDENCY_REAUTH_PASS",flush=True)
 cp=subprocess.run([PY,"-I","-B","-c","import sys; exec(compile(sys.stdin.buffer.read(),'<v19.7.29-same-memory>','exec'))",repo],input=v29)
 return cp.returncode if 0<=cp.returncode<=255 else 92
if __name__=="__main__": raise SystemExit(main())
