#!/usr/bin/env python3
"""V19.7.30 review-only pre-OAuth readiness launcher.
NONCANONICAL / NO LIVE AUTHORITY. No OAuth, Step3, Step4, apply, production mutation, or Runtime activation.
"""
import hashlib, os, pathlib, platform, stat, subprocess, sys, urllib.request, zipfile
PY="/usr/local/python/current/bin/python"
ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-pydeps"); DL=ROOT/"wheels"; SITE=ROOT/"site"
ART={
"pynacl.whl":("https://files.pythonhosted.org/packages/7f/81/d60984052df5c97b1d24365bc1e30024379b42c4edcd79d2436b1b9806f2/pynacl-1.6.2-cp38-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","22de65bb9010a725b0dac248f353bb072969c94fa8d6b1f34b87d7953cf7bbe4"),
"pycparser.whl":("https://files.pythonhosted.org/packages/a0/e3/59cd50310fc9b59512193629e1984c1f95e5c8ae6e5d8c69532ccc65a7fe/pycparser-2.23-py3-none-any.whl","e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934")}
CFFI={(3,11):("https://files.pythonhosted.org/packages/f7/a4/4399daaf8f7dfee9d7c3327fdb0426ee041cc63edc358b93911ceb2bfc7a/cffi-2.1.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632"),(3,12):("https://files.pythonhosted.org/packages/b1/db/dceb9dd5b231e1da801793f8acc9f3c52a7e1afe40bb1aae37e02b0faad5/cffi-2.1.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","c1453022f490d2459a11819d83ad1d586e9ff65a12ac3e705ffebd46d3685dcf"),(3,13):("https://files.pythonhosted.org/packages/95/95/86342356ff5953b3fb06f7ef7c5bee212d45e770abc7218d451b9148313c/cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","a931079504ecc49efed7744c476a5c343a92fabf66dec2db95edb1b2fdc770e2"),(3,14):("https://files.pythonhosted.org/packages/e9/02/4e7d553a7ac4b4238b38b3c1b80d486e9d4436f8d2acbf87a0997fe3f402/cffi-2.1.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","b0431303acaea1089ad4b3e9ce4e6518193def1118d4073ca848635ee4ea2e96")}
def die(x): print("PHASE_C_V19_7_30_READINESS_DENIED:"+x,flush=True); raise SystemExit(92)
def fst(p): return subprocess.check_output(["stat","-f","-c","%T",str(p)],text=True).strip()
def extract(src,dst):
 with zipfile.ZipFile(src) as z:
  for i in z.infolist():
   q=pathlib.PurePosixPath(i.filename); mode=(i.external_attr>>16)&0o170000
   if q.is_absolute() or ".." in q.parts or mode==stat.S_IFLNK: die("WHEEL_MEMBER")
  z.extractall(dst)
def fetch(n,u,h):
 p=DL/n; req=urllib.request.Request(u,headers={"User-Agent":"multiverse-v19.7.30-readiness"})
 with urllib.request.urlopen(req,timeout=60) as r,open(p,"xb") as f:
  if r.geturl()!=u: die("DOWNLOAD_REDIRECT")
  while True:
   b=r.read(1048576)
   if not b: break
   f.write(b)
 if hashlib.sha256(p.read_bytes()).hexdigest()!=h: die("ARTIFACT_SHA256")
 return p
def main():
 if os.environ.get("CODESPACES")!="true" or not os.environ.get("CODESPACE_NAME"): die("CODESPACES")
 if sys.executable!=PY or not os.path.samefile(sys.executable,PY): die("TRUSTED_PYTHON")
 if platform.system()!="Linux" or platform.machine()!="x86_64" or sys.version_info[:2] not in CFFI: die("PLATFORM")
 if len(pathlib.Path("/proc/swaps").read_text().splitlines())>1: die("ACTIVE_SWAP")
 if ROOT.exists(): die("PYDEPS_ROOT_PREEXISTS")
 ROOT.mkdir(mode=0o700); DL.mkdir(mode=0o700); SITE.mkdir(mode=0o700)
 if fst(ROOT) not in {"tmpfs","ramfs"}: die("PYDEPS_NOT_MEMORY_FS")
 st=os.lstat(ROOT)
 if st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700: die("PYDEPS_PERMISSIONS")
 a=dict(ART); a["cffi.whl"]=CFFI[sys.version_info[:2]]; paths=[fetch(n,*v) for n,v in a.items()]
 for p in paths: extract(p,SITE)
 # -I intentionally ignores PYTHONPATH. Insert only the exact verified tmpfs site from literal argv.
 code='import sys; p=sys.argv[1]; sys.path[:]=[p]+[x for x in sys.path if x!=p and "site-packages" not in x and ".local" not in x]; from nacl.public import PrivateKey,SealedBox; import nacl; assert nacl.__version__=="1.6.2"; k=PrivateKey.generate(); m=b"multiverse-v19.7.30"; c=SealedBox(k.public_key).encrypt(m); assert SealedBox(k).decrypt(c)==m; print("PYNACL_1_6_2_ROUNDTRIP_PASS")'
 cp=subprocess.run([PY,"-I","-B","-c",code,str(SITE)],env={"PATH":"/usr/local/bin:/usr/bin:/bin","PYTHONNOUSERSITE":"1"},text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if cp.returncode or cp.stdout.strip()!="PYNACL_1_6_2_ROUNDTRIP_PASS": die("PYNACL_ROUNDTRIP")
 with open(ROOT/"MANIFEST.sha256","x",encoding="ascii") as f:
  for p in paths: f.write(hashlib.sha256(p.read_bytes()).hexdigest()+"  wheels/"+p.name+"\n")
 print("PHASE_C_V19_7_30_PRE_OAUTH_READINESS_PASS",flush=True); print("OAUTH_STARTED=false",flush=True); print("PRODUCTION_MUTATION_PERFORMED=false",flush=True); print("RUNTIME_ACTIVATION_PERFORMED=false",flush=True)
if __name__=="__main__": main()
