package main

import (
    "fmt"
    "net/http"
    "net/http/httptest"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "syscall"
    "testing"
)

func testServer(before,after int,reset int64)*httptest.Server{
    mux:=http.NewServeMux()
    mux.HandleFunc("/rate_limit",func(w http.ResponseWriter,r *http.Request){w.Header().Set("Date","Wed, 01 Jan 2031 00:00:00 GMT");w.Header().Set("Content-Type","application/json");fmt.Fprintf(w,`{"resources":{"core":{"limit":60,"remaining":%d,"reset":%d}}}`,before,reset)})
    mux.HandleFunc("/repos/fufufu1116/multiverse-research/issues/74/comments",func(w http.ResponseWriter,r *http.Request){w.Header().Set("Date","Wed, 01 Jan 2031 00:00:00 GMT");w.Header().Set("X-RateLimit-Limit","60");w.Header().Set("X-RateLimit-Remaining",fmt.Sprint(after));w.Header().Set("X-RateLimit-Reset",fmt.Sprint(reset));w.Header().Set("X-RateLimit-Resource","core");w.WriteHeader(200);fmt.Fprint(w,"[]")})
    return httptest.NewServer(mux)
}

func TestRateCommitFloors(t *testing.T){
    s:=testServer(60,59,1924995600);defer s.Close(); r:=probeAt(s.URL,s.Client()); if !r.Ready{t.Fatalf("60/59 must be ready: %+v",r)}
    s2:=testServer(59,58,1924995600);defer s2.Close(); r=probeAt(s2.URL,s2.Client()); if r.Ready||r.Reason!="RATE_RESERVE_BEFORE"{t.Fatalf("59/58 must fail before: %+v",r)}
    s3:=testServer(60,58,1924995600);defer s3.Close(); r=probeAt(s3.URL,s3.Client()); if r.Ready||r.Reason!="RATE_DECREMENT_NOT_EXACT_ONE"{t.Fatalf("unexpected decrement must fail: %+v",r)}
}

func publishAt(lockPath,statusPath,controlPath,name,gen string)error{
    l,e:=openLock(lockPath);if e!=nil{return e};defer releaseLock(l)
    st,ct:=render(name,gen,"probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e=atomicReplaceUnique(statusPath,st,gen,0444);e!=nil{return e}
    if e=atomicReplaceUnique(controlPath,ct,gen,0644);e!=nil{return e}
    return verifyPairAt(statusPath,controlPath,gen)
}

func TestIndependentPublisherProcessHelper(t *testing.T){
    if os.Getenv("V7R10_PUBLISH_HELPER")!="1"{return}
    d:=os.Getenv("V7R10_PUBLISH_DIR"); gen:=os.Getenv("V7R10_PUBLISH_GEN")
    if d==""||gen==""{os.Exit(97)}
    if e:=publishAt(filepath.Join(d,"lock"),filepath.Join(d,"status"),filepath.Join(d,"control"),"rate-test",gen);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(98)}
    os.Exit(0)
}

func TestConcurrentIndependentProcessesKeepGenerationPair(t *testing.T){
    d:=t.TempDir(); cmds:=make([]*exec.Cmd,0,12)
    for i:=0;i<12;i++{
        gen:=fmt.Sprintf("%032x",i+1)
        c:=exec.Command(os.Args[0],"-test.run=TestIndependentPublisherProcessHelper")
        c.Env=append(os.Environ(),"V7R10_PUBLISH_HELPER=1","V7R10_PUBLISH_DIR="+d,"V7R10_PUBLISH_GEN="+gen)
        if e:=c.Start();e!=nil{t.Fatal(e)};cmds=append(cmds,c)
    }
    for _,c:=range cmds{if e:=c.Wait();e!=nil{t.Fatalf("publisher process failed: %v",e)}}
    sb,e:=os.ReadFile(filepath.Join(d,"status"));if e!=nil{t.Fatal(e)};cb,e:=os.ReadFile(filepath.Join(d,"control"));if e!=nil{t.Fatal(e)}
    sg,cg:=extractGeneration(string(sb)),extractGeneration(string(cb));if sg==""||cg==""||sg!=cg{t.Fatalf("mixed generation status=%q control=%q",sg,cg)}
    if e:=verifyPairAt(filepath.Join(d,"status"),filepath.Join(d,"control"),sg);e!=nil{t.Fatalf("consumer verification failed: %v",e)}
}

func TestPreexistingSymlinkLockFailsClosed(t *testing.T){
    d:=t.TempDir(); target:=filepath.Join(d,"target"); if e:=os.WriteFile(target,[]byte("x"),0600);e!=nil{t.Fatal(e)}; lock:=filepath.Join(d,"lock"); if e:=os.Symlink(target,lock);e!=nil{t.Fatal(e)}
    if _,e:=openLock(lock);e==nil{t.Fatal("symlink lock unexpectedly accepted")}
}

func TestStaleRegularLockIsSafelyReusable(t *testing.T){
    d:=t.TempDir(); lock:=filepath.Join(d,"lock"); if e:=os.WriteFile(lock,[]byte("stale"),0600);e!=nil{t.Fatal(e)}
    l,e:=openLock(lock);if e!=nil{t.Fatalf("safe stale regular lock rejected: %v",e)};releaseLock(l)
}

func TestUniqueTempPreexistingCollisionFailsClosed(t *testing.T){
    d:=t.TempDir(); p:=filepath.Join(d,"status"); gen:="11111111111111111111111111111111"; tmp:=p+".tmp."+gen
    if e:=os.WriteFile(tmp,[]byte("attacker-preexisting"),0600);e!=nil{t.Fatal(e)}
    if e:=atomicReplaceUnique(p,"new",gen,0444);e==nil{t.Fatal("O_EXCL collision unexpectedly accepted")}
    b,e:=os.ReadFile(tmp);if e!=nil||string(b)!="attacker-preexisting"{t.Fatal("collision file was modified")}
}

func writePairFiles(t *testing.T,d,gen string)(string,string){
    t.Helper();status:=filepath.Join(d,"status");control:=filepath.Join(d,"control")
    st,ct:=render("rate-test",gen,"probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e:=os.WriteFile(status,[]byte(st),0444);e!=nil{t.Fatal(e)};if e:=os.WriteFile(control,[]byte(ct),0644);e!=nil{t.Fatal(e)}
    return status,control
}

func TestFinalTargetSymlinkRejectedByAuthorityConsumer(t *testing.T){
    d:=t.TempDir();gen:="22222222222222222222222222222222";_,control:=writePairFiles(t,d,gen);real:=filepath.Join(d,"real-status")
    st,_:=render("rate-test",gen,"probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600});if e:=os.WriteFile(real,[]byte(st),0444);e!=nil{t.Fatal(e)}
    status:=filepath.Join(d,"status");if e:=os.Remove(status);e!=nil{t.Fatal(e)};if e:=os.Symlink(real,status);e!=nil{t.Fatal(e)}
    if e:=verifyPairAt(status,control,gen);e==nil{t.Fatal("final symlink unexpectedly accepted")}
}

func TestFinalTargetHardlinkRejectedByAuthorityConsumer(t *testing.T){
    d:=t.TempDir();gen:="33333333333333333333333333333333";_,control:=writePairFiles(t,d,gen);real:=filepath.Join(d,"real-status")
    st,_:=render("rate-test",gen,"probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600});if e:=os.WriteFile(real,[]byte(st),0444);e!=nil{t.Fatal(e)}
    status:=filepath.Join(d,"status");if e:=os.Remove(status);e!=nil{t.Fatal(e)};if e:=os.Link(real,status);e!=nil{t.Fatal(e)}
    if e:=verifyPairAt(status,control,gen);e==nil{t.Fatal("final hardlink unexpectedly accepted")}
}

func TestGenerationMismatchDeniedByAuthorityConsumer(t *testing.T){
    d:=t.TempDir();status,control:=writePairFiles(t,d,"44444444444444444444444444444444")
    _,ct:=render("rate-test","55555555555555555555555555555555","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600});if e:=os.WriteFile(control,[]byte(ct),0644);e!=nil{t.Fatal(e)}
    if e:=verifyPairAt(status,control,"44444444444444444444444444444444");e==nil{t.Fatal("generation mismatch unexpectedly authorized")}
}

func TestPartialPublicationIsDetectablyIncoherent(t *testing.T){
    d:=t.TempDir(); status:=filepath.Join(d,"status"); control:=filepath.Join(d,"control")
    _,oldCt:=render("rate-test","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e:=os.WriteFile(control,[]byte(oldCt),0644);e!=nil{t.Fatal(e)}
    newSt,_:=render("rate-test","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e:=atomicReplaceUnique(status,newSt,"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",0444);e!=nil{t.Fatal(e)}
    if e:=verifyPairAt(status,control,"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");e==nil{t.Fatal("partial publication unexpectedly authorized")}
}

func TestRenderNeverGrantsAuthority(t *testing.T){
    s,c:=render("rate-test","00112233445566778899aabbccddeeff","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    for _,x:=range []string{s,c}{for _,want:=range []string{"one_shot_guard_consumed","authority_consumer_requires_generation_match","runtime","generation"}{if !strings.Contains(x,want){t.Fatalf("missing %s",want)}}}
}

func TestOpenLockUsesFlock(t *testing.T){
    d:=t.TempDir();l,e:=openLock(filepath.Join(d,"lock"));if e!=nil{t.Fatal(e)};defer releaseLock(l)
    if e:=syscall.Flock(int(l.Fd()),syscall.LOCK_EX|syscall.LOCK_NB);e!=nil{t.Fatal(e)}
}
