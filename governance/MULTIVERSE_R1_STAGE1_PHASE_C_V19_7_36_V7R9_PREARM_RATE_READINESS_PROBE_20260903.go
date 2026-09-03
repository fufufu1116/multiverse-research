package main

import (
    "crypto/rand"
    "crypto/tls"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
    "strconv"
    "strings"
    "syscall"
    "time"
)

const (
    githubAPIBase = "https://api.github.com"
    controlPath = "/workspaces/multiverse-research/MULTIVERSE_PRELIVE_START_HERE.md"
    statusPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r9-rate-readiness.txt"
    lockPath = "/opt/multiverse/v36/empty-config"
    guardPath = "/usr/local/bin/multiverse-v36-ui-ready-env-guard-v7r7"
    minBeforeComments = 60
    minAfterComments = 59
)

type rateEnvelope struct { Resources struct { Core struct { Limit int `json:"limit"`; Remaining int `json:"remaining"`; Reset int64 `json:"reset"` } `json:"core"` } `json:"resources"` }
type probeResult struct { Ready bool; Reason string; Before int; After int; Reset int64 }

func validName(s string) bool {
    if len(s)==0 || len(s)>128 { return false }
    for _,r:=range s { if (r>='a'&&r<='z')||(r>='A'&&r<='Z')||(r>='0'&&r<='9')||r=='-' { continue }; return false }
    return true
}

func client()*http.Client { return &http.Client{Transport:&http.Transport{Proxy:nil,TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12}},Timeout:10*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}} }
func parseDate(h http.Header)(time.Time,bool){ s:=strings.TrimSpace(h.Get("Date")); if s==""{return time.Time{},false}; t,e:=http.ParseTime(s); return t.UTC(),e==nil }
func headerInt(h http.Header,k string)(int64,bool){ s:=strings.TrimSpace(h.Get(k)); if s==""{return 0,false}; n,e:=strconv.ParseInt(s,10,64); return n,e==nil }

func probeAt(base string,cl *http.Client) probeResult {
    base=strings.TrimRight(base,"/")
    req,e:=http.NewRequest("GET",base+"/rate_limit",nil); if e!=nil{return probeResult{Reason:"RATE_REQUEST"}}
    req.Header.Set("Accept","application/vnd.github+json"); req.Header.Set("X-GitHub-Api-Version","2022-11-28")
    resp,e:=cl.Do(req); if e!=nil{return probeResult{Reason:"RATE_NETWORK"}}; defer resp.Body.Close()
    if resp.StatusCode!=200{return probeResult{Reason:"RATE_STATUS"}}
    date,ok:=parseDate(resp.Header); if !ok{return probeResult{Reason:"RATE_DATE"}}
    var env rateEnvelope; if json.NewDecoder(io.LimitReader(resp.Body,64<<10)).Decode(&env)!=nil{return probeResult{Reason:"RATE_BODY"}}
    core:=env.Resources.Core
    if core.Limit!=60 || core.Remaining<0 || core.Remaining>core.Limit || core.Reset<=date.Unix(){return probeResult{Reason:"RATE_CORE",Before:core.Remaining,Reset:core.Reset}}
    if core.Remaining<minBeforeComments{return probeResult{Reason:"RATE_RESERVE_BEFORE",Before:core.Remaining,Reset:core.Reset}}
    creq,e:=http.NewRequest("GET",base+"/repos/fufufu1116/multiverse-research/issues/74/comments?per_page=1&page=1",nil); if e!=nil{return probeResult{Reason:"COMMENTS_REQUEST",Before:core.Remaining,Reset:core.Reset}}
    creq.Header.Set("Accept","application/vnd.github+json"); creq.Header.Set("X-GitHub-Api-Version","2022-11-28")
    cres,e:=cl.Do(creq); if e!=nil{return probeResult{Reason:"COMMENTS_NETWORK",Before:core.Remaining,Reset:core.Reset}}; defer cres.Body.Close()
    if cres.StatusCode!=200{return probeResult{Reason:"COMMENTS_STATUS",Before:core.Remaining,Reset:core.Reset}}
    cdate,ok:=parseDate(cres.Header); if !ok{return probeResult{Reason:"COMMENTS_DATE",Before:core.Remaining,Reset:core.Reset}}
    limit,ok1:=headerInt(cres.Header,"X-RateLimit-Limit"); remaining,ok2:=headerInt(cres.Header,"X-RateLimit-Remaining"); reset,ok3:=headerInt(cres.Header,"X-RateLimit-Reset")
    if !ok1||!ok2||!ok3||limit!=60||remaining<0||remaining>limit||reset<=cdate.Unix()||strings.TrimSpace(cres.Header.Get("X-RateLimit-Resource"))!="core" { return probeResult{Reason:"COMMENTS_RATE_HEADERS",Before:core.Remaining,After:int(remaining),Reset:reset} }
    if reset!=core.Reset{return probeResult{Reason:"RATE_RESET_CHANGED",Before:core.Remaining,After:int(remaining),Reset:reset}}
    if int(remaining)!=core.Remaining-1{return probeResult{Reason:"RATE_DECREMENT_NOT_EXACT_ONE",Before:core.Remaining,After:int(remaining),Reset:reset}}
    if int(remaining)<minAfterComments{return probeResult{Reason:"RATE_RESERVE_AFTER",Before:core.Remaining,After:int(remaining),Reset:reset}}
    return probeResult{Ready:true,Reason:"READY",Before:core.Remaining,After:int(remaining),Reset:reset}
}

func newGeneration()(string,error){ var b [16]byte; if _,e:=io.ReadFull(rand.Reader,b[:]);e!=nil{return "",e}; return hex.EncodeToString(b[:]),nil }

func openLockWithOperation(path string, operation int)(*os.File,error){
    fd,e:=syscall.Open(path,syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC|syscall.O_DIRECTORY,0); if e!=nil{return nil,e}
    var st syscall.Stat_t; if e=syscall.Fstat(fd,&st);e!=nil{syscall.Close(fd);return nil,e}
    if st.Uid!=0 || st.Mode&syscall.S_IFMT!=syscall.S_IFDIR || uint32(st.Mode&0777)!=0555 { syscall.Close(fd); return nil,fmt.Errorf("lock-anchor-class") }
    if e=syscall.Flock(fd,operation);e!=nil{syscall.Close(fd);return nil,e}
    return os.NewFile(uintptr(fd),path),nil
}
func openLock(path string)(*os.File,error){ return openLockWithOperation(path,syscall.LOCK_EX) }
func releaseLock(f *os.File){ if f==nil{return}; _=syscall.Flock(int(f.Fd()),syscall.LOCK_UN); _=f.Close() }

func atomicReplaceUnique(path,body,gen string,mode uint32)error{
    tmp:=path+".tmp."+gen
    fd,e:=syscall.Open(tmp,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC,0600); if e!=nil{return e}
    f:=os.NewFile(uintptr(fd),tmp); cleanup:=true
    defer func(){if cleanup{_ = os.Remove(tmp)}}()
    if _,e=io.WriteString(f,body);e!=nil{_ = f.Close();return e}; if e=f.Sync();e!=nil{_ = f.Close();return e}; if e=f.Chmod(os.FileMode(mode));e!=nil{_ = f.Close();return e}; if e=f.Close();e!=nil{return e}
    if e=os.Rename(tmp,path);e!=nil{return e}; cleanup=false; return nil
}

func extractGeneration(s string)string{
    for _,ln:=range strings.Split(s,"\n"){
        ln=strings.TrimSpace(strings.TrimPrefix(ln,"- ")); ln=strings.Trim(ln,"`")
        if strings.HasPrefix(ln,"generation="){return strings.Trim(strings.TrimPrefix(ln,"generation="),"`")}
    }
    return ""
}

func readEvidenceGeneration(path string, expectedMode uint32)(string,error){
    fd,e:=syscall.Open(path,syscall.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC,0); if e!=nil{return "",e}
    f:=os.NewFile(uintptr(fd),path); defer f.Close()
    var st syscall.Stat_t; if e=syscall.Fstat(fd,&st);e!=nil{return "",e}
    if st.Uid!=uint32(os.Getuid()) || st.Mode&syscall.S_IFMT!=syscall.S_IFREG || st.Nlink!=1 || uint32(st.Mode&0777)!=expectedMode { return "",fmt.Errorf("evidence-class") }
    b,e:=io.ReadAll(io.LimitReader(f,64<<10)); if e!=nil{return "",e}
    g:=extractGeneration(string(b)); if len(g)!=32{return "",fmt.Errorf("generation-format")}
    return g,nil
}
func verifyPairAt(status,control,expected string)error{
    sg,e:=readEvidenceGeneration(status,0444); if e!=nil{return e}
    cg,e:=readEvidenceGeneration(control,0644); if e!=nil{return e}
    if sg!=cg || sg!=expected { return fmt.Errorf("generation-mismatch") }
    return nil
}

func render(name,gen,mode string,r probeResult)(string,string){
    state:="NOT_READY"; if r.Ready{state="READY"}
    status:=fmt.Sprintf("PHASE_C_V19_7_36_V7R11_PREARM_RATE_%s\ngeneration=%s\nmode=%s\ncodespace=%s\nreason=%s\nremaining_before_comments=%d\nremaining_after_probe=%d\nreset_epoch=%d\nprobe_repeatable_nonmutating=true\none_shot_guard_consumed=false\ncommit_invokes_guard_only_after_final_ready=true\nauthority_consumer_requires_generation_match=true\nlock_anchor_root_owned_nonreplaceable=true\nrate_residual_bound=AT_LEAST_FIVE_EXTERNAL_CORE_DECREMENTS_REQUIRED_BETWEEN_FINAL_PROBE_AND_HELPER_THRESHOLD_FAILURE\nnext_action=RETURN_TO_CORE_BEFORE_STATIC_GUARD_COMMIT\nruntime=OFF\n",state,gen,mode,name,r.Reason,r.Before,r.After,r.Reset)
    control:=fmt.Sprintf("# MULTIVERSE PRE-LIVE CONTROL — V19.7.36 v7r11\n\n`PHASE_C_V19_7_36_V7R11_PREARM_RATE_%s`\n\n- generation=`%s`\n- mode=`%s`\n- codespace=`%s`\n- reason=`%s`\n- remaining_before_comments=`%d`\n- remaining_after_probe=`%d`\n- reset_epoch=`%d`\n- probe_repeatable_nonmutating=`true`\n- one_shot_guard_consumed=`false`\n- commit_invokes_guard_only_after_final_ready=`true`\n- authority_consumer_requires_generation_match=`true`\n- lock_anchor_root_owned_nonreplaceable=`true`\n- next_action=`RETURN_TO_CORE_BEFORE_STATIC_GUARD_COMMIT`\n- runtime=`OFF`\n\nStatus and control are valid only when their generation values match. The commit-mode authority-bearing consumer mechanically re-opens both final files with O_NOFOLLOW, rejects non-regular/multi-link/wrong-mode files, requires the exact generation just published, and holds an exclusive flock on the root-owned mode-0555 /opt/multiverse/v36/empty-config directory through final generation verification and guard exec. The codespace UID cannot unlink, rename, recreate, or replace that anchor because its parent is root-owned mode 0555. Probe evidence remains nonauthoritative.\n",state,gen,mode,name,r.Reason,r.Before,r.After,r.Reset)
    return status,control
}

func publishPair(name,mode string,r probeResult,hold bool)(*os.File,string,error){
    lock,e:=openLock(lockPath); if e!=nil{return nil,"",e}
    gen,e:=newGeneration(); if e!=nil{releaseLock(lock);return nil,"",e}
    status,control:=render(name,gen,mode,r)
    if e=atomicReplaceUnique(statusPath,status,gen,0444);e!=nil{releaseLock(lock);return nil,"",e}
    if e=atomicReplaceUnique(controlPath,control,gen,0644);e!=nil{releaseLock(lock);return nil,"",e}
    if e=verifyPairAt(statusPath,controlPath,gen);e!=nil{releaseLock(lock);return nil,"",e}
    if hold{return lock,gen,nil}
    releaseLock(lock); return nil,gen,nil
}

func selftest(){
    if minBeforeComments!=60||minAfterComments!=59{panic("threshold")}
    if lockPath!="/opt/multiverse/v36/empty-config"{panic("lock-anchor")}
    s,c:=render("rate-probe-test","00112233445566778899aabbccddeeff","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    for _,x:=range []string{s,c}{for _,w:=range []string{"generation=","one_shot_guard_consumed","authority_consumer_requires_generation_match","lock_anchor_root_owned_nonreplaceable","runtime"}{if !strings.Contains(x,w){panic("render")}}}
    fmt.Println("PHASE_C_V19_7_36_V7R11_RATE_READINESS_SELFTEST_PASS")
    fmt.Println("FINAL_COMMIT_RATE_FLOOR=60/59")
    fmt.Println("PAIR_GENERATION_BINDING=true")
    fmt.Println("AUTHORITY_CONSUMER_REQUIRES_GENERATION_MATCH=true")
    fmt.Println("LOCK_ANCHOR_ROOT_OWNED_NONREPLACEABLE=true")
    fmt.Println("ONE_SHOT_GUARD_CONSUMED=false")
    fmt.Println("SECURITY_AUTHORITY_GRANTED=false")
    fmt.Println("RUNTIME=OFF")
}

func main(){
    if len(os.Args)==2&&os.Args[1]=="build-selftest"{selftest();return}
    mode:="probe"; if len(os.Args)==2&&os.Args[1]=="commit"{mode="commit"}else if len(os.Args)!=1{fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:ARGS");os.Exit(92)}
    uid:=os.Getuid(); if uid==0||os.Geteuid()!=uid{fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:USER_BOUNDARY");os.Exit(92)}
    if os.Getenv("CODESPACES")!="true"{fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:CODESPACES");os.Exit(92)}
    name:=os.Getenv("CODESPACE_NAME"); if !validName(name){fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:CODESPACE_NAME");os.Exit(92)}
    envs:=os.Environ(); if len(envs)!=2{fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:SANITIZER_ENV_COUNT");os.Exit(92)}
    for _,k:=range envs{ if !(strings.HasPrefix(k,"CODESPACES=")||strings.HasPrefix(k,"CODESPACE_NAME=")){fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:SANITIZER_ENV");os.Exit(92)} }
    os.Clearenv()
    r:=probeAt(githubAPIBase,client())
    hold:=mode=="commit"&&r.Ready
    lock,gen,e:=publishPair(name,mode,r,hold); if e!=nil{fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_PROBE_DENIED:EVIDENCE_WRITE_OR_VERIFY");os.Exit(92)}
    if !r.Ready{fmt.Printf("PHASE_C_V19_7_36_V7R11_PREARM_RATE_NOT_READY codespace=%s mode=%s reason=%s one_shot_guard_consumed=false runtime=OFF\n",name,mode,r.Reason);return}
    if mode=="probe"{fmt.Printf("PHASE_C_V19_7_36_V7R11_PREARM_RATE_READY codespace=%s mode=probe remaining_after_probe=%d one_shot_guard_consumed=false runtime=OFF\n",name,r.After);return}
    if e=verifyPairAt(statusPath,controlPath,gen);e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_COMMIT_DENIED:GENERATION_CONSUMER");os.Exit(92)}
    fmt.Printf("PHASE_C_V19_7_36_V7R11_RATE_COMMIT_READY codespace=%s remaining_after_probe=%d generation=%s next=EXEC_V7R7_STATIC_GUARD runtime=OFF\n",name,r.After,gen)
    env:=[]string{"CODESPACES=true","CODESPACE_NAME="+name}; argv:=[]string{guardPath,name}
    if e:=syscall.Exec(guardPath,argv,env);e!=nil{releaseLock(lock);fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R11_RATE_COMMIT_DENIED:GUARD_EXEC");os.Exit(92)}
}
