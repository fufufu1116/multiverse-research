package main

import (
    "bufio"
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "os"
    "os/exec"
    "strconv"
    "strings"
    "syscall"
    "time"
)

const ghPath = "/usr/bin/gh"
const gitPath = "/usr/bin/git"
const mainWant = "5c1403c1f5aabb80d29e8c868440aede8888ce61"
const envName = "multiverse-r1-stage1-writer-key-v1"
const fenceRef = "/repos/fufufu1116/multiverse-research/git/ref/tags/multiverse-r1-stage1-writer-provision-fence-v1"

func die(s string) { fmt.Fprintln(os.Stderr,"PHASE_C_V19_7_36_V7R2_CONTROL_DENIED:"+s); os.Exit(92) }
func openC(p string)(*os.File,error){ f,e:=os.Open(p); if e!=nil{return nil,e}; st,e:=f.Stat(); if e!=nil{f.Close();return nil,e}; if st.Sys().(*syscall.Stat_t).Uid!=0 || st.Mode().Perm()&0022!=0 || !st.Mode().IsRegular(){f.Close();return nil,errors.New("class-c")}; return f,nil }
func env(d string)[]string{return []string{"LANG=C","LC_ALL=C","PATH=/usr/bin:/bin","HOME=/nonexistent","GH_CONFIG_DIR="+d,"GIT_CONFIG_NOSYSTEM=1","GIT_CONFIG_GLOBAL=/dev/null","GIT_CONFIG_SYSTEM=/dev/null","GIT_TERMINAL_PROMPT=0","GIT_ASKPASS=/bin/false","SSH_ASKPASS=/bin/false","GH_BROWSER=/bin/false","GH_PAGER=cat"}}
func runfd(p string,args []string,ev []string,timeout time.Duration)([]byte,[]byte,error){f,e:=openC(p);if e!=nil{return nil,nil,e};defer f.Close();c:=exec.Command("/proc/self/fd/3",args...);c.ExtraFiles=[]*os.File{f};c.Env=ev;var o,r bytes.Buffer;c.Stdout=&o;c.Stderr=&r;done:=make(chan error,1);go func(){done<-c.Run()}();select{case e=<-done:case <-time.After(timeout):if c.Process!=nil{_=c.Process.Kill()};e=errors.New("timeout")};return o.Bytes(),r.Bytes(),e}

type HTTP struct{Status int;Headers map[string]string;Body []byte}
func included(raw []byte)(HTTP,error){s:=strings.ReplaceAll(string(raw),"\r\n","\n");a:=strings.SplitN(s,"\n\n",2);if len(a)!=2{return HTTP{},errors.New("headers")};lines:=strings.Split(a[0],"\n");if len(lines)==0||!strings.HasPrefix(lines[0],"HTTP/"){return HTTP{},errors.New("status")};f:=strings.Fields(lines[0]);if len(f)<2{return HTTP{},errors.New("status")};n,e:=strconv.Atoi(f[1]);if e!=nil{return HTTP{},e};h:=map[string]string{};for _,l:=range lines[1:]{if i:=strings.IndexByte(l,':');i>0{h[strings.ToLower(strings.TrimSpace(l[:i]))]=strings.TrimSpace(l[i+1:])}};return HTTP{n,h,[]byte(a[1])},nil}
func ghGet(ep,d string)(HTTP,error){o,r,e:=runfd(ghPath,[]string{"api","--hostname","github.com","--include","-H","Accept: application/vnd.github+json","-H","X-GitHub-Api-Version: 2022-11-28","--method","GET",ep},env(d),20*time.Second);if e!=nil && len(o)==0{return HTTP{},fmt.Errorf("gh:%w:%s",e,string(r))};return included(o)}
func scopes(h string)bool{m:=map[string]bool{};for _,x:=range strings.Split(h,","){x=strings.TrimSpace(x);if x!=""{m[x]=true}};return len(m)==3&&m["repo"]&&m["read:org"]&&m["gist"]}
func step3(d string)map[string]any{
    r:=bufio.NewReader(io.LimitReader(os.NewFile(3,"control"),1<<20));line,e:=r.ReadBytes('\n');if e!=nil{die("REQUEST")};var q map[string]any;if json.Unmarshal(line,&q)!=nil||q["action"]!="STEP3_NONMUTATING_PREFLIGHT"||q["version"]!="V19.7.36-v6"{die("REQUEST_SCHEMA")}
    u,e:=ghGet("/user",d);if e!=nil||u.Status!=200{die("USER")};if !scopes(u.Headers["x-oauth-scopes"]){die("SCOPES")};var uj map[string]any;if json.Unmarshal(u.Body,&uj)!=nil||uj["login"]!="fufufu1116"{die("IDENTITY")}
    rp,e:=ghGet("/repos/fufufu1116/multiverse-research",d);if e!=nil||rp.Status!=200{die("REPO")};var rj map[string]any;if json.Unmarshal(rp.Body,&rj)!=nil{die("REPO_JSON")};pm,ok:=rj["permissions"].(map[string]any);if !ok||pm["admin"]!=true{die("ADMIN")}
    ma,e:=ghGet("/repos/fufufu1116/multiverse-research/git/ref/heads/main",d);if e!=nil||ma.Status!=200{die("MAIN")};var mj struct{Object struct{SHA string `json:"sha"`} `json:"object"`};if json.Unmarshal(ma.Body,&mj)!=nil||mj.Object.SHA!=mainWant{die("MAIN_SHA")}
    rs,e:=ghGet("/repos/fufufu1116/multiverse-research/rulesets/21227261",d);if e!=nil||rs.Status!=200{die("RULESET")}
    fe,e:=ghGet(fenceRef,d);if e!=nil||fe.Status!=404{die("FENCE_NOT_ABSENT")}
    en,e:=ghGet("/repos/fufufu1116/multiverse-research/environments/"+envName,d);if e!=nil||en.Status!=404{die("ENV_NOT_ABSENT")}
    return map[string]any{"version":"V19.7.36-v6","action":"STEP3_NONMUTATING_PREFLIGHT","mutations":0,"identity":true,"scopes":true,"repo_admin":true,"fresh_main":true,"ruleset":true,"fence_absent_404":true,"environment_absent_404":true}
}
func buildSelftest(){o,_,e:=runfd(gitPath,[]string{"ls-remote","--exit-code","https://github.com/fufufu1116/multiverse-research","refs/heads/main"},env("/opt/multiverse/v36/empty-config"),20*time.Second);if e!=nil||!strings.Contains(string(o),"refs/heads/main"){die("GIT_SELFTEST")};if _,_,e=runfd(ghPath,[]string{"version"},env("/opt/multiverse/v36/empty-config"),5*time.Second);e!=nil{die("GH_SELFTEST")};fmt.Println("PHASE_C_V19_7_36_V7R2_CONTROL_BUILD_SELFTEST_PASS")}
func main(){if len(os.Args)!=2{die("ARGV")};switch os.Args[1]{case "build-selftest":buildSelftest();case "step3-preflight":d:=os.Getenv("GH_CONFIG_DIR");if !strings.HasPrefix(d,"/dev/shm/"){die("GH_CONFIG_DIR")};b,_:=json.Marshal(step3(d));_,_=os.Stdout.Write(b);default:die("ACTION")}}
