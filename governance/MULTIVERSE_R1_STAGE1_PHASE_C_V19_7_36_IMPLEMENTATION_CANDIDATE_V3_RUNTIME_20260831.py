#!/usr/bin/env python3
"""V19.7.36 v3 REVIEW-ONLY / NO LIVE AUTHORITY."""
import fcntl,hashlib,json,os,stat,sys
RC=92
MAIN='5c1403c1f5aabb80d29e8c868440aede8888ce61'
TREE='3d47741b4863411e5c36cb4c28925ac455ab6441'
FDENV='MULTIVERSE_V36_ATTEST_FD'
FORBID_PREFIX=('PYTHON','LD_','GIT_','GH_','GITHUB_')
ALLOWED={'CODESPACES','CODESPACE_NAME','LANG','LC_ALL','MULTIVERSE_V36_ATTEST_FD','MULTIVERSE_V36_PLATFORM_ENTRY_FD','MULTIVERSE_V36_PLATFORM_PYTHON_FD','MULTIVERSE_V36_RUNTIME_FD'}
def deny(x): print('PHASE_C_V19_7_36_V3_DENIED:'+x,flush=True); raise SystemExit(RC)
def readall(fd,limit=8<<20):
 os.lseek(fd,0,0); out=[]; n=0
 while True:
  b=os.read(fd,65536)
  if not b: break
  n+=len(b)
  if n>limit: deny('ATTEST_TOO_LARGE')
  out.append(b)
 return b''.join(out)
def sealed(fd):
 need=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
 try: s=fcntl.fcntl(fd,fcntl.F_GET_SEALS); st=os.fstat(fd)
 except OSError: deny('ATTEST_FD_INVALID')
 if not stat.S_ISREG(st.st_mode) or s&need!=need: deny('ATTEST_NOT_SEALED')
def env_gate():
 for k,v in os.environ.items():
  if k not in ALLOWED: deny('AMBIENT_UNEXPECTED_'+''.join(c if c.isalnum() else '_' for c in k)[:80].upper())
  if v and k.startswith(FORBID_PREFIX): deny('AMBIENT_FORBIDDEN_'+k[:80].upper())
 f=sys.flags
 if not(f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,'safe_path',False)): deny('PYTHON_ISOLATION')
def attest():
 s=os.environ.get(FDENV,'')
 if not s.isdecimal(): deny('ATTEST_FD_MISSING')
 fd=int(s); sealed(fd)
 try: a=json.loads(readall(fd).decode('utf-8'))
 except Exception: deny('ATTEST_JSON')
 required={'version','source','canonical_main','canonical_tree','entry','python','runtime','python_runtime','git','gh','browser','ca_tls','environment','matrix','receipts'}
 if set(a)!=required or a['version']!='V19.7.36-v3': deny('ATTEST_SCHEMA')
 if a['source']!='EXTERNAL_PLATFORM_ANCHOR': deny('ATTEST_SOURCE')
 if a['canonical_main']!=MAIN or a['canonical_tree']!=TREE: deny('CANONICAL_BINDING')
 for name in ('entry','python','runtime'):
  d=a[name]
  if set(d)!={'class','same_uid_mutable','fd','sha256','size'}: deny('ATTEST_'+name.upper())
  if d['class']!='A' or d['same_uid_mutable'] is not False or not isinstance(d['fd'],int) or d['fd']<0: deny('ATTEST_'+name.upper())
  if not isinstance(d['sha256'],str) or len(d['sha256'])!=64 or not isinstance(d['size'],int) or d['size']<=0: deny('ATTEST_'+name.upper())
 for n in ('python_runtime','git','gh','browser','ca_tls'):
  d=a[n]
  if not isinstance(d,dict) or d.get('complete') is not True or d.get('same_uid_mutable') is not False or d.get('actual_use_bound') is not True: deny('ATTEST_'+n.upper())
 if a['environment']!={'env_i_from_outermost':True,'ambient_authority_denied':True}: deny('ATTEST_ENVIRONMENT')
 if a['matrix'].get('rows')!=16 or a['matrix'].get('all_pre_oauth_proven') is not True: deny('ATTEST_MATRIX')
 if a['receipts'].get('pre_python') is not True or a['receipts'].get('runtime_stage_specific') is not True: deny('ATTEST_RECEIPTS')
 return a
def fd_identity(fd,expected):
 sealed(fd)
 b=readall(fd)
 if len(b)!=expected['size'] or hashlib.sha256(b).hexdigest()!=expected['sha256']: deny('FD_IDENTITY_MISMATCH')
def main():
 env_gate(); a=attest()
 for key,envname in (('entry','MULTIVERSE_V36_PLATFORM_ENTRY_FD'),('python','MULTIVERSE_V36_PLATFORM_PYTHON_FD'),('runtime','MULTIVERSE_V36_RUNTIME_FD')):
  v=os.environ.get(envname,'')
  if not v.isdecimal() or int(v)!=a[key]['fd']: deny('FD_NUMBER_BINDING_'+key.upper())
  fd_identity(int(v),a[key])
 print('PHASE_C_V19_7_36_V3_EXTERNAL_PLATFORM_ANCHOR_PASS',flush=True)
 for i in range(1,17): print(f'PHASE_C_V19_7_36_V3_MATRIX_{i:02d}:PASS',flush=True)
 print('OAUTH_STARTED=false',flush=True)
 print('PRODUCTION_MUTATION_PERFORMED=false',flush=True)
 print('RUNTIME_ACTIVATION_PERFORMED=false',flush=True)
 deny('REVIEW_FREEZE_NO_LIVE_AUTHORITY')
if __name__=='__main__':
 try: main()
 except SystemExit: raise
 except BaseException as e: deny('TOPLEVEL_'+type(e).__name__.upper())
