#!/usr/bin/env python3
import hashlib,json,os,re,stat,subprocess,sys
OUT='/opt/multiverse/v36/closure-manifest.json'
ROOTS=['/usr/bin/python3','/usr/bin/git','/usr/bin/gh','/bin/false','/etc/ld.so.cache','/etc/ld.so.conf','/etc/ld.so.conf.d','/etc/ssl/certs','/usr/lib/git-core','/usr/lib/python3','/usr/local/lib/python3','/opt/multiverse/v36/pydeps','/opt/multiverse/v36/runtime.py','/opt/multiverse/v36/step3-binding.json','/usr/local/bin/multiverse-v36-trigger','/usr/local/sbin/multiverse-v36-anchor-producer']

def one(p):
 st=os.lstat(p)
 if stat.S_ISLNK(st.st_mode): return {'path':p,'type':'symlink','target':os.readlink(p),'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode)}
 if stat.S_ISDIR(st.st_mode): return {'path':p,'type':'dir','uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode)}
 if not stat.S_ISREG(st.st_mode): raise SystemExit('UNSUPPORTED:'+p)
 h=hashlib.sha256(); n=0
 with open(p,'rb',buffering=0) as f:
  while True:
   b=f.read(1<<20)
   if not b: break
   n+=len(b); h.update(b)
 return {'path':p,'type':'file','uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'size':n,'sha256':h.hexdigest()}

def walk(p,out):
 if not os.path.lexists(p): return
 out[p]=one(p)
 if os.path.isdir(p) and not os.path.islink(p):
  for root,ds,fs in os.walk(p,followlinks=False):
   for n in sorted(ds+fs):
    q=os.path.join(root,n)
    if q not in out: out[q]=one(q)

def ldd(exe):
 r=subprocess.run(['/usr/bin/ldd',exe],text=True,capture_output=True,check=True,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
 ps=[]
 for line in r.stdout.splitlines():
  for x in re.findall(r'(/[^ ()]+)',line):
   if os.path.exists(x): ps.append(os.path.realpath(x))
 return sorted(set(ps))

objs={}
for p in ROOTS: walk(p,objs)
for exe in ['/usr/bin/python3','/usr/bin/git','/usr/bin/gh']:
 for p in ldd(exe): walk(p,objs)
try:
 ep=subprocess.check_output(['/usr/bin/git','--exec-path'],text=True,env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null'}).strip()
 walk(ep,objs)
except Exception as e: raise SystemExit('GIT_EXEC_PATH:'+type(e).__name__)
for p in ['/etc/gitconfig','/etc/gitattributes','/etc/hosts','/etc/resolv.conf','/etc/nsswitch.conf','/etc/ca-certificates.conf','/etc/ssl/openssl.cnf']:
 walk(p,objs)
manifest={'version':'V19.7.36-v5','objects':[objs[k] for k in sorted(objs)],'policy':{'same_uid_mutable':False,'loader_search_env':'cleared','git_env':'frozen','gh_env':'frozen','browser_pre_oauth':'/bin/false','row14':'POST_OAUTH_ONLY'}}
b=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
os.chown(OUT,0,0);os.chmod(OUT,0o444)
print(hashlib.sha256(b).hexdigest(),len(b))
