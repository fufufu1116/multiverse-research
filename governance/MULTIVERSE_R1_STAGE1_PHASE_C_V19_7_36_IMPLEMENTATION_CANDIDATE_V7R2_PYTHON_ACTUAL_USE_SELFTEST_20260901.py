#!/usr/bin/env python3
import hashlib,json,os,stat,sys
MF='/opt/multiverse/v36/closure-manifest-v7.json'
def die(x):
    print('PHASE_C_V19_7_36_V7R2_PYTHON_BUILD_DENIED:'+x,file=sys.stderr,flush=True);raise SystemExit(92)
def hfile(p):
    h=hashlib.sha256();n=0
    with open(p,'rb',buffering=0) as f:
        for b in iter(lambda:f.read(1<<20),b''):n+=len(b);h.update(b)
    return n,h.hexdigest()
def main():
    f=sys.flags
    if not(f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,'safe_path',False)):die('ISOLATION')
    with open(MF,'rb') as z:m=json.load(z)
    if m.get('version')!='V19.7.36-v7':die('MANIFEST_VERSION')
    idx={x['path']:x for x in m.get('objects',[]) if x.get('type')=='file'}
    sys.path.insert(0,'/opt/multiverse/v36/pydeps')
    try:
        import nacl
        from nacl.public import PrivateKey,SealedBox
        if nacl.__version__!='1.6.2':die('PYNACL_VERSION')
        sk=PrivateKey.generate();msg=b'v7r2-build-actual-use';ct=SealedBox(sk.public_key).encrypt(msg)
        if SealedBox(sk).decrypt(ct)!=msg:die('PYNACL_ROUNDTRIP')
    except SystemExit:raise
    except BaseException as e:die('PYNACL_'+type(e).__name__.upper())
    paths=set()
    for x in sys.modules.values():
        p=getattr(x,'__file__',None)
        if p and os.path.exists(p):paths.add(os.path.realpath(p))
    with open('/proc/self/maps',errors='replace') as z:
        for line in z:
            q=line.rstrip().split(None,5)
            if len(q)==6 and q[5].startswith('/') and os.path.isfile(q[5]):paths.add(os.path.realpath(q[5]))
    paths.discard(os.path.realpath(__file__))
    if not paths:die('NO_ACTUAL_USE_PATHS')
    for p in sorted(paths):
        e=idx.get(p)
        if not e:die('ACTUAL_USE_UNMANIFESTED:'+p)
        st=os.stat(p)
        if st.st_uid!=0 or st.st_mode&0o022 or not stat.S_ISREG(st.st_mode):die('CLASS_C:'+p)
        n,h=hfile(p)
        if n!=e.get('size') or h!=e.get('sha256'):die('IDENTITY:'+p)
    print('PHASE_C_V19_7_36_V7R2_PYTHON_BUILD_ACTUAL_USE_PASS')
if __name__=='__main__':main()
