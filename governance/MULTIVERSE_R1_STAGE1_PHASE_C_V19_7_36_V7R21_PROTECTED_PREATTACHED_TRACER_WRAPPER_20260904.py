#!/usr/bin/env python3
import errno, importlib.util, os, subprocess, time

BASE='/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R21_RETAINED_ACCESS_SELFTEST_20260904.py'
spec=importlib.util.spec_from_file_location('v7r21_retained', BASE)
R=importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

# The production-equivalent launcher in the inherited selftest crosses the
# protected-credential interval too quickly for an external observer to attach
# deterministically. This wrapper modifies ONLY the ephemeral CI launcher C
# source generated in /tmp. It inserts one SIGSTOP after setresuid has already
# established the authority UID and after PR_SET_DUMPABLE(0), but before guard
# exec. No production binary/source/image receives a delay, signal hook, env
# knob, FD protocol, network surface, or reusable privilege capability.
_base_configure=R.configure_base

def configure_with_protected_ci_stop():
    _base_configure()
    s=R.M.LAUNCHER_C
    inc='#include <string.h>'
    if inc not in s or '#include <signal.h>' in s:
        raise SystemExit('unexpected CI launcher include topology')
    s=s.replace(inc, inc+'\n#include <signal.h>', 1)
    needle='if(prctl(PR_SET_DUMPABLE,0,0,0,0)!=0)return 97;'
    if s.count(needle)!=1:
        raise SystemExit('unexpected CI launcher protected-stop insertion point')
    s=s.replace(needle, needle+'if(raise(SIGSTOP)!=0)return 99;', 1)
    R.M.LAUNCHER_C=s

R.configure_base=configure_with_protected_ci_stop


def uid_tuple(pid):
    try:
        with open(f'/proc/{pid}/status', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Uid:'):
                    vals=tuple(map(int, line.split()[1:5]))
                    return vals if len(vals)==4 else None
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None
    return None


def protected_preattached_tracer_fail_closed(uid, gid):
    # CI-only stronger attacker topology. The child stops itself only after the
    # reviewed setuid launcher has established the protected authority UID.
    # Attaching before that point would cause Linux exec/setuid tracing rules to
    # suppress the privilege transition and merely reproduce the old pre-exec
    # denial instead of the requested protected-boundary tracer case.
    fd=R.M.make_authority()
    def child_ids():
        os.setgroups([])
        os.setresgid(gid, gid, gid)
        os.setresuid(uid, uid, uid)

    p=subprocess.Popen(
        ['/tmp/v7r20-launcher', R.NAME, str(fd), R.M.GEN],
        env={'CODESPACES':'true','CODESPACE_NAME':R.NAME},
        pass_fds=(fd,), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, preexec_fn=child_ids)

    try:
        stopped_pid,status=os.waitpid(p.pid, os.WUNTRACED)
        if stopped_pid!=p.pid or not os.WIFSTOPPED(status) or os.WSTOPSIG(status)!=19:
            raise SystemExit(f'CI protected-stop not observed:status={status}')
        u=uid_tuple(p.pid)
        if u is None or u[1:]!=(R.AUTH_UID,R.AUTH_UID,R.AUTH_UID):
            raise SystemExit(f'CI protected-stop credential mismatch:{u}')
        try:
            attach_exe=os.readlink(f'/proc/{p.pid}/exe')
        except OSError:
            attach_exe='UNKNOWN'

        rv,er=R.M.ptrace(R.M.PTRACE_ATTACH,p.pid)
        if rv!=0:
            raise SystemExit(f'protected-preattached-tracer-attach-failed:{er}')
        try:
            os.waitpid(p.pid, os.WUNTRACED)
        except ChildProcessError:
            pass

        seen_helper=False
        deadline=time.time()+4
        while time.time()<deadline:
            try:
                if os.readlink(f'/proc/{p.pid}/exe')==R.HELPER:
                    seen_helper=True
            except OSError:
                pass
            rv,er=R.M.ptrace(R.PTRACE_CONT,p.pid)
            if rv!=0 and er not in (errno.ESRCH,):
                raise SystemExit(f'protected-preattached-tracer-cont-failed:{er}')
            try:
                _,status=os.waitpid(p.pid,0)
            except ChildProcessError:
                break
            if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                break

        text=p.stdout.read() or ''
        try:
            p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait(timeout=1)
    finally:
        os.close(fd)

    denied='PHASE_C_V19_7_36_V7R21_HELPER_DENIED:PROTECTED_STARTUP:tracer-present' in text
    dropped='V7R21_IRREVERSIBLE_USER_DROP_COMPLETE' in text
    if not seen_helper:
        raise SystemExit('protected preattached tracer did not reach helper image')
    if not denied:
        raise SystemExit('protected preattached tracer reached helper without exact tracer-present fail-closed denial')
    if dropped:
        raise SystemExit('protected preattached tracer crossed irreversible user-drop boundary')

    print(text,end='')
    print('PRELAB_V7R21_PREATTACHED_TRACER_ATTEMPTS=1')
    print('PRELAB_V7R21_PREATTACHED_TRACER_PROTECTED_UID_OBSERVED=true')
    print('PRELAB_V7R21_PREATTACHED_TRACER_CI_ONLY_PROTECTED_STOP=true')
    print(f'PRELAB_V7R21_PREATTACHED_TRACER_ATTACH_EXE={attach_exe}')
    print('PRELAB_V7R21_PREATTACHED_TRACER_REACHED_HELPER=true')
    print('PRELAB_V7R21_PREATTACHED_TRACER_EXACT_BOUNDARY_RESULT=FAIL_CLOSED_TRACER_PRESENT_BEFORE_IRREVERSIBLE_DROP')


R.preattached_tracer_fail_closed=protected_preattached_tracer_fail_closed
R.main()
