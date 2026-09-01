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
    "strings"
    "syscall"
    "time"
)

const commentsURL = "https://api.github.com/repos/fufufu1116/multiverse-research/issues/74/comments?per_page=100&page=1"
const producerPath = "/usr/local/sbin/multiverse-v36-anchor-v7r2"
const imageIdentityPath = "/opt/multiverse/v36/image-identity-v7r3.json"
const requiredApp = "chatgpt-codex-connector"
const requiredUser = "fufufu1116"
const receiptPrefix = "MULTIVERSE_V7R3_SESSION_BINDING "
const approvalPrefix = "MULTIVERSE_V7R3_OWNER_APPROVAL_RECEIPT "

type comment struct {
    ID int64 `json:"id"`
    Body string `json:"body"`
    User struct { Login string `json:"login"` } `json:"user"`
    PerformedVia *struct { Slug string `json:"slug"` } `json:"performed_via_github_app"`
}

type sessionReceipt struct {
    Version string `json:"version"`
    CodespaceName string `json:"codespace_name"`
    Challenge string `json:"challenge"`
    CandidateHead string `json:"candidate_head"`
    CandidateTree string `json:"candidate_tree"`
    ImageIdentitySHA256 string `json:"image_identity_sha256"`
    OwnerApprovalComment int64 `json:"owner_approval_comment"`
    OneShot bool `json:"one_shot"`
    Runtime string `json:"runtime"`
}

type approvalReceipt struct {
    Version string `json:"version"`
    CandidateHead string `json:"candidate_head"`
    CandidateTree string `json:"candidate_tree"`
    ImageIdentitySHA256 string `json:"image_identity_sha256"`
    ExactPhrase string `json:"exact_phrase"`
    OneShot bool `json:"one_shot"`
    Runtime string `json:"runtime"`
}

func die(s string) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R3_SESSION_GATE_DENIED:"+s); os.Exit(92) }
func isHex(s string,n int) bool { if len(s)!=n{return false}; _,e:=hex.DecodeString(s); return e==nil }
func appBound(c comment) bool { return c.User.Login==requiredUser && c.PerformedVia!=nil && c.PerformedVia.Slug==requiredApp }
func linePayload(body,prefix string)([]byte,bool){ for _,l:=range strings.Split(body,"\n"){ if strings.HasPrefix(l,prefix){ return []byte(strings.TrimPrefix(l,prefix)),true } }; return nil,false }
func httpClient()*http.Client{ return &http.Client{Transport:&http.Transport{Proxy:nil,TLSClientConfig:&tls.Config{MinVersion:tls.VersionTLS12}},Timeout:10*time.Second,CheckRedirect:func(*http.Request,[]*http.Request)error{return http.ErrUseLastResponse}} }
func comments(cl *http.Client)([]comment,error){ r,e:=http.NewRequest("GET",commentsURL,nil);if e!=nil{return nil,e};r.Header.Set("Accept","application/vnd.github+json");r.Header.Set("X-GitHub-Api-Version","2022-11-28");x,e:=cl.Do(r);if e!=nil{return nil,e};defer x.Body.Close();if x.StatusCode!=200{return nil,fmt.Errorf("http:%d",x.StatusCode)};var z []comment;if e=json.NewDecoder(io.LimitReader(x.Body,8<<20)).Decode(&z);e!=nil{return nil,e};return z,nil }
func imageIdentity()(string,error){ f,e:=os.Open(imageIdentityPath);if e!=nil{return "",e};defer f.Close();st,e:=f.Stat();if e!=nil{return "",e};if st.Sys().(*syscall.Stat_t).Uid!=0||st.Mode().Perm()&0022!=0||!st.Mode().IsRegular(){return "",errors.New("identity-class-c")};b,e:=io.ReadAll(io.LimitReader(f,1<<20));if e!=nil{return "",e};h:=sha256.Sum256(b);return hex.EncodeToString(h[:]),nil }
func findApproval(cs []comment,id int64,s sessionReceipt)error{ for _,c:=range cs{if c.ID!=id{continue};if !appBound(c){return errors.New("approval-origin")};b,ok:=linePayload(c.Body,approvalPrefix);if !ok{return errors.New("approval-marker")};var a approvalReceipt;if json.Unmarshal(b,&a)!=nil{return errors.New("approval-json")};if a.Version!="V19.7.36-v7r3"||a.CandidateHead!=s.CandidateHead||a.CandidateTree!=s.CandidateTree||a.ImageIdentitySHA256!=s.ImageIdentitySHA256||a.ExactPhrase!="APPROVE V19.7.36 v7r3 ONE-SHOT LIVE"||!a.OneShot||a.Runtime!="OFF"{return errors.New("approval-binding")};return nil};return errors.New("approval-missing") }
func waitReceipt(name,challenge,identity string)(sessionReceipt,error){cl:=httpClient();deadline:=time.Now().Add(10*time.Minute);for time.Now().Before(deadline){cs,e:=comments(cl);if e==nil{matches:=0;var got sessionReceipt;for _,c:=range cs{if !appBound(c){continue};b,ok:=linePayload(c.Body,receiptPrefix);if !ok{continue};var s sessionReceipt;if json.Unmarshal(b,&s)!=nil{continue};if s.Version!="V19.7.36-v7r3"||s.CodespaceName!=name||s.Challenge!=challenge||s.ImageIdentitySHA256!=identity||!s.OneShot||s.Runtime!="OFF"||!isHex(s.CandidateHead,40)||!isHex(s.CandidateTree,40){continue};if findApproval(cs,s.OwnerApprovalComment,s)!=nil{continue};matches++;got=s};if matches==1{return got,nil};if matches>1{return sessionReceipt{},errors.New("ambiguous")}};time.Sleep(2*time.Second)};return sessionReceipt{},errors.New("timeout") }
func main(){ if os.Geteuid()!=0{die("EUID")};if os.Getenv("CODESPACES")!="true"{die("CODESPACES")};name:=os.Getenv("CODESPACE_NAME");if name==""{die("CODESPACE_NAME")};identity,e:=imageIdentity();if e!=nil{die("IMAGE_IDENTITY")};raw:=make([]byte,16);if _,e=rand.Read(raw);e!=nil{die("RANDOM")};challenge:=hex.EncodeToString(raw);fmt.Printf("PHASE_C_V19_7_36_V7R3_SESSION_CHALLENGE codespace=%s challenge=%s image_identity_sha256=%s\n",name,challenge,identity);fmt.Println("PHASE_C_V19_7_36_V7R3_WAITING_FOR_EXTERNAL_SESSION_BINDING");s,e:=waitReceipt(name,challenge,identity);if e!=nil{die("SESSION_RECEIPT")};fmt.Printf("PHASE_C_V19_7_36_V7R3_EXTERNAL_SESSION_BINDING_PASS head=%s tree=%s\n",s.CandidateHead,s.CandidateTree);p,e:=os.Open(producerPath);if e!=nil{die("PRODUCER_OPEN")};defer p.Close();st,e:=p.Stat();if e!=nil||st.Sys().(*syscall.Stat_t).Uid!=0||st.Mode().Perm()&0022!=0||!st.Mode().IsRegular(){die("PRODUCER_CLASS_C")};cmd:=exec.Command("/proc/self/fd/3");cmd.ExtraFiles=[]*os.File{p};cmd.Env=[]string{"CODESPACES=true","CODESPACE_NAME="+name,"LANG=C","LC_ALL=C"};cmd.Stdin=os.Stdin;cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr;if e=cmd.Run();e!=nil{if x,ok:=e.(*exec.ExitError);ok{os.Exit(x.ExitCode())};die("PRODUCER_EXEC")}}
