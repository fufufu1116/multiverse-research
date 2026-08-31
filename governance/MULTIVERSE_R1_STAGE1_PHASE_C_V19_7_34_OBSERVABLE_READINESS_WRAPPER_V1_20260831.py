#!/usr/bin/env python3
import hashlib, os, stat, subprocess, sys
PY='/usr/local/python/current/bin/python'
ROOT='/dev/shm/multiverse-r1-stage1-phase-c-v19-7-34-review'
TARGET=ROOT+'/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_34_PRE_OAUTH_SEALED_DEPENDENCY_READINESS_V1_20260831.py'
TARGET_BLOB='0b616ee9835e323a9d5b45faae00dbfd902e1753'
RESULT_DIR='/dev/shm/multiverse-r1-stage1-phase-c-v19-7-34-readiness-result'
FALLBACK_DIR='/dev/shm/multiverse-r1-stage1-phase-c-v19-7-34-readiness-receipt-failure'
RESULT_NAME='result.txt'

def git_blob(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def write_all(fd,data):
    view=memoryview(data)
    while view:
        n=os.write(fd,view)
        if n<=0: raise OSError('short write')
        view=view[n:]
def memory_fs(path):
    cp=subprocess.run(['/usr/bin/stat','-f','-c','%T',path],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    return cp.returncode==0 and cp.stdout.strip() in {'tmpfs','ramfs'}
def persist_at(dirpath,line):
    data=(line+'\n').encode('utf-8')
    if not memory_fs('/dev/shm'): raise OSError('devshm not memory fs')
    os.mkdir(dirpath,0o700); ds=os.lstat(dirpath)
    if not stat.S_ISDIR(ds.st_mode) or ds.st_uid!=os.geteuid() or stat.S_IMODE(ds.st_mode)!=0o700: raise OSError('result dir trust')
    path=dirpath+'/'+RESULT_NAME; flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0); fd=os.open(path,flags,0o600)
    try:
        write_all(fd,data); os.fsync(fd); rs=os.fstat(fd)
        if not stat.S_ISREG(rs.st_mode) or rs.st_uid!=os.geteuid() or rs.st_nlink!=1 or stat.S_IMODE(rs.st_mode)!=0o600: raise OSError('result file trust')
    finally: os.close(fd)
    rf=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        got=os.read(rf,len(data)+1)
        if got!=data or os.read(rf,1)!=b'': raise OSError('result verify')
    finally: os.close(rf)
def receipt_failure(reason):
    line='PHASE_C_V19_7_34_RECEIPT_FAILURE:'+reason; print(line,flush=True)
    try: persist_at(FALLBACK_DIR,line)
    except Exception as e: print('PHASE_C_V19_7_34_FALLBACK_RECEIPT_FAILURE:'+type(e).__name__,flush=True)
    return 93
def finish(line,rc):
    print(line,flush=True)
    try: persist_at(RESULT_DIR,line)
    except Exception as e: return receipt_failure(type(e).__name__)
    return rc
def read_target_once():
    fd=os.open(TARGET,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_nlink!=1: raise OSError('target trust')
        chunks=[]; total=0
        while True:
            b=os.read(fd,1048576)
            if not b: break
            chunks.append(b); total+=len(b)
            if total>1048576: raise OSError('target size')
        data=b''.join(chunks)
    finally: os.close(fd)
    if git_blob(data)!=TARGET_BLOB: raise OSError('target blob')
    return data
def main():
    if os.environ.get('CODESPACES')!='true' or not os.environ.get('CODESPACE_NAME'): return finish('PHASE_C_V19_7_34_DENIED:CODESPACES',92)
    if os.path.lexists(RESULT_DIR): return receipt_failure('RESULT_DIR_PREEXISTS')
    if os.path.lexists(FALLBACK_DIR): print('PHASE_C_V19_7_34_FALLBACK_RECEIPT_DIR_PREEXISTS',flush=True); return 93
    try: target=read_target_once()
    except Exception as e: return finish('PHASE_C_V19_7_34_DENIED:TARGET_'+type(e).__name__,92)
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','CODESPACES':os.environ['CODESPACES'],'CODESPACE_NAME':os.environ['CODESPACE_NAME']}
    loader='import sys; d=sys.stdin.buffer.read(); exec(compile(d,"<v19.7.34-readiness-exact-same-memory>","exec"),{"__name__":"__main__"})'
    cp=subprocess.run([PY,'-I','-S','-B','-c',loader],input=target,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    out=cp.stdout.decode('utf-8','replace')
    if out: print(out,end='' if out.endswith('\n') else '\n',flush=True)
    if cp.returncode:
        reason=''
        for line in out.splitlines():
            if line.startswith('PHASE_C_V19_7_34_READINESS_DENIED:'): reason=line
        return finish(reason or f'PHASE_C_V19_7_34_DENIED:UNKNOWN_RC_{cp.returncode}',92)
    if 'PHASE_C_V19_7_34_PRE_OAUTH_READINESS_PASS' not in out.splitlines(): return finish('PHASE_C_V19_7_34_DENIED:PASS_MARKER_MISSING',92)
    return finish('PHASE_C_V19_7_34_PRE_OAUTH_READINESS_PASS',0)
if __name__=='__main__': raise SystemExit(main())
