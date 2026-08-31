#!/usr/bin/env python3
"""V19.7.35 review-only pre-OAuth sealed dependency readiness. NONCANONICAL / NO LIVE AUTHORITY."""
import fcntl, hashlib, http.client, importlib, importlib.machinery, importlib.util, io, os, pathlib, platform, ssl, stat, subprocess, sys, urllib.parse, zipfile
PY="/usr/local/python/current/bin/python"; HOST="files.pythonhosted.org"; ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-pydeps"); DL=ROOT/"wheels"; MAN=ROOT/"MANIFEST.sha256"
ART={"pynacl.whl":("https://files.pythonhosted.org/packages/7f/81/d60984052df5c97b1d24365bc1e30024379b42c4edcd79d2436b1b9806f2/pynacl-1.6.2-cp38-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","22de65bb9010a725b0dac248f353bb072969c94fa8d6b1f34b87d7953cf7bbe4"),"pycparser.whl":("https://files.pythonhosted.org/packages/a0/e3/59cd50310fc9b59512193629e1984c1f95e5c8ae6e5d8c69532ccc65a7fe/pycparser-2.23-py3-none-any.whl","e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934")}
CFFI={(3,11):("https://files.pythonhosted.org/packages/f7/a4/4399daaf8f7dfee9d7c3327fdb0426ee041cc63edc358b93911ceb2bfc7a/cffi-2.1.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","34e261f78cb6ceaaa36f42f2613f4380d94d9c759a9c73c769ee6e0247364632"),(3,12):("https://files.pythonhosted.org/packages/b1/db/dceb9dd5b231e1da801793f8acc9f3c52a7e1afe40bb1aae37e02b0faad5/cffi-2.1.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","c1453022f490d2459a11819d83ad1d586e9ff65a12ac3e705ffebd46d3685dcf"),(3,13):("https://files.pythonhosted.org/packages/95/95/86342356ff5953b3fb06f7ef7c5bee212d45e770abc7218d451b9148313c/cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","a931079504ecc49efed7744c476a5c343a92fabf66dec2db95edb1b2fdc770e2"),(3,14):("https://files.pythonhosted.org/packages/e9/02/4e7d553a7ac4b4238b38b3c1b80d486e9d4436f8d2acbf87a0997fe3f402/cffi-2.1.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl","b0431303acaea1089ad4b3e9ce4e6518193def1118d4073ca848635ee4ea2e96")}
def die(x): print("PHASE_C_V19_7_35_READINESS_DENIED:"+x,flush=True); raise SystemExit(92)
def guard(label,fn):
 try: return fn()
 except SystemExit: raise
 except BaseException as e: die(label+"_"+type(e).__name__.upper())
def trusted_chain(path,allow_missing_leaf=False):
 root=pathlib.Path(os.path.realpath("/usr/local/python/current")); p=pathlib.Path(path)
 target=p.parent.resolve(strict=True) if allow_missing_leaf and not p.exists() else p.resolve(strict=True)
 try: rel=target.relative_to(root)
 except ValueError: die("STDLIB_OUTSIDE_TRUST_ROOT")
 cur=root
 for part in ((),*[(x,) for x in rel.parts]):
  if part: cur=cur/part[0]
  st=os.lstat(cur)
  if st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022: die("STDLIB_WRITABLE_OR_UNOWNED")
 if allow_missing_leaf and not p.exists() and p.parent.resolve(strict=True)!=target: die("STDLIB_PATH_STATE")
def trusted_stdlib_paths():
 f=sys.flags
 if not (f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,"safe_path",False)): die("PYTHON_ISOLATION_REQUIRED")
 trust=os.path.realpath("/usr/local/python/current"); pyreal=os.path.realpath(PY)
 if not pyreal.startswith(trust+os.sep): die("PYTHON_TRUST_ROOT")
 trusted_chain(pyreal)
 mm=f"python{sys.version_info.major}.{sys.version_info.minor}"; compact=f"python{sys.version_info.major}{sys.version_info.minor}.zip"; std=os.path.join(trust,"lib",mm); dyn=os.path.join(std,"lib-dynload"); z=os.path.join(trust,"lib",compact)
 trusted_chain(std); trusted_chain(dyn); trusted_chain(z,allow_missing_leaf=True)
 allowed={os.path.realpath(std),os.path.realpath(dyn),os.path.realpath(z) if os.path.exists(z) else os.path.abspath(z)}; out=[]
 for p in sys.path:
  if not p: die("STDLIB_EMPTY_PATH")
  rp=os.path.realpath(p) if os.path.exists(p) else os.path.abspath(p)
  if rp not in allowed: die("STDLIB_PATH_UNEXPECTED")
  trusted_chain(p,allow_missing_leaf=not os.path.exists(p)); out.append(p)
 if not out: die("STDLIB_PATH_EMPTY")
 return out
def fst(p): return subprocess.check_output(["/usr/bin/stat","-f","-c","%T",str(p)],text=True).strip()
def write_all(fd,data):
 v=memoryview(data); done=0
 while done<len(v):
  n=os.write(fd,v[done:])
  if n<=0: die("WRITE_SHORT")
  done+=n
def exact_read_file(p,expected):
 fd=os.open(p,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_nlink!=1: die("WHEEL_FILE_STATE")
  chunks=[]
  while True:
   b=os.read(fd,1048576)
   if not b: break
   chunks.append(b)
  data=b"".join(chunks)
 finally: os.close(fd)
 if hashlib.sha256(data).hexdigest()!=expected: die("WHEEL_REAUTH")
 return data
def fetch(n,u,h):
 def run():
  x=urllib.parse.urlsplit(u)
  if x.scheme!="https" or x.hostname!=HOST or x.port not in (None,443) or x.username or x.password or x.fragment: die("DOWNLOAD_URL")
  p=DL/n; conn=http.client.HTTPSConnection(HOST,443,timeout=60,context=ssl.create_default_context())
  try:
   conn.request("GET",urllib.parse.urlunsplit(("","",x.path,x.query,"")),headers={"Host":HOST,"User-Agent":"multiverse-v19.7.35-readiness","Connection":"close"}); r=conn.getresponse()
   if 300<=r.status<400: die("DOWNLOAD_REDIRECT")
   if r.status!=200: die("DOWNLOAD_HTTP_STATUS")
   fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o400)
   try:
    while True:
     b=r.read(1048576)
     if not b: break
     write_all(fd,b)
    os.fsync(fd)
   finally: os.close(fd)
  finally: conn.close()
  data=exact_read_file(p,h)
  return p,data
 return guard("DOWNLOAD_"+n.split('.')[0].upper(),run)
def sealed(name,data):
 def run():
  if not hasattr(os,"memfd_create") or not hasattr(os,"MFD_ALLOW_SEALING"): die("MEMFD_UNAVAILABLE")
  need=("F_ADD_SEALS","F_GET_SEALS","F_SEAL_SEAL","F_SEAL_SHRINK","F_SEAL_GROW","F_SEAL_WRITE")
  if any(not hasattr(fcntl,x) for x in need): die("MEMFD_UNAVAILABLE")
  fd=os.memfd_create(name,getattr(os,"MFD_CLOEXEC",0)|os.MFD_ALLOW_SEALING)
  try:
   write_all(fd,data); os.fsync(fd); st=os.fstat(fd)
   if not stat.S_ISREG(st.st_mode) or st.st_size!=len(data): die("MEMFD_SIZE")
   expected=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE; fcntl.fcntl(fd,fcntl.F_ADD_SEALS,expected)
   if fcntl.fcntl(fd,fcntl.F_GET_SEALS)&expected!=expected: die("MEMFD_SEALS")
   os.lseek(fd,0,os.SEEK_SET); h=hashlib.sha256()
   while True:
    b=os.read(fd,1048576)
    if not b: break
    h.update(b)
   if h.digest()!=hashlib.sha256(data).digest(): die("MEMFD_READBACK")
   os.lseek(fd,0,os.SEEK_SET); return fd
  except BaseException:
   os.close(fd); raise
 return guard("MEMFD_"+name.replace(".","_").upper(),run)
def wheel_part(data,kind):
 def run():
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for i in z.infolist():
    q=pathlib.PurePosixPath(i.filename); mode=(i.external_attr>>16)&0o170000
    if q.is_absolute() or ".." in q.parts or mode==stat.S_IFLNK: die("WHEEL_MEMBER")
   sos=[i for i in z.infolist() if not i.is_dir() and i.filename.endswith(".so")]
   c=[i for i in sos if pathlib.PurePosixPath(i.filename).name.startswith("_sodium" if kind=="pynacl" else "_cffi_backend")]
   if len(c)!=1 or len(sos)!=1: die(("PYNACL" if kind=="pynacl" else "CFFI")+"_EXTENSION_SET")
   return z.read(c[0])
 return guard("WHEEL_PARSE_"+kind.upper(),run)
def spec(fullname,fd):
 p=f"/proc/self/fd/{fd}"; loader=importlib.machinery.ExtensionFileLoader(fullname,p); s=importlib.util.spec_from_file_location(fullname,p,loader=loader)
 if s is None: die("EXTENSION_SPEC")
 return s
def load_ext(fullname,fd):
 def run():
  s=spec(fullname,fd); m=importlib.util.module_from_spec(s); sys.modules[fullname]=m; s.loader.exec_module(m); return m
 return guard("LOAD_"+fullname.replace(".","_").upper(),run)
class SodiumFinder:
 def __init__(self,fd): self.fd=fd
 def find_spec(self,fullname,path=None,target=None): return spec(fullname,self.fd) if fullname=="nacl._sodium" else None
def probe(wheels,stdlib):
 wf={}; ef={}; finder=None; old=list(sys.path)
 try:
  if old!=stdlib: die("STDLIB_PATH_DRIFT")
  for n,d in wheels.items(): wf[n]=sealed("multiverse-v19-7-35-"+n,d)
  ef["_cffi_backend"]=sealed("multiverse-v19-7-35-cffi",wheel_part(wheels["cffi.whl"],"cffi")); ef["nacl._sodium"]=sealed("multiverse-v19-7-35-sodium",wheel_part(wheels["pynacl.whl"],"pynacl"))
  z=[f"/proc/self/fd/{wf[n]}" for n in ("pynacl.whl","cffi.whl","pycparser.whl")]; sys.path[:]=z+stdlib; importlib.invalidate_caches(); load_ext("_cffi_backend",ef["_cffi_backend"])
  finder=SodiumFinder(ef["nacl._sodium"]); sys.meta_path.insert(0,finder)
  nacl=guard("IMPORT_NACL",lambda: importlib.import_module("nacl")); public=guard("IMPORT_NACL_PUBLIC",lambda: importlib.import_module("nacl.public"))
  if getattr(nacl,"__version__",None)!="1.6.2": die("PYNACL_VERSION")
  def crypto():
   k=public.PrivateKey.generate(); m=b"multiverse-v19.7.35-sealed-probe"; c=public.SealedBox(k.public_key).encrypt(m); return m,public.SealedBox(k).decrypt(c)
  m,out=guard("PYNACL_CRYPTO",crypto)
  if out!=m: die("PYNACL_ROUNDTRIP_MISMATCH")
  print("PHASE_C_V19_7_35_SEALED_PYNACL_1_6_2_ROUNDTRIP_PASS",flush=True)
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
 stdlib=guard("STDLIB_BASELINE",trusted_stdlib_paths)
 if len(pathlib.Path("/proc/swaps").read_text().splitlines())>1: die("ACTIVE_SWAP")
 if ROOT.exists(): die("PYDEPS_ROOT_PREEXISTS")
 guard("ROOT_CREATE",lambda: (ROOT.mkdir(mode=0o700),DL.mkdir(mode=0o700)))
 if guard("PYDEPS_FS",lambda: fst(ROOT)) not in {"tmpfs","ramfs"}: die("PYDEPS_NOT_MEMORY_FS")
 st=os.lstat(ROOT)
 if st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700: die("PYDEPS_PERMISSIONS")
 a=dict(ART); a["cffi.whl"]=CFFI[sys.version_info[:2]]; fetched={n:fetch(n,*v) for n,v in a.items()}; wheels={n:pd[1] for n,pd in fetched.items()}
 probe(wheels,stdlib)
 def write_manifest():
  fd=os.open(MAN,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o400)
  try:
   for n in ("pynacl.whl","pycparser.whl","cffi.whl"): write_all(fd,(a[n][1]+"  wheels/"+n+"\n").encode("ascii"))
   os.fsync(fd)
  finally: os.close(fd)
 guard("MANIFEST_WRITE",write_manifest)
 print("PHASE_C_V19_7_35_PRE_OAUTH_READINESS_PASS",flush=True); print("OAUTH_STARTED=false",flush=True); print("PRODUCTION_MUTATION_PERFORMED=false",flush=True); print("RUNTIME_ACTIVATION_PERFORMED=false",flush=True)
if __name__=="__main__":
 try: main()
 except SystemExit: raise
 except BaseException as e: die("TOPLEVEL_"+type(e).__name__.upper())
