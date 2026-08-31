#!/usr/bin/env python3
"""V19.7.36 implementation candidate v2 runtime. REVIEW-ONLY / NO LIVE AUTHORITY."""
import fcntl,hashlib,json,os,pathlib,stat,sys
RC=92; FDENV='MULTIVERSE_V19_7_36_BOOTSTRAP_ATTEST_FD'; MAIN='5c1403c1f5aabb80d29e8c868440aede8888ce61'; TREE='3d47741b4863411e5c36cb4c28925ac455ab6441'; R=pathlib.Path('/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v2-receipts')
FORBID={'PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT','LD_DEBUG','GIT_CONFIG','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_CONFIG_COUNT','GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_INDEX_FILE','GIT_CEILING_DIRECTORIES','GIT_EXEC_PATH','GIT_SSH','GIT_SSH_COMMAND','GIT_ASKPASS','SSH_ASKPASS','GIT_EDITOR','GIT_PAGER','PAGER','EDITOR','VISUAL','BROWSER','GH_TOKEN','GITHUB_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN','GH_CONFIG_DIR','GH_HOST','GH_REPO','GH_BROWSER','GH_PAGER','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE','GIT_SSL_CAINFO','GIT_SSL_CAPATH','GIT_SSL_NO_VERIFY','GIT_PROXY_COMMAND','CURL_HOME','NETRC'}
def clean(s): return ''.join(c if c.isalnum() else '_' for c in s)[:80].upper()
def receipt(s):
 try:R.mkdir(mode=0o700)
 except FileExistsError:pass
 except OSError:return
 try:
  st=os.lstat(R)
  if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o700:return
  fd=os.open(R/s,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o400);os.close(fd)
 except OSError:pass
def deny(x):receipt('DENIED_'+x);print('PHASE_C_V19_7_36_V2_DENIED:'+x,flush=True);raise SystemExit(RC)
def readfd(fd,limit=4<<20):
 os.lseek(fd,0,0);o=[];n=0
 while 1:
  b=os.read(fd,65536)
  if not b:break
  n+=len(b)
  if n>limit:deny('ATTEST_TOO_LARGE')
  o.append(b)
 return b''.join(o)
def sealed(fd):
 need=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
 try:got=fcntl.fcntl(fd,fcntl.F_GET_SEALS)
 except OSError:deny('ATTEST_NOT_SEALABLE')
 if not stat.S_ISREG(os.fstat(fd).st_mode) or got&need!=need:deny('ATTEST_NOT_SEALED')
def attest():
 x=os.environ.get(FDENV,'')
 if not x.isdecimal():deny('ATTEST_FD_MISSING')
 fd=int(x);sealed(fd)
 try:a=json.loads(readfd(fd).decode())
 except Exception:deny('ATTEST_JSON')
 req={'version','trust_class','same_uid_mutable','canonical_main','canonical_tree','outer_transport','bootstrap_shell','stat_tool','python','python_stdlib','loader_roots','ld_cache','git','gh','ca_tls','environment'}
 if set(a)!=req or a['version']!='V19.7.36-v2' or a['trust_class'] not in {'B','C'} or a['same_uid_mutable'] is not False:deny('ATTEST_SCHEMA')
 if a['canonical_main']!=MAIN or a['canonical_tree']!=TREE:deny('CANONICAL_BINDING')
 for k in ('outer_transport','bootstrap_shell','stat_tool','python','python_stdlib','loader_roots','ld_cache','git','gh','ca_tls'):
  d=a[k]
  if not isinstance(d,dict) or d.get('class') not in {'B','C'} or d.get('same_uid_mutable') is not False:deny('ATTEST_'+k.upper())
 if a['environment'].get('sanitized') is not True or a['environment'].get('env_i_equivalent') is not True:deny('ATTEST_ENV')
 return a
def isolation():
 f=sys.flags
 if not(f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,'safe_path',False)):deny('PYTHON_ISOLATION')
 allowed={'CODESPACES','CODESPACE_NAME','LANG','LC_ALL',FDENV}
 for k,v in os.environ.items():
  if v and (k in FORBID or k.startswith(('PYTHON','LD_','GIT_CONFIG_','GH_','GITHUB_'))):deny('AMBIENT_'+clean(k))
  if k not in allowed:deny('AMBIENT_UNEXPECTED_'+clean(k))
def memfdprobe():
 if not hasattr(os,'memfd_create') or not hasattr(os,'MFD_ALLOW_SEALING'):deny('MATRIX06_MEMFD')
 fd=-1
 try:
  fd=os.memfd_create('mv-v36-v2',os.MFD_ALLOW_SEALING|getattr(os,'MFD_CLOEXEC',0));p=b'v19.7.36-v2';v=memoryview(p);o=0
  while o<len(v):
   n=os.write(fd,v[o:])
   if n<=0:deny('MATRIX06_SHORT_WRITE')
   o+=n
  os.fsync(fd);st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_size!=len(p):deny('MATRIX06_STATE')
  q=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE;fcntl.fcntl(fd,fcntl.F_ADD_SEALS,q)
  if fcntl.fcntl(fd,fcntl.F_GET_SEALS)&q!=q:deny('MATRIX06_SEALS')
  os.lseek(fd,0,0);g=readfd(fd,1024)
  if g!=p or hashlib.sha256(g).digest()!=hashlib.sha256(p).digest():deny('MATRIX06_READBACK')
 except SystemExit:raise
 except BaseException as e:deny('MATRIX06_'+type(e).__name__.upper())
 finally:
  if fd>=0:
   try:os.close(fd)
   except OSError:pass
def subprocesses(a):
 req={'class','same_uid_mutable','absolute_path','elf_loader','transitive_libraries','loader_authority','helpers','config','credential_helpers','ca_tls','environment','cwd_repo','network_protocol','preexec_drift'}
 for name in ('git','gh'):
  d=a[name]
  if set(d)!=req or d['class'] not in {'B','C'} or d['same_uid_mutable'] is not False or not d['absolute_path'].startswith('/'):deny('SUBPROCESS_'+name.upper())
  for k in req-{'class','same_uid_mutable','absolute_path'}:
   if d[k] not in (True,'FORBIDDEN','ROOT_CONTROLLED','FIXED','DISABLED'):deny('SUBPROCESS_'+name.upper()+'_'+k.upper())
def matrix(a):
 if os.environ.get('CODESPACES')!='true' or not os.environ.get('CODESPACE_NAME'):deny('MATRIX01_CODESPACES')
 if sys.platform!='linux' or os.uname().machine!='x86_64':deny('MATRIX02_PLATFORM')
 try:s=pathlib.Path('/proc/swaps').read_bytes().splitlines()
 except OSError as e:deny('MATRIX03_'+type(e).__name__.upper())
 if len(s)>1:deny('MATRIX03_SWAP')
 if not pathlib.Path('/dev/shm').is_dir():deny('MATRIX04_SHM')
 if not pathlib.Path('/proc/self/fd').is_dir():deny('MATRIX05_PROC')
 memfdprobe()
 rows={1:('PASS','Codespaces class'),2:('PASS','Linux/x86_64/runtime ABI gate'),3:('PASS','zero swap'),4:('PASS','/dev/shm'),5:('PASS','/proc/self/fd'),6:('PASS','memfd/seals/full-write/readback'),7:('PASS','bootstrap inventory sealed attestation'),8:('PASS','sanitized allowlist environment'),9:('PASS','import authority -I -S -B'),10:('BLOCKED','pinned dependency roundtrip successor hook required'),11:('BLOCKED','git actual execution intentionally disabled'),12:('PASS','canonical main/tree exact binding'),13:('BLOCKED','ADMIN/PREFLIGHT/Step3 exact byte bindings required'),14:('POST_OAUTH_ONLY','gh credential-dependent proof; executable trust pre-bound'),15:('PARTIAL','runtime receipt present; pre-Python receipt owned by outer bootstrap'),16:('PARTIAL','outer bootstrap must enforce fresh receipt/root nonexistence')}
 for n,(s,t) in rows.items():print(f'PHASE_C_V19_7_36_V2_MATRIX_{n:02d}:{s}:{t}',flush=True)
 if any(s in {'BLOCKED','PARTIAL'} for s,_ in rows.values()):deny('PRE_OAUTH_MATRIX_INCOMPLETE')
def main():
 a=attest();isolation();subprocesses(a);matrix(a)
 deny('REVIEW_FREEZE_NO_LIVE_AUTHORITY')
if __name__=='__main__':
 try:main()
 except SystemExit:raise
 except BaseException as e:deny('TOPLEVEL_'+type(e).__name__.upper())
