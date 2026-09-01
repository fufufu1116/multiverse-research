package main

import (
    "crypto/rand"
    "crypto/sha256"
    "crypto/tls"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "net/http"
    "os"
    "os/exec"
    "strconv"
    "strings"
    "syscall"
    "time"
)

const commentsBase = "https://api.github.com/repos/fufufu1116/multiverse-research/issues/74/comments?per_page=100&page="
const producerPath = "/usr/local/sbin/multiverse-v36-anchor-v7r2"
const imageIdentityPath = "/opt/multiverse/v36/image-identity-v7r3.json"
const requiredApp = "chatgpt-codex-connector"
const requiredUser = "fufufu1116"
const freezePrefix = "MULTIVERSE_V7R4_CANDIDATE_FREEZE "
const receiptPrefix = "MULTIVERSE_V7R4_SESSION_BINDING "
const approvalPrefix = "MULTIVERSE_V7R4_OWNER_APPROVAL_RECEIPT "

type comment struct {
    ID int64 `json:"id"`
    Body string `json:"body"`
    CreatedAt time.Time `json:"created_at"`
    User struct { Login string `json:"login"` } `json:"user"`
    PerformedVia *struct { Slug string `json:"slug"` } `json:"performed_via_github_app"`
}
type freezeReceipt struct {
    Version string `json:"version"`
    CandidateHead string `json:"candidate_head"`
    CandidateTree string `json:"candidate_tree"`
    ImageIdentitySHA256 string `json:"image_identity_sha256"`
    ExactPhrase string `json:"exact_phrase"`
    Runtime string `json:"runtime"`
}
type sessionReceipt struct {
    Version string `json:"version"`
    CodespaceName string `json:"codespace_name"`
    Challenge string `json:"challenge"`
    CandidateHead string `json:"candidate_head"`
    CandidateTree string `json:"candidate_tree"`
    ImageIdentitySHA256 string `json:"image_identity_sha256"`
    CandidateFreezeComment int64 `json:"candidate_freeze_comment"`
    OwnerApprovalComment int64 `json:"owner_approval_comment"`
    OneShot bool `json:"one_shot"`
    Runtime string `json:"runtime"`
}
type approvalReceipt struct {
    Version string `json:"version"`
    CodespaceName string `json:"codespace_name"`
    Challenge string `json:"challenge"`
    CandidateHead string `json:"candidate_head"`
    CandidateTree string `json:"candidate_tree"`
    ImageIdentitySHA256 string `json:"image_identity_sha256"`
    CandidateFreezeComment int64 `json:"candidate_freeze_comment"`
    ExactPhrase string `json:"exact_phrase"`
    OneShot bool `json:"one_shot"`
    Runtime string `json:"runtime"`
}
func die(s string) { fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R4_SESSION_GATE_DENIED:"+s);os.Exit(92) }
func isHex(s string,n int)bool{if len(s)!=n{return false};_,e:=hex.DecodeString(s);return e==nil}
func appBound(c comment)bool{return c.User.Login==requiredUser&&c.PerformedVia!=nil&&c.PerformedVia.Slug==requiredApp}
func linePayload(body,prefix string)([]byte,bool){for _,l:=range strings.Split(body,"\n"){if strings.HasPrefix(l,prefix){return []byte(strings.TrimPrefix(l,prefix)),true}};return nil,false}
func httpClient()*http.Client{return &http.Client{Transport:&http.Transport{Proxy:nil,TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12}},Timeout:10*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}}}
func getPage(cl *http.Client,page int)([]comment,http.Header,error){r,e:=http.NewRequest("GET",commentsBase+strconv.Itoa(page),nil);if e!=nil{return nil,nil,e};r.Header.Set("Accept","application/vnd.github+json");r.Header.Set("X-GitHub-Api-Version","2022-11-28");x,e:=cl.Do(r);if e!=nil{return nil,nil,e};defer x.Body.Close();if x.StatusCode!=200{return nil,nil,fmt.Errorf("http:%d",x.StatusCode)};var z []comment;if e=json.NewDecoder(io.LimitReader(x.Body,8<<20)).Decode(&z);e!=nil{return nil,nil,e};return z,x.Header.Clone(),nil}
func lastPage(link string)int{last:=1;for _,part:=range strings.Split(link,","){if !strings.Contains(part,"rel=\"last\""){continue};i:=strings.Index(part,"page=");if i<0{continue};s:=part[i+5:];j:=strings.IndexAny(s,">& ");if j>=0{s=s[:j]};if n,e:=strconv.Atoi(s);e==nil&&n>last{last=n}};return last}
func comments(cl *http.Client)([]comment,error){first,h,e:=getPage(cl,1);if e!=nil{return nil,e};n:=lastPage(h.Get("Link"));if n<=1{return first,nil};pages:=[]int{n};if n>1{pages=append([]int{n-1},pages...)};out:=make([]comment,0,200);for _,p:=range pages{z,_,e:=getPage(cl,p);if e!=nil{return nil,e};out=append(out,z...)};return out,nil}
func githubServerNow(cl *http.Client)(time.Time,error){_,h,e:=getPage(cl,1);if e!=nil{return time.Time{},e};d:=h.Get("Date");if d==""{return time.Time{},errors.New("date-missing")};t,e:=http.ParseTime(d);if e!=nil{return time.Time{},e};return t.UTC(),nil}
func imageIdentity()(string,error){f,e:=os.Open(imageIdentityPath);if e!=nil{return "",e};defer f.Close();st,e:=f.Stat();if e!=nil{return "",e};if st.Sys().(*syscall.Stat_t).Uid!=0||st.Mode().Perm()&0022!=0||!st.Mode().IsRegular(){return "",errors.New("identity-class-c")};b,e:=io.ReadAll(io.LimitReader(f,1<<20));if e!=nil{return "",e};h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil}
func parseFreeze(c comment)(freezeReceipt,bool){if !appBound(c){return freezeReceipt{},false};b,ok:=linePayload(c.Body,freezePrefix);if !ok{return freezeReceipt{},false};var f freezeReceipt;if json.Unmarshal(b,&f)!=nil{return freezeReceipt{},false};if f.Version!="V19.7.36-v7r4"||!isHex(f.CandidateHead,40)||!isHex(f.CandidateTree,40)||!isHex(f.ImageIdentitySHA256,64)||f.ExactPhrase!="FREEZE V19.7.36 v7r4 CANDIDATE"||f.Runtime!="OFF"{return freezeReceipt{},false};return f,true}
func findFreeze(cs []comment,id int64,identity string)(freezeReceipt,error){matches:=0;var chosen freezeReceipt;refFound:=false;for _,c:=range cs{f,ok:=parseFreeze(c);if !ok||f.ImageIdentitySHA256!=identity{continue};matches++;if c.ID==id{chosen=f;refFound=true}};if !refFound{return freezeReceipt{},errors.New("freeze-missing")};if matches!=1{return freezeReceipt{},errors.New("freeze-ambiguous")};return chosen,nil}
func approvalMatches(c comment,s sessionReceipt,issued time.Time)bool{if !appBound(c)||c.ID!=s.OwnerApprovalComment||c.CreatedAt.Before(issued){return false};b,ok:=linePayload(c.Body,approvalPrefix);if !ok{return false};var a approvalReceipt;if json.Unmarshal(b,&a)!=nil{return false};return a.Version=="V19.7.36-v7r4"&&a.CodespaceName==s.CodespaceName&&a.Challenge==s.Challenge&&a.CandidateHead==s.CandidateHead&&a.CandidateTree==s.CandidateTree&&a.ImageIdentitySHA256==s.ImageIdentitySHA256&&a.CandidateFreezeComment==s.CandidateFreezeComment&&a.ExactPhrase=="APPROVE V19.7.36 v7r4 ONE-SHOT LIVE"&&a.OneShot&&a.Runtime=="OFF"}
func selectReceipt(cs []comment,name,challenge,identity string,issued time.Time)(sessionReceipt,error){matches:=0;var got sessionReceipt;for _,c:=range cs{if !appBound(c){continue};b,ok:=linePayload(c.Body,receiptPrefix);if !ok{continue};var s sessionReceipt;if json.Unmarshal(b,&s)!=nil{continue};if s.Version!="V19.7.36-v7r4"||s.CodespaceName!=name||s.Challenge!=challenge||s.ImageIdentitySHA256!=identity||!s.OneShot||s.Runtime!="OFF"||!isHex(s.CandidateHead,40)||!isHex(s.CandidateTree,40){continue};f,e:=findFreeze(cs,s.CandidateFreezeComment,identity);if e!=nil||f.CandidateHead!=s.CandidateHead||f.CandidateTree!=s.CandidateTree{continue};approvalCount:=0;for _,a:=range cs{if approvalMatches(a,s,issued)&&!a.CreatedAt.After(c.CreatedAt){approvalCount++}};if approvalCount!=1{continue};matches++;got=s};if matches==1{return got,nil};if matches>1{return sessionReceipt{},errors.New("ambiguous")};return sessionReceipt{},errors.New("missing")}
func waitReceipt(name,challenge,identity string,issued time.Time)(sessionReceipt,error){cl:=httpClient();deadline:=time.Now().Add(10*time.Minute);for time.Now().Before(deadline){cs,e:=comments(cl);if e==nil{if s,e:=selectReceipt(cs,name,challenge,identity,issued);e==nil{return s,nil}else if e.Error()=="ambiguous"{return sessionReceipt{},e}};time.Sleep(30*time.Second)};return sessionReceipt{},errors.New("timeout")}
func mkComment(id int64,created time.Time,prefix string,v any)comment{b,_:=json.Marshal(v);var c comment;c.ID=id;c.CreatedAt=created;c.Body=prefix+string(b);c.User.Login=requiredUser;c.PerformedVia=&struct{Slug string `json:"slug"`}{Slug:requiredApp};return c}
func selftest(){t:=time.Unix(2000000000,0).UTC();head:=strings.Repeat("a",40);tree:=strings.Repeat("b",40);image:=strings.Repeat("c",64);challenge:=strings.Repeat("d",32);f:=freezeReceipt{"V19.7.36-v7r4",head,tree,image,"FREEZE V19.7.36 v7r4 CANDIDATE","OFF"};a:=approvalReceipt{"V19.7.36-v7r4","cs1",challenge,head,tree,image,1,"APPROVE V19.7.36 v7r4 ONE-SHOT LIVE",true,"OFF"};s:=sessionReceipt{"V19.7.36-v7r4","cs1",challenge,head,tree,image,1,2,true,"OFF"};base:=[]comment{mkComment(1,t,freezePrefix,f),mkComment(2,t.Add(time.Second),approvalPrefix,a),mkComment(3,t.Add(2*time.Second),receiptPrefix,s)};if _,e:=selectReceipt(base,"cs1",challenge,image,t);e!=nil{panic("positive")};tests:=[][]comment{};x:=append([]comment{},base...);s2:=s;s2.CandidateHead=strings.Repeat("e",40);x[2]=mkComment(3,t.Add(2*time.Second),receiptPrefix,s2);tests=append(tests,x);x=append([]comment{},base...);s2=s;s2.CandidateTree=strings.Repeat("e",40);x[2]=mkComment(3,t.Add(2*time.Second),receiptPrefix,s2);tests=append(tests,x);x=append([]comment{},base...);x[1]=mkComment(2,t.Add(-time.Second),approvalPrefix,a);tests=append(tests,x);x=append([]comment{},base...);a2:=a;a2.Challenge=strings.Repeat("e",32);x[1]=mkComment(2,t.Add(time.Second),approvalPrefix,a2);tests=append(tests,x);x=append([]comment{},base...);s2=s;s2.CodespaceName="other";x[2]=mkComment(3,t.Add(2*time.Second),receiptPrefix,s2);tests=append(tests,x);x=append([]comment{},base...);s2=s;s2.ImageIdentitySHA256=strings.Repeat("e",64);x[2]=mkComment(3,t.Add(2*time.Second),receiptPrefix,s2);tests=append(tests,x);x=append([]comment{},base...);x=append(x,mkComment(4,t.Add(3*time.Second),receiptPrefix,s));tests=append(tests,x);x=append([]comment{},base...);x=append(x,mkComment(5,t,freezePrefix,f));tests=append(tests,x);for i,z:=range tests{if _,e:=selectReceipt(z,"cs1",challenge,image,t);e==nil{panic(fmt.Sprintf("negative-%d",i))}};fmt.Println("PHASE_C_V19_7_36_V7R4_SESSION_GATE_NEGATIVE_SELFTEST_PASS")}
func main(){if len(os.Args)==2&&os.Args[1]=="build-selftest"{selftest();return};if os.Geteuid()!=0{die("EUID")};if os.Getenv("CODESPACES")!="true"{die("CODESPACES")};name:=os.Getenv("CODESPACE_NAME");if name==""{die("CODESPACE_NAME")};identity,e:=imageIdentity();if e!=nil{die("IMAGE_IDENTITY")};raw:=make([]byte,16);if _,e=rand.Read(raw);e!=nil{die("RANDOM")};challenge:=hex.EncodeToString(raw);cl:=httpClient();issued,e:=githubServerNow(cl);if e!=nil{die("GITHUB_SERVER_TIME")};fmt.Printf("PHASE_C_V19_7_36_V7R4_SESSION_CHALLENGE codespace=%s challenge=%s image_identity_sha256=%s\n",name,challenge,identity);fmt.Println("PHASE_C_V19_7_36_V7R4_WAITING_FOR_EXTERNAL_SESSION_BINDING");s,e:=waitReceipt(name,challenge,identity,issued);if e!=nil{die("SESSION_RECEIPT")};fmt.Printf("PHASE_C_V19_7_36_V7R4_EXTERNAL_SESSION_BINDING_PASS head=%s tree=%s\n",s.CandidateHead,s.CandidateTree);p,e:=os.Open(producerPath);if e!=nil{die("PRODUCER_OPEN")};defer p.Close();st,e:=p.Stat();if e!=nil||st.Sys().(*syscall.Stat_t).Uid!=0||st.Mode().Perm()&0022!=0||!st.Mode().IsRegular(){die("PRODUCER_CLASS_C")};cmd:=exec.Command("/proc/self/fd/3");cmd.ExtraFiles=[]*os.File{p};cmd.Env=[]string{"CODESPACES=true","CODESPACE_NAME="+name,"LANG=C","LC_ALL=C"};cmd.Stdin=os.Stdin;cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr;if e=cmd.Run();e!=nil{if x,ok:=e.(*exec.ExitError);ok{os.Exit(x.ExitCode())};die("PRODUCER_EXEC")}}
