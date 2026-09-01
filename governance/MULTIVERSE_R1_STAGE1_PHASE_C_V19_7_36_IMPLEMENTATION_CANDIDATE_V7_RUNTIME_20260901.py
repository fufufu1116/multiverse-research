#!/usr/bin/env python3
"""V19.7.36 v7 review-only runtime verifier."""
import hashlib,json,os,stat,sys
RC=92
MF='MULTIVERSE_V36_V7_MANIFEST_FD';AF='MULTIVERSE_V36_V7_ATTEST_FD'
def deny(x):print('PHASE_C_V19_7_36_V7_DENIED:'+x,flush=True);raise SystemExit(RC)
def readfd(fd,lim=128<<20):
 os.lseek(fd,0,0);o=[];n=0
 while 1:
  b=os.read(fd,1<<20)
  if not b:break
  n+=len(b)
  if n>lim:deny('FD_TOO_LARGE')
  o.append(b)
 return b''.join(o)
def ident(p,e):
 s=os.stat(p);h=hashlib.sha256();n=0
 if s.st_uid or s.st_mode&0o022 or not stat.S_ISREG(s.st_mode):deny('CLASS_C')
 with open(p,'rb',buffering=0) as f:
  for b in iter(lambda:f.read(1<<20),b''):n+=len(b);h.update(b)
 if n!=e['size'] or h.hexdigest()!=e['sha256']:deny('IDENTITY')
def main():
 f=sys.flags
 if not(f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,'safe_path',False)):deny('PYTHON_ISOLATION')
 try:m=json.loads(readfd(int(os.environ[MF])));a=json.loads(os.read(int(os.environ[AF]),1<<20))
 except Exception:deny('ATTEST_OR_MANIFEST')
 if m.get('version')!='V19.7.36-v7' or a.get('version')!='V19.7.36-v7':deny('VERSION')
 idx={x['path']:x for x in m['objects'] if x.get('type')=='file'}
 sys.path.insert(0,'/opt/multiverse/v36/pydeps')
 try:
  import nacl
  from nacl.public import PrivateKey,SealedBox
  if nacl.__version__!='1.6.2':deny('PYNACL_VERSION')
  sk=PrivateKey.generate();msg=b'v36-v7';ct=SealedBox(sk.public_key).encrypt(msg)
  if SealedBox(sk).decrypt(ct)!=msg:deny('PYNACL_ROUNDTRIP')
 except SystemExit:raise
 except BaseException as e:deny('PYNACL_'+type(e).__name__.upper())
 paths=set()
 for x in sys.modules.values():
  p=getattr(x,'__file__',None)
  if p:paths.add(os.path.realpath(p))
 for line in open('/proc/self/maps',errors='replace'):
  z=line.rstrip().split(None,5)
  if len(z)==6 and z[5].startswith('/') and os.path.isfile(z[5]):paths.add(os.path.realpath(z[5]))
 for p in sorted(paths):
  e=idx.get(p)
  if not e:deny('ACTUAL_USE_UNMANIFESTED')
  ident(p,e)
 print('PHASE_C_V19_7_36_V7_RUNTIME_ACTUAL_USE_PASS',flush=True)
 print('OAUTH_STARTED=false',flush=True);print('RUNTIME_ACTIVATION_PERFORMED=false',flush=True)
 deny('REVIEW_FREEZE_NO_LIVE_AUTHORITY')
if __name__=='__main__':main()
