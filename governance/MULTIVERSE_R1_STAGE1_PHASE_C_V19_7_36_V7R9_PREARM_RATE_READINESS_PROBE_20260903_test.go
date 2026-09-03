package main

import (
    "fmt"
    "net/http"
    "net/http/httptest"
    "os"
    "path/filepath"
    "strings"
    "sync"
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

func extractGeneration(s string)string{for _,ln:=range strings.Split(s,"\n"){ln=strings.TrimSpace(strings.TrimPrefix(ln,"- "));ln=strings.Trim(ln,"`");if strings.HasPrefix(ln,"generation="){return strings.Trim(strings.TrimPrefix(ln,"generation="),"`")}};return ""}

func publishAt(lockPath,statusPath,controlPath,name,gen string)error{
    l,e:=openLock(lockPath);if e!=nil{return e};defer func(){_ = syscall.Flock(int(l.Fd()),syscall.LOCK_UN);_ = l.Close()}()
    st,ct:=render(name,gen,"probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e=atomicReplaceUnique(statusPath,st,gen,0444);e!=nil{return e}
    if e=atomicReplaceUnique(controlPath,ct,gen,0644);e!=nil{return e}
    return nil
}

func TestConcurrentPublicationKeepsGenerationPair(t *testing.T){
    d:=t.TempDir(); lock:=filepath.Join(d,"lock"); status:=filepath.Join(d,"status"); control:=filepath.Join(d,"control")
    var wg sync.WaitGroup; errs:=make(chan error,16)
    for i:=0;i<16;i++{wg.Add(1);go func(i int){defer wg.Done();gen:=fmt.Sprintf("%032x",i+1);errs<-publishAt(lock,status,control,"rate-test",gen)}(i)}
    wg.Wait();close(errs);for e:=range errs{if e!=nil{t.Fatalf("publish: %v",e)}}
    sb,e:=os.ReadFile(status);if e!=nil{t.Fatal(e)};cb,e:=os.ReadFile(control);if e!=nil{t.Fatal(e)}
    sg,cg:=extractGeneration(string(sb)),extractGeneration(string(cb));if sg==""||cg==""||sg!=cg{t.Fatalf("mixed generation status=%q control=%q",sg,cg)}
}

func TestPreexistingSymlinkLockFailsClosed(t *testing.T){
    d:=t.TempDir(); target:=filepath.Join(d,"target"); if e:=os.WriteFile(target,[]byte("x"),0600);e!=nil{t.Fatal(e)}; lock:=filepath.Join(d,"lock"); if e:=os.Symlink(target,lock);e!=nil{t.Fatal(e)}
    if _,e:=openLock(lock);e==nil{t.Fatal("symlink lock unexpectedly accepted")}
}

func TestPartialPublicationIsDetectablyIncoherent(t *testing.T){
    d:=t.TempDir(); status:=filepath.Join(d,"status"); control:=filepath.Join(d,"control")
    oldSt,oldCt:=render("rate-test","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600});_ = oldSt
    if e:=os.WriteFile(control,[]byte(oldCt),0644);e!=nil{t.Fatal(e)}
    newSt,_:=render("rate-test","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    if e:=atomicReplaceUnique(status,newSt,"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",0444);e!=nil{t.Fatal(e)}
    sb,_:=os.ReadFile(status);cb,_:=os.ReadFile(control);if extractGeneration(string(sb))==extractGeneration(string(cb)){t.Fatal("partial publication falsely coherent")}
}

func TestRenderNeverGrantsAuthority(t *testing.T){
    s,c:=render("rate-test","00112233445566778899aabbccddeeff","probe",probeResult{Ready:true,Reason:"READY",Before:60,After:59,Reset:1924995600})
    for _,x:=range []string{s,c}{for _,want:=range []string{"one_shot_guard_consumed","runtime","generation"}{if !strings.Contains(x,want){t.Fatalf("missing %s",want)}}}
}
