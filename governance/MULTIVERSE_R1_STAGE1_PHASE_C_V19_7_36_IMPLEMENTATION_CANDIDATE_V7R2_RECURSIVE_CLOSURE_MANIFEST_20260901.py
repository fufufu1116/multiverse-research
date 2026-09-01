#!/usr/bin/env python3
import hashlib,json,os,re,stat,subprocess
OUT='/opt/multiverse/v36/closure-manifest-v7.json'
ROOTS=['/usr/bin/python3','/usr/bin/git','/usr/bin/gh','/bin/false','/etc/ld.so.cache','/etc/ld.so.conf','/etc/ld.so.conf.d','/etc/ssl/certs','/usr/lib/git-core','/usr/lib/locale','/usr/lib/x86_64-linux-gnu/gconv','/opt/multiverse/v36/pydeps','/opt/multiverse/v36/runtime-v7.py','/opt/multiverse/v36/step3.py','/opt/multiverse/v36/step3-binding.json','/usr/local/sbin/multiverse-v36-anchor-v7r2','/usr/local/sbin/multiverse-v36-control-v7r2','/usr/local/sbin/multiverse-v36-session-gate-v7r7','/usr/local/bin/multiverse-v36-ui-ready-v7r7','/usr/local/bin/multiverse-v36-arm-v7r7']
RUNTIME_DYNAMIC_NETWORK_PATHS=['/etc/hosts','/etc/resolv.conf']
def python_roots():
 r=subprocess.run(['/usr/bin/python3','-I','-S','-B','-c','import sysconfig;print(sysconfig.get_path("stdlib"));print(sysconfig.get_path("platstdlib"))'],text=True,capture_output=True,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
 if r.returncode!=0:raise SystemExit('PYTHON_STDLIB_DISCOVERY_RC')
 z=[]
 for p in r.stdout.splitlines():
  p=p.strip()
  if p and os.path.isdir(p) and p not in z:z.append(p)
 if not z:raise SystemExit('PYTHON_STDLIB_DISCOVERY_EMPTY')
 return z
ROOTS.extend(python_roots())
def obj(p):
 s=os.lstat(p);base={'path':p,'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode)}
 if stat.S_ISLNK(s.st_mode):return {**base,'type':'symlink','target':os.readlink(p)}
 if stat.S_ISDIR(s.st_mode):return {**base,'type':'dir'}
 if not stat.S_ISREG(s.st_mode):raise SystemExit('UNSUPPORTED:'+p)
 h=hashlib.sha256();n=0
 with open(p,'rb',buffering=0) as f:
  for b in iter(lambda:f.read(1<<20),b''):n+=len(b);h.update(b)
 return {**base,'type':'file','size':n,'sha256':h.hexdigest()}
def add(p,out,q):
 if not os.path.lexists(p) or p in out:return
 out[p]=obj(p)
 if os.path.islink(p):add(os.path.realpath(p),out,q);return
 if os.path.isdir(p):
  for root,ds,fs in os.walk(p,followlinks=False):
   for n in sorted(ds+fs):add(os.path.join(root,n),out,q)
 if os.path.isfile(p):q.append(os.path.realpath(p))
def iself(p):
 try:
  with open(p,'rb') as f:return f.read(4)==b'\x7fELF'
 except OSError:return False
def deps(p):
 r=subprocess.run(['/usr/bin/ldd',p],text=True,capture_output=True,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
 if r.returncode not in (0,1):raise SystemExit('LDD_RC:'+p)
 if 'not found' in r.stdout+r.stderr:raise SystemExit('LDD_UNRESOLVED:'+p)
 z=set()
 for line in (r.stdout+'\n'+r.stderr).splitlines():
  for x in re.findall(r'(/[^ ()]+)',line):
   if os.path.exists(x):z.add(os.path.realpath(x))
 return z
out={};q=[]
for p in ROOTS:add(p,out,q)
seen=set()
while q:
 p=q.pop()
 if p in seen:continue
 seen.add(p)
 if iself(p):
  for d in deps(p):add(d,out,q)
ep=subprocess.check_output(['/usr/bin/git','--exec-path'],text=True,env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null'}).strip();add(ep,out,q)
while q:
 p=q.pop()
 if p in seen:continue
 seen.add(p)
 if iself(p):
  for d in deps(p):add(d,out,q)
for p in ['/etc/gitconfig','/etc/gitattributes','/etc/nsswitch.conf','/etc/ca-certificates.conf','/etc/ssl/openssl.cnf']:add(p,out,q)
m={'version':'V19.7.36-v7','objects':[out[k] for k in sorted(out)],'policy':{'resolved_symlink_targets':True,'recursive_elf_closure':True,'git_exec_path_recursive':ep,'unresolved_elf_forbidden':True,'browser':'/bin/false','row14':'POST_OAUTH_ONLY','owner_trigger':'ATTACH_READY_THEN_EXPLICIT_FIXED_SETUID_ARM','same_uid_in_container_wake_channel':True,'wake_channel_scope':'no-args fixed root launcher only; root O_EXCL arm lock; launcher restores NoNewPrivs before exact fd-bound session gate exec','codespace_creation_starts_600_second_window':False,'locale_actual_use_substrate':'/usr/lib/locale','gconv_actual_use_substrate':'/usr/lib/x86_64-linux-gnu/gconv','python_stdlib_roots':python_roots(),'runtime_dynamic_network_paths_excluded_from_build_identity':RUNTIME_DYNAMIC_NETWORK_PATHS,'runtime_dynamic_network_paths_exclusion_reason':'Docker/Codespaces supplies these per build/runtime; build-time bytes are not stable image-content identity and must not create false cross-build identity drift.'}}
b=json.dumps(m,sort_keys=True,separators=(',',':')).encode();open(OUT,'wb').write(b);os.chown(OUT,0,0);os.chmod(OUT,0o444);print(hashlib.sha256(b).hexdigest(),len(b))
