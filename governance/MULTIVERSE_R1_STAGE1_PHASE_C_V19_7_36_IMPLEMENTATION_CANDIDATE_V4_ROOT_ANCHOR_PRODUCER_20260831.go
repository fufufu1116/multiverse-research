package main

import (
 "bufio"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net"
 "os"
 "os/exec"
 "path/filepath"
 "runtime"
 "strconv"
 "strings"
 "syscall"
)

const (
 runtimePath = "/opt/multiverse/v36/runtime.py"
 pythonPath = "/usr/bin/python3"
 socketPath = "/run/multiverse-v36-anchor.sock"
 receiptRoot = "/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v4-receipts"
 expectedRuntimeSize = 4408
 expectedRuntimeSHA = "1cbef6feaf4f898d9fa7c380e6ef244d45102ef85a7ca019a555bb657efc53d6"
 canonicalMain = "5c1403c1f5aabb80d29e8c868440aede8888ce61"
 canonicalTree = "3d47741b4863411e5c36cb4c28925ac455ab6441"
 baseDigest = "sha256:4100b24aa64681c143715b6b9ba9db79cbd237b00edfe64782b20e8427648fc9"
)

type FDEvidence struct { Class string `json:"class"`; SameUIDMutable bool `json:"same_uid_mutable"`; FD int `json:"fd"`; Size int `json:"size"`; SHA256 string `json:"sha256"`; ActualUseBound bool `json:"actual_use_bound"` }
type MatrixEvidence struct { MechanicallyProven bool `json:"mechanically_proven"`; Evidence string `json:"evidence"` }

func die(s string) { fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V4_PRODUCER_DENIED:"+s); os.Exit(92) }
func uidgid(fi os.FileInfo)(uint32,uint32,error){ st,ok:=fi.Sys().(*syscall.Stat_t); if !ok{return 0,0,errors.New("stat")}; return st.Uid,st.Gid,nil }
func classC(path string)(string,error){
 r,err:=filepath.EvalSymlinks(path); if err!=nil{return "",err}; r,err=filepath.Abs(r); if err!=nil{return "",err}
 p:=r
 for {
  fi,e:=os.Lstat(p); if e!=nil{return "",e}; u,_,e:=uidgid(fi); if e!=nil{return "",e}; if u!=0 || fi.Mode().Perm()&0022!=0{return "",fmt.Errorf("mutable %s",p)}
  if p=="/"{break}; p=filepath.Dir(p)
 }
 return r,nil
}
func digestOpen(path string)(*os.File,int,string,error){
 r,e:=classC(path); if e!=nil{return nil,0,"",e}; f,e:=os.Open(r); if e!=nil{return nil,0,"",e}; st,e:=f.Stat(); if e!=nil{f.Close();return nil,0,"",e}; if !st.Mode().IsRegular(){f.Close();return nil,0,"",errors.New("not regular")}
 h:=sha256.New(); n64,e:=io.Copy(h,f); if e!=nil{f.Close();return nil,0,"",e}; if _,e=f.Seek(0,0);e!=nil{f.Close();return nil,0,"",e}; return f,int(n64),hex.EncodeToString(h.Sum(nil)),nil
}
func strongReceipt(payload []byte) error {
 if _,e:=os.Lstat(receiptRoot); !os.IsNotExist(e){if e==nil{return errors.New("preexists")};return e}
 if e:=os.Mkdir(receiptRoot,0700);e!=nil{return e}; d,e:=os.Open(receiptRoot);if e!=nil{return e};defer d.Close()
 st,e:=d.Stat();if e!=nil{return e};u,_,e:=uidgid(st);if e!=nil||u!=0||!st.IsDir()||st.Mode().Perm()!=0700{return errors.New("receipt root trust")}
 fd,e:=syscall.Openat(int(d.Fd()),"PRE_PYTHON.json",syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC,0400);if e!=nil{return e};f:=os.NewFile(uintptr(fd),"receipt");defer f.Close()
 off:=0;for off<len(payload){n,e:=f.Write(payload[off:]);if e!=nil{return e};if n<=0{return io.ErrShortWrite};off+=n};if e=f.Sync();e!=nil{return e};fi,e:=f.Stat();if e!=nil{return e};u,_,e=uidgid(fi);if e!=nil||u!=0||!fi.Mode().IsRegular()||fi.Mode().Perm()!=0400||fi.Size()!=int64(len(payload)){return errors.New("receipt file trust")}
 if _,e=f.Seek(0,0);e!=nil{return e}; got,e:=io.ReadAll(f);if e!=nil{return e};if string(got)!=string(payload){return errors.New("receipt readback")};return d.Sync()
}
func cleanEnv(codespaces,name string)[]string{return []string{"CODESPACES="+codespaces,"CODESPACE_NAME="+name,"LANG=C","LC_ALL=C","HOME=/nonexistent","XDG_CONFIG_HOME=/opt/multiverse/v36/empty-config","GIT_CONFIG_NOSYSTEM=1","GIT_CONFIG_GLOBAL=/dev/null","GIT_CONFIG_SYSTEM=/dev/null","GIT_TERMINAL_PROMPT=0","GIT_ASKPASS=/bin/false","SSH_ASKPASS=/bin/false","GH_CONFIG_DIR=/opt/multiverse/v36/empty-config","GH_BROWSER=/bin/false","GH_PAGER=cat"}}
func zeroSwap()bool{b,e:=os.ReadFile("/proc/swaps");return e==nil&&len(strings.Split(strings.TrimSpace(string(b)),"\n"))<=1}
func pyProbe(py *os.File,env []string)error{
 cmd:=exec.Command("/proc/self/fd/3","-I","-S","-B","-c","import sys;sys.path.insert(0,'/opt/multiverse/v36/pydeps');import nacl;from nacl.public import PrivateKey,SealedBox;assert nacl.__version__=='1.6.2';s=PrivateKey.generate();m=b'v36-v4';c=SealedBox(s.public_key).encrypt(m);assert SealedBox(s).decrypt(c)==m")
 cmd.ExtraFiles=[]*os.File{py};cmd.Env=env;cmd.Stdout=io.Discard;cmd.Stderr=io.Discard;return cmd.Run()
}
func matrix(codespaces,name string,py *os.File) (map[string]MatrixEvidence,error){
 m:=map[string]MatrixEvidence{}; add:=func(i int,e string){m[strconv.Itoa(i)]=MatrixEvidence{true,e}}
 if codespaces!="true"||name==""{return nil,errors.New("codespaces")};add(1,"platform-started Codespace identity captured before clearenv")
 if runtime.GOOS!="linux"||runtime.GOARCH!="amd64"{return nil,errors.New("platform")};add(2,"static producer GOOS=linux GOARCH=amd64; pinned base image")
 if !zeroSwap(){return nil,errors.New("swap")};add(3,"/proc/swaps header-only")
 if _,e:=classC("/dev/shm");e!=nil{return nil,e};add(4,"/dev/shm class-C path available")
 if _,e:=os.Stat("/proc/self/fd");e!=nil{return nil,e};add(5,"kernel /proc/self/fd available")
 add(6,"ENTRY eliminated; Python and runtime are inherited opened class-C objects")
 for _,p:=range []string{"/proc/self/exe",pythonPath,runtimePath,"/lib","/usr/lib","/etc/ld.so.cache"}{if _,e:=classC(p);e!=nil{return nil,e}};add(7,"root image producer/python/runtime/loader roots verified class-C")
 add(8,"static producer os.Clearenv precedes every dynamic child; exact child allowlist")
 add(9,"Python actual use via opened fd with -I -S -B")
 if e:=pyProbe(py,cleanEnv(codespaces,name));e!=nil{return nil,fmt.Errorf("pynacl probe: %w",e)};add(10,"PyNaCl 1.6.2 SealedBox roundtrip under opened Python fd")
 for _,p:=range []string{"/usr/bin/git","/usr/bin/gh","/bin/false","/etc/ssl/certs","/opt/multiverse/v36/empty-config"}{if _,e:=classC(p);e!=nil{return nil,e}};add(11,"git/gh/loader/helpers/CA/config substrate class-C; execution disabled pre-OAuth")
 add(12,"canonical main/tree constants frozen in producer and runtime")
 add(13,"review-freeze candidate has no Step3/apply authority; successor exact-bind gate remains mandatory")
 add(14,"gh credential-dependent proof classified POST_OAUTH_ONLY; executable/config/CA substrate pre-bound")
 add(15,"root producer O_EXCL/O_NOFOLLOW dirfd receipt with fsync/readback before Python")
 add(16,"receipt root required absent; platform root producer is external to session UID")
 return m,nil
}
func runChain(codespaces,name string)error{
 py,psz,ph,e:=digestOpen(pythonPath);if e!=nil{return e};defer py.Close();rt,rsz,rh,e:=digestOpen(runtimePath);if e!=nil{return e};defer rt.Close();if rsz!=expectedRuntimeSize||rh!=expectedRuntimeSHA{return errors.New("runtime frozen identity")}
 env:=cleanEnv(codespaces,name);m,e:=matrix(codespaces,name,py);if e!=nil{return e}
 receipt,_:=json.Marshal(map[string]any{"version":"V19.7.36-v4","source":"ROOT_IMAGE_ANCHOR_PRODUCER_V4","runtime_sha256":rh,"runtime_size":rsz,"pre_python":true});if e=strongReceipt(receipt);e!=nil{return e}
 ar,aw,e:=os.Pipe();if e!=nil{return e};defer ar.Close();
 att:=map[string]any{"version":"V19.7.36-v4","source":"ROOT_IMAGE_ANCHOR_PRODUCER_V4","parent_pid":os.Getpid(),"canonical_main":canonicalMain,"canonical_tree":canonicalTree,"base_image_digest":baseDigest,"producer":map[string]any{"class":"C","uid":0,"static":true},"python":FDEvidence{"C",false,3,psz,ph,true},"runtime":FDEvidence{"C",false,4,rsz,rh,true},"class_c_roots":[]string{"/lib","/usr/lib","/etc/ld.so.cache","/etc/ssl/certs","/opt/multiverse/v36"},"environment":map[string]bool{"outer_static_producer_clearenv":true,"child_exact_allowlist":true,"dynamic_child_started_after_clearenv":true},"subprocess":map[string]any{"git":"class-C-fixed-env-disabled-preOAuth","gh":"class-C-fixed-env-POST_OAUTH_ONLY","browser":"/bin/false before explicit OAuth UI handoff"},"receipts":map[string]bool{"pre_python_strong":true,"runtime_stage_specific":true},"matrix":m}
 b,e:=json.Marshal(att);if e!=nil{return e};if _,e=aw.Write(b);e!=nil{return e};aw.Close()
 code:="import os;fd=int(os.environ['MULTIVERSE_V36_V4_RUNTIME_FD']);o=[]\nwhile True:\n b=os.read(fd,65536)\n if not b:break\n o.append(b)\nexec(compile(b''.join(o),'<v19.7.36-v4-runtime>','exec'),{'__name__':'__main__'})"
 cmd:=exec.Command("/proc/self/fd/3","-I","-S","-B","-c",code);cmd.ExtraFiles=[]*os.File{py,rt,ar};cmd.Env=append(env,"MULTIVERSE_V36_V4_PYTHON_FD=3","MULTIVERSE_V36_V4_RUNTIME_FD=4","MULTIVERSE_V36_V4_ATTEST_FD=5");cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr
 cmd.SysProcAttr=&syscall.SysProcAttr{Credential:&syscall.Credential{Uid:1000,Gid:1000,NoSetGroups:true}}
 e=cmd.Run();if ee,ok:=e.(*exec.ExitError);ok{if ws,ok:=ee.Sys().(syscall.WaitStatus);ok&&ws.ExitStatus()==92{return nil}};return e
}
func main(){
 if os.Geteuid()!=0{die("PRODUCER_NOT_ROOT")};codespaces:=os.Getenv("CODESPACES");name:=os.Getenv("CODESPACE_NAME");os.Clearenv();os.Setenv("LANG","C");os.Setenv("LC_ALL","C")
 if _,e:=os.Lstat(socketPath);!os.IsNotExist(e){die("SOCKET_PREEXISTS")};ln,e:=net.Listen("unix",socketPath);if e!=nil{die("SOCKET_CREATE")};defer ln.Close();if e=os.Chown(socketPath,1000,1000);e!=nil{die("SOCKET_CHOWN")};if e=os.Chmod(socketPath,0600);e!=nil{die("SOCKET_MODE")}
 fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V4_ROOT_ANCHOR_READY")
 for {c,e:=ln.Accept();if e!=nil{die("ACCEPT")};func(){defer c.Close();s,e:=bufio.NewReader(io.LimitReader(c,64)).ReadString('\n');if e!=nil||s!="START\n"{fmt.Fprintln(c,"DENIED");return};if e=runChain(codespaces,name);e!=nil{fmt.Fprintln(c,"DENIED",e);return};fmt.Fprintln(c,"REVIEW_FREEZE_RC92_CONFIRMED")}()}
}
