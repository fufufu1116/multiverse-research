#!/usr/bin/env python3
import ctypes,errno,fcntl,json,os,pathlib,re,selectors,subprocess,time
AUTH_UID=64173
PTRACE_ATTACH=16; PTRACE_DETACH=17; PTRACE_GETREGS=12; PTRACE_SETREGS=13
F_ADD_SEALS=1033; F_SEAL_SEAL=1; F_SEAL_SHRINK=2; F_SEAL_GROW=4; F_SEAL_WRITE=8
SEALS=F_SEAL_SEAL|F_SEAL_SHRINK|F_SEAL_GROW|F_SEAL_WRITE
NAME='rate-v7r19-test'; GEN='00112233445566778899aabbccddeeff'
HELPER='/usr/local/bin/multiverse-v36-ui-ready-v7r19'
GUARD='/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r19'
LAUNCHER_C=r'''#define _GNU_SOURCE
#include <stdio.h>
#include <sys/types.h>
#include <sys/prctl.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#define AUTH_UID 64173
static const char guard[]="/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r19";
static int valid_name(const char*s){size_t n=strlen(s);if(!n||n>128)return 0;for(size_t i=0;i<n;i++){char c=s[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'))return 0;}return 1;}
int main(int argc,char**argv){if(argc!=4||geteuid()!=0)return 90;uid_t r=getuid();if(r==0||r==AUTH_UID||!valid_name(argv[1]))return 91;char*end=0;long fd=strtol(argv[2],&end,10);if(!end||*end||fd<3)return 92;if(strlen(argv[3])!=32)return 93;if(setresuid(r,AUTH_UID,AUTH_UID)!=0)return 94;uid_t rr=0,ee=0,ss=0;if(getresuid(&rr,&ee,&ss)!=0||rr!=r||ee!=AUTH_UID||ss!=AUTH_UID)return 95;if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)!=0)return 96;if(prctl(PR_SET_DUMPABLE,0,0,0,0)!=0)return 97;char e1[]="CODESPACES=true";char e2[160];snprintf(e2,sizeof(e2),"CODESPACE_NAME=%s",argv[1]);char*env[]={e1,e2,0};char*av[]={(char*)guard,argv[1],argv[2],argv[3],0};execve(guard,av,env);return 98;}
'''
class IOV(ctypes.Structure): _fields_=[('iov_base',ctypes.c_void_p),('iov_len',ctypes.c_size_t)]
class Regs(ctypes.Structure): _fields_=[(n,ctypes.c_ulonglong) for n in ('r15','r14','r13','r12','rbp','rbx','r11','r10','r9','r8','rax','rcx','rdx','rsi','rdi','orig_rax','rip','cs','eflags','rsp','ss','fs_base','gs_base','ds','es','fs','gs')]
libc=ctypes.CDLL(None,use_errno=True)
libc.ptrace.argtypes=[ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_void_p]; libc.ptrace.restype=ctypes.c_long
libc.process_vm_writev.argtypes=[ctypes.c_int,ctypes.POINTER(IOV),ctypes.c_ulong,ctypes.POINTER(IOV),ctypes.c_ulong,ctypes.c_ulong]; libc.process_vm_writev.restype=ctypes.c_ssize_t

def ptrace(req,pid,a=None,d=None): ctypes.set_errno(0); rv=libc.ptrace(req,pid,a,d); return rv,ctypes.get_errno()
def task_uid_tuples(pid):
    out=[]
    try: tids=os.listdir(f'/proc/{pid}/task')
    except (FileNotFoundError,PermissionError): return out
    for tid in tids:
        try:
            for line in open(f'/proc/{pid}/task/{tid}/status',encoding='utf-8'):
                if line.startswith('Uid:'): out.append((int(tid),tuple(map(int,line.split()[1:5])))); break
        except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    return out

def build_launcher():
    p=pathlib.Path('/tmp/v7r19-launcher.c'); p.write_text(LAUNCHER_C,encoding='utf-8')
    subprocess.run(['gcc','-O2','-fno-stack-protector','-Wl,-z,noexecstack','-o','/tmp/v7r19-launcher',str(p)],check=True)
    os.chown('/tmp/v7r19-launcher',0,0); os.chmod('/tmp/v7r19-launcher',0o4555)
def make_authority():
    fd=os.memfd_create('multiverse-v36-v7r19-authority-test',os.MFD_ALLOW_SEALING)
    snap={'version':'V19.7.36-v7r15','generation':GEN,'codespace':NAME,'mode':'commit','reason':'READY','before':60,'after':59,'reset':1924995600,'status_sha256':'a'*64,'control_sha256':'b'*64,'runtime':'OFF'}
    b=(json.dumps(snap,sort_keys=True,separators=(',',':'))+'\n').encode(); os.write(fd,b); os.lseek(fd,0,0); fcntl.fcntl(fd,F_ADD_SEALS,SEALS); os.set_inheritable(fd,True); return fd
def maps_addr(pid):
    try:
        for ln in open(f'/proc/{pid}/maps',encoding='utf-8'):
            a,perms,*_=ln.split()
            if 'w' in perms:
                start=int(a.split('-')[0],16)
                if start:return start
    except (OSError,ValueError): pass
    return None
def attack_once(pid,addr,authority_fd):
    rv,er=ptrace(PTRACE_ATTACH,pid)
    if rv==0:
        try: os.waitpid(pid,0)
        except ChildProcessError: pass
        regs=Regs(); gr,_=ptrace(PTRACE_GETREGS,pid,None,ctypes.byref(regs))
        if gr==0: regs.rax^=1; ptrace(PTRACE_SETREGS,pid,None,ctypes.byref(regs))
        ptrace(PTRACE_DETACH,pid); return 'PTRACE_ATTACH_REGISTER_MODIFY_DETACH_SUCCEEDED'
    if er not in (errno.EPERM,errno.ESRCH): return f'PTRACE_ERR_{er}'
    a=addr or maps_addr(pid)
    try:
        m=os.open(f'/proc/{pid}/mem',os.O_RDWR)
        try:
            if a is not None:
                try: os.pwrite(m,b'Z',a); return 'PROC_MEM_ACTUAL_ADDRESS_WRITE_SUCCEEDED'
                except OSError as ex:
                    if ex.errno not in (errno.EIO,errno.EFAULT,errno.EPERM,errno.EACCES,errno.ESRCH): return f'PROC_MEM_WRITE_ERR_{ex.errno}'
            return 'PROC_MEM_OPEN_SUCCEEDED'
        finally: os.close(m)
    except OSError as ex:
        if ex.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT,errno.ESRCH): return f'PROC_MEM_OPEN_ERR_{ex.errno}'
    try: x=os.open(f'/proc/{pid}/fd/{authority_fd}',os.O_RDONLY); os.close(x); return 'AUTHORITY_PROC_FD_OPEN_SUCCEEDED'
    except OSError as ex:
        if ex.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT,errno.ESRCH): return f'AUTHORITY_PROC_FD_ERR_{ex.errno}'
    if a is not None:
        byte=ctypes.c_ubyte(0x51); local=IOV(ctypes.cast(ctypes.pointer(byte),ctypes.c_void_p),1); remote=IOV(ctypes.c_void_p(a),1)
        ctypes.set_errno(0); rv=libc.process_vm_writev(pid,ctypes.byref(local),1,ctypes.byref(remote),1,0); er=ctypes.get_errno()
        if rv>=0:return f'PROCESS_VM_WRITE_ACTUAL_ADDRESS_SUCCEEDED_{rv}'
        if er not in (errno.EPERM,errno.ESRCH,errno.EFAULT):return f'PROCESS_VM_WRITE_ERR_{er}'
    return None

def main():
    if os.geteuid()!=0: raise SystemExit('root preparation required')
    build_launcher(); uid=int(subprocess.check_output(['id','-u','codespace'],text=True)); gid=int(subprocess.check_output(['id','-g','codespace'],text=True))
    os.setgroups([]); os.setresgid(gid,gid,gid); os.setresuid(uid,uid,uid); fd=make_authority()
    p=subprocess.Popen(['/tmp/v7r19-launcher',NAME,str(fd),GEN],env={'CODESPACES':'true','CODESPACE_NAME':NAME},pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    sel=selectors.DefaultSelector(); sel.register(p.stdout,selectors.EVENT_READ)
    protected_seen=helper_entry_seen=retired_seen=ordinary_seen=drop_marker=False; mixed_seen=False; addr=None; protected_attempts=0; mixed_attempts=0; post_safe=[]; out=[]; deadline=time.time()+8
    while time.time()<deadline and p.poll() is None:
        for key,_ in sel.select(timeout=0):
            line=key.fileobj.readline()
            if line:
                out.append(line)
                if 'V7R19_AUTHORITY_RETIRED_BEFORE_PROTECTED_HELPER_EXEC' in line: retired_seen=True
                if 'V7R19_PROTECTED_HELPER_ENTRY' in line:
                    helper_entry_seen=True; m=re.search(r'codespace_name_addr=0x([0-9a-fA-F]+)',line); addr=int(m.group(1),16) if m else addr
                if 'V7R19_IRREVERSIBLE_USER_DROP_COMPLETE' in line:
                    if 'all_tasks_ordinary=true' not in line: p.kill(); raise SystemExit('drop marker missing all-task proof')
                    m=re.search(r'proof_tasks=(\d+)',line)
                    if not m or int(m.group(1))<2: p.kill(); raise SystemExit('drop marker not multithreaded')
                    drop_marker=True
        tasks=task_uid_tuples(p.pid)
        ordinary_tasks=[u for _,u in tasks if u==(uid,uid,uid,uid)]
        authority_tasks=[u for _,u in tasks if u[1]==AUTH_UID or u[2]==AUTH_UID or u[3]==AUTH_UID]
        protected=bool(tasks and len(authority_tasks)==len(tasks) and all(u[0]==uid for u in authority_tasks))
        ordinary=bool(tasks and len(ordinary_tasks)==len(tasks))
        mixed=bool(tasks and ordinary_tasks and authority_tasks)
        protected_seen|=protected; ordinary_seen|=ordinary; mixed_seen|=mixed
        bad=attack_once(p.pid,addr,fd)
        if protected:
            protected_attempts+=1
            if bad: p.kill(); raise SystemExit('MATERIAL_PROTECTED_TRANSIENT_ACCESS:'+bad)
        elif mixed:
            mixed_attempts+=1
            if bad: p.kill(); raise SystemExit('MATERIAL_MIXED_CREDENTIAL_TRANSITION_ACCESS:'+bad)
        elif ordinary:
            if not helper_entry_seen or not drop_marker:
                if bad: p.kill(); raise SystemExit('MATERIAL_ORDINARY_BEFORE_SAFE_BOUNDARY:'+str(bad))
            elif bad: post_safe.append(bad)
        elif bad:
            p.kill(); raise SystemExit('MATERIAL_UNKNOWN_STATE_ACCESS:'+bad)
    try: rc=p.wait(timeout=3)
    except subprocess.TimeoutExpired: p.kill(); rc=p.wait(timeout=3)
    out.append(p.stdout.read() or ''); text=''.join(out)
    if not protected_seen: raise SystemExit('protected credential state not observed')
    if not retired_seen: raise SystemExit('authority retirement marker missing: '+text)
    if not helper_entry_seen: raise SystemExit('protected helper entry marker missing: '+text)
    if protected_attempts<1: raise SystemExit('no continuous attack attempt during protected state')
    if not drop_marker: raise SystemExit('whole-process drop marker missing: '+text)
    print(text,end='')
    print(f'PRELAB_V7R19_PROTECTED_ATTACK_ATTEMPTS={protected_attempts}')
    print(f'PRELAB_V7R19_MIXED_TRANSITION_OBSERVED={str(mixed_seen).lower()}')
    print(f'PRELAB_V7R19_MIXED_ATTACK_ATTEMPTS={mixed_attempts}')
    print(f'PRELAB_V7R19_POST_SAFE_SAME_UID_ACCESS_NONAUTHORITY_COUNT={len(post_safe)}')
    print('PRELAB_V7R19_ACTUAL_ADDRESS_PROCESS_VM_PROC_MEM_AND_PTRACE_REGISTER_ATTACKS=true')
    print('PRELAB_V7R19_ALL_TASK_DROP_MARKER_VERIFIED=true')
    print(f'PRELAB_V7R19_TARGET_RC={rc}')
    print('RUNTIME=OFF')
if __name__=='__main__': main()
