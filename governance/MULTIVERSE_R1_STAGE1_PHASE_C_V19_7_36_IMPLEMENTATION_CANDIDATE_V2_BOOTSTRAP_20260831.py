#!/usr/bin/env python3
"""V19.7.36 v2 pre-Python bootstrap verifier. REVIEW-ONLY / NO LIVE AUTHORITY."""
import fcntl,hashlib,json,os,pathlib,stat,subprocess,sys
RC=92; MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"; TREE="3d47741b4863411e5c36cb4c28925ac455ab6441"
R="/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v2-receipts"
def deny(x):
 print("PHASE_C_V19_7_36_V2_BOOTSTRAP_DENIED:"+x,flush=True);raise SystemExit(RC)
def cpath(p,kind="file"):
 q=pathlib.Path(p)
 try:r=q.resolve(strict=True)
 except OSError:deny("CLASS_C_MISSING_"+p.replace("/","_"))
 cur=pathlib.Path("/")
 for part in r.parts[1:]:
  cur/=part; st=os.lstat(cur)
  if st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022:deny("CLASS_C_MUTABLE_"+str(cur).replace("/","_"))
 if kind=="file" and not stat.S_ISREG(os.stat(r).st_mode):deny("CLASS_C_NOT_FILE")
 if kind=="dir" and not stat.S_ISDIR(os.stat(r).st_mode):deny("CLASS_C_NOT_DIR")
 return str(r)
def run(argv):
 e={"PATH":"/usr/bin:/bin","HOME":"/nonexistent","LANG":"C","LC_ALL":"C","GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":"/dev/null","GIT_CONFIG_SYSTEM":"/dev/null","GIT_TERMINAL_PROMPT":"0","GIT_ASKPASS":"/bin/false","SSH_ASKPASS":"/bin/false"}
 try:return subprocess.check_output(argv,env=e,stderr=subprocess.STDOUT,text=True,timeout=20).strip()
 except BaseException as z:deny("SUBPROCESS_"+type(z).__name__.upper())
def ldd_paths(exe):
 ldd=cpath("/usr/bin/ldd"); out=run([ldd,exe]); z=[]
 for line in out.splitlines():
  s=line.strip()
  p=(s.split("=>",1)[1].strip().split()[0] if "=>" in s else s.split()[0])
  if p.startswith("/"):z.append(cpath(p))
 return sorted(set(z))
def trust_exec(p):
 p=cpath(p); return {"class":"C","same_uid_mutable":False,"absolute_path":p,"elf_loader":True,"transitive_libraries":ldd_paths(p),"loader_authority":"ROOT_CONTROLLED","helpers":"FORBIDDEN","config":"FORBIDDEN","credential_helpers":"FORBIDDEN","ca_tls":"ROOT_CONTROLLED","environment":"FIXED","cwd_repo":"FIXED","network_protocol":"DISABLED","preexec_drift":"ROOT_CONTROLLED"}
def simple(p,kind="file"):return {"class":"C","same_uid_mutable":False,"absolute_path":cpath(p,kind)}
def write_all(fd,b):
 v=memoryview(b);n=0
 while n<len(v):
  q=os.write(fd,v[n:])
  if q<=0:deny("MEMFD_SHORT_WRITE")
  n+=q
def seal(name,b):
 if not hasattr(os,"memfd_create") or not hasattr(os,"MFD_ALLOW_SEALING"):deny("MEMFD_UNAVAILABLE")
 fd=os.memfd_create(name,os.MFD_ALLOW_SEALING)
 write_all(fd,b);os.fsync(fd);st=os.fstat(fd)
 if not stat.S_ISREG(st.st_mode) or st.st_size!=len(b):deny("MEMFD_STATE")
 m=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE;fcntl.fcntl(fd,fcntl.F_ADD_SEALS,m)
 if fcntl.fcntl(fd,fcntl.F_GET_SEALS)&m!=m:deny("MEMFD_SEALS")
 os.lseek(fd,0,0)
 if os.read(fd,len(b)+1)!=b:deny("MEMFD_READBACK")
 os.lseek(fd,0,0);return fd
def main():
 if os.environ.get("CODESPACES")!="true" or not os.environ.get("CODESPACE_NAME"):deny("CODESPACES")
 for k in os.environ:
  if k not in {"CODESPACES","CODESPACE_NAME","LANG","LC_ALL"}:deny("AMBIENT_ENV_"+k.replace("-","_"))
 if not pathlib.Path(R).is_dir():deny("PRE_PYTHON_RECEIPT_ROOT")
 py=simple("/usr/bin/python3"); std=simple("/usr/lib/python3", "dir") if pathlib.Path("/usr/lib/python3").exists() else simple("/usr/lib","dir")
 a={"version":"V19.7.36-v2","trust_class":"C","same_uid_mutable":False,"canonical_main":MAIN,"canonical_tree":TREE,
 "outer_transport":simple("/bin/bash"),"bootstrap_shell":simple("/bin/bash"),"stat_tool":simple("/usr/bin/stat"),"python":py,"python_stdlib":std,
 "loader_roots":simple("/lib","dir"),"ld_cache":simple("/etc/ld.so.cache"),"git":trust_exec("/usr/bin/git"),"gh":trust_exec("/usr/bin/gh"),
 "ca_tls":simple("/etc/ssl/certs","dir"),"environment":{"sanitized":True,"env_i_equivalent":True}}
 b=json.dumps(a,sort_keys=True,separators=(",",":")).encode();fd=seal("mv-v36-v2-attest",b)
 print("PHASE_C_V19_7_36_V2_BOOTSTRAP_ATTESTATION_SEALED",flush=True)
 print("MULTIVERSE_V19_7_36_BOOTSTRAP_ATTEST_FD="+str(fd),flush=True)
 deny("RUNTIME_EXACT_SHA256_SAME_OBJECT_TRANSPORT_NOT_YET_FROZEN")
if __name__=="__main__":
 try:main()
 except SystemExit:raise
 except BaseException as e:deny("TOPLEVEL_"+type(e).__name__.upper())
