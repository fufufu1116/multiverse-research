#!/usr/bin/env python3
import hashlib
import pathlib
import re
import sys

EXPECTED_GIT_BLOB = "a047858d445dddc9229ed7f7c0cc1193d0bf7eb2"
OLD_GUARD = 'guardPath = "/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7"'
NEW_GUARD = 'guardPath = "/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r15"'

NEW_BOUNDARY = r'''func prepareGuardExecProtectedBoundary(a *sealedAuthority,lock *os.File)(int,error){
	if a==nil||a.File==nil||lock==nil{return -1,fmt.Errorf("protected-boundary-nil")}
	afd:=int(a.File.Fd());lfd:=int(lock.Fd())
	entries,err:=os.ReadDir("/proc/self/fd");if err!=nil{return -1,err}
	for _,ent:=range entries{n,pe:=strconv.Atoi(ent.Name());if pe!=nil||n<3||n==afd||n==lfd{continue};_=syscall.Close(n)}
	flags,_,eno:=syscall.Syscall(syscall.SYS_FCNTL,uintptr(afd),uintptr(1),0);if eno!=0{return -1,eno}
	if _,_,eno=syscall.Syscall(syscall.SYS_FCNTL,uintptr(afd),uintptr(2),flags&^uintptr(1));eno!=0{return -1,eno}
	flags2,_,eno:=syscall.Syscall(syscall.SYS_FCNTL,uintptr(afd),uintptr(1),0);if eno!=0{return -1,eno};if flags2&1!=0{return -1,fmt.Errorf("authority-fd-cloexec")}
	if err=setCommitNondumpable();err!=nil{return -1,err};if err=verifyNoTracer();err!=nil{return -1,err};if err=verifySealedAuthority(a);err!=nil{return -1,err}
	return afd,nil
}
'''

OLD_CALL = 'if e=prepareGuardExecUserBoundary();e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R13_RATE_COMMIT_DENIED:GUARD_CREDENTIAL_BOUNDARY");os.Exit(92)};if e=verifySealedAuthority(a);e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R13_RATE_COMMIT_DENIED:FINAL_SEALED_AUTHORITY_REVERIFY");os.Exit(92)};env:=[]string{"CODESPACES=true","CODESPACE_NAME="+name};argv:=[]string{guardPath,name};if e:=syscall.Exec(guardPath,argv,env);e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R13_RATE_COMMIT_DENIED:GUARD_EXEC");os.Exit(92)}'
NEW_CALL = 'authorityFD,e:=prepareGuardExecProtectedBoundary(a,lock);if e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R13_RATE_COMMIT_DENIED:PROTECTED_GUARD_BOUNDARY");os.Exit(92)};if e=verifySealedAuthority(a);e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R13_RATE_COMMIT_DENIED:FINAL_SEALED_AUTHORITY_REVERIFY");os.Exit(92)};env:=[]string{"CODESPACES=true","CODESPACE_NAME="+name};argv:=[]string{guardPath,name,strconv.Itoa(authorityFD),gen};if e:=syscall.Exec(guardPath,argv,env);e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R13_RATE_COMMIT_DENIED:GUARD_EXEC");os.Exit(92)}'


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require_one(text: str, needle: str, label: str) -> str:
    n = text.count(needle)
    if n != 1:
        raise SystemExit(f"{label}: expected one match, got {n}")
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: patcher.py <base-go> <out-go>")
    src = pathlib.Path(sys.argv[1]).read_bytes()
    if git_blob_sha(src) != EXPECTED_GIT_BLOB:
        raise SystemExit("base source git-blob mismatch")
    text = src.decode("utf-8")
    require_one(text, OLD_GUARD, "guard-path")
    text = text.replace(OLD_GUARD, NEW_GUARD)
    pattern = r'func prepareGuardExecUserBoundary\(\)error\{.*?\}\nfunc createMemfd'
    text, n = re.subn(pattern, NEW_BOUNDARY + 'func createMemfd', text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"credential-boundary replacement count {n}")
    require_one(text, OLD_CALL, "final-transition")
    text = text.replace(OLD_CALL, NEW_CALL)
    text = text.replace("V7R13", "V7R15").replace("v7r13", "v7r15")
    required = [
        'guardPath = "/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r15"',
        'prepareGuardExecProtectedBoundary(a,lock)',
        'strconv.Itoa(authorityFD)',
        'Version:"V19.7.36-v7r15"',
        'PHASE_C_V19_7_36_V7R15_RATE_COMMIT_READY',
    ]
    for marker in required:
        if marker not in text:
            raise SystemExit("missing patched marker: " + marker)
    forbidden = ["prepareGuardExecUserBoundary()", "EXEC_V7R7_STATIC_GUARD"]
    for marker in forbidden:
        if marker in text:
            raise SystemExit("forbidden predecessor marker remains: " + marker)
    pathlib.Path(sys.argv[2]).write_text(text, encoding="utf-8")
    print("PHASE_C_V19_7_36_V7R15_PROBE_TRANSITION_PATCH_PASS")
    print("PROTECTED_CREDENTIAL_MISMATCH_PRESERVED_TO_GUARD_EXEC=true")
    print("SEALED_AUTHORITY_FD_INHERITED_TO_GUARD=true")
    print("RETAINED_FD_SWEEP_BEFORE_GUARD_EXEC=true")
    print("RUNTIME=OFF")


if __name__ == "__main__":
    main()
