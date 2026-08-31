#!/usr/bin/env python3
"""V19.7.36 implementation candidate v1. REVIEW-ONLY / NONCANONICAL / NO LIVE AUTHORITY.

This candidate implements the authenticated-runtime policy layer after an outer
bootstrap has established a Class B/C Python execution substrate. It MUST fail
closed when invoked without the bootstrap attestation contract below. It does
not start OAuth or execute Step3/Step4/apply.
"""
import fcntl, hashlib, json, os, pathlib, stat, sys

RC=92
ROOT=pathlib.Path('/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36')
ATTEST_FD_ENV='MULTIVERSE_V19_7_36_BOOTSTRAP_ATTEST_FD'
EXPECTED_MAIN='5c1403c1f5aabb80d29e8c868440aede8888ce61'
EXPECTED_MAIN_TREE='3d47741b4863411e5c36cb4c28925ac455ab6441'


def deny(reason):
    print('PHASE_C_V19_7_36_IMPLEMENTATION_DENIED:'+reason, flush=True)
    raise SystemExit(RC)


def read_fd_exact(fd, limit=1048576):
    os.lseek(fd,0,os.SEEK_SET); out=[]; n=0
    while True:
        b=os.read(fd,65536)
        if not b: break
        n+=len(b)
        if n>limit: deny('BOOTSTRAP_ATTEST_TOO_LARGE')
        out.append(b)
    return b''.join(out)


def require_sealed_fd(fd):
    need=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
    try: got=fcntl.fcntl(fd,fcntl.F_GET_SEALS)
    except OSError: deny('BOOTSTRAP_ATTEST_NOT_SEALABLE')
    if got & need != need: deny('BOOTSTRAP_ATTEST_NOT_SEALED')
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode): deny('BOOTSTRAP_ATTEST_NOT_REGULAR')


def bootstrap_attestation():
    raw=os.environ.get(ATTEST_FD_ENV,'')
    if not raw.isdecimal(): deny('BOOTSTRAP_ATTEST_FD_MISSING')
    fd=int(raw); require_sealed_fd(fd); data=read_fd_exact(fd)
    try: a=json.loads(data.decode('utf-8'))
    except Exception: deny('BOOTSTRAP_ATTEST_JSON')
    required={'version','class','python','python_sha256','loader','loader_sha256','shared_libraries','outer_transport','outer_transport_sha256','same_uid_mutable','canonical_main','canonical_tree'}
    if set(a)!=required: deny('BOOTSTRAP_ATTEST_SCHEMA')
    if a['version']!='V19.7.36-v1': deny('BOOTSTRAP_ATTEST_VERSION')
    if a['class'] not in {'B','C'}: deny('BOOTSTRAP_TRUST_CLASS')
    if a['same_uid_mutable'] is not False: deny('BOOTSTRAP_SAME_UID_MUTABLE')
    if a['canonical_main']!=EXPECTED_MAIN or a['canonical_tree']!=EXPECTED_MAIN_TREE: deny('CANONICAL_BINDING')
    for k in ('python','loader','outer_transport'):
        if not isinstance(a[k],str) or not a[k].startswith('/'): deny('BOOTSTRAP_PATH_'+k.upper())
    for k in ('python_sha256','loader_sha256','outer_transport_sha256'):
        v=a[k]
        if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v): deny('BOOTSTRAP_DIGEST_'+k.upper())
    libs=a['shared_libraries']
    if not isinstance(libs,list) or not libs: deny('BOOTSTRAP_SHARED_LIBRARY_EMPTY')
    for x in libs:
        if set(x)!={'path','sha256','class'} or x['class'] not in {'B','C'} or not x['path'].startswith('/') or len(x['sha256'])!=64: deny('BOOTSTRAP_SHARED_LIBRARY_SCHEMA')
    return a


def isolation_gate():
    f=sys.flags
    if not (f.isolated and f.no_site and f.ignore_environment and f.no_user_site and getattr(f,'safe_path',False)): deny('PYTHON_ISOLATION_REQUIRED')
    forbidden=('PYTHONPATH','PYTHONHOME','LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_ASKPASS','SSH_ASKPASS','GH_CONFIG_DIR','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','SSL_CERT_FILE','SSL_CERT_DIR')
    for k in forbidden:
        if os.environ.get(k): deny('AMBIENT_ENV_'+k)


def memfd_probe():
    if not hasattr(os,'memfd_create') or not hasattr(os,'MFD_ALLOW_SEALING'): deny('PRE_OAUTH_MEMFD_UNAVAILABLE')
    fd=os.memfd_create('multiverse-v19-7-36-probe',os.MFD_ALLOW_SEALING|getattr(os,'MFD_CLOEXEC',0))
    try:
        b=b'v19.7.36'; os.write(fd,b)
        seals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
        fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
        if fcntl.fcntl(fd,fcntl.F_GET_SEALS)&seals!=seals: deny('PRE_OAUTH_MEMFD_SEALS')
        os.lseek(fd,0,os.SEEK_SET)
        if os.read(fd,len(b))!=b: deny('PRE_OAUTH_MEMFD_READBACK')
    finally: os.close(fd)


def platform_nonmutating_checks():
    if os.environ.get('CODESPACES')!='true' or not os.environ.get('CODESPACE_NAME'): deny('CODESPACES')
    if sys.platform!='linux': deny('PLATFORM')
    try: swaps=pathlib.Path('/proc/swaps').read_bytes().splitlines()
    except OSError: deny('PRE_OAUTH_SWAP_READ')
    if len(swaps)>1: deny('PRE_OAUTH_ACTIVE_SWAP')
    if not pathlib.Path('/proc/self/fd').is_dir(): deny('PRE_OAUTH_PROC_FD')
    memfd_probe()


def subprocess_policy_manifest():
    # No subprocess is executed by this v1 candidate. A successor Live operator
    # must supply a frozen full-closure manifest and Class A/B/C use proof for
    # every git/gh/helper executable before this gate can be removed.
    return {
      'git': {'allowed':False,'reason':'FULL_SUBPROCESS_TRUST_CLOSURE_NOT_YET_FROZEN'},
      'gh': {'allowed':False,'reason':'FULL_SUBPROCESS_TRUST_CLOSURE_NOT_YET_FROZEN'},
      'browser': {'allowed':False,'reason':'FULL_SUBPROCESS_TRUST_CLOSURE_NOT_YET_FROZEN'}
    }


def main():
    a=bootstrap_attestation(); isolation_gate(); platform_nonmutating_checks()
    policy=subprocess_policy_manifest()
    if any(v['allowed'] for v in policy.values()): deny('SUBPROCESS_POLICY_UNEXPECTED_ALLOW')
    print('PHASE_C_V19_7_36_AUTHENTICATED_RUNTIME_POLICY_PASS',flush=True)
    print('PHASE_C_V19_7_36_SUBPROCESS_POLICY_FAIL_CLOSED',flush=True)
    print('OAUTH_STARTED=false',flush=True)
    print('PRODUCTION_MUTATION_PERFORMED=false',flush=True)
    print('RUNTIME_ACTIVATION_PERFORMED=false',flush=True)
    # Deliberate implementation-freeze blocker: until the outer bootstrap and
    # full git/gh closure are concrete reviewed artifacts, this candidate is
    # not Live-capable and must terminate nonzero.
    deny('SUCCESSOR_BOOTSTRAP_AND_SUBPROCESS_CLOSURE_NOT_IMPLEMENTED')

if __name__=='__main__':
    try: main()
    except SystemExit: raise
    except BaseException as e: deny('TOPLEVEL_'+type(e).__name__.upper())
