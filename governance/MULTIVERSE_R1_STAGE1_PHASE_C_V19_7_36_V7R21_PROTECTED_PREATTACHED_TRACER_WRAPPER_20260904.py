#!/usr/bin/env python3
import errno, hashlib, importlib.util, os, pathlib, shutil, signal, subprocess, time

BASE='/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R21_RETAINED_ACCESS_SELFTEST_20260904.py'
spec=importlib.util.spec_from_file_location('v7r21_retained',BASE)
R=importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

PROD_GUARD='/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r21'
CI_GUARD='/tmp/v7r21-guard-tracer-selftest'


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def run(*args):
    subprocess.run(list(args),check=True)


def build_exact_ci_guard_copy():
    g='/src/governance/'
    # Reproduce the Dockerfile.v7r21 source-path and patcher topology exactly.
    # Go command-line packages can encode source-file identity even with
    # -trimpath, so byte-for-byte comparison must use the same /tmp names.
    shutil.copyfile(g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R16_POST_AUTH_CREDENTIAL_DROP_GUARD_20260904.go','/tmp/v7r16-guard.go')
    shutil.copyfile(g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R7_UI_READY_WRITER_20260901.go','/tmp/v7r7-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R18_HELPER_CREDENTIAL_CONTRACT_PATCHER_20260904.py','/tmp/v7r16-guard.go','/tmp/v7r7-helper.go','/tmp/v7r18-guard.go','/tmp/v7r18-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R19_WHOLE_PROCESS_CREDENTIAL_DROP_PATCHER_20260904.py','/tmp/v7r18-guard.go','/tmp/v7r18-helper.go','/tmp/v7r19-guard.go','/tmp/v7r19-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R20_MIXED_TRANSITION_RACE_PATCHER_20260904.py','/tmp/v7r19-guard.go','/tmp/v7r19-helper.go','/tmp/v7r20-guard.go','/tmp/v7r20-helper.go')
    run('python3',g+'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R21_NEW_THREAD_REGAIN_PATCHER_20260904.py','/tmp/v7r20-guard.go','/tmp/v7r20-helper.go','/tmp/v7r21-guard.go','/tmp/v7r21-helper.go')
    run('gofmt','-w','/tmp/v7r21-guard.go','/tmp/v7r21-helper.go')
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o','/tmp/ui-ready-v7r21','/tmp/v7r21-helper.go')
    helper_sha=sha('/tmp/ui-ready-v7r21')
    if helper_sha!=sha(R.HELPER): raise SystemExit('CI regenerated helper does not byte-match production helper')
    p=pathlib.Path('/tmp/v7r21-guard.go'); s=p.read_text(encoding='utf-8')
    if s.count('__V7R21_HELPER_SHA256__')!=1: raise SystemExit('guard helper hash placeholder topology changed')
    s=s.replace('__V7R21_HELPER_SHA256__',helper_sha,1); p.write_text(s,encoding='utf-8'); run('gofmt','-w',str(p))
    run('env','CGO_ENABLED=0','go','build','-trimpath','-buildvcs=false','-ldflags=-s -w -buildid=','-o','/tmp/ui-ready-env-guard-v7r21',str(p))
    if sha('/tmp/ui-ready-env-guard-v7r21')!=sha(PROD_GUARD): raise SystemExit('CI regenerated guard does not byte-match production guard')

    # Insert exactly one unconditional CI-only stop AFTER the production guard
    # has completed verifyProtectedCredentialBoundary(), which includes its
    # TracerPid=0 check. All production code before and after this one line is
    # byte-for-source identical to the regenerated production guard.
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

R.preattached_tracer_fail_closed=protected_preattached_tracer_fail_closed
R.main()
