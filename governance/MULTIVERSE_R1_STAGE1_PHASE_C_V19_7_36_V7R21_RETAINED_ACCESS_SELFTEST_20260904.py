#!/usr/bin/env python3
import errno,fcntl,hashlib,importlib.util,json,os,re,selectors,subprocess,time
BASE='/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R20_MIXED_TID_ATTACK_SELFTEST_20260904.py'
spec=importlib.util.spec_from_file_location('v7r20',BASE); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
NAME='rate-v7r21-test'; AUTH_UID=M.AUTH_UID

def configure_base():
    M.NAME=NAME
    M.GUARD='/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r21'
    M.LAUNCHER_C=M.LAUNCHER_C.replace('v7r20','v7r21').replace('rate-v7r20-test',NAME)

def task_states(pid):
    out={}
    try:tids=os.listdir(f'/proc/{pid}/task')
    except (FileNotFoundError,PermissionError):return out
    for s_tid in tids:
        try:
            tid=int(s_tid); d={}
            for line in open(f'/proc/{pid}/task/{tid}/status',encoding='utf-8'):
                for k in ('Uid:','CapInh:','CapPrm:','CapEff:','CapAmb:','NoNewPrivs:'):
                    if line.startswith(k): d[k]=line.split(':',1)[1].strip()
            u=tuple(map(int,d.get('Uid:','').split()))
            if len(u)!=4: raise RuntimeError(f'tid-{tid}-uid-fields')
            out[tid]={'uid':u,'fsuid':u[3],'cap_inh':d.get('CapInh:'),'cap_prm':d.get('CapPrm:'),'cap_eff':d.get('CapEff:'),'cap_amb':d.get('CapAmb:'),'nnp':d.get('NoNewPrivs:')}
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    return out

def validate_ordinary_state(tid,s,uid):
    if s['uid']!=(uid,uid,uid,uid) or s['fsuid']!=uid: raise SystemExit(f'MATERIAL_POST_SAFE_NEW_TID_UID:tid={tid}:{s}')
    if s['nnp']!='1': raise SystemExit(f'MATERIAL_POST_SAFE_NEW_TID_NNP:tid={tid}:{s}')
    for k in ('cap_inh','cap_prm','cap_eff','cap_amb'):
        if s[k]!='0000000000000000': raise SystemExit(f'MATERIAL_POST_SAFE_NEW_TID_CAP:tid={tid}:{k}={s[k]}')

def prove_nondumpable_ptrace_denial(tid):
    rv,er=M.ptrace(M.PTRACE_ATTACH,tid)
    if rv==0:
        try:os.waitpid(tid,0)
        except ChildProcessError:pass
        M.ptrace(M.PTRACE_DETACH,tid)
        raise SystemExit(f'MATERIAL_PTRACE_ELIGIBLE_TID:tid={tid}')
    if er not in (errno.EPERM,errno.ESRCH): raise SystemExit(f'AMBIGUOUS_PTRACE_ELIGIBILITY:tid={tid}:errno={er}')
    return er

def retained_authority_fd_attack(fd,baseline):
    # Exact sealed authority memfd: created before the protected transition,
    # inherited by the target, and intentionally retained by the attacker.
    results=[]
    try:
        os.pwrite(fd,b'X',0); raise SystemExit('MATERIAL_RETAINED_AUTHORITY_FD_PWRITE_SUCCEEDED')
    except OSError as e:
        if e.errno not in (errno.EPERM,errno.EACCES): raise
        results.append(f'pwrite={e.errno}')
    try:
        os.ftruncate(fd,0); raise SystemExit('MATERIAL_RETAINED_AUTHORITY_FD_TRUNCATE_SUCCEEDED')
    except OSError as e:
        if e.errno not in (errno.EPERM,errno.EACCES): raise
        results.append(f'truncate={e.errno}')
    seals=fcntl.fcntl(fd,1034) # Linux F_GET_SEALS
    if seals!=M.SEALS: raise SystemExit(f'MATERIAL_RETAINED_AUTHORITY_FD_SEALS_CHANGED:{seals}')
    now=os.pread(fd,1<<20,0)
    if hashlib.sha256(now).hexdigest()!=baseline: raise SystemExit('MATERIAL_RETAINED_AUTHORITY_FD_CONTENT_CHANGED')
    return ','.join(results)

def main():
    if os.geteuid()!=0: raise SystemExit('root preparation required')
    configure_base(); M.build_launcher()
    uid=int(subprocess.check_output(['id','-u','codespace'],text=True)); gid=int(subprocess.check_output(['id','-g','codespace'],text=True))
    os.setgroups([]); os.setresgid(gid,gid,gid); os.setresuid(uid,uid,uid)
    fd=M.make_authority(); baseline=hashlib.sha256(os.pread(fd,1<<20,0)).hexdigest()
    p=subprocess.Popen(['/tmp/v7r20-launcher',NAME,str(fd),M.GEN],env={'CODESPACES':'true','CODESPACE_NAME':NAME},pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    sel=selectors.DefaultSelector(); sel.register(p.stdout,selectors.EVENT_READ)
    helper_entry=retired=drop_marker=stress_armed=stress_pass=False; addr=None
    protected_attempts=pre_boundary_attach_denials=mixed_snapshots=mixed_tid_attempts=retained_fd_mixed_attempts=0
    mixed_targeted=set(); all_tids=set(); pre_safe_tids=set(); post_safe_records={}; post_safe_scans=0; out=[]; deadline=time.time()+15
    while time.time()<deadline and p.poll() is None:
        for key,_ in sel.select(timeout=0):
            line=key.fileobj.readline()
            if line:
                out.append(line)
                if 'V7R21_AUTHORITY_RETIRED_BEFORE_PROTECTED_HELPER_EXEC' in line:retired=True
                if 'V7R21_PROTECTED_HELPER_ENTRY' in line:
                    helper_entry=True; m=re.search(r'codespace_name_addr=0x([0-9a-fA-F]+)',line); addr=int(m.group(1),16) if m else addr
                if 'V7R21_THREAD_CREATION_STRESS_ARMED' in line:stress_armed=True
                if 'V7R21_POSTDROP_THREAD_CREATION_STRESS_PASS' in line:
                    stress_pass=True
                    m=re.search(r'per_thread_regain_denied=(\d+)',line)
                    if not m or int(m.group(1))<1: p.kill(); raise SystemExit('new-thread regain-denial count absent')
                if 'V7R21_IRREVERSIBLE_USER_DROP_COMPLETE' in line:
                    if 'all_tasks_ordinary=true' not in line: p.kill(); raise SystemExit('safe marker missing all-task proof')
                    drop_marker=True
        states=task_states(p.pid); tids=set(states); all_tids|=tids
        ordinary=[tid for tid,s in states.items() if s['uid']==(uid,uid,uid,uid)]
        authority=[tid for tid,s in states.items() if AUTH_UID in s['uid'][1:]]
        protected=bool(states and len(authority)==len(states)); mixed=bool(ordinary and authority); ordinary_all=bool(states and len(ordinary)==len(states))
        if not drop_marker: pre_safe_tids|=tids
        else:
            post_safe_scans+=1
            for tid in sorted(tids-pre_safe_tids):
                s=states[tid]; validate_ordinary_state(tid,s,uid)
                er=prove_nondumpable_ptrace_denial(tid)
                rec=dict(s); rec['ptrace_attach_errno']=er; rec['dumpability_evidence']='kernel_ptrace_attach_denied_after_helper_PR_SET_DUMPABLE_0'
                post_safe_records[tid]=rec
        if protected:
            if helper_entry:
                for tid in list(states):
                    prove_nondumpable_ptrace_denial(tid); pre_boundary_attach_denials+=1
            bad=M.attack_tid(p.pid,p.pid,addr,fd); protected_attempts+=1
            if bad:p.kill(); raise SystemExit('MATERIAL_PROTECTED_TRANSIENT_ACCESS:'+bad)
        elif mixed:
            mixed_snapshots+=1
            retained_authority_fd_attack(fd,baseline); retained_fd_mixed_attempts+=1
            for tid in ordinary:
                mixed_tid_attempts+=1; mixed_targeted.add(tid)
                bad=M.attack_tid(p.pid,tid,addr,fd)
                if bad:p.kill(); raise SystemExit(f'MATERIAL_MIXED_TID_ACCESS:tid={tid}:'+bad)
        elif ordinary_all and not drop_marker:
            for tid in ordinary:
                bad=M.attack_tid(p.pid,tid,addr,fd)
                if bad:p.kill(); raise SystemExit(f'MATERIAL_ORDINARY_BEFORE_SAFE_BOUNDARY:tid={tid}:'+str(bad))
        time.sleep(0.0004)
    try: rc=p.wait(timeout=3)
    except subprocess.TimeoutExpired: p.kill(); rc=p.wait(timeout=3)
    out.append(p.stdout.read() or ''); text=''.join(out); print(text,end='')
    if not retired or not helper_entry or not stress_armed or not drop_marker or not stress_pass: raise SystemExit('required helper boundary marker missing')
    if protected_attempts<1 or pre_boundary_attach_denials<1: raise SystemExit('no exact-boundary preattach challenge')
    if mixed_snapshots<1 or mixed_tid_attempts<1 or not mixed_targeted: raise SystemExit('mixed-state per-TID proof absent')
    if retained_fd_mixed_attempts<1: raise SystemExit('true retained authority FD not attacked during mixed state')
    if not post_safe_records: raise SystemExit('no externally persisted post-safe new-TID full-state record')
    encoded=json.dumps({str(k):v for k,v in sorted(post_safe_records.items())},sort_keys=True,separators=(',',':'))
    print(f'PRELAB_V7R21_PRE_BOUNDARY_PTRACE_ATTACH_DENIALS={pre_boundary_attach_denials}')
    print('PRELAB_V7R21_PREATTACHED_TRACER_EXACT_BOUNDARY_RESULT=ATTACH_DENIED_BY_KERNEL_NONDUMPABLE_BEFORE_MIXED')
    print(f'PRELAB_V7R21_RETAINED_AUTHORITY_FD_MIXED_ATTACKS={retained_fd_mixed_attempts}')
    print('PRELAB_V7R21_TRUE_RETAINED_FD_VARIANT=true')
    print(f'PRELAB_V7R21_MIXED_SNAPSHOTS={mixed_snapshots}')
    print(f'PRELAB_V7R21_MIXED_TID_ATTACK_ATTEMPTS={mixed_tid_attempts}')
    print(f'PRELAB_V7R21_POST_SAFE_NEW_TID_FULL_STATE_RECORDS={len(post_safe_records)}')
    print(f'PRELAB_V7R21_POST_SAFE_NEW_TID_FULL_STATE_SHA256={hashlib.sha256(encoded.encode()).hexdigest()}')
    print('PRELAB_V7R21_POST_SAFE_PER_BIRTH_FAIL_CLOSED=true')
    print('PRELAB_V7R21_DUMPABILITY_PTRACE_ELIGIBILITY_PROOF=KERNEL_PTRACE_ATTACH_DENIAL_PER_OBSERVED_NEW_TID')
    print(f'PRELAB_V7R21_UNIQUE_TIDS_OBSERVED={len(all_tids)}')
    print(f'PRELAB_V7R21_POST_SAFE_SCANS={post_safe_scans}')
    print(f'PRELAB_V7R21_TARGET_RC={rc}')
    print('RUNTIME=OFF')
if __name__=='__main__': main()
