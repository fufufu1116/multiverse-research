#!/usr/bin/env python3
import pathlib,sys

def once(src,old,new,label):
    n=src.count(old)
    if n!=1: raise SystemExit(f'{label}: expected exactly one anchor, got {n}')
    return src.replace(old,new,1)

def patch_helper(src):
    src=src.replace('v7r19','v7r20').replace('V7R19','V7R20')
    anchor='''func v7r20DropIrreversibly(uid uint32) (int,error) {\n'''
    insert=r'''func v7r20TaskIDs() (map[int]struct{},error) {
	ents,err:=os.ReadDir("/proc/self/task"); if err!=nil{return nil,err}
	out:=map[int]struct{}{}
	for _,ent:=range ents { if !ent.IsDir(){continue}; n,e:=strconv.Atoi(ent.Name()); if e==nil{out[n]=struct{}{}} }
	return out,nil
}

func v7r20VerifyTaskOrdinary(tid int,uid uint32) error {
	m,err:=v7r20ReadTaskStatus(fmt.Sprintf("/proc/self/task/%d/status",tid)); if err!=nil{return err}
	f:=strings.Fields(m["Uid:"]); if len(f)!=4{return fmt.Errorf("task-%d-uid-fields",tid)}
	for i,s:=range f { n,e:=strconv.ParseUint(s,10,32); if e!=nil||uint32(n)!=uid{return fmt.Errorf("task-%d-uid-%d",tid,i)} }
	if m["NoNewPrivs:"]!="1" { return fmt.Errorf("task-%d-nnp",tid) }
	for _,k:=range []string{"CapInh:","CapPrm:","CapEff:","CapAmb:"} { if m[k]!="0000000000000000" { return fmt.Errorf("task-%d-%s",tid,strings.TrimSuffix(k,":")) } }
	return nil
}

func v7r20PostDropThreadCreationStress(uid uint32, pre map[int]struct{}) (int,int,error) {
	unique:=map[int]struct{}{}; newSeen:=map[int]struct{}{}
	for round:=0;round<8;round++ {
		const n=12
		ready:=make(chan int,n); release:=make(chan struct{}); var wg sync.WaitGroup
		for i:=0;i<n;i++ { wg.Add(1); go func(){ runtime.LockOSThread(); tid:=syscall.Gettid(); ready<-tid; <-release; runtime.UnlockOSThread(); wg.Done() }() }
		for i:=0;i<n;i++ { select { case tid:=<-ready: unique[tid]=struct{}{}; if _,ok:=pre[tid]; !ok {newSeen[tid]=struct{}{}}; if err:=v7r20VerifyTaskOrdinary(tid,uid); err!=nil { close(release); wg.Wait(); return len(unique),len(newSeen),err }; case <-time.After(3*time.Second): close(release); wg.Wait(); return len(unique),len(newSeen),fmt.Errorf("postdrop-thread-create-timeout") } }
		// Keep the newly-created locked OS threads live while doing substantive
		// per-task verification. This gives the external observer a deterministic
		// work window without adding a production sleep or a control channel.
		for check:=0;check<32;check++ { if _,err:=v7r20VerifyAllTasks(uid,false); err!=nil { close(release); wg.Wait(); return len(unique),len(newSeen),err }; runtime.Gosched() }
		close(release); wg.Wait(); runtime.Gosched()
	}
	if len(newSeen)<1{return len(unique),0,fmt.Errorf("no-new-postdrop-tid-observed")}
	return len(unique),len(newSeen),nil
}

'''
    src=once(src,anchor,insert+anchor,'helper-insert-postdrop-thread-stress')
    old='''\tbefore,err:=v7r20VerifyAllTasks(uid,true); if err!=nil{return 0,fmt.Errorf("pre-drop-all-task-proof:%w",err)}\n\tif before<2{return 0,fmt.Errorf("pre-drop-not-multithreaded")}\n'''
    new='''\tbefore,err:=v7r20VerifyAllTasks(uid,true); if err!=nil{return 0,fmt.Errorf("pre-drop-all-task-proof:%w",err)}\n\tif before<2{return 0,fmt.Errorf("pre-drop-not-multithreaded")}\n\tpreTIDs,err:=v7r20TaskIDs(); if err!=nil{return 0,fmt.Errorf("pre-drop-tids:%w",err)}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R20_THREAD_CREATION_STRESS_ARMED pre_tasks=%d runtime=OFF\\n",len(preTIDs))\n'''
    src=once(src,old,new,'helper-pre-tid-capture')
    # The v7r19 function verifies post-drop static tasks before the final UID,
    # fsuid, caps, no_new_privs, regain and dumpability checks. Keep that order.
    # The v7r20 active creation stress must occur only after a truthful safe
    # boundary marker so external evidence can observe genuinely post-boundary
    # TID births rather than infer them from an internal counter.
    old='''\tif maxTasks<2{return 0,fmt.Errorf("post-drop-not-multithreaded")}\n\tr,e,s,err:=v7r20GetResUIDs();'''
    new='''\tif maxTasks<2{return 0,fmt.Errorf("post-drop-not-multithreaded")}\n\tr,e,s,err:=v7r20GetResUIDs();'''
    src=once(src,old,new,'helper-preserve-postdrop-order')
    old='''\tif err:=v7r20SetNondumpable(); err!=nil{return 0,err}\n\treturn maxTasks,nil\n}'''
    new='''\tif err:=v7r20SetNondumpable(); err!=nil{return 0,err}\n\tif _,e:=v7r20VerifyAllTasks(uid,false); e!=nil{return 0,fmt.Errorf("safe-boundary-all-task-proof:%w",e)}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R20_IRREVERSIBLE_USER_DROP_COMPLETE uid=%d fsuid=%d no_new_privs=1 caps=0 all_tasks_ordinary=true proof_tasks=%d authority_fd=retired runtime=OFF\\n",uid,uid,maxTasks)\n\tuniqueStress,newStress,err:=v7r20PostDropThreadCreationStress(uid,preTIDs); if err!=nil{return 0,fmt.Errorf("post-safe-thread-creation-stress:%w",err)}\n\tfmt.Printf("PHASE_C_V19_7_36_V7R20_POSTDROP_THREAD_CREATION_STRESS_PASS unique_tids=%d new_tids=%d runtime=OFF\\n",uniqueStress,newStress)\n\tif _,e:=v7r20VerifyAllTasks(uid,false); e!=nil{return 0,fmt.Errorf("post-safe-stress-all-task-proof:%w",e)}\n\treturn maxTasks,nil\n}'''
    src=once(src,old,new,'helper-safe-boundary-before-active-stress')
    # The inherited main marker would otherwise duplicate the safe-boundary
    # token after the stress has completed. Rename only that inherited marker;
    # the authoritative boundary marker is emitted inside DropIrreversibly.
    old='''\tfmt.Printf("PHASE_C_V19_7_36_V7R20_IRREVERSIBLE_USER_DROP_COMPLETE uid=%d fsuid=%d no_new_privs=1 caps=0 all_tasks_ordinary=true proof_tasks=%d authority_fd=retired runtime=OFF\\n", targetUID,targetUID,proofTasks)'''
    new='''\tfmt.Printf("PHASE_C_V19_7_36_V7R20_POST_SAFE_THREAD_STRESS_COMPLETE uid=%d fsuid=%d no_new_privs=1 caps=0 all_tasks_ordinary=true proof_tasks=%d authority_fd=retired runtime=OFF\\n", targetUID,targetUID,proofTasks)'''
    src=once(src,old,new,'helper-deduplicate-safe-boundary-marker')
    if 'syscall.AllThreadsSyscall(syscall.SYS_SETRESUID' not in src: raise SystemExit('allthreads-setresuid-missing')
    if 'v7r20PostDropThreadCreationStress' not in src: raise SystemExit('thread-stress-missing')
    if src.count('PHASE_C_V19_7_36_V7R20_IRREVERSIBLE_USER_DROP_COMPLETE') != 1: raise SystemExit('safe-boundary-marker-count')
    return src

def patch_guard(src):
    src=src.replace('v7r19','v7r20').replace('V7R19','V7R20')
    if '/usr/local/bin/multiverse-v36-ui-ready-v7r20' not in src: raise SystemExit('guard-helper-path-missing')
    if '__V7R20_HELPER_SHA256__' not in src: raise SystemExit('guard-helper-hash-placeholder-missing')
    return src

def main():
    if len(sys.argv)!=5: raise SystemExit('usage: patcher V7R19_GUARD V7R19_HELPER OUT_GUARD OUT_HELPER')
    ing,inh,outg,outh=map(pathlib.Path,sys.argv[1:])
    outg.write_text(patch_guard(ing.read_text(encoding='utf-8')),encoding='utf-8')
    outh.write_text(patch_helper(inh.read_text(encoding='utf-8')),encoding='utf-8')
    print('V7R20_MIXED_TRANSITION_THREAD_CREATION_PATCHER_PASS')

if __name__=='__main__': main()
