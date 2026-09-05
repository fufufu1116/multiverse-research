#!/usr/bin/env python3
import errno, hashlib, importlib.util, os, pathlib, shutil, signal, subprocess, time

BASE='/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R21_RETAINED_ACCESS_SELFTEST_20260904.py'
spec=importlib.util.spec_from_file_location('v7r21_retained',BASE)
R=importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

PROD_GUARD='/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r21'
CI_GUARD='/tmp/v7r21-guard-tracer-selftest'
CI_STABLE_HELPER='/tmp/v7r21-helper-stable-birth-selftest'
CI_STABLE_GUARD='/tmp/v7r21-guard-stable-birth-selftest'
CI_BIRTH_PREFIX='/tmp/v7r21-ci-birth-proof-'


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def run(*args):
    subprocess.run(list(args),check=True)


def regenerate_production_sources():
    g='/src/governance/'
    shutil.copyfile(g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R16_POST_AUTH_CREDENTIAL_DROP_GUARD_20260904.go','/tmp/v7r16-guard.go')
    shutil.copyfile(g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_20260901.go','/tmp/v7r7-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R18_HELPER_CREDENTIAL_CONTRACT_PATCHER_20260904.py','/tmp/v7r16-guard.go','/tmp/v7r7-helper.go','/tmp/v7r18-guard.go','/tmp/v7r18-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R19_WHOLE_PROCESS_CREDENTIAL_DROP_PATCHER_20260904.py','/tmp/v7r18-guard.go','/tmp/v7r18-helper.go','/tmp/v7r19-guard.go','/tmp/v7r19-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R20_MIXED_TRANSITION_RACE_PATCHER_20260904.py','/tmp/v7r19-guard.go','/tmp/v7r19-helper.go','/tmp/v7r20-guard.go','/tmp/v7r20-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R21_NEW_THREAD_REGAIN_PATCHER_20260904.py','/tmp/v7r20-guard.go','/tmp/v7r20-helper.go','/tmp/v7r21-guard.go','/tmp/v7r21-helper.go')
    run('gofmt','-w','/tmp/v7r21-guard.go','/tmp/v7r21-helper.go')


def bind_guard_helper_hash(helper_sha):
    p=pathlib.Path('/tmp/v7r21-guard.go'); s=p.read_text(encoding='utf-8')
    if s.count('__V7R21_HELPER_SHA256__')!=1: raise SystemExit('guard helper hash placeholder topology changed')
    s=s.replace('__V7R21_HELPER_SHA256__',helper_sha,1); p.write_text(s,encoding='utf-8'); run('gofmt','-w',str(p))


def build_exact_ci_guard_copy():
    regenerate_production_sources()
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o','/tmp/ui-ready-v7r21','/tmp/v7r21-helper.go')
    helper_sha=sha('/tmp/ui-ready-v7r21')
    if helper_sha!=sha(R.HELPER): raise SystemExit('CI regenerated helper does not byte-match production helper')
    bind_guard_helper_hash(helper_sha)
    p=pathlib.Path('/tmp/v7r21-guard.go')
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o','/tmp/ui-ready-env-guard-v7r21',str(p))
    if sha('/tmp/ui-ready-env-guard-v7r21')!=sha(PROD_GUARD): raise SystemExit('CI regenerated guard does not byte-match production guard')

    s=p.read_text(encoding='utf-8')
    anchor='\tif err != nil {\n\t\tdeny("PROTECTED_CREDENTIAL_BOUNDARY")\n\t}\n'
    if s.count(anchor)!=1: raise SystemExit('guard protected-boundary anchor changed')
    injected=anchor+'\tif err := syscall.Kill(syscall.Getpid(), syscall.SIGSTOP); err != nil { deny("CI_TRACER_STOP") }\n'
    ci=s.replace(anchor,injected,1)
    if ci.replace('\tif err := syscall.Kill(syscall.Getpid(), syscall.SIGSTOP); err != nil { deny("CI_TRACER_STOP") }\n','',1)!=s:
        raise SystemExit('CI guard differs by more than exact stop line')
    p.write_text(ci,encoding='utf-8'); run('gofmt','-w',str(p))
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o',CI_GUARD,str(p))
    os.chown(CI_GUARD,0,0); os.chmod(CI_GUARD,0o555)
    print('PRELAB_V7R21_CI_GUARD_REGENERATED_PRODUCTION_MATCH=true')
    print('PRELAB_V7R21_CI_GUARD_ONLY_DIFF=ONE_UNCONDITIONAL_SIGSTOP_AFTER_PROTECTED_TRACER_GATE')


def build_stable_birth_proof_pair():
    regenerate_production_sources()
    helper=pathlib.Path('/tmp/v7r21-helper.go'); prod_helper_src=helper.read_text(encoding='utf-8')
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o','/tmp/v7r21-helper-production-recheck',str(helper))
    if sha('/tmp/v7r21-helper-production-recheck')!=sha(R.HELPER): raise SystemExit('stable-proof regenerated helper does not byte-match production helper')

    anchor='\t\t\tready<-proof{tid,e}; <-release; runtime.UnlockOSThread(); wg.Done()\n'
    if prod_helper_src.count(anchor)!=1: raise SystemExit('stable birth helper anchor changed')
    barrier=r'''\t\t\tif e==nil {
\t\t\t\tpath:=fmt.Sprintf("/tmp/v7r21-ci-birth-proof-%d",tid)
\t\t\t\t_ = syscall.Unlink(path)
\t\t\t\tif be:=syscall.Mkfifo(path,0600); be!=nil { e=fmt.Errorf("ci-birth-proof-mkfifo-%d:%v",tid,be) } else {
\t\t\t\t\tfd,be:=syscall.Open(path,syscall.O_RDONLY,0)
\t\t\t\t\tif be!=nil { e=fmt.Errorf("ci-birth-proof-open-%d:%v",tid,be) } else {
\t\t\t\t\t\tvar ack [8]byte; n,re:=syscall.Read(fd,ack[:]); _=syscall.Close(fd); _=syscall.Unlink(path)
\t\t\t\t\t\tif re!=nil || string(ack[:n])!="release\\n" { e=fmt.Errorf("ci-birth-proof-ack-%d-n-%d-err-%v",tid,n,re) }
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
'''
    ci_helper_src=prod_helper_src.replace(anchor,barrier+anchor,1)
    if ci_helper_src.replace(barrier,'',1)!=prod_helper_src: raise SystemExit('CI stable helper differs by more than exact FIFO barrier block')
    helper.write_text(ci_helper_src,encoding='utf-8'); run('gofmt','-w',str(helper))
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o',CI_STABLE_HELPER,str(helper))
    os.chown(CI_STABLE_HELPER,0,0); os.chmod(CI_STABLE_HELPER,0o555)
    ci_helper_sha=sha(CI_STABLE_HELPER)

    guard=pathlib.Path('/tmp/v7r21-guard.go'); prod_guard_src=guard.read_text(encoding='utf-8')
    helper_path='/usr/local/bin/multiverse-v36-ui-ready-v7r21'
    if prod_guard_src.count(helper_path)!=1: raise SystemExit('stable guard helper path topology changed')
    ci_guard_src=prod_guard_src.replace(helper_path,CI_STABLE_HELPER,1)
    guard.write_text(ci_guard_src,encoding='utf-8')
    bind_guard_helper_hash(ci_helper_sha)
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o',CI_STABLE_GUARD,str(guard))
    os.chown(CI_STABLE_GUARD,0,0); os.chmod(CI_STABLE_GUARD,0o555)
    final_guard_src=guard.read_text(encoding='utf-8')
    normalized=final_guard_src.replace(CI_STABLE_HELPER,helper_path,1).replace(ci_helper_sha,'__V7R21_HELPER_SHA256__',1)
    if normalized!=prod_guard_src: raise SystemExit('CI stable guard differs beyond helper path/hash binding')
    print('PRELAB_V7R21_CI_STABLE_HELPER_PRODUCTION_SOURCE_REGENERATED_MATCH=true')
    print('PRELAB_V7R21_CI_STABLE_HELPER_ONLY_DIFF=POSTDROP_LOCKED_WORKER_FIFO_ACK_BARRIER')
    print('PRELAB_V7R21_CI_STABLE_GUARD_ONLY_DIFF=CI_HELPER_PATH_AND_EXACT_HASH_BINDING')
    print(f'PRELAB_V7R21_CI_STABLE_HELPER_SHA256={ci_helper_sha}')


def stable_fifo_tids():
    out=set()
    for p in pathlib.Path('/tmp').glob('v7r21-ci-birth-proof-*'):
        try: out.add(int(p.name.rsplit('-',1)[1]))
        except ValueError: raise SystemExit(f'CI birth FIFO malformed:{p}')
    return out


def enable_stable_birth_observer():
    base_task_states=R.task_states
    base_prove=R.prove_nondumpable_ptrace_denial
    def stable_task_states(pid):
        states=base_task_states(pid); stable=stable_fifo_tids()
        return {tid:s for tid,s in states.items() if tid in stable}
    def stable_prove_and_release(pid,tid,expected,uid):
        path=f'{CI_BIRTH_PREFIX}{tid}'
        if not os.path.exists(path): raise SystemExit(f'AMBIGUOUS_CI_STABLE_BIRTH_BARRIER_ABSENT:tid={tid}')
        er=base_prove(pid,tid,expected,uid)
        if not os.path.exists(path): raise SystemExit(f'AMBIGUOUS_CI_STABLE_BIRTH_BARRIER_VANISHED_BEFORE_ACK:tid={tid}')
        try:
            fd=os.open(path,os.O_WRONLY)
            try:
                n=os.write(fd,b'release\n')
                if n!=8: raise SystemExit(f'AMBIGUOUS_CI_STABLE_BIRTH_ACK_SHORT_WRITE:tid={tid}:n={n}')
            finally: os.close(fd)
        except OSError as e:
            raise SystemExit(f'AMBIGUOUS_CI_STABLE_BIRTH_ACK_FAILED:tid={tid}:errno={e.errno}')
        print(f'PRELAB_V7R21_CI_STABLE_PER_BIRTH_ACK_RELEASED_TID={tid}')
        return er
    R.task_states=stable_task_states
    R.prove_nondumpable_ptrace_denial=stable_prove_and_release


_base_configure=R.configure_base
def configure_ci_guard():
    _base_configure(); build_exact_ci_guard_copy()
    old=PROD_GUARD
    if R.M.LAUNCHER_C.count(old)!=1: raise SystemExit('launcher guard path topology changed')
    R.M.LAUNCHER_C=R.M.LAUNCHER_C.replace(old,CI_GUARD,1)
R.configure_base=configure_ci_guard


def uid_tuple(pid):
    try:
        for line in open(f'/proc/{pid}/status',encoding='utf-8'):
            if line.startswith('Uid:'):
                v=tuple(map(int,line.split()[1:5])); return v if len(v)==4 else None
    except (FileNotFoundError,PermissionError,ProcessLookupError): return None
    return None


def wait_stop(pid,seconds):
    end=time.time()+seconds
    while time.time()<end:
        try: wp,status=os.waitpid(pid,os.WUNTRACED|os.WNOHANG)
        except ChildProcessError:return None
        if wp==pid:return status
        time.sleep(0.001)
    return None


def protected_preattached_tracer_fail_closed(uid,gid):
    fd=R.M.make_authority()
    def child_ids():
        os.setgroups([]); os.setresgid(gid,gid,gid); os.setresuid(uid,uid,uid)
    p=subprocess.Popen(['/tmp/v7r20-launcher',R.NAME,str(fd),R.M.GEN],env={'CODESPACES':'true','CODESPACE_NAME':R.NAME},pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,preexec_fn=child_ids)
    try:
        status=wait_stop(p.pid,2.0)
        if status is None or not os.WIFSTOPPED(status) or os.WSTOPSIG(status)!=signal.SIGSTOP: raise SystemExit(f'CI guard protected-stop not observed:{status}')
        try: attach_exe=os.readlink(f'/proc/{p.pid}/exe')
        except OSError: attach_exe='UNKNOWN'
        if attach_exe!=CI_GUARD: raise SystemExit(f'CI stop occurred outside guard:{attach_exe}')
        u=uid_tuple(p.pid)
        if u is None or u[1:]!=(R.AUTH_UID,R.AUTH_UID,R.AUTH_UID): raise SystemExit(f'CI guard protected-stop credential mismatch:{u}')
        rv,er=R.M.ptrace(R.M.PTRACE_ATTACH,p.pid)
        if rv!=0: raise SystemExit(f'guard-post-tracer-gate attach failed:{er}')
        os.kill(p.pid,signal.SIGCONT)
        status=wait_stop(p.pid,1.0)
        if status is None or not os.WIFSTOPPED(status): raise SystemExit(f'ptrace attach-stop not observed:{status}')
        seen_helper=False; deadline=time.time()+4
        while time.time()<deadline:
            try:
                if os.readlink(f'/proc/{p.pid}/exe')==R.HELPER: seen_helper=True
            except OSError:pass
            rv,er=R.M.ptrace(R.PTRACE_CONT,p.pid)
            if rv!=0:
                if er==errno.ESRCH:break
                raise SystemExit(f'ptrace cont failed:{er}')
            try:_,status=os.waitpid(p.pid,0)
            except ChildProcessError:break
            try:
                if os.readlink(f'/proc/{p.pid}/exe')==R.HELPER: seen_helper=True
            except OSError:pass
            if os.WIFEXITED(status) or os.WIFSIGNALED(status):break
        text=p.stdout.read() or ''
        try:p.wait(timeout=1)
        except subprocess.TimeoutExpired:p.kill(); p.wait(timeout=1)
    finally:os.close(fd)
    denied='PHASE_C_V19_7_36_V7R21_HELPER_DENIED:PROTECTED_STARTUP:tracer-present' in text
    dropped='V7R21_IRREVERSIBLE_USER_DROP_COMPLETE' in text
    if not seen_helper: raise SystemExit('post-guard-gate tracer did not reach production helper image')
    if not denied: raise SystemExit('production helper did not fail closed on retained tracer')
    if dropped: raise SystemExit('retained tracer crossed irreversible user-drop boundary')
    print(text,end='')
    print('PRELAB_V7R21_PREATTACHED_TRACER_ATTEMPTS=1')
    print('PRELAB_V7R21_PREATTACHED_TRACER_PROTECTED_UID_OBSERVED=true')
    print('PRELAB_V7R21_PREATTACHED_TRACER_CI_ONLY_PROTECTED_STOP=true')
    print('PRELAB_V7R21_PREATTACHED_TRACER_GUARD_TRACER_GATE_ALREADY_PASSED=true')
    print(f'PRELAB_V7R21_PREATTACHED_TRACER_ATTACH_EXE={attach_exe}')
    print('PRELAB_V7R21_PREATTACHED_TRACER_REACHED_HELPER=true')
    print('PRELAB_V7R21_PREATTACHED_TRACER_EXACT_BOUNDARY_RESULT=FAIL_CLOSED_TRACER_PRESENT_BEFORE_IRREVERSIBLE_DROP')
    if R.M.LAUNCHER_C.count(CI_GUARD)!=1: raise SystemExit('CI guard launcher topology changed before stable proof rebind')
    build_stable_birth_proof_pair()
    R.M.LAUNCHER_C=R.M.LAUNCHER_C.replace(CI_GUARD,CI_STABLE_GUARD,1)
    R.M.build_launcher()
    if R.M.LAUNCHER_C.count(CI_STABLE_GUARD)!=1 or CI_GUARD in R.M.LAUNCHER_C: raise SystemExit('stable proof guard launcher rebind failed')
    enable_stable_birth_observer()
    print('PRELAB_V7R21_NORMAL_PREBOUNDARY_PROOF_REBUILT_WITH_CI_STABLE_POSTDROP_HELPER=true')

R.preattached_tracer_fail_closed=protected_preattached_tracer_fail_closed
R.main()
