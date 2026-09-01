package main

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"
)

const gitPath = "/usr/bin/git"
const ghPath = "/usr/bin/gh"
const browserPath = "/bin/false"

func die(s string) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7_CONTROL_DENIED:"+s); os.Exit(92) }
func openC(p string) (*os.File, error) {
	f, e := os.Open(p)
	if e != nil {
		return nil, e
	}
	st, e := f.Stat()
	if e != nil {
		f.Close()
		return nil, e
	}
	u := st.Sys().(*syscall.Stat_t).Uid
	if u != 0 || st.Mode().Perm()&0022 != 0 || !st.Mode().IsRegular() {
		f.Close()
		return nil, errors.New("class-c")
	}
	return f, nil
}
func env(extra ...string) []string {
	v := []string{"LANG=C", "LC_ALL=C", "PATH=/usr/bin:/bin", "HOME=/nonexistent", "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=/dev/null", "GIT_CONFIG_SYSTEM=/dev/null", "GIT_TERMINAL_PROMPT=0", "GIT_ASKPASS=/bin/false", "SSH_ASKPASS=/bin/false", "GH_BROWSER=/bin/false", "GH_PAGER=cat"}
	return append(v, extra...)
}
func runfd(p string, args []string, ev []string, timeout time.Duration) ([]byte, []byte, error) {
	f, e := openC(p)
	if e != nil {
		return nil, nil, e
	}
	defer f.Close()
	c := exec.Command("/proc/self/fd/3", args...)
	c.ExtraFiles = []*os.File{f}
	c.Env = ev
	var o, r bytes.Buffer
	c.Stdout = &o
	c.Stderr = &r
	if timeout > 0 {
		done := make(chan error, 1)
		go func() { done <- c.Run() }()
		select {
		case e = <-done:
		case <-time.After(timeout):
			if c.Process != nil {
				_ = c.Process.Kill()
			}
			e = errors.New("timeout")
		}
	} else {
		e = c.Run()
	}
	return o.Bytes(), r.Bytes(), e
}
func buildSelftest() {
	o, _, e := runfd(gitPath, []string{"ls-remote", "--exit-code", "https://github.com/fufufu1116/multiverse-research", "refs/heads/main"}, env("GIT_PROTOCOL_FROM_USER=0"), 20*time.Second)
	if e != nil || !strings.Contains(string(o), "refs/heads/main") {
		die("GIT_LS_REMOTE")
	}
	if _, _, e = runfd(ghPath, []string{"version"}, env(), 5*time.Second); e != nil {
		die("GH_VERSION")
	}
	_, _, e = runfd(browserPath, nil, env(), 2*time.Second)
	if x, ok := e.(*exec.ExitError); !ok || x.ExitCode() != 1 {
		die("BROWSER_FALSE")
	}
	fmt.Println("PHASE_C_V19_7_36_V7_CONTROL_BUILD_SELFTEST_PASS")
}
func postOAuth() { // Frozen future-only actions. Credential source must be reviewed GH_CONFIG_DIR supplied by producer after OAuth.
	d := os.Getenv("GH_CONFIG_DIR")
	if d == "" || !strings.HasPrefix(d, "/dev/shm/") {
		die("GH_CONFIG_DIR")
	}
	ev := env("GH_CONFIG_DIR=" + d)
	allowed := map[string][]string{"user": {"api", "--hostname", "github.com", "--method", "GET", "/user"}, "repo": {"api", "--hostname", "github.com", "--method", "GET", "/repos/fufufu1116/multiverse-research"}, "ruleset": {"api", "--hostname", "github.com", "--method", "GET", "/repos/fufufu1116/multiverse-research/rulesets/21227261"}}
	a := os.Getenv("MULTIVERSE_V36_V7_CONTROL_ACTION")
	args, ok := allowed[a]
	if !ok {
		die("ACTION")
	}
	o, r, e := runfd(ghPath, args, ev, 15*time.Second)
	if e != nil {
		_, _ = io.Copy(os.Stderr, bytes.NewReader(r))
		die("GH_ACTION")
	}
	_, _ = os.Stdout.Write(o)
}
func main() {
	if len(os.Args) != 2 {
		die("ARGV")
	}
	switch os.Args[1] {
	case "build-selftest":
		buildSelftest()
	case "post-oauth":
		postOAuth()
	default:
		die("ACTION")
	}
}
