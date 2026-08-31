#!/usr/bin/env python3
import hashlib,json,os,re,stat,subprocess
OUT='/opt/multiverse/v36/closure-manifest.json'
ROOTS=['/usr/bin/python3','/usr/bin/git','/usr/bin/gh','/bin/false','/etc/ld.so.cache','/etc/ld.so.conf','/etc/ld.so.conf.d','/etc/ssl/certs','/usr/lib/git-core','/usr/lib/python3','/usr/local/lib/python3','/opt/multiverse/v36/pydeps','/opt/multiverse/v36/runtime.py','/opt/multiverse/v36/step3.py','/opt/multiverse/v36/step3-binding.json','/opt/multiverse/v36/build-selftest.py','/usr/local/bin/multiverse-v36-trigger','/usr/local/sbin/multiverse-v36-anchor-producer','/usr/local/sbin/multiverse-v36-control']
def rec_file(p,st):
 h=hashlib.sha256();n=0
 with open(p,'rb',buffering=0) as f:
  while True:
   b=f.read(1<<20)
   if not b:break
   n+=len(b);h.update(b)
 return {'path':p,'type':'file','uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'size':n,'sha256':h.hexdigest()}
def add(p,out,seen=None):
 if seen is None: seen=set()
 if p in seen:return
 seen.add(p)
 if not os.path.lexists(p):return
 st=os.lstat(p)
 if stat.S_ISLNK(st.st_mode):
  target=os.readlink(p)
  out[p]={'path':p,'type':'symlink','target':target,'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode)}
  q=target if os.path.isabs(target) else os.path.normpath(os.path.join(os.path.dirname(p),target))
  add(q,out,seen)
  return
 if stat.S_ISDIR(st.st_mode):
  out[p]={'path':p,'type':'dir','uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode)}
  for root,ds,fs in os.walk(p,followlinks=False):
   for n in sorted(ds+fs): add(os.path.join(root,n),out,seen)
  return
 if not stat.S_ISREG(st.st_mode): raise SystemExit('UNSUPPORTED:'+p)
 out[p]=rec_file(p,st)
def ldd(exe):
 real=os.path.realpath(exe)
 r=subprocess.run(['/usr/bin/ldd',real],text=True,capture_output=True,check=True,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
 ps=[real]
 for line in r.stdout.splitlines():
  for x in re.findall(r'(/[^ ()]+)',line):
   if os.path.lexists(x): ps.append(x)
 return sorted(set(ps))
objs={}
for p in ROOTS:add(p,objs)
for exe in ['/usr/bin/python3','/usr/bin/git','/usr/bin/gh']:
 for p in ldd(exe):add(p,objs)
ep=subprocess.check_output(['/usr/bin/git','--exec-path'],text=True,env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null'}).strip()
add(ep,objs)
for p in ['/etc/gitconfig','/etc/gitattributes','/etc/hosts','/etc/resolv.conf','/etc/nsswitch.conf','/etc/ca-certificates.conf','/etc/ssl/openssl.cnf']:add(p,objs)
m={'version':'V19.7.36-v6','objects':[objs[k] for k in sorted(objs)],'policy':{'symlink_targets_recursive':True,'actual_use_same_object':True,'control_plane_runner':'/usr/local/sbin/multiverse-v36-control','row11':'FROZEN_ACTUAL_SUCCESSOR_RUNNER','row13':'EXACT_STEP3_BYTES_AND_SAME_OBJECT','row14':'POST_OAUTH_ONLY'}}
b=json.dumps(m,sort_keys=True,separators=(',',':')).encode()
with open(OUT,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
os.chown(OUT,0,0);os.chmod(OUT,0o444)
print(hashlib.sha256(b).hexdigest(),len(b))
