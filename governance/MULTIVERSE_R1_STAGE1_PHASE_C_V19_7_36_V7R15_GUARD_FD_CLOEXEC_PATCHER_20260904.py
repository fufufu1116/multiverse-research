#!/usr/bin/env python3
import hashlib,pathlib,sys
EXPECTED_GIT_BLOB='d578811086af3744a69d3af1a2604f10ac28dcb2'
OLD='''    if int(flags)&fdCloexec != 0 { return zero,"",fmt.Errorf("fd-still-cloexec") }\n    if _,_,er = syscall.Syscall(syscall.SYS_FCNTL, uintptr(fd), uintptr(fSetFD), uintptr(fdCloexec)); er != 0 { return zero,"",er }'''
NEW='''    if int(flags)&fdCloexec == 0 {\n        if _,_,er = syscall.Syscall(syscall.SYS_FCNTL, uintptr(fd), uintptr(fSetFD), uintptr(fdCloexec)); er != 0 { return zero,"",er }\n    }'''
def gitblob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def main():
 if len(sys.argv)!=3:raise SystemExit('usage: patcher <in> <out>')
 b=pathlib.Path(sys.argv[1]).read_bytes()
 if gitblob(b)!=EXPECTED_GIT_BLOB:raise SystemExit('guard source git-blob mismatch')
 s=b.decode()
 if s.count(OLD)!=1:raise SystemExit('authority-fd block match failure')
 s=s.replace(OLD,NEW)
 pathlib.Path(sys.argv[2]).write_text(s,encoding='utf-8')
 print('PHASE_C_V19_7_36_V7R15_GUARD_FD_PATCH_PASS')
if __name__=='__main__':main()
