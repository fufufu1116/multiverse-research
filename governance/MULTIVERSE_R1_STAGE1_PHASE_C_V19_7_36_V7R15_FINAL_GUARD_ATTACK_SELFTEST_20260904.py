#!/usr/bin/env python3
import ctypes,errno,fcntl,json,os,pathlib,selectors,subprocess,time

AUTH_UID=64173
PTRACE_ATTACH=16
PTRACE_DETACH=17
F_ADD_SEALS=1033
F_SEAL_SEAL=0x1
F_SEAL_SHRINK=0x2
F_SEAL_GROW=0x4
F_SEAL_WRITE=0x8
SEALS=F_SEAL_SEAL|F_SEAL_SHRINK|F_SEAL_GROW|F_SEAL_WRITE
NAME='rate-v7r15-test'
GEN='00112233445566778899aabbccddeeff'

LAUNCHER_C=r'''#define _GNU_SOURCE
#include <stdio.h>
#include <sys/types.h>
#include <sys/prctl.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#define AUTH_UID 64173
static const char guard[]="/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r15";
static int valid_name(const char*s){size_t n=strlen(s);if(!n||n>128)return 0;for(size_t i=0;i<n;i++){char c=s[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'))return 0;}return 1;}
int main(int argc,char**argv){
 if(argc!=4||geteuid()!=0)return 90;
 uid_t r=getuid();if(r==0||r==AUTH_UID||!valid_name(argv[1]))return 91;
 char *end=0;long fd=strtol(argv[2],&end,10);if(!end||*end||fd<3)return 92;
 if(strlen(argv[3])!=32)return 93;
 if(setresuid(r,AUTH_UID,AUTH_UID)!=0)return 94;
 uid_t rr=0,ee=0,ss=0;if(getresuid(&rr,&ee,&ss)!=0||rr!=r||ee!=AUTH_UID||ss!=AUTH_UID)return 95;
 if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)!=0)return 96;
 if(prctl(PR_SET_DUMPABLE,0,0,0,0)!=0)return 97;
 char e1[]="CODESPACES=true";char e2[160];snprintf(e2,sizeof(e2),"CODESPACE_NAME=%s",argv[1]);char*env[]={e1,e2,0};
 char*av[]={(char*)guard,argv[1],argv[2],argv[3],0};execve(guard,av,env);return 98;
}
'''

class IOV(ctypes.Structure):
    _fields_=[('iov_base',ctypes.c_void_p),('iov_len',ctypes.c_size_t)]
libc=ctypes.CDLL(None,use_errno=True)
libc.ptrace.argtypes=[ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_void_p]
libc.ptrace.restype=ctypes.c_long
libc.process_vm_writev.argtypes=[ctypes.c_int,ctypes.POINTER(IOV),ctypes.c_ulong,ctypes.POINTER(IOV),ctypes.c_ulong,ctypes.c_ulong]
libc.process_vm_writev.restype=ctypes.c_ssize_t

def ptrace(req,pid):
    ctypes.set_errno(0);rv=libc.ptrace(req,pid,None,None);return rv,ctypes.get_errno()

def uid_tuple(pid):
    try:
        with open(f'/proc/{pid}/status',encoding='utf-8') as f:
            for line in f:
                if line.startswith('Uid:'):return tuple(map(int,line.split()[1:5]))
    except FileNotFoundError:return None
    return None

def build_launcher():
    p=pathlib.Path('/tmp/v7r15-final-launcher.c');p.write_text(LAUNCHER_C,encoding='utf-8')
    subprocess.run(['gcc','-O2','-fno-stack-protector','-Wl,-z,noexecstack','-o','/tmp/v7r15-final-launcher',str(p)],check=True)
    os.chown('/tmp/v7r15-final-launcher',0,0);os.chmod('/tmp/v7r15-final-launcher',0o4555)

def make_authority():
    fd=os.memfd_create('multiverse-v36-v7r15-authority-test',os.MFD_ALLOW_SEALING)
    snap={'version':'V19.7.36-v7r15','generation':GEN,'codespace':NAME,'mode':'commit','reason':'READY','before':60,'after':59,'reset':1924995600,'status_sha256':'a'*64,'control_sha256':'b'*64,'runtime':'OFF'}
    b=(json.dumps(snap,sort_keys=True,separators=(',',':'))+'\n').encode();os.write(fd,b);os.lseek(fd,0,os.SEEK_SET)
    fcntl.fcntl(fd,F_ADD_SEALS,SEALS);os.set_inheritable(fd,True);return fd

def attack_once(pid):
    rv,er=ptrace(PTRACE_ATTACH,pid)
    if rv==0:
        try: os.waitpid(pid,0)
        except ChildProcessError: pass
        ptrace(PTRACE_DETACH,pid)
        return 'PTRACE_ATTACH_SUCCEEDED'
    if er not in (errno.EPERM,errno.ESRCH):return f'PTRACE_ERR_{er}'
    try:
        x=os.open(f'/proc/{pid}/mem',os.O_RDWR);os.close(x);return 'PROC_MEM_OPEN_SUCCEEDED'
    except OSError as ex:
        if ex.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT,errno.ESRCH):return f'PROC_MEM_ERR_{ex.errno}'
    try:
        x=os.open(f'/proc/{pid}/fd/1',os.O_RDONLY);os.close(x);return 'PROC_FD_OPEN_SUCCEEDED'
    except OSError as ex:
        if ex.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT,errno.ESRCH):return f'PROC_FD_ERR_{ex.errno}'
    byte=ctypes.c_ubyte(0x41);local=IOV(ctypes.cast(ctypes.pointer(byte),ctypes.c_void_p),1);remote=IOV(ctypes.c_void_p(0),1)
    ctypes.set_errno(0);rv=libc.process_vm_writev(pid,ctypes.byref(local),1,ctypes.byref(remote),1,0);er=ctypes.get_errno()
    if rv>=0:return f'PROCESS_VM_WRITE_SUCCEEDED_{rv}'
    if er not in (errno.EPERM,errno.ESRCH):return f'PROCESS_VM_PERMISSION_GATE_NOT_DENIED_{er}'
    return None

def main():
    if os.geteuid()!=0:raise SystemExit('root preparation required')
    build_launcher();uid=int(subprocess.check_output(['id','-u','codespace'],text=True));gid=int(subprocess.check_output(['id','-g','codespace'],text=True))
    os.setgroups([]);os.setresgid(gid,gid,gid);os.setresuid(uid,uid,uid)
    fd=make_authority()
    p=subprocess.Popen(['/tmp/v7r15-final-launcher',NAME,str(fd),GEN],env={'CODESPACES':'true','CODESPACE_NAME':NAME},pass_fds=(fd,),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    protected=False;start=time.time()
    while time.time()-start<2 and p.poll() is None:
        u=uid_tuple(p.pid)
        if u and u[0]!=u[1] and u[1]==AUTH_UID and u[2]==AUTH_UID:protected=True;break
    if not protected:
        p.kill();raise SystemExit('protected credential boundary not observed')
    sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
    attempts=0;out=[];sealed=False;deadline=time.time()+5
    while time.time()<deadline and p.poll() is None and not sealed:
        bad=attack_once(p.pid);attempts+=1
        if bad:p.kill();raise SystemExit(bad)
        for key,_ in sel.select(timeout=0):
            line=key.fileobj.readline()
            if line:
                out.append(line)
                if 'PHASE_C_V19_7_36_V7R15_PROTECTED_GUARD_PASS' in line:sealed=True
    if not sealed:
        p.kill();rest=p.communicate()[0] or '';raise SystemExit('authorization seal marker not observed: '+''.join(out)+rest)
    rc=p.wait(timeout=10);rest=p.stdout.read() or '';out.append(rest);text=''.join(out)
    if attempts<1:raise SystemExit('no attack attempts')
    if rc not in (0,92):raise SystemExit(f'unexpected post-boundary helper rc={rc} out={text!r}')
    print(text,end='')
    print(f'PRELAB_V7R15_FINAL_GUARD_CONTINUOUS_ATTACK_DENIED_UNTIL_AUTHORITY_SEALED=true attempts={attempts}')
    print('PRELAB_V7R15_PARENT_PTRACE_DENIED=true')
    print('PRELAB_V7R15_PROCESS_VM_WRITEV_PERMISSION_DENIED=true')
    print('PRELAB_V7R15_PROC_MEM_DENIED=true')
    print('PRELAB_V7R15_PROC_FD_DENIED=true')
    print('PRELAB_V7R15_YAMA_PARENT_EXCEPTION_DOES_NOT_SUPPLY_PROTECTION=true')
    print('RUNTIME=OFF')
if __name__=='__main__':main()
