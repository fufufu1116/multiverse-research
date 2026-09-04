#!/usr/bin/env python3
import errno, importlib.util, os, subprocess, time

BASE='/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R21_RETAINED_ACCESS_SELFTEST_20260904.py'
spec=importlib.util.spec_from_file_location('v7r21_retained', BASE)
R=importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


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
    # CI-only stronger attacker topology. We first wait until the reviewed
    # setuid launcher has actually established the protected authority UID.
    # Attaching before that point would cause Linux exec/setuid tracing rules
    # to suppress the privilege transition and would only reproduce the old
    # pre-exec denial, not the requested protected-boundary tracer case.
    # The workflow grants SYS_PTRACE only to this network-disabled test
    # container; production images/paths gain no capability or control knob.
    for attempt in range(24):
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

        protected_seen=False
        attach_exe='UNKNOWN'
        observe_deadline=time.time()+0.75
        while time.time() < observe_deadline and p.poll() is None:
            u=uid_tuple(p.pid)
            if u is not None and u[1:] == (R.AUTH_UID, R.AUTH_UID, R.AUTH_UID):
                protected_seen=True
                try:
                    attach_exe=os.readlink(f'/proc/{p.pid}/exe')
                except OSError:
                    pass
                break
            time.sleep(0.0001)

        if not protected_seen:
            try:
                p.kill(); p.wait(timeout=1)
            except Exception:
                pass
            os.close(fd)
            continue

        rv, er=R.M.ptrace(R.M.PTRACE_ATTACH, p.pid)
        if rv != 0:
            try:
                p.kill(); p.wait(timeout=1)
            except Exception:
                pass
            os.close(fd)
            if er in (errno.ESRCH, errno.EPERM):
                continue
            raise SystemExit(f'protected-preattached-tracer-attach-unexpected:{er}')

        try:
            try:
                os.waitpid(p.pid, 0)
            except ChildProcessError:
                pass
            seen_helper=False
            deadline=time.time()+4
            while time.time() < deadline:
                try:
                    if os.readlink(f'/proc/{p.pid}/exe') == R.HELPER:
                        seen_helper=True
                except OSError:
                    pass
                R.M.ptrace(R.PTRACE_CONT, p.pid)
                try:
                    _, status=os.waitpid(p.pid, 0)
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
        if denied and not dropped and seen_helper:
            print(text, end='')
            print(f'PRELAB_V7R21_PREATTACHED_TRACER_ATTEMPTS={attempt+1}')
            print('PRELAB_V7R21_PREATTACHED_TRACER_PROTECTED_UID_OBSERVED=true')
            print(f'PRELAB_V7R21_PREATTACHED_TRACER_ATTACH_EXE={attach_exe}')
            print('PRELAB_V7R21_PREATTACHED_TRACER_REACHED_HELPER=true')
            print('PRELAB_V7R21_PREATTACHED_TRACER_EXACT_BOUNDARY_RESULT=FAIL_CLOSED_TRACER_PRESENT_BEFORE_IRREVERSIBLE_DROP')
            return

    raise SystemExit('protected-boundary preattached tracer variant did not reach helper fail-closed boundary')


R.preattached_tracer_fail_closed=protected_preattached_tracer_fail_closed
R.main()
