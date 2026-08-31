package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

const gitPath = "/usr/bin/git"
const ghPath = "/usr/bin/gh"
const browserPath = "/bin/false"
const cfg = "/dev/shm/multiverse-v36-gh-root"
const apiVersion = "2022-11-28"
const repo = "fufufu1116/multiverse-research"
const rulesetID = "21227261"
const fenceEndpoint = "/repos/fufufu1116/multiverse-research/git/ref/tags/multiverse-r1-stage1-writer-provision-fence-v1"
const environmentEndpoint = "/repos/fufufu1116/multiverse-research/environments/multiverse-r1-stage1-writer-key-v1"

type Result struct {
	Version      string `json:"version"`
	Action       string `json:"action"`
	RC           int    `json:"rc"`
	Mutations    int    `json:"mutations"`
	StdoutSHA256 string `json:"stdout_sha256"`
	StdoutBytes  int    `json:"stdout_bytes"`
}

type Step3Receipt struct {
	Version        string          `json:"version"`
	Action         string          `json:"action"`
	Mutations      int             `json:"mutations"`
	Checks         map[string]bool `json:"checks"`
	EvidenceSHA256 string          `json:"evidence_sha256"`
}

func die(s string) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V6_CONTROL_DENIED:"+s); os.Exit(92) }

func rootFile(p string) *os.File {
	r, e := filepath.EvalSymlinks(p)
	if e != nil {
		die("REALPATH")
	}
	fi, e := os.Stat(r)
	if e != nil {
		die("STAT")
	}
	st, ok := fi.Sys().(*syscall.Stat_t)
	if !ok || st.Uid != 0 || fi.Mode().Perm()&0022 != 0 || !fi.Mode().IsRegular() {
		die("CLASS_C")
	}
	f, e := os.Open(r)
	if e != nil {
		die("OPEN")
	}
	return f
}

func fixedEnv() []string {
	return []string{
		"LANG=C", "LC_ALL=C", "PATH=/usr/bin:/bin", "HOME=/nonexistent",
		"XDG_CONFIG_HOME=" + cfg, "GH_CONFIG_DIR=" + cfg, "GH_BROWSER=" + browserPath, "GH_PAGER=cat",
		"GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=/dev/null", "GIT_CONFIG_SYSTEM=/dev/null",
		"GIT_TERMINAL_PROMPT=0", "GIT_ASKPASS=/bin/false", "SSH_ASKPASS=/bin/false",
		"GIT_CONFIG_COUNT=4", "GIT_CONFIG_KEY_0=credential.helper", "GIT_CONFIG_VALUE_0=",
		"GIT_CONFIG_KEY_1=core.hooksPath", "GIT_CONFIG_VALUE_1=/dev/null",
		"GIT_CONFIG_KEY_2=protocol.file.allow", "GIT_CONFIG_VALUE_2=never",
		"GIT_CONFIG_KEY_3=protocol.ext.allow", "GIT_CONFIG_VALUE_3=never",
	}
}

func runFD(p string, args []string, interactive bool) (int, []byte) {
	f := rootFile(p)
	defer f.Close()
	c := exec.Command("/proc/self/fd/3", args...)
	c.ExtraFiles = []*os.File{f}
	c.Env = fixedEnv()
	var b, eb bytes.Buffer
	if interactive {
		c.Stdin = os.Stdin
		c.Stdout = os.Stdout
		c.Stderr = os.Stderr
	} else {
		c.Stdout = &b
		c.Stderr = &eb
	}
	e := c.Run()
	if e == nil {
		return 0, b.Bytes()
	}
	if x, ok := e.(*exec.ExitError); ok {
		return x.ExitCode(), b.Bytes()
	}
	die("EXEC")
	return 92, nil
}

func ghArgs(endpoint string, include bool) []string {
	a := []string{"api", "--hostname", "github.com"}
	if include {
		a = append(a, "--include")
	}
	a = append(a, "--method", "GET", "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: "+apiVersion, endpoint)
	return a
}

func parseIncluded(b []byte) (int, map[string]string, []byte) {
	s := strings.ReplaceAll(string(b), "\r\n", "\n")
	parts := strings.SplitN(s, "\n\n", 2)
	if len(parts) != 2 {
		die("INCLUDED_FORMAT")
	}
	lines := strings.Split(parts[0], "\n")
	if len(lines) == 0 || !strings.HasPrefix(lines[0], "HTTP/") {
		die("HTTP_STATUS")
	}
	f := strings.Fields(lines[0])
	if len(f) < 2 {
		die("HTTP_STATUS")
	}
	st, e := strconv.Atoi(f[1])
	if e != nil {
		die("HTTP_STATUS")
	}
	h := map[string]string{}
	for _, l := range lines[1:] {
		if i := strings.IndexByte(l, ':'); i > 0 {
			k := strings.ToLower(strings.TrimSpace(l[:i]))
			if _, ok := h[k]; ok {
				die("DUP_HEADER")
			}
			h[k] = strings.TrimSpace(l[i+1:])
		}
	}
	return st, h, []byte(strings.TrimSpace(parts[1]))
}

func ghIncluded(endpoint string) (int, map[string]string, []byte) {
	rc, out := runFD(ghPath, ghArgs(endpoint, true), false)
	if rc != 0 && len(out) == 0 {
		die("GH_NO_RESPONSE")
	}
	return parseIncluded(out)
}

func checkStep3() Step3Receipt {
	checks := map[string]bool{}
	var evidence bytes.Buffer
	st, h, b := ghIncluded("/user")
	var user map[string]any
	if json.Unmarshal(b, &user) != nil || st != 200 || user["login"] != "fufufu1116" {
		die("STEP3_USER")
	}
	scopes := map[string]bool{}
	for _, x := range strings.Split(h["x-oauth-scopes"], ",") {
		x = strings.TrimSpace(x)
		if x != "" {
			scopes[x] = true
		}
	}
	if len(scopes) != 3 || !scopes["repo"] || !scopes["read:org"] || !scopes["gist"] {
		die("STEP3_SCOPES")
	}
	checks["identity_scope_exact"] = true
	evidence.Write(b)
	st, _, b = ghIncluded("/repos/" + repo)
	var rp map[string]any
	if json.Unmarshal(b, &rp) != nil || st != 200 {
		die("STEP3_REPO")
	}
	pm, ok := rp["permissions"].(map[string]any)
	if !ok || pm["admin"] != true {
		die("STEP3_ADMIN")
	}
	checks["repo_admin"] = true
	evidence.Write(b)
	st, _, b = ghIncluded("/repos/" + repo + "/git/ref/heads/main")
	var mr map[string]any
	if json.Unmarshal(b, &mr) != nil || st != 200 {
		die("STEP3_MAIN")
	}
	obj, ok := mr["object"].(map[string]any)
	if !ok || obj["sha"] != "5c1403c1f5aabb80d29e8c868440aede8888ce61" {
		die("STEP3_MAIN_DRIFT")
	}
	checks["main_exact"] = true
	evidence.Write(b)
	st, _, b = ghIncluded("/repos/" + repo + "/rulesets/" + rulesetID)
	var rs map[string]any
	if json.Unmarshal(b, &rs) != nil || st != 200 {
		die("STEP3_RULESET")
	}
	rid, ok := rs["id"].(float64)
	if !ok || int64(rid) != 21227261 || rs["updated_at"] != "2026-08-23T06:39:18.750Z" {
		die("STEP3_RULESET")
	}
	checks["ruleset_binding"] = true
	evidence.Write(b)
	st, _, _ = ghIncluded(fenceEndpoint)
	if st != 404 {
		die("STEP3_FENCE")
	}
	checks["fence_absent_404"] = true
	st, _, _ = ghIncluded(environmentEndpoint)
	if st != 404 {
		die("STEP3_ENVIRONMENT")
	}
	checks["environment_absent_404"] = true
	hh := sha256.Sum256(evidence.Bytes())
	return Step3Receipt{"V19.7.36-v6", "STEP3_NONMUTATING_PREFLIGHT", 0, checks, hex.EncodeToString(hh[:])}
}

func main() {
	if os.Geteuid() != 0 {
		die("ROOT_REQUIRED")
	}
	if len(os.Args) != 2 {
		die("ARGV")
	}
	a := os.Args[1]
	if a == "oauth-login" {
		if e := os.MkdirAll(cfg, 0700); e != nil {
			die("CFG")
		}
		_ = os.Chown(cfg, 0, 0)
		rc, _ := runFD(ghPath, []string{"auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web", "--scopes", "repo,read:org,gist"}, true)
		if rc != 0 {
			os.Exit(rc)
		}
		return
	}
	if a == "step3-preflight" {
		r := checkStep3()
		if e := json.NewEncoder(os.Stdout).Encode(r); e != nil {
			die("OUTPUT")
		}
		return
	}
	var p string
	var args []string
	switch a {
	case "gh-user":
		p = ghPath
		args = ghArgs("/user", true)
	case "gh-repo":
		p = ghPath
		args = ghArgs("/repos/"+repo, true)
	case "gh-ruleset":
		p = ghPath
		args = ghArgs("/repos/"+repo+"/rulesets/"+rulesetID, true)
	case "gh-main-ref":
		p = ghPath
		args = ghArgs("/repos/"+repo+"/git/ref/heads/main", true)
	case "gh-fence":
		p = ghPath
		args = ghArgs(fenceEndpoint, true)
	case "gh-environment":
		p = ghPath
		args = ghArgs(environmentEndpoint, true)
	case "git-ls-remote-main":
		p = gitPath
		args = []string{"ls-remote", "--exit-code", "https://github.com/fufufu1116/multiverse-research.git", "refs/heads/main"}
	default:
		die("ACTION")
	}
	rc, out := runFD(p, args, false)
	hh := sha256.Sum256(out)
	r := Result{"V19.7.36-v6", a, rc, 0, hex.EncodeToString(hh[:]), len(out)}
	_ = json.NewEncoder(io.Writer(os.Stdout)).Encode(r)
	if rc != 0 {
		os.Exit(rc)
	}
}
