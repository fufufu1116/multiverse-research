#!/usr/bin/env python3
import hashlib,json,os,sys
M="/opt/multiverse/v36/closure-manifest.json"
def die(x): raise SystemExit("V36_V6_BUILD_SELFTEST:"+x)
with open(M,"rb") as f: manifest=json.load(f)
idx={x["path"]:x for x in manifest["objects"] if x["type"]=="file"}
sys.path.insert(0,"/opt/multiverse/v36/pydeps")
import nacl
from nacl.public import PrivateKey,SealedBox
if nacl.__version__!="1.6.2": die("PYNACL_VERSION")
sk=PrivateKey.generate();m=b"v36-v6";c=SealedBox(sk.public_key).encrypt(m)
if SealedBox(sk).decrypt(c)!=m: die("PYNACL_ROUNDTRIP")
paths=set()
for mod in list(sys.modules.values()):
 p=getattr(mod,"__file__",None)
 if p:
  p=os.path.realpath(p)
  if p.endswith((".pyc",".pyo")) and "/__pycache__/" in p:
   p=p.rsplit("/__pycache__/",1)[0]+"/"+p.rsplit("/",1)[-1].split(".",1)[0]+".py"
  paths.add(p)
with open("/proc/self/maps","rt",encoding="utf-8",errors="replace") as f:
 for line in f:
  z=line.rstrip().split(None,5)
  if len(z)==6 and z[5].startswith("/") and os.path.isfile(z[5]): paths.add(os.path.realpath(z[5]))
for p in sorted(paths):
 e=idx.get(p)
 if e is None: die("UNMANIFESTED:"+p)
 h=hashlib.sha256()
 with open(p,"rb",buffering=0) as f:
  while True:
   b=f.read(1<<20)
   if not b: break
   h.update(b)
 if h.hexdigest()!=e["sha256"]: die("HASH:"+p)
print("PHASE_C_V19_7_36_V6_BUILD_ACTUAL_USE_SELFTEST_PASS")
