package main

import (
	"fmt"
	"os"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"
)

const authorityUID uint32 = 64173

func getresuid() (uint32,uint32,uint32,error) { var r,e,s uint32; _,_,er:=syscall.Syscall(syscall.SYS_GETRESUID,uintptr(unsafe.Pointer(&r)),uintptr(unsafe.Pointer(&e)),uintptr(unsafe.Pointer(&s))); if er!=0{return 0,0,0,er}; return r,e,s,nil }
func getfsuid() uint32 { r,_,_:=syscall.Syscall(syscall.SYS_SETFSUID,^uintptr(0),0,0); return uint32(r) }
func taskUIDs() ([][4]uint32,error) { ents,err:=os.ReadDir("/proc/self/task"); if err!=nil{return nil,err}; out:=make([][4]uint32,0,len(ents)); for _,ent:=range ents { if !ent.IsDir(){continue}; if _,e:=strconv.ParseUint(ent.Name(),10,64); e!=nil{continue}; b,e:=os.ReadFile("/proc/self/task/"+ent.Name()+"/status"); if e!=nil{return nil,e}; for _,ln:=range strings.Split(string(b),"\n") { if strings.HasPrefix(ln,"Uid:") { f:=strings.Fields(ln); if len(f)!=5{return nil,fmt.Errorf("uid-fields")}; var u [4]uint32; for i:=0;i<4;i++ { n,e:=strconv.ParseUint(f[i+1],10,32); if e!=nil{return nil,e}; u[i]=uint32(n) }; out=append(out,u); break } } }; return out,nil }
func main(){
	if len(os.Args)!=1{panic("args")}; r,e,_,err:=getresuid(); if err!=nil{panic(err)}
	if e==0 { if r==0||r==authorityUID{panic("setuid-root ordinary ruid required")}; if _,_,er:=syscall.AllThreadsSyscall(syscall.SYS_SETFSUID,uintptr(authorityUID),0,0); er!=0{panic(er)}; if _,_,er:=syscall.AllThreadsSyscall(syscall.SYS_SETRESUID,uintptr(r),uintptr(authorityUID),uintptr(authorityUID)); er!=0{panic(er)} }
	r,e,s,err:=getresuid(); if err!=nil{panic(err)}; if r==0||r==authorityUID||e!=authorityUID||s!=authorityUID||getfsuid()!=authorityUID{panic("protected-credentials-required")}
	runtime.GOMAXPROCS(4); ready:=make(chan struct{},4); release:=make(chan struct{}); var wg sync.WaitGroup
	for i:=0;i<4;i++ { wg.Add(1); go func(){runtime.LockOSThread(); ready<-struct{}{}; <-release; runtime.UnlockOSThread(); wg.Done()}() }
	for i:=0;i<4;i++ { select {case <-ready: case <-time.After(3*time.Second): panic("thread-timeout")} }
	before,err:=taskUIDs(); if err!=nil||len(before)<2{panic("precondition-multithread")}; uid:=r
	if _,_,er:=syscall.Syscall(syscall.SYS_SETFSUID,uintptr(uid),0,0); er!=0{panic(er)}
	if _,_,er:=syscall.Syscall(syscall.SYS_SETRESUID,uintptr(uid),uintptr(uid),uintptr(uid)); er!=0{panic(er)}
	after,err:=taskUIDs(); if err!=nil{panic(err)}; ordinary:=0; retained:=0
	for _,u:=range after { if u==[4]uint32{uid,uid,uid,uid}{ordinary++}; if u[1]==authorityUID||u[2]==authorityUID||u[3]==authorityUID{retained++} }
	close(release); wg.Wait(); if ordinary<1||retained<1{panic(fmt.Sprintf("negative-control-not-reproduced ordinary=%d retained=%d tasks=%v",ordinary,retained,after))}
	fmt.Printf("V7R18_RAW_THREAD_DROP_NEGATIVE_CONTROL_REPRODUCED=true ordinary_threads=%d retained_authority_threads=%d total_tasks=%d\n",ordinary,retained,len(after)); fmt.Println("RUNTIME=OFF")
}
