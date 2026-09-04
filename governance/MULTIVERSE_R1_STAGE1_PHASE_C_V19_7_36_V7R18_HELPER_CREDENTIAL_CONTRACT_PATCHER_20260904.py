#!/usr/bin/env python3
import pathlib,sys

def once(src, old, new, label):
    n=src.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected exactly one anchor, got {n}')
    return src.replace(old,new,1)

def patch_helper(src):
    src=once(src,'\t"os"\n\t"strconv"','\t"os"\n\t"runtime"\n\t"strconv"','helper-import-runtime')
    src=once(src,'\t"time"\n)','\t"time"\n\t"unsafe"\n)','helper-import-unsafe')
    src=once(src,'const imageIdentityPathV7R7 = "/opt/multiverse/v36/image-identity-v7r3.json"','const imageIdentityPathV7R7 = "/opt/multiverse/v36/image-identity-v7r18.json"','helper-image-identity')
    inject=r'''
const authorityUIDV7R18 uint32 = 64173
const v7r18PrSetDumpable = 4
const v7r18PrGetDumpable = 3

func v7r18GetResUIDs() (uint32,uint32,uint32,error) {
	var r,e,s uint32
	_,_,er := syscall.Syscall(syscall.SYS_GETRESUID, uintptr(unsafe.Pointer(&r)), uintptr(unsafe.Pointer(&e)), uintptr(unsafe.Pointer(&s)))
	if er != 0 { return 0,0,0,er }
	return r,e,s,nil
}

func v7r18GetFSUID() (uint32,error) {
	cur,_,er := syscall.Syscall(syscall.SYS_SETFSUID, ^uintptr(0), 0, 0)
	if er != 0 { return 0,er }
	return uint32(cur),nil
}

func v7r18SetFSUIDAndVerify(uid uint32) error {
	if _,_,er := syscall.Syscall(syscall.SYS_SETFSUID, uintptr(uid), 0, 0); er != 0 { return er }
	cur,err := v7r18GetFSUID(); if err != nil { return err }
	if cur != uid { return fmt.Errorf("fsuid-mismatch") }
	return nil
}

func v7r18SetNondumpable() error {
	if _,_,er := syscall.Syscall6(syscall.SYS_PRCTL, uintptr(v7r18PrSetDumpable), 0,0,0,0,0); er != 0 { return er }
	v,_,er := syscall.Syscall6(syscall.SYS_PRCTL, uintptr(v7r18PrGetDumpable), 0,0,0,0,0)
	if er != 0 { return er }
	if v != 0 { return fmt.Errorf("dumpable-not-zero") }
	return nil
}

func v7r18VerifyNoTracer() error {
	b,err := os.ReadFile("/proc/self/status"); if err != nil { return err }
	for _,ln := range strings.Split(string(b),"\n") {
		if strings.HasPrefix(ln,"TracerPid:") {
			if strings.TrimSpace(strings.TrimPrefix(ln,"TracerPid:")) != "0" { return fmt.Errorf("tracer-present") }
			return nil
		}
	}
	return fmt.Errorf("tracerpid-missing")
}

func v7r18VerifyNoNewPrivsAndZeroCaps() error {
	b,err := os.ReadFile("/proc/self/status"); if err != nil { return err }
	want := map[string]string{"NoNewPrivs:":"1","CapInh:":"0000000000000000","CapPrm:":"0000000000000000","CapEff:":"0000000000000000","CapAmb:":"0000000000000000"}
	seen := map[string]bool{}
	for _,ln := range strings.Split(string(b),"\n") {
		for k,v := range want {
			if strings.HasPrefix(ln,k) {
				if strings.TrimSpace(strings.TrimPrefix(ln,k)) != v { return fmt.Errorf("status-%s",strings.TrimSuffix(k,":")) }
				seen[k]=true
			}
		}
	}
	for k := range want { if !seen[k] { return fmt.Errorf("status-missing-%s",strings.TrimSuffix(k,":")) } }
	return nil
}

func v7r18ProtectedStartup() (uint32,error) {
	r,e,s,err := v7r18GetResUIDs(); if err != nil { return 0,err }
	if r == 0 || r == authorityUIDV7R18 || e != authorityUIDV7R18 || s != authorityUIDV7R18 { return 0,fmt.Errorf("credential-mismatch") }
	fs,err := v7r18GetFSUID(); if err != nil { return 0,err }
	if fs != authorityUIDV7R18 { return 0,fmt.Errorf("fsuid-protected-mismatch") }
	if err := v7r18VerifyNoNewPrivsAndZeroCaps(); err != nil { return 0,err }
	if err := v7r18SetNondumpable(); err != nil { return 0,err }
	if err := v7r18VerifyNoTracer(); err != nil { return 0,err }
	return r,nil
}

func v7r18VerifyProtectedEnv(name string) error {
	envs:=os.Environ(); if len(envs)!=3 { return fmt.Errorf("env-count") }
	want:=map[string]int{"CODESPACES=true":0,"CODESPACE_NAME="+name:0,"GOTRACEBACK=none":0}
	for _,v:=range envs { if _,ok:=want[v]; !ok { return fmt.Errorf("env-unexpected") }; want[v]++ }
	for _,n:=range want { if n!=1 { return fmt.Errorf("env-duplicate-or-missing") } }
	return nil
}

func v7r18DropIrreversibly(uid uint32) error {
	if uid == 0 || uid == authorityUIDV7R18 { return fmt.Errorf("drop-target") }
	if err := v7r18SetFSUIDAndVerify(uid); err != nil { return err }
	if _,_,er := syscall.Syscall(syscall.SYS_SETRESUID, uintptr(uid),uintptr(uid),uintptr(uid)); er != 0 { return er }
	r,e,s,err := v7r18GetResUIDs(); if err != nil { return err }
	if r!=uid || e!=uid || s!=uid { return fmt.Errorf("post-drop-uid-tuple") }
	fs,err := v7r18GetFSUID(); if err != nil { return err }; if fs!=uid { return fmt.Errorf("post-drop-fsuid") }
	if err := v7r18VerifyNoNewPrivsAndZeroCaps(); err != nil { return err }
	_,_,er := syscall.Syscall(syscall.SYS_SETRESUID, uintptr(authorityUIDV7R18),uintptr(authorityUIDV7R18),uintptr(authorityUIDV7R18))
	if er == 0 { return fmt.Errorf("authority-regain-succeeded") }
	if er != syscall.EPERM { return fmt.Errorf("authority-regain-unexpected") }
	// Defense in depth only. Security does not rely on this late prctl: by this
	// point the helper image is already entered, startup binding is complete,
	// the authority descriptor was retired by the protected guard, and all IDs
	// plus fsuid are ordinary and irreversible.
	if err := v7r18SetNondumpable(); err != nil { return err }
	return nil
}
'''
    src=once(src,'\nfunc main() {\n',inject+'\nfunc main() {\n','helper-function-inject')
    old='''\tif os.Geteuid() == 0 {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:ROOT_REMOTE_USER")\n\t\tos.Exit(92)\n\t}\n'''
    new='''\truntime.LockOSThread()\n\ttargetUID, err := v7r18ProtectedStartup()\n\tif err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R18_HELPER_DENIED:PROTECTED_STARTUP:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n'''
    src=once(src,old,new,'helper-protected-startup')
    anchor='''\tif !validName(name) {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:CODESPACE_NAME")\n\t\tos.Exit(92)\n\t}\n\tidentity, err := imageIdentitySHA256()\n'''
    repl='''\tif !validName(name) {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:CODESPACE_NAME")\n\t\tos.Exit(92)\n\t}\n\tif err := v7r18VerifyProtectedEnv(name); err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R18_HELPER_DENIED:PROTECTED_ENV:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n\tnameAddr := uintptr(unsafe.Pointer(unsafe.StringData(name)))\n\tfmt.Printf("PHASE_C_V19_7_36_V7R18_PROTECTED_HELPER_ENTRY codespace_name_addr=0x%x runtime=OFF\\n", nameAddr)\n\tidentity, err := imageIdentitySHA256()\n'''
    src=once(src,anchor,repl,'helper-protected-env')
    anchor='''\tif err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:IMAGE_IDENTITY")\n\t\tos.Exit(92)\n\t}\n\tif _, err := os.Lstat(armLockPath); err == nil {\n'''
    repl='''\tif err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R7_UI_READY_DENIED:IMAGE_IDENTITY")\n\t\tos.Exit(92)\n\t}\n\tif err := v7r18DropIrreversibly(targetUID); err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R18_HELPER_DENIED:IRREVERSIBLE_USER_DROP:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R18_IRREVERSIBLE_USER_DROP_COMPLETE uid=%d fsuid=%d no_new_privs=1 caps=0 authority_fd=retired runtime=OFF\\n", targetUID,targetUID)\n\truntime.KeepAlive(name)\n\tif _, err := os.Lstat(armLockPath); err == nil {\n'''
    src=once(src,anchor,repl,'helper-user-drop')
    return src

def patch_guard(src):
    src=once(src,'helperPath = "/usr/local/bin/multiverse-v36-ui-ready-v7r7"','helperPath = "/usr/local/bin/multiverse-v36-ui-ready-v7r18"','guard-helper-path')
    src=once(src,'expectedHelperSHA256 = "2fd9e085e866924fb52995e5bb5fcb58763bdbd1fa1ee2c96e1d57df28a42301"','expectedHelperSHA256 = "__V7R18_HELPER_SHA256__"','guard-helper-hash')
    start=src.index('// dropToOrdinaryUser is intentionally the final authority-transition syscall.')
    end=src.index('func selftest()',start)
    src=src[:start]+src[end:]
    src=src.replace('retireAuthorityBeforeUserDrop','retireAuthorityBeforeProtectedHelperExec')
    src=src.replace('v7r16','v7r18').replace('V7R16','V7R18')
    src=once(src,'uid,err := verifyProtectedCredentialBoundary()','_,err = verifyProtectedCredentialBoundary()','guard-unused-target-uid')
    src=src.replace('AUTHORITY_FD_RETIRED_BEFORE_ORDINARY_UID=true','AUTHORITY_FD_RETIRED_BEFORE_PROTECTED_HELPER_EXEC=true')
    src=src.replace('NO_POST_DROP_AUTHORIZATION_DECISION=true','PROTECTED_HELPER_IMAGE_ENTRY_BEFORE_USER_DROP=true')
    src=src.replace('FINAL_AUTHORITY_TRANSITION_SYSCALL=SETRESUID','FINAL_GUARD_TRANSITION=PROTECTED_EXEC_TO_V7R18_HELPER')
    cut=src.index('    os.Clearenv()\n')
    tail='''    os.Clearenv()\n    verifyHelper()\n    if err = retireAuthorityBeforeProtectedHelperExec(fd); err != nil { deny("AUTHORITY_RETIREMENT") }\n\n    fmt.Printf("PHASE_C_V19_7_36_V7R18_AUTHORITY_RETIRED_BEFORE_PROTECTED_HELPER_EXEC codespace=%s generation=%s authority_sha256=%s rate=%d/%d runtime=OFF\\n", name,generation,authoritySHA,snap.Before,snap.After)\n\n    env := []string{"CODESPACES=true","CODESPACE_NAME="+name,"GOTRACEBACK=none"}\n    argv := []string{helperPath}\n\n    // SECURITY BOUNDARY: the guard remains ruid=ordinary/euid=suid=authorityUID\n    // through exec. The fixed root-owned helper image is therefore entered\n    // before same-UID process access can become possible. The helper itself\n    // verifies protected startup and performs the sole irreversible user drop.\n    if err := syscall.Exec(helperPath,argv,env); err != nil {\n        fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R18_PROTECTED_HELPER_EXEC_FAILED")\n        os.Exit(92)\n    }\n}\n'''
    src=src[:cut]+tail
    return src

def main():
    if len(sys.argv)!=5:
        raise SystemExit('usage: patcher OLD_GUARD OLD_HELPER OUT_GUARD OUT_HELPER')
    oldg,oldh,outg,outh=map(pathlib.Path,sys.argv[1:])
    g=patch_guard(oldg.read_text(encoding='utf-8'))
    h=patch_helper(oldh.read_text(encoding='utf-8'))
    if '__V7R18_HELPER_SHA256__' not in g: raise SystemExit('helper hash placeholder missing')
    if 'syscall.Exec(' in h: raise SystemExit('helper must not contain a post-drop exec surface')
    outg.write_text(g,encoding='utf-8')
    outh.write_text(h,encoding='utf-8')
    print('V7R18_HELPER_CREDENTIAL_CONTRACT_PATCHER_PASS')

if __name__=='__main__': main()
