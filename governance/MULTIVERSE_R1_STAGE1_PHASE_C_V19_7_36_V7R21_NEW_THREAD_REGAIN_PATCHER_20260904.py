#!/usr/bin/env python3
import pathlib,sys

def once(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit(f'{label}: expected exactly one anchor, got {n}')
    return src.replace(old,new,1)

def patch_helper(src):
    src=src.replace('v7r20','v7r21').replace('V7R20','V7R21')
    start=src.index('func v7r21PostDropThreadCreationStress(')
    end=src.index('\nfunc v7r21DropIrreversibly(',start)
    replacement=r'''func v7r21AttemptAuthorityRegainOnCurrentLockedThread(uid uint32) (int,error) {
	before:=syscall.Gettid()
	_,_,er:=syscall.RawSyscall(syscall.SYS_SETRESUID,uintptr(authorityUIDV7R21),uintptr(authorityUIDV7R21),uintptr(authorityUIDV7R21))
	after:=syscall.Gettid()
	if before!=after{return before,fmt.Errorf("regain-thread-migrated-before-%d-after-%d",before,after)}
	if er==0{return before,fmt.Errorf("authority-regain-succeeded-on-new-thread-%d",before)}
	if er!=syscall.EPERM{return before,fmt.Errorf("authority-regain-unexpected-on-new-thread-%d:%v",before,er)}
	if err:=v7r21VerifyTaskOrdinary(before,uid); err!=nil{return before,fmt.Errorf("post-regain-task-proof:%w",err)}
	return before,nil
}

func v7r21PostDropThreadCreationStress(uid uint32, pre map[int]struct{}) (int,int,int,error) {
	type proof struct{tid int; err error}
	unique:=map[int]struct{}{}; newSeen:=map[int]struct{}{}; regainDenied:=0
	for round:=0;round<8;round++ {
		const n=12
		ready:=make(chan proof,n); release:=make(chan struct{}); var wg sync.WaitGroup
		for i:=0;i<n;i++ { wg.Add(1); go func(){
			runtime.LockOSThread(); tid:=syscall.Gettid()
			attemptTID,e:=v7r21AttemptAuthorityRegainOnCurrentLockedThread(uid)
			if e==nil && attemptTID!=tid { e=fmt.Errorf("regain-attempt-tid-mismatch-created-%d-attempt-%d",tid,attemptTID) }
			ready<-proof{tid,e}; <-release; runtime.UnlockOSThread(); wg.Done()
		}() }
		for i:=0;i<n;i++ { select {
		case p:=<-ready:
			unique[p.tid]=struct{}{}; if _,ok:=pre[p.tid]; !ok {newSeen[p.tid]=struct{}{}}
			if p.err!=nil { close(release); wg.Wait(); return len(unique),len(newSeen),regainDenied,p.err }
			regainDenied++
			if err:=v7r21VerifyTaskOrdinary(p.tid,uid); err!=nil { close(release); wg.Wait(); return len(unique),len(newSeen),regainDenied,err }
		case <-time.After(3*time.Second): close(release); wg.Wait(); return len(unique),len(newSeen),regainDenied,fmt.Errorf("postdrop-thread-create-timeout") }
		}
		for check:=0;check<32;check++ { if _,err:=v7r21VerifyAllTasks(uid,false); err!=nil { close(release); wg.Wait(); return len(unique),len(newSeen),regainDenied,err }; runtime.Gosched() }
		close(release); wg.Wait(); runtime.Gosched()
	}
	if len(newSeen)<1{return len(unique),0,regainDenied,fmt.Errorf("no-new-postdrop-tid-observed")}
	if regainDenied<1{return len(unique),len(newSeen),0,fmt.Errorf("no-new-thread-regain-attempt")}
	return len(unique),len(newSeen),regainDenied,nil
}
'''
    src=src[:start]+replacement+src[end:]
    old='uniqueStress,newStress,err:=v7r21PostDropThreadCreationStress(uid,preTIDs); if err!=nil{return 0,fmt.Errorf("post-safe-thread-creation-stress:%w",err)}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R21_POSTDROP_THREAD_CREATION_STRESS_PASS unique_tids=%d new_tids=%d runtime=OFF\\n",uniqueStress,newStress)'
    new='uniqueStress,newStress,regainDenied,err:=v7r21PostDropThreadCreationStress(uid,preTIDs); if err!=nil{return 0,fmt.Errorf("post-safe-thread-creation-stress:%w",err)}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R21_POSTDROP_THREAD_CREATION_STRESS_PASS unique_tids=%d new_tids=%d per_thread_regain_denied=%d runtime=OFF\\n",uniqueStress,newStress,regainDenied)'
    src=once(src,old,new,'helper-stress-return-regain-count')
    if 'syscall.AllThreadsSyscall(syscall.SYS_SETRESUID' not in src: raise SystemExit('allthreads-production-drop-missing')
    if 'syscall.RawSyscall(syscall.SYS_SETRESUID' not in src: raise SystemExit('per-new-thread-regain-attempt-missing')
    if src.count('PHASE_C_V19_7_36_V7R21_IRREVERSIBLE_USER_DROP_COMPLETE')!=1: raise SystemExit('safe-boundary-marker-count')
    return src

def patch_guard(src):
    src=src.replace('v7r20','v7r21').replace('V7R20','V7R21')
    if '/usr/local/bin/multiverse-v36-ui-ready-v7r21' not in src: raise SystemExit('guard-helper-path-missing')
    if '__V7R21_HELPER_SHA256__' not in src: raise SystemExit('guard-helper-hash-placeholder-missing')
    return src

def main():
    if len(sys.argv)!=5: raise SystemExit('usage: patcher V7R20_GUARD V7R20_HELPER OUT_GUARD OUT_HELPER')
    ing,inh,outg,outh=map(pathlib.Path,sys.argv[1:])
    outg.write_text(patch_guard(ing.read_text(encoding='utf-8')),encoding='utf-8')
    outh.write_text(patch_helper(inh.read_text(encoding='utf-8')),encoding='utf-8')
    print('V7R21_NEW_THREAD_REGAIN_PATCHER_PASS')

if __name__=='__main__': main()
