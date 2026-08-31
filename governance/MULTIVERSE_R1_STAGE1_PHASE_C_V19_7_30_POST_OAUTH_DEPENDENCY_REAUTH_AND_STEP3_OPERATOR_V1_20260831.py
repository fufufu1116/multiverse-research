#!/usr/bin/env python3
"""V19.7.30 post-OAuth review candidate. NONCANONICAL; NONMUTATING Step3 only."""
import fcntl, hashlib, importlib, importlib.machinery, importlib.util, io, json, os, pathlib, stat, subprocess, sys, types, zipfile
PY="/usr/local/python/current/bin/python"
ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-pydeps"); MAN=ROOT/"MANIFEST.sha256"
GH_CONFIG_DIR="/dev/shm/multiverse-r1-stage1-phase-c-gh-auth"
EXEC_ROOT=pathlib.Path("/dev/shm/multiverse-r1-stage1-phase-c-execution")
CANONICAL_MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"; CANONICAL_TREE="3d47741b4863411e5c36cb4c28925ac455ab6441"
PREFLIGHT="tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py"; PREFLIGHT_BLOB="0232c66bcf40cc1f61ce5bcc855604f73fce665a"; PREFLIGHT_BYTES=13902
ADMIN="tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py"; ADMIN_BLOB="ec05a014964211c15e48c3a2c327648a13f64dcf"; ADMIN_BYTES=20970
PYNACL="22de65bb9010a725b0dac248f353bb072969c94fa8d6b1f34b87d7953cf7bbe4"; PYCPARSER="e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934"
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
def write_all(fd,payload):
 view=memoryview(payload); done=0
 while done<len(view):
  n=os.write(fd,view[done:])
  if n<=0: die("MEMFD_SHORT_WRITE")
  done+=n
 if done!=len(view): die("MEMFD_SHORT_WRITE")
def sealed_memfd(name,data):
 if not hasattr(os,"memfd_create") or not hasattr(os,"MFD_ALLOW_SEALING"): die("MEMFD_SEALING_UNAVAILABLE")
 names=("F_ADD_SEALS","F_GET_SEALS","F_SEAL_SEAL","F_SEAL_SHRINK","F_SEAL_GROW","F_SEAL_WRITE")
 if any(not hasattr(fcntl,x) for x in names): die("MEMFD_SEALING_UNAVAILABLE")
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
 except BaseException: os.close(fd); raise
def trusted_chain(path,allow_missing_leaf=False):
 root=pathlib.Path(os.path.realpath("/usr/local/python/current")); p=pathlib.Path(path)
 if allow_missing_leaf and not p.exists(): target=p.parent.resolve(strict=True)
 else: target=p.resolve(strict=True)
 try: rel=target.relative_to(root)
 except ValueError: die("STDLIB_OUTSIDE_TRUST_ROOT")
 cur=root
 for part in ((),*[(x,) for x in rel.parts]):
  if part: cur=cur/part[0]
  st=os.lstat(cur)
  if st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022: die("STDLIB_WRITABLE_OR_UNOWNED")
 if allow_missing_leaf and not p.exists():
  if p.parent.resolve(strict=True)!=target: die("STDLIB_PATH_STATE")
def trusted_stdlib_paths():
 f=sys.flags
 if not (f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,"safe_path",False)): die("PYTHON_ISOLATION_REQUIRED")
 trust=os.path.realpath("/usr/local/python/current"); pyreal=os.path.realpath(PY)
 if not pyreal.startswith(trust+os.sep): die("PYTHON_TRUST_ROOT")
 trusted_chain(pyreal)
 mm=f"python{sys.version_info.major}.{sys.version_info.minor}"; compact=f"python{sys.version_info.major}{sys.version_info.minor}.zip"
 std=os.path.join(trust,"lib",mm); dyn=os.path.join(std,"lib-dynload"); z=os.path.join(trust,"lib",compact)
 trusted_chain(std); trusted_chain(dyn); trusted_chain(z,allow_missing_leaf=True)
 allowed={os.path.realpath(std),os.path.realpath(dyn),os.path.realpath(z) if os.path.exists(z) else os.path.abspath(z)}; out=[]
 for p in sys.path:
  if not p: die("STDLIB_EMPTY_PATH")
  rp=os.path.realpath(p) if os.path.exists(p) else os.path.abspath(p)
  if rp not in allowed: die("STDLIB_PATH_UNEXPECTED")
  trusted_chain(p,allow_missing_leaf=not os.path.exists(p)); out.append(p)
 if not out: die("STDLIB_PATH_EMPTY")
 return out
def exact_wheels(expected):
 out={}
 for n,h in expected.items():
  data=read_once(str(ROOT/"wheels"/n))
  if hashlib.sha256(data).hexdigest()!=h: die("WHEEL_REAUTH")
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for i in z.infolist():
    q=pathlib.PurePosixPath(i.filename); mode=(i.external_attr>>16)&0o170000
    if q.is_absolute() or ".." in q.parts or mode==stat.S_IFLNK: die("WHEEL_MEMBER")
  out[n]=data
 return out
def extension_bytes(wheels):
 found={}
 for n,data in wheels.items():
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   sos=[i for i in z.infolist() if not i.is_dir() and i.filename.endswith(".so")]
   if n=="pynacl.whl":
    cand=[i for i in sos if pathlib.PurePosixPath(i.filename).name.startswith("_sodium")]
    if len(cand)!=1 or len(sos)!=1: die("PYNACL_EXTENSION_SET")
    found["nacl._sodium"]=z.read(cand[0])
   elif n=="cffi.whl":
    cand=[i for i in sos if pathlib.PurePosixPath(i.filename).name.startswith("_cffi_backend")]
    if len(cand)!=1 or len(sos)!=1: die("CFFI_EXTENSION_SET")
    found["_cffi_backend"]=z.read(cand[0])
   elif sos: die("UNEXPECTED_EXTENSION_SET")
 if set(found)!={"nacl._sodium","_cffi_backend"}: die("EXTENSION_SET")
 return found
def extension_spec(fullname,fd):
 path=f"/proc/self/fd/{fd}"; loader=importlib.machinery.ExtensionFileLoader(fullname,path); spec=importlib.util.spec_from_file_location(fullname,path,loader=loader)
 if spec is None: die("EXTENSION_SPEC")
 return spec
def load_extension(fullname,fd):
 spec=extension_spec(fullname,fd); mod=importlib.util.module_from_spec(spec); sys.modules[fullname]=mod; spec.loader.exec_module(mod); return mod
class ExactSodiumFinder:
 def __init__(self,fd): self.fd=fd
 def find_spec(self,fullname,path=None,target=None):
  return extension_spec(fullname,self.fd) if fullname=="nacl._sodium" else None
def load_sealed_dependencies(wheels,stdlib):
 for k in list(sys.modules):
  if k=="_cffi_backend" or k=="nacl" or k.startswith("nacl.") or k=="cffi" or k.startswith("cffi.") or k=="pycparser" or k.startswith("pycparser."): sys.modules.pop(k,None)
 wheel_fds={}; ext_fds={}; old_path=list(sys.path); finder=None
 try:
  if old_path!=stdlib: die("STDLIB_PATH_DRIFT")
  for n,data in wheels.items(): wheel_fds[n]=sealed_memfd("multiverse-v19-7-30-"+n,data)
  for fullname,data in extension_bytes(wheels).items(): ext_fds[fullname]=sealed_memfd("multiverse-v19-7-30-"+fullname.replace(".","-"),data)
  zpaths=[f"/proc/self/fd/{wheel_fds[n]}" for n in ("pynacl.whl","cffi.whl","pycparser.whl")]
  sys.path[:]=zpaths+stdlib; importlib.invalidate_caches()
  load_extension("_cffi_backend",ext_fds["_cffi_backend"])
  finder=ExactSodiumFinder(ext_fds["nacl._sodium"]); sys.meta_path.insert(0,finder)
  nacl=importlib.import_module("nacl"); public=importlib.import_module("nacl.public")
  if finder in sys.meta_path: sys.meta_path.remove(finder)
  if "nacl._sodium" not in sys.modules: die("SODIUM_EXTENSION_NOT_LOADED")
  PrivateKey=public.PrivateKey; SealedBox=public.SealedBox
  if getattr(nacl,"__version__",None)!="1.6.2": die("PYNACL_VERSION")
  k=PrivateKey.generate(); m=b"multiverse-v19.7.30-sealed-memfd"; c=SealedBox(k.public_key).encrypt(m)
  if SealedBox(k).decrypt(c)!=m: die("PYNACL_ROUNDTRIP")
  allowed=tuple(zpaths+[f"/proc/self/fd/{fd}" for fd in ext_fds.values()])
  for name,mod in list(sys.modules.items()):
   if name=="_cffi_backend" or name=="nacl" or name.startswith("nacl.") or name=="cffi" or name.startswith("cffi.") or name=="pycparser" or name.startswith("pycparser."):
    origin=getattr(mod,"__file__",None)
    if origin is not None and not str(origin).startswith(allowed): die("DEPENDENCY_ORIGIN")
  sys.path[:]=stdlib; importlib.invalidate_caches(); return wheel_fds,ext_fds
 except BaseException:
  if finder in sys.meta_path: sys.meta_path.remove(finder)
  sys.path[:]=old_path
  for fd in list(wheel_fds.values())+list(ext_fds.values()):
   try: os.close(fd)
   except OSError: pass
  raise
def exact_exec_module(name,rel,expected_blob,expected_bytes):
 path=EXEC_ROOT/rel; data=read_once(str(path))
 if len(data)!=expected_bytes or blob(data)!=expected_blob: die("CANONICAL_MODULE_EXACT_IDENTITY")
 mod=types.ModuleType(name); mod.__file__=str(path); mod.__package__=name.rpartition(".")[0]; sys.modules[name]=mod; exec(compile(data,"<canonical-main:"+rel+">","exec"),mod.__dict__,mod.__dict__); return mod
def same_process_canonical_preflight(stdlib):
 old=list(sys.path)
 if old!=stdlib: die("STDLIB_PATH_DRIFT")
 sys.path[:]=stdlib; importlib.invalidate_caches()
 try:
  exact_exec_module("multiverse_r1_stage1_writer_key_admin_channel_v1",ADMIN,ADMIN_BLOB,ADMIN_BYTES)
  pre=exact_exec_module("_multiverse_phase_c_canonical_preflight",PREFLIGHT,PREFLIGHT_BLOB,PREFLIGHT_BYTES); fn=getattr(pre,"live_preflight",None)
  if not callable(fn): die("PREFLIGHT_ENTRY")
  d=fn()
 finally: sys.path[:]=stdlib; importlib.invalidate_caches()
 if not isinstance(d,dict) or d.get("status")!="PHASE_C_NONMUTATING_PREFLIGHT_PASS" or d.get("execution_checkout_sha")!=CANONICAL_MAIN or d.get("fresh_main_sha")!=CANONICAL_MAIN or d.get("production_mutation_performed") is not False or d.get("runtime_activation_performed") is not False: die("STEP3_RESULT")
 return d
def main():
 os.umask(0o077); sys.dont_write_bytecode=True
 if os.environ.get("CODESPACES")!="true" or not os.environ.get("CODESPACE_NAME") or sys.executable!=PY or len(sys.argv)!=2 or sys.version_info[:2] not in CFFI: die("ENTRY")
 stdlib=trusted_stdlib_paths()
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
 wheels=exact_wheels(expected); wheel_fds,ext_fds=load_sealed_dependencies(wheels,stdlib)
 try:
  repo=os.path.realpath(sys.argv[1]); v29=read_once(os.path.join(repo,V29))
  if len(v29)!=V29_BYTES or blob(v29)!=V29_BLOB or hashlib.sha256(v29).hexdigest()!=V29_SHA: die("V19_7_29_IDENTITY")
  ns={"__name__":"_multiverse_v19_7_29_same_memory_"}; exec(compile(v29,"<v19.7.29-same-memory>","exec"),ns,ns); rebootstrap=ns.get("rebootstrap_current_main")
  if not callable(rebootstrap): die("V19_7_29_REBOOTSTRAP_ENTRY")
  print("PHASE_C_V19_7_30_POST_OAUTH_SEALED_MEMFD_DEPENDENCY_PASS",flush=True); rebootstrap(); same_process_canonical_preflight(stdlib)
 finally:
  for fd in list(wheel_fds.values())+list(ext_fds.values()):
   try: os.close(fd)
   except OSError: pass
 print("PHASE_C_V19_7_30_STEP3_PREFLIGHT_PASS",flush=True); print("PRODUCTION_MUTATION_PERFORMED=false",flush=True); print("RUNTIME_ACTIVATION_PERFORMED=false",flush=True); return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except SystemExit: raise
 except BaseException: os._exit(92)
