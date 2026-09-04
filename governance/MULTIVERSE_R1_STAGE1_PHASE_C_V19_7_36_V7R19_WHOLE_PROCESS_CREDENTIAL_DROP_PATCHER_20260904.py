#!/usr/bin/env python3
import pathlib,sys

def once(src, old, new, label):
    n=src.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected exactly one anchor, got {n}')
    return src.replace(old,new,1)

def patch_helper(src):
    src=src.replace('v7r18','v7r19').replace('V7R18','V7R19')
    src=once(src,'\t"runtime"\n\t"strconv"','\t"runtime"\n\t"strconv"\n\t"sync"','helper-import-sync')
    src=once(src,'const imageIdentityPathV7R7 = "/opt/multiverse/v36/image-identity-v7r19.json"','const imageIdentityPathV7R7 = "/opt/multiverse/v36/image-identity-v7r19.json"','helper-image-identity-already-rebound') if False else src
    # v7r18 global rename does not affect the literal identity path because the
    # original helper source contains v7r18 there; assert the expected result.
    if 'image-identity-v7r19.json' not in src:
        raise SystemExit('helper-image-identity-v7r19-missing')
    start=src.index('func v7r19DropIrreversibly(')
    end=src.index('\nfunc main() {',start)
    replacement=r'''func v7r19ReadTaskStatus(path string) (map[string]string,error) {
	b,err:=os.ReadFile(path); if err!=nil{return nil,err}
	m:=map[string]string{}
	for _,ln:=range strings.Split(string(b),"\n") {
		for _,k:=range []string{"Uid:","NoNewPrivs:","CapInh:","CapPrm:","CapEff:","CapAmb:"} {
			if strings.HasPrefix(ln,k) { m[k]=strings.TrimSpace(strings.TrimPrefix(ln,k)) }
		}
	}
	return m,nil
}

func v7r19VerifyAllTasks(uid uint32, protected bool) (int,error) {
	ents,err:=os.ReadDir("/proc/self/task"); if err!=nil{return 0,err}
	seen:=0
	for _,ent:=range ents {
		if !ent.IsDir(){continue}
		if _,err:=strconv.ParseUint(ent.Name(),10,64); err!=nil{continue}
		m,err:=v7r19ReadTaskStatus("/proc/self/task/"+ent.Name()+"/status"); if err!=nil{return 0,err}
		f:=strings.Fields(m["Uid:"]); if len(f)!=4{return 0,fmt.Errorf("task-%s-uid-fields",ent.Name())}
		want:=[]uint32{uid,uid,uid,uid}
		if protected { want=[]uint32{uid,authorityUIDV7R19,authorityUIDV7R19,authorityUIDV7R19} }
		for i,s:=range f { n,e:=strconv.ParseUint(s,10,32); if e!=nil||uint32(n)!=want[i]{return 0,fmt.Errorf("task-%s-uid-%d",ent.Name(),i)} }
		if m["NoNewPrivs:"]!="1" { return 0,fmt.Errorf("task-%s-nnp",ent.Name()) }
		for _,k:=range []string{"CapInh:","CapPrm:","CapEff:","CapAmb:"} { if m[k]!="0000000000000000" { return 0,fmt.Errorf("task-%s-%s",ent.Name(),strings.TrimSuffix(k,":")) } }
		seen++
	}
	if seen<1{return 0,fmt.Errorf("no-tasks")}
	return seen,nil
}

func v7r19StartPinnedProofThreads(n int) (func(),func(),error) {
	ready:=make(chan struct{},n); release:=make(chan struct{}); var wg sync.WaitGroup
	for i:=0;i<n;i++ { wg.Add(1); go func(){ runtime.LockOSThread(); ready<-struct{}{}; <-release; runtime.UnlockOSThread(); wg.Done() }() }
	for i:=0;i<n;i++ { select { case <-ready: case <-time.After(3*time.Second): close(release); return nil,nil,fmt.Errorf("pinned-thread-timeout") } }
	var once sync.Once
	return func(){once.Do(func(){close(release)})},func(){wg.Wait()},nil
}

func v7r19DropIrreversibly(uid uint32) (int,error) {
	if uid == 0 || uid == authorityUIDV7R19 { return 0,fmt.Errorf("drop-target") }
	before,err:=v7r19VerifyAllTasks(uid,true); if err!=nil{return 0,fmt.Errorf("pre-drop-all-task-proof:%w",err)}
	if before<2{return 0,fmt.Errorf("pre-drop-not-multithreaded")}
	// CGO is disabled for this exact helper. AllThreadsSyscall is therefore the
	// Go-runtime process-wide primitive: it runs the syscall on every runtime OS
	// thread and terminates on inconsistent per-thread return values.
	if _,_,er:=syscall.AllThreadsSyscall(syscall.SYS_SETFSUID,uintptr(uid),0,0); er!=0{return 0,er}
	if _,_,er:=syscall.AllThreadsSyscall(syscall.SYS_SETRESUID,uintptr(uid),uintptr(uid),uintptr(uid)); er!=0{return 0,er}
	// Repeated enumeration covers runtime scheduling/thread-creation after the
	// transition. New runtime threads must inherit only ordinary credentials.
	maxTasks:=0
	for i:=0;i<16;i++ { n,e:=v7r19VerifyAllTasks(uid,false); if e!=nil{return 0,fmt.Errorf("post-drop-all-task-proof:%w",e)}; if n>maxTasks{maxTasks=n}; runtime.Gosched() }
	if maxTasks<2{return 0,fmt.Errorf("post-drop-not-multithreaded")}
	r,e,s,err:=v7r19GetResUIDs(); if err!=nil{return 0,err}; if r!=uid||e!=uid||s!=uid{return 0,fmt.Errorf("post-drop-current-uid-tuple")}
	fs,err:=v7r19GetFSUID(); if err!=nil{return 0,err}; if fs!=uid{return 0,fmt.Errorf("post-drop-current-fsuid")}
	if err:=v7r19VerifyNoNewPrivsAndZeroCaps(); err!=nil{return 0,err}
	if _,_,er:=syscall.AllThreadsSyscall(syscall.SYS_SETRESUID,uintptr(authorityUIDV7R19),uintptr(authorityUIDV7R19),uintptr(authorityUIDV7R19)); er==0{return 0,fmt.Errorf("authority-regain-succeeded")} else if er!=syscall.EPERM{return 0,fmt.Errorf("authority-regain-unexpected")}
	if _,e:=v7r19VerifyAllTasks(uid,false); e!=nil{return 0,fmt.Errorf("post-regain-all-task-proof:%w",e)}
	if err:=v7r19SetNondumpable(); err!=nil{return 0,err}
	return maxTasks,nil
}
'''
    src=src[:start]+replacement+src[end:]
    src=once(src,'\tif err := v7r19DropIrreversibly(targetUID); err != nil {','\treleaseProofThreads, waitProofThreads, err := v7r19StartPinnedProofThreads(4)\n\tif err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R19_HELPER_DENIED:PINNED_PROOF_THREADS:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n\tproofTasks, err := v7r19DropIrreversibly(targetUID)\n\tif err != nil {','helper-drop-call')
    src=once(src,'\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R19_HELPER_DENIED:IRREVERSIBLE_USER_DROP:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R19_IRREVERSIBLE_USER_DROP_COMPLETE uid=%d fsuid=%d no_new_privs=1 caps=0 authority_fd=retired runtime=OFF\\n", targetUID,targetUID)','\t\treleaseProofThreads()\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R19_HELPER_DENIED:IRREVERSIBLE_USER_DROP:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n\treleaseProofThreads(); waitProofThreads()\n\tif _, err := v7r19VerifyAllTasks(targetUID,false); err != nil {\n\t\tfmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R19_HELPER_DENIED:POST_RELEASE_ALL_TASK_PROOF:"+strings.ReplaceAll(err.Error(), "\\n", "_"))\n\t\tos.Exit(92)\n\t}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R19_IRREVERSIBLE_USER_DROP_COMPLETE uid=%d fsuid=%d no_new_privs=1 caps=0 all_tasks_ordinary=true proof_tasks=%d authority_fd=retired runtime=OFF\\n", targetUID,targetUID,proofTasks)','helper-drop-marker')
    if 'syscall.Syscall(syscall.SYS_SETRESUID' in src:
        raise SystemExit('raw-calling-thread-setresuid-survives')
    if 'syscall.AllThreadsSyscall(syscall.SYS_SETRESUID' not in src:
        raise SystemExit('allthreads-setresuid-missing')
    return src

def patch_guard(src):
    src=src.replace('v7r18','v7r19').replace('V7R18','V7R19')
    src=once(src,'expectedHelperSHA256 = "__V7R19_HELPER_SHA256__"','expectedHelperSHA256 = "__V7R19_HELPER_SHA256__"','guard-helper-placeholder') if False else src
    if '/usr/local/bin/multiverse-v36-ui-ready-v7r19' not in src: raise SystemExit('guard-v7r19-helper-path-missing')
    if '__V7R19_HELPER_SHA256__' not in src: raise SystemExit('guard-v7r19-helper-hash-placeholder-missing')
    return src

def main():
    if len(sys.argv)!=5: raise SystemExit('usage: patcher V7R18_GUARD V7R18_HELPER OUT_GUARD OUT_HELPER')
    ing,inh,outg,outh=map(pathlib.Path,sys.argv[1:])
    g=patch_guard(ing.read_text(encoding='utf-8'))
    h=patch_helper(inh.read_text(encoding='utf-8'))
    outg.write_text(g,encoding='utf-8'); outh.write_text(h,encoding='utf-8')
    print('V7R19_WHOLE_PROCESS_CREDENTIAL_DROP_PATCHER_PASS')

if __name__=='__main__': main()
