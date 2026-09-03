package main

import (
    "errors"
    "fmt"
    "net/http"
    "net/http/httptest"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "syscall"
    "testing"
    "time"
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

func productionAnchorAvailable()bool{
    st,e:=os.Stat(lockPath); return e==nil&&st.IsDir()
}

func publishAt(statusPath,controlPath,name,gen string)error{
    l,e:=openLock(lockPath);if e!=nil{return e};defer releaseLock(l)
    st,ct:=render(name,gen,"probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e=atomicReplaceUnique(statusPath,st,gen,0444);e!=nil{return e}
    if e=atomicReplaceUnique(controlPath,ct,gen,0644);e!=nil{return e}
    return verifyPairAt(statusPath,controlPath,gen)
}

func TestIndependentPublisherProcessHelper(t *testing.T){
    if os.Getenv("V7R11_PUBLISH_HELPER")!="1"{return}
    d:=os.Getenv("V7R11_PUBLISH_DIR"); gen:=os.Getenv("V7R11_PUBLISH_GEN")
    if d==""||gen==""{os.Exit(97)}
    if e:=publishAt(filepath.Join(d,"status"),filepath.Join(d,"control"),"rate-test",gen);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(98)}
    os.Exit(0)
}

func TestConcurrentIndependentProcessesKeepGenerationPair(t *testing.T){
    if !productionAnchorAvailable(){t.Skip("production lock anchor exists only in exact image")}
    d:=t.TempDir(); cmds:=make([]*exec.Cmd,0,12)
    for i:=0;i<12;i++{
        gen:=fmt.Sprintf("%032x",i+1)
        c:=exec.Command(os.Args[0],"-test.run=TestIndependentPublisherProcessHelper")
        c.Env=append(os.Environ(),"V7R11_PUBLISH_HELPER=1","V7R11_PUBLISH_DIR="+d,"V7R11_PUBLISH_GEN="+gen)
        if e:=c.Start();e!=nil{t.Fatal(e)};cmds=append(cmds,c)
    }
    for _,c:=range cmds{if e:=c.Wait();e!=nil{t.Fatalf("publisher process failed: %v",e)}}
    sb,e:=os.ReadFile(filepath.Join(d,"status"));if e!=nil{t.Fatal(e)};cb,e:=os.ReadFile(filepath.Join(d,"control"));if e!=nil{t.Fatal(e)}
    sg,cg:=extractGeneration(string(sb)),extractGeneration(string(cb));if sg==""||cg==""||sg!=cg{t.Fatalf("mixed generation status=%q control=%q",sg,cg)}
    if e:=verifyPairAt(filepath.Join(d,"status"),filepath.Join(d,"control"),sg);e!=nil{t.Fatalf("consumer verification failed: %v",e)}
}

func TestPreexistingSymlinkLockFailsClosed(t *testing.T){
    d:=t.TempDir(); target:=filepath.Join(d,"target"); if e:=os.Mkdir(target,0555);e!=nil{t.Fatal(e)}; lock:=filepath.Join(d,"lock"); if e:=os.Symlink(target,lock);e!=nil{t.Fatal(e)}
    if _,e:=openLock(lock);e==nil{t.Fatal("symlink lock unexpectedly accepted")}
}

func TestUserOwnedRegularLockCannotSubstituteForRootAnchor(t *testing.T){
    d:=t.TempDir(); lock:=filepath.Join(d,"lock"); if e:=os.WriteFile(lock,[]byte("stale"),0600);e!=nil{t.Fatal(e)}
    if _,e:=openLock(lock);e==nil{t.Fatal("user-owned regular lock unexpectedly accepted")}
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
    for _,x:=range []string{s,c}{for _,want:=range []string{"one_shot_guard_consumed","authority_consumer_requires_generation_match","lock_anchor_root_owned_nonreplaceable","runtime","generation"}{if !strings.Contains(x,want){t.Fatalf("missing %s",want)}}}
}

func TestProductionLockAnchorHolderHelper(t *testing.T){
    if os.Getenv("V7R11_LOCK_HOLDER")!="1"{return}
    signalDir:=os.Getenv("V7R11_LOCK_SIGNAL_DIR"); if signalDir==""{os.Exit(96)}
    l,e:=openLock(lockPath);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(97)};defer releaseLock(l)
    if e=os.WriteFile(filepath.Join(signalDir,"held"),[]byte("held"),0600);e!=nil{os.Exit(98)}
    deadline:=time.Now().Add(10*time.Second)
    for time.Now().Before(deadline){if _,e=os.Stat(filepath.Join(signalDir,"release"));e==nil{os.Exit(0)};time.Sleep(10*time.Millisecond)}
    os.Exit(99)
}

func TestProductionLockAnchorRejectsPathReplacementAndSecondDomain(t *testing.T){
    if !productionAnchorAvailable(){t.Skip("production lock anchor exists only in exact image")}
    signalDir:=t.TempDir()
    holder:=exec.Command(os.Args[0],"-test.run=TestProductionLockAnchorHolderHelper")
    holder.Env=append(os.Environ(),"V7R11_LOCK_HOLDER=1","V7R11_LOCK_SIGNAL_DIR="+signalDir)
    if e:=holder.Start();e!=nil{t.Fatal(e)}
    deadline:=time.Now().Add(5*time.Second)
    for {if _,e:=os.Stat(filepath.Join(signalDir,"held"));e==nil{break};if time.Now().After(deadline){_ = holder.Process.Kill();t.Fatal("holder did not acquire production anchor")};time.Sleep(10*time.Millisecond)}

    if e:=os.Remove(lockPath);e==nil{_ = holder.Process.Kill();t.Fatal("same-UID unlink unexpectedly replaced production lock anchor")}
    moved:=lockPath+".attacker-moved"
    if e:=os.Rename(lockPath,moved);e==nil{_ = holder.Process.Kill();t.Fatal("same-UID rename unexpectedly moved production lock anchor")}
    if e:=os.Mkdir(lockPath,0555);e==nil{_ = holder.Process.Kill();t.Fatal("same-UID recreate unexpectedly replaced production lock anchor")}

    second,e:=openLockWithOperation(lockPath,syscall.LOCK_EX|syscall.LOCK_NB)
    if e==nil{releaseLock(second);_ = holder.Process.Kill();t.Fatal("second lock domain unexpectedly acquired while holder owns production anchor")}
    if !errors.Is(e,syscall.EWOULDBLOCK)&&!errors.Is(e,syscall.EAGAIN){_ = holder.Process.Kill();t.Fatalf("expected flock contention, got %v",e)}

    if e:=os.WriteFile(filepath.Join(signalDir,"release"),[]byte("release"),0600);e!=nil{_ = holder.Process.Kill();t.Fatal(e)}
    if e:=holder.Wait();e!=nil{t.Fatalf("holder failed: %v",e)}
    after,e:=openLockWithOperation(lockPath,syscall.LOCK_EX|syscall.LOCK_NB);if e!=nil{t.Fatalf("anchor unavailable after holder release: %v",e)};releaseLock(after)
}

func TestProductionLockAnchorUsesFlock(t *testing.T){
    if !productionAnchorAvailable(){t.Skip("production lock anchor exists only in exact image")}
    l,e:=openLock(lockPath);if e!=nil{t.Fatal(e)};defer releaseLock(l)
    if _,e:=openLockWithOperation(lockPath,syscall.LOCK_EX|syscall.LOCK_NB);e==nil{t.Fatal("second exclusive flock unexpectedly succeeded")}
}
