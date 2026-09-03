#!/usr/bin/env python3
import ctypes
import errno
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

AUTH_UID = 64173
PTRACE_ATTACH = 16
PTRACE_CONT = 7
LAUNCHER_SRC = pathlib.Path('/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R9_PREARM_RATE_COMMIT_SANITIZER_20260903.c')
ENV = {'CODESPACES': 'true', 'CODESPACE_NAME': 'rate-v7r13-test'}

HOLD_C = r'''#define _GNU_SOURCE
#include <sys/types.h>
#include <unistd.h>
#include <time.h>
#include <fcntl.h>
volatile unsigned char target_byte __attribute__((used)) = 0x35;
int main(void){
  uid_t r=0,e=0,s=0;
  if(getresuid(&r,&e,&s)!=0||r==0||e!=64173||s!=64173)return 93;
  int fd=open("/tmp/v7r13-hold-reached",O_WRONLY|O_CREAT|O_TRUNC,0644);
  if(fd>=0){if(write(fd,"ok\n",3)!=3)return 94;close(fd);}
  struct timespec ts={2,0};nanosleep(&ts,0);
  return target_byte==0x35?0:95;
}
'''

class IOV(ctypes.Structure):
    _fields_ = [('iov_base', ctypes.c_void_p), ('iov_len', ctypes.c_size_t)]

libc = ctypes.CDLL(None, use_errno=True)
libc.ptrace.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
libc.ptrace.restype = ctypes.c_long
libc.process_vm_writev.argtypes = [ctypes.c_int, ctypes.POINTER(IOV), ctypes.c_ulong, ctypes.POINTER(IOV), ctypes.c_ulong, ctypes.c_ulong]
libc.process_vm_writev.restype = ctypes.c_ssize_t


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def ptrace(req, pid, addr=0, data=0):
    ctypes.set_errno(0)
    rv = libc.ptrace(req, pid, ctypes.c_void_p(addr), ctypes.c_void_p(data))
    return rv, ctypes.get_errno()


def uid_tuple(pid):
    try:
        with open(f'/proc/{pid}/status', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Uid:'):
                    return tuple(map(int, line.split()[1:5]))
    except FileNotFoundError:
        return None
    return None


def build_fixture():
    pathlib.Path('/tmp/v7r13-hold.c').write_text(HOLD_C, encoding='utf-8')
    run(['gcc', '-O2', '-no-pie', '-o', '/tmp/v7r13-hold', '/tmp/v7r13-hold.c'])
    nm = subprocess.check_output(['nm', '-n', '/tmp/v7r13-hold'], text=True)
    addrs = [line.split()[0] for line in nm.splitlines() if line.split() and line.split()[-1] == 'target_byte']
    if len(addrs) != 1:
        raise SystemExit(f'target_byte symbol count {len(addrs)}')
    remote_addr = int(addrs[0], 16)
    run([
        'gcc', '-nostdlib', '-static', '-fno-stack-protector', '-fno-asynchronous-unwind-tables',
        '-fno-unwind-tables', '-fno-ident', '-Wl,--build-id=none', '-Wl,-z,noexecstack',
        '-DV7R13_PROBE_PATH=/tmp/v7r13-hold', '-o', '/tmp/v7r13-launcher', str(LAUNCHER_SRC),
    ])
    os.chown('/tmp/v7r13-launcher', 0, 0)
    os.chown('/tmp/v7r13-hold', 0, 0)
    os.chmod('/tmp/v7r13-launcher', 0o4555)
    os.chmod('/tmp/v7r13-hold', 0o555)
    try:
        os.unlink('/tmp/v7r13-hold-reached')
    except FileNotFoundError:
        pass
    return remote_addr


def attack_once(pid, remote_addr):
    rv, er = ptrace(PTRACE_ATTACH, pid)
    if rv == 0:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        return 'PTRACE_ATTACH_SUCCEEDED'
    if er not in (errno.EPERM, errno.ESRCH):
        return f'PTRACE_ERR_{er}'

    for path, flags in ((f'/proc/{pid}/mem', os.O_RDWR), (f'/proc/{pid}/fd/1', os.O_RDONLY)):
        try:
            fd = os.open(path, flags)
            os.close(fd)
            return f'PROC_ACCESS_SUCCEEDED:{path}'
        except OSError as ex:
            if ex.errno not in (errno.EACCES, errno.EPERM, errno.ENOENT, errno.ESRCH):
                return f'PROC_ERR_{ex.errno}:{path}'

    byte = ctypes.c_ubyte(0x41)
    local = IOV(ctypes.cast(ctypes.pointer(byte), ctypes.c_void_p), 1)
    remote = IOV(ctypes.c_void_p(remote_addr), 1)
    ctypes.set_errno(0)
    rv = libc.process_vm_writev(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
    er = ctypes.get_errno()
    if rv >= 0:
        return f'PROCESS_VM_WRITE_SUCCEEDED_{rv}'
    if er not in (errno.EPERM, errno.ESRCH):
        return f'PROCESS_VM_NOT_PERMISSION_DENIED_{er}'
    return None


def preexec_attach_must_fail_closed():
    pid = os.fork()
    if pid == 0:
        os.kill(os.getpid(), signal.SIGSTOP)
        os.execve('/tmp/v7r13-launcher', ['/tmp/v7r13-launcher'], ENV)
    _, st = os.waitpid(pid, os.WUNTRACED)
    if not os.WIFSTOPPED(st):
        raise SystemExit('preexec child did not stop')
    rv, er = ptrace(PTRACE_ATTACH, pid)
    if rv != 0:
        raise SystemExit(f'preexec attach unexpectedly failed {er}')
    os.waitpid(pid, 0)
    ptrace(PTRACE_CONT, pid)
    while True:
        _, st = os.waitpid(pid, 0)
        if os.WIFEXITED(st):
            if os.WEXITSTATUS(st) != 92:
                raise SystemExit(f'traced preexec reached unexpected exit {os.WEXITSTATUS(st)}')
            break
        if os.WIFSIGNALED(st):
            raise SystemExit('traced preexec signaled')
        ptrace(PTRACE_CONT, pid)
    if os.path.exists('/tmp/v7r13-hold-reached'):
        raise SystemExit('traced preexec reached authority target')


def continuous_post_secureexec_attacks(remote_addr):
    p = subprocess.Popen(['/tmp/v7r13-launcher'], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 1.0
    observed = False
    while time.time() < deadline and p.poll() is None:
        u = uid_tuple(p.pid)
        if u and not (u[0] == u[1] == u[2]):
            observed = True
            break
    if not observed:
        p.kill()
        raise SystemExit('credential mismatch boundary not observed')

    attempts = 0
    while p.poll() is None:
        u = uid_tuple(p.pid)
        if u and u[0] == u[1] == u[2]:
            p.kill()
            raise SystemExit(f'same-uid credential window observed {u}')
        bad = attack_once(p.pid, remote_addr)
        attempts += 1
        if bad:
            p.kill()
            raise SystemExit(bad)
        if attempts > 500:
            break
    rc = p.wait(timeout=3)
    out, err = p.communicate()
    if rc != 0:
        raise SystemExit(f'held target failed rc={rc} stdout={out!r} stderr={err!r}')
    if attempts < 10:
        raise SystemExit(f'insufficient attack attempts {attempts}')
    if not os.path.exists('/tmp/v7r13-hold-reached'):
        raise SystemExit('hold target not reached')
    print(f'PRELAB_V7R13_PREEXEC_ATTACH_FAIL_CLOSED=true attempts={attempts}')
    print('PRELAB_V7R13_CONTINUOUS_PTRACE_DENIED=true')
    print('PRELAB_V7R13_CONTINUOUS_PROCESS_VM_WRITEV_DENIED=true')
    print('PRELAB_V7R13_CONTINUOUS_PROC_MEM_DENIED=true')
    print('PRELAB_V7R13_CONTINUOUS_PROC_FD_DENIED=true')


def main():
    if os.getuid() == 0:
        raise SystemExit('attacker must run as nonroot same UID')
    remote_addr = build_fixture() if False else None
    # Fixture preparation needs root only for ownership/mode. A parent root shell prepares it,
    # then invokes this script after dropping to codespace; receive the validated address via argv.
    if len(sys.argv) != 2:
        raise SystemExit('usage: attack_selftest.py <target-byte-hex>')
    remote_addr = int(sys.argv[1], 16)
    preexec_attach_must_fail_closed()
    continuous_post_secureexec_attacks(remote_addr)


if __name__ == '__main__':
    main()
