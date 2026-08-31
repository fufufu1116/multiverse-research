#!/usr/bin/env python3
"""V19.7.34 review-only pre-OAuth sealed dependency readiness. NONCANONICAL / NO LIVE AUTHORITY."""
import fcntl, hashlib, http.client, importlib, importlib.machinery, importlib.util, io, os, pathlib, platform, ssl, stat, subprocess, sys, urllib.parse, zipfile
PY="/usr/local/python/current/bin/python"; HOST="files.pythonhosted.org"; ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-pydeps-v19-7-34"); DL=ROOT/"wheels"
ART={"pynacl.whl":("https://files.pythonhosted.org/packages/7f/81/d60984052df5c97b1d24365bc1e30024379b42c4edcd79d2436b1b9806f2/pynacl-1.6.2-cp38-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","22de65bb9010a725b0dac248f353bb072969c94fa8d6b1f34b87d7953cf7bbe4"),"pycparser.whl":("https://files.pythonhosted.org/packages/a0/e3/59cd50310fc9b59512193629e1984c1f95e5c8ae6e5d8c69532ccc65a7fe/pycparser-2.23-py3-none-any.whl","e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934")}
CFFI={(3,11):("https://files.pythonhosted.org/packages/f7/a4/4399daaf8f7dfee9d7c3327fdb0426ee041cc63edc358b93911ceb2bfc7a/cffi-2.1.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632"),(3,12):("https://files.pythonhosted.org/packages/b1/db/dceb9dd5b231e1da801793f8acc9f3c52a7e1afe40bb1aae37e02b0faad5/cffi-2.1.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","c1453022f490d2459a11819d83ad1d586e9ff65a12ac3e705ffebd46d3685dcf"),(3,13):("https://files.pythonhosted.org/packages/95/95/86342356ff5953b3fb06f7ef7c5bee212d45e770abc7218d451b9148313c/cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","a931079504ecc49efed7744c476a5c343a92fabf66dec2db95edb1b2fdc770e2"),(3,14):("https://files.pythonhosted.org/packages/e9/02/4e7d553a7ac4b4238b38b3c1b80d486e9d4436f8d2acbf87a0997fe3f402/cffi-2.1.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","b0431303acaea1089ad4b3e9ce4e6518193def1118d4073ca848635ee4ea2e96")}
def die(x): print("PHASE_C_V19_7_34_READINESS_DENIED:"+x,flush=True); raise SystemExit(92)
def fst(p): return subprocess.check_output(["/usr/bin/stat","-f","-c","%T",str(p)],text=True).strip()
def fetch(n,u,h):
 x=urllib.parse.urlsplit(u)
 if x.scheme!="https" or x.hostname!=HOST or x.port not in (None,443) or x.username or x.password or x.fragment: die("DOWNLOAD_URL")
 p=DL/n; conn=http.client.HTTPSConnection(HOST,443,timeout=60,context=ssl.create_default_context())
 try:
  conn.request("GET",urllib.parse.urlunsplit(("","",x.path,x.query,"")),headers={"Host":HOST,"User-Agent":"multiverse-v19.7.34-readiness","Connection":"close"}); r=conn.getresponse()
  if 300<=r.status<400: die("DOWNLOAD_REDIRECT")
  if r.status!=200: die("DOWNLOAD_HTTP_STATUS")
  with open(p,"xb") as f:
   while True:
    b=r.read(1048576)
    if not b: break
    f.write(b)
 finally: conn.close()
 if hashlib.sha256(p.read_bytes()).hexdigest()!=h: die("ARTIFACT_SHA256")
 return p
def write_all(fd,data):
 v=memoryview(data); done=0
 while done<len(v):
  n=os.write(fd,v[done:])
  if n<=0: die("MEMFD_SHORT_WRITE")
  done+=n
 if done!=len(v): die("MEMFD_SHORT_WRITE")
def sealed(name,data):
 if not hasattr(os,"memfd_create") or not hasattr(os,"MFD_ALLOW_SEALING"): die("MEMFD_UNAVAILABLE")
 need=("F_ADD_SEALS","F_GET_SEALS","F_SEAL_SEAL","F_SEAL_SHRINK","F_SEAL_GROW","F_SEAL_WRITE")
 if any(not hasattr(fcntl,x) for x in need): die("MEMFD_UNAVAILABLE")
 fd=os.memfd_create(name,getattr(os,"MFD_CLOEXEC",0)|os.MFD_ALLOW_SEALING)
 try:
  write_all(fd,data); os.fsync(fd); expected=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE; fcntl.fcntl(fd,fcntl.F_ADD_SEALS,expected)
  if fcntl.fcntl(fd,fcntl.F_GET_SEALS)&expected!=expected: die("MEMFD_SEALS")
  os.lseek(fd,0,os.SEEK_SET); got=b""
  while True:
   b=os.read(fd,1048576)
   if not b: break
   got+=b
  if got!=data: die("MEMFD_READBACK")
  os.lseek(fd,0,os.SEEK_SET); return fd
 except BaseException: os.close(fd); raise
def wheel_parts(data,kind):
 try:
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for i in z.infolist():
    q=pathlib.PurePosixPath(i.filename); mode=(i.external_attr>>16)&0o170000
    if q.is_absolute() or ".." in q.parts or mode==stat.S_IFLNK: die("WHEEL_MEMBER")
   sos=[i for i in z.infolist() if not i.is_dir() and i.filename.endswith(".so")]
   if kind=="pynacl":
    c=[i for i in sos if pathlib.PurePosixPath(i.filename).name.startswith("_sodium")]
    if len(c)!=1 or len(sos)!=1: die("PYNACL_EXTENSION_SET")
    return z.read(c[0])
   if kind=="cffi":
    c=[i for i in sos if pathlib.PurePosixPath(i.filename).name.startswith("_cffi_backend")]
    if len(c)!=1 or len(sos)!=1: die("CFFI_EXTENSION_SET")
    return z.read(c[0])
 except SystemExit: raise
 except Exception as e: die("WHEEL_PARSE_"+type(e).__name__)
def spec(fullname,fd):
 p=f"/proc/self/fd/{fd}"; loader=importlib.machinery.ExtensionFileLoader(fullname,p); s=importlib.util.spec_from_file_location(fullname,p,loader=loader)
 if s is None: die("EXTENSION_SPEC")
 return s
def load_ext(fullname,fd):
 try:
  s=spec(fullname,fd); m=importlib.util.module_from_spec(s); sys.modules[fullname]=m; s.loader.exec_module(m); return m
 except SystemExit: raise
 except Exception as e: die("LOAD_"+fullname.replace(".","_").upper()+"_"+type(e).__name__)
class SodiumFinder:
 def __init__(self,fd): self.fd=fd
 def find_spec(self,fullname,path=None,target=None): return spec(fullname,self.fd) if fullname=="nacl._sodium" else None
def probe(wheels):
 wf={}; ef={}; finder=None; old=list(sys.path)
 try:
  for n,d in wheels.items(): wf[n]=sealed("multiverse-v19-7-34-"+n,d)
  ef["_cffi_backend"]=sealed("multiverse-v19-7-34-cffi",wheel_parts(wheels["cffi.whl"],"cffi")); ef["nacl._sodium"]=sealed("multiverse-v19-7-34-sodium",wheel_parts(wheels["pynacl.whl"],"pynacl"))
  z=[f"/proc/self/fd/{wf[n]}" for n in ("pynacl.whl","cffi.whl","pycparser.whl")]; sys.path[:]=z+old; importlib.invalidate_caches(); load_ext("_cffi_backend",ef["_cffi_backend"])
  finder=SodiumFinder(ef["nacl._sodium"]); sys.meta_path.insert(0,finder)
  try: nacl=importlib.import_module("nacl"); public=importlib.import_module("nacl.public")
  except Exception as e: die("IMPORT_NACL_"+type(e).__name__)
  if getattr(nacl,"__version__",None)!="1.6.2": die("PYNACL_VERSION")
  try:
   k=public.PrivateKey.generate(); m=b"multiverse-v19.7.34-sealed-probe"; c=public.SealedBox(k.public_key).encrypt(m); out=public.SealedBox(k).decrypt(c)
  except Exception as e: die("PYNACL_CRYPTO_"+type(e).__name__)
  if out!=m: die("PYNACL_ROUNDTRIP_MISMATCH")
  print("PHASE_C_V19_7_34_SEALED_PYNACL_1_6_2_ROUNDTRIP_PASS",flush=True)
 finally:
  if finder in sys.meta_path: sys.meta_path.remove(finder)
  sys.path[:]=old; importlib.invalidate_caches()
  for fd in list(wf.values())+list(ef.values()):
   try: os.close(fd)
   except OSError: pass
def main():
 if os.environ.get("CODESPACES")!="true" or not os.environ.get("CODESPACE_NAME"): die("CODESPACES")
 if sys.executable!=PY or not os.path.samefile(sys.executable,PY): die("TRUSTED_PYTHON")
 if platform.system()!="Linux" or platform.machine()!="x86_64" or sys.version_info[:2] not in CFFI: die("PLATFORM")
 if len(pathlib.Path("/proc/swaps").read_text().splitlines())>1: die("ACTIVE_SWAP")
 if ROOT.exists(): die("PYDEPS_ROOT_PREEXISTS")
 ROOT.mkdir(mode=0o700); DL.mkdir(mode=0o700)
 if fst(ROOT) not in {"tmpfs","ramfs"}: die("PYDEPS_NOT_MEMORY_FS")
 st=os.lstat(ROOT)
 if st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700: die("PYDEPS_PERMISSIONS")
 a=dict(ART); a["cffi.whl"]=CFFI[sys.version_info[:2]]; paths={n:fetch(n,*v) for n,v in a.items()}; wheels={n:p.read_bytes() for n,p in paths.items()}; probe(wheels)
 with open(ROOT/"MANIFEST.sha256","x",encoding="ascii") as f:
  for n,p in paths.items(): f.write(hashlib.sha256(p.read_bytes()).hexdigest()+"  wheels/"+n+"\n")
 print("PHASE_C_V19_7_34_PRE_OAUTH_READINESS_PASS",flush=True); print("OAUTH_STARTED=false",flush=True); print("PRODUCTION_MUTATION_PERFORMED=false",flush=True); print("RUNTIME_ACTIVATION_PERFORMED=false",flush=True)
if __name__=="__main__": main()
