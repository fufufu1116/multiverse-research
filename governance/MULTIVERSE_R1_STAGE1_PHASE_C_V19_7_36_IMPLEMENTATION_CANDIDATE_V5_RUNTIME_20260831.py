#!/usr/bin/env python3
"""V19.7.36 v5 runtime verifier. REVIEW-ONLY / NO LIVE AUTHORITY."""
import hashlib,json,os,stat,sys
RC=92; AFD='MULTIVERSE_V36_V5_ATTEST_FD'; RFD='MULTIVERSE_V36_V5_RUNTIME_FD'; MFD='MULTIVERSE_V36_V5_MANIFEST_FD'
ALLOWED={'CODESPACES','CODESPACE_NAME','LANG','LC_ALL','HOME','XDG_CONFIG_HOME','GIT_CONFIG_NOSYSTEM','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_TERMINAL_PROMPT','GIT_ASKPASS','SSH_ASKPASS','GH_CONFIG_DIR','GH_BROWSER','GH_PAGER','PATH',AFD,RFD,MFD}
def deny(x): print('PHASE_C_V19_7_36_V5_DENIED:'+x,flush=True);raise SystemExit(RC)
def readpipe(fd,lim=16<<20):
 o=[];n=0
 while 1:
  b=os.read(fd,65536)
  if not b:break
  n+=len(b)
  if n>lim:deny('PIPE_TOO_LARGE')
  o.append(b)
 return b''.join(o)
def readfd(fd,lim=128<<20):
 os.lseek(fd,0,0);o=[];n=0
 while 1:
  b=os.read(fd,1<<20)
  if not b:break
  n+=len(b)
  if n>lim:deny('FD_TOO_LARGE')
  o.append(b)
 return b''.join(o)
def env_gate():
 if set(os.environ)-ALLOWED:deny('AMBIENT_UNEXPECTED')
 f=sys.flags
 if not(f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,'safe_path',False)):deny('PYTHON_ISOLATION')
def ident(path,e):
 try: st=os.stat(path,follow_symlinks=True)
 except OSError:deny('OBJECT_MISSING')
 if st.st_uid!=0 or st.st_mode&0o022 or not stat.S_ISREG(st.st_mode):deny('OBJECT_CLASS_C')
 h=hashlib.sha256();n=0
 try:
  with open(path,'rb',buffering=0) as f:
   while 1:
    b=f.read(1<<20)
    if not b:break
    n+=len(b);h.update(b)
 except OSError:deny('OBJECT_READ')
 if n!=e['size'] or h.hexdigest()!=e['sha256']:deny('OBJECT_IDENTITY')
def manifest():
 s=os.environ.get(MFD,'');
 if not s.isdecimal():deny('MANIFEST_FD')
 try:m=json.loads(readfd(int(s)).decode())
 except Exception:deny('MANIFEST_JSON')
 if m.get('version')!='V19.7.36-v5':deny('MANIFEST_VERSION')
 idx={x['path']:x for x in m.get('objects',[]) if x.get('type')=='file'}
 if not idx:deny('MANIFEST_EMPTY')
 return m,idx
def att():
 s=os.environ.get(AFD,'')
 if not s.isdecimal():deny('ATTEST_FD')
 try:a=json.loads(readpipe(int(s)).decode())
 except Exception:deny('ATTEST_JSON')
 if a.get('version')!='V19.7.36-v5' or a.get('source')!='ROOT_IMAGE_ANCHOR_PRODUCER_V5':deny('ATTEST_SCHEMA')
 if a.get('environment')!={'clearenv_before_dynamic_child':True,'fixed_child_env':True}:deny('ATTEST_ENV')
 q=a.get('matrix',{})
 if set(q)!={str(i) for i in range(1,17)}:deny('MATRIX_KEYS')
 for i in range(1,17):
  d=q[str(i)];state=d.get('state');ev=d.get('evidence')
  if not isinstance(ev,str) or not ev:deny(f'MATRIX_{i:02d}_EVIDENCE')
  if i==14:
   if state!='POST_OAUTH_ONLY':deny('MATRIX_14_STATE')
  elif state!='PASS':deny(f'MATRIX_{i:02d}_STATE')
 return a
def used_paths(idx):
 paths=set()
 for m in list(sys.modules.values()):
  p=getattr(m,'__file__',None)
  if p:
   p=os.path.realpath(p)
   if p.endswith(('.pyc','.pyo')):
    p=p.rsplit('/__pycache__/',1)[0]+'/'+p.rsplit('/',1)[-1].split('.',1)[0]+'.py'
   paths.add(p)
 try:
  for line in open('/proc/self/maps','rt',encoding='utf-8',errors='replace'):
   z=line.rstrip().split(None,5)
   if len(z)==6 and z[5].startswith('/') and os.path.isfile(z[5]):paths.add(os.path.realpath(z[5]))
 except OSError:deny('MAPS_READ')
 missing=[]
 for p in sorted(paths):
  e=idx.get(p)
  if e is None:missing.append(p);continue
  ident(p,e)
 if missing:deny('ACTUAL_USE_UNMANIFESTED')
def dependency_probe():
 sys.path.insert(0,'/opt/multiverse/v36/pydeps')
 try:
  import nacl
  from nacl.public import PrivateKey,SealedBox
  if nacl.__version__!='1.6.2':deny('PYNACL_VERSION')
  sk=PrivateKey.generate();msg=b'v36-v5';ct=SealedBox(sk.public_key).encrypt(msg)
  if SealedBox(sk).decrypt(ct)!=msg:deny('PYNACL_ROUNDTRIP')
 except SystemExit:raise
 except BaseException as e:deny('PYNACL_'+type(e).__name__.upper())
def main():
 env_gate();m,idx=manifest();a=att();dependency_probe();used_paths(idx)
 for i in range(1,17):
  d=a['matrix'][str(i)];print(f"PHASE_C_V19_7_36_V5_MATRIX_{i:02d}:{d['state']}:{d['evidence']}",flush=True)
 print('PHASE_C_V19_7_36_V5_PLATFORM_ANCHOR_PASS',flush=True);print('OAUTH_STARTED=false',flush=True);print('RUNTIME_ACTIVATION_PERFORMED=false',flush=True)
 deny('REVIEW_FREEZE_NO_LIVE_AUTHORITY')
if __name__=='__main__':
 try:main()
 except SystemExit:raise
 except BaseException as e:deny('TOPLEVEL_'+type(e).__name__.upper())
