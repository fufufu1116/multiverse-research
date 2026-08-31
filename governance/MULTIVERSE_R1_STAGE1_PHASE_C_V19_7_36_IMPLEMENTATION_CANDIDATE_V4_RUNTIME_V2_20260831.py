#!/usr/bin/env python3
"""V19.7.36 v4 runtime verifier. REVIEW-ONLY / NO LIVE AUTHORITY."""
import hashlib,json,os,stat,sys
RC=92
MAIN="5c1403c1f5aabb80d29e8c868440aede8888ce61"
TREE="3d47741b4863411e5c36cb4c28925ac455ab6441"
AFD="MULTIVERSE_V36_V4_ATTEST_FD"; PFD="MULTIVERSE_V36_V4_PYTHON_FD"; RFD="MULTIVERSE_V36_V4_RUNTIME_FD"
ALLOWED={"CODESPACES","CODESPACE_NAME","LANG","LC_ALL",AFD,PFD,RFD,"HOME","XDG_CONFIG_HOME","GIT_CONFIG_NOSYSTEM","GIT_CONFIG_GLOBAL","GIT_CONFIG_SYSTEM","GIT_TERMINAL_PROMPT","GIT_ASKPASS","SSH_ASKPASS","GH_CONFIG_DIR","GH_BROWSER","GH_PAGER"}
def deny(x): print("PHASE_C_V19_7_36_V4_DENIED:"+x,flush=True); raise SystemExit(RC)
def readall(fd,limit=32<<20):
    os.lseek(fd,0,0); out=[]; n=0
    while True:
        b=os.read(fd,65536)
        if not b: break
        n+=len(b)
        if n>limit: deny("FD_TOO_LARGE")
        out.append(b)
    return b"".join(out)
def readpipe(fd,limit=1<<20):
    out=[]; n=0
    while True:
        b=os.read(fd,65536)
        if not b: break
        n+=len(b)
        if n>limit: deny("ATTEST_TOO_LARGE")
        out.append(b)
    return b"".join(out)
def sha_fd(fd):
    b=readall(fd); return len(b),hashlib.sha256(b).hexdigest()
def parent_root():
    p=os.getppid()
    try: data=open(f"/proc/{p}/status","rb").read()
    except OSError: deny("PARENT_STATUS")
    uid=None
    for line in data.splitlines():
        if line.startswith(b"Uid:"): uid=int(line.split()[1]); break
    if uid!=0: deny("PARENT_NOT_ROOT")
    return p
def env_gate():
    for k in os.environ:
        if k not in ALLOWED: deny("AMBIENT_UNEXPECTED_"+''.join(c if c.isalnum() else '_' for c in k)[:80].upper())
    f=sys.flags
    if not(f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,"safe_path",False)): deny("PYTHON_ISOLATION")
def attest(ppid):
    s=os.environ.get(AFD,"")
    if not s.isdecimal(): deny("ATTEST_FD")
    try: a=json.loads(readpipe(int(s)).decode("utf-8"))
    except Exception: deny("ATTEST_JSON")
    req={"version","source","parent_pid","canonical_main","canonical_tree","base_image_digest","producer","python","runtime","class_c_roots","environment","subprocess","receipts","matrix"}
    if set(a)!=req or a["version"]!="V19.7.36-v4" or a["source"]!="ROOT_IMAGE_ANCHOR_PRODUCER_V4": deny("ATTEST_SCHEMA")
    if a["parent_pid"]!=ppid or a["canonical_main"]!=MAIN or a["canonical_tree"]!=TREE: deny("ATTEST_BINDING")
    for name,ev in (("python",PFD),("runtime",RFD)):
        d=a[name]; s=os.environ.get(ev,"")
        if set(d)!={"class","same_uid_mutable","fd","size","sha256","actual_use_bound"} or d["class"]!="C" or d["same_uid_mutable"] is not False or d["actual_use_bound"] is not True or not s.isdecimal() or int(s)!=d["fd"]: deny("ATTEST_"+name.upper())
        n,h=sha_fd(int(s))
        if n!=d["size"] or h!=d["sha256"]: deny("FD_IDENTITY_"+name.upper())
    if a["environment"]!={"outer_static_producer_clearenv":True,"child_exact_allowlist":True,"dynamic_child_started_after_clearenv":True}: deny("ATTEST_ENV")
    if a["receipts"].get("pre_python_strong") is not True: deny("ATTEST_RECEIPT")
    if set(a["matrix"])!={str(i) for i in range(1,17)}: deny("ATTEST_MATRIX_KEYS")
    return a
def dependency_probe():
    sys.path.insert(0,"/opt/multiverse/v36/pydeps")
    try:
        import nacl
        from nacl.public import PrivateKey,SealedBox
        if getattr(nacl,"__version__",None)!="1.6.2": deny("PYNACL_VERSION")
        sk=PrivateKey.generate(); msg=b"multiverse-v19.7.36-v4"; ct=SealedBox(sk.public_key).encrypt(msg)
        if SealedBox(sk).decrypt(ct)!=msg: deny("PYNACL_ROUNDTRIP")
    except SystemExit: raise
    except BaseException as e: deny("PYNACL_"+type(e).__name__.upper())
def matrix(a):
    evidence=a["matrix"]
    for i in range(1,17):
        d=evidence[str(i)]
        if not isinstance(d,dict) or d.get("mechanically_proven") is not True or not isinstance(d.get("evidence"),str) or not d["evidence"]: deny(f"MATRIX_{i:02d}_EVIDENCE")
    dependency_probe()
    for i in range(1,17): print(f"PHASE_C_V19_7_36_V4_MATRIX_{i:02d}:PASS:{evidence[str(i)]['evidence']}",flush=True)
def main():
    env_gate(); p=parent_root(); a=attest(p); matrix(a)
    print("PHASE_C_V19_7_36_V4_PLATFORM_ANCHOR_PASS",flush=True)
    print("OAUTH_STARTED=false",flush=True); print("PRODUCTION_MUTATION_PERFORMED=false",flush=True); print("RUNTIME_ACTIVATION_PERFORMED=false",flush=True)
    deny("REVIEW_FREEZE_NO_LIVE_AUTHORITY")
if __name__=="__main__":
    try: main()
    except SystemExit: raise
    except BaseException as e: deny("TOPLEVEL_"+type(e).__name__.upper())
