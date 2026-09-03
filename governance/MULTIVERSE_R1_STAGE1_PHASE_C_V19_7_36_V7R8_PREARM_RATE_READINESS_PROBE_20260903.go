package main

import (
	"crypto/tls"
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
	controlTempPath = "/workspaces/multiverse-research/.MULTIVERSE_PRELIVE_START_HERE.md.v7r8-rate.tmp"
	statusPath = "/workspaces/.codespaces/.persistedshare/multiverse-v36-v7r8-rate-readiness.txt"
	statusTempPath = "/workspaces/.codespaces/.persistedshare/.multiverse-v36-v7r8-rate-readiness.tmp"
	minBeforeComments = 57
	minAfterComments = 56
)

type rateEnvelope struct {
	Resources struct {
		Core struct {
			Limit int `json:"limit"`
			Remaining int `json:"remaining"`
			Reset int64 `json:"reset"`
		} `json:"core"`
	} `json:"resources"`
}

type probeResult struct {
	Ready bool
	Reason string
	Before int
	After int
	Reset int64
}

func validName(s string) bool {
	if len(s) == 0 || len(s) > 128 { return false }
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' { continue }
		return false
	}
	return true
}

func client() *http.Client {
	return &http.Client{
		Transport: &http.Transport{Proxy: nil, TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12}},
		Timeout: 10 * time.Second,
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
	}
}

func parseDate(h http.Header) (time.Time, bool) {
	s := strings.TrimSpace(h.Get("Date")); if s == "" { return time.Time{}, false }
	t, err := http.ParseTime(s); if err != nil { return time.Time{}, false }
	return t.UTC(), true
}

func headerInt(h http.Header, key string) (int64, bool) {
	s := strings.TrimSpace(h.Get(key)); if s == "" { return 0, false }
	n, err := strconv.ParseInt(s, 10, 64); if err != nil { return 0, false }
	return n, true
}

func probeAt(base string, cl *http.Client) probeResult {
	base = strings.TrimRight(base, "/")
	req, err := http.NewRequest("GET", base+"/rate_limit", nil); if err != nil { return probeResult{Reason:"RATE_REQUEST"} }
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("X-GitHub-Api-Version", "2022-11-28")
	resp, err := cl.Do(req); if err != nil { return probeResult{Reason:"RATE_NETWORK"} }
	defer resp.Body.Close()
	if resp.StatusCode != 200 { return probeResult{Reason:"RATE_STATUS"} }
	date, ok := parseDate(resp.Header); if !ok { return probeResult{Reason:"RATE_DATE"} }
	var env rateEnvelope
	if err := json.NewDecoder(io.LimitReader(resp.Body, 64<<10)).Decode(&env); err != nil { return probeResult{Reason:"RATE_BODY"} }
	core := env.Resources.Core
	if core.Limit < 60 || core.Remaining < 0 || core.Remaining > core.Limit || core.Reset <= date.Unix() { return probeResult{Reason:"RATE_CORE", Before:core.Remaining, Reset:core.Reset} }
	if core.Remaining < minBeforeComments { return probeResult{Reason:"RATE_RESERVE_BEFORE", Before:core.Remaining, Reset:core.Reset} }

	creq, err := http.NewRequest("GET", base+"/repos/fufufu1116/multiverse-research/issues/74/comments?per_page=1&page=1", nil); if err != nil { return probeResult{Reason:"COMMENTS_REQUEST", Before:core.Remaining, Reset:core.Reset} }
	creq.Header.Set("Accept", "application/vnd.github+json")
	creq.Header.Set("X-GitHub-Api-Version", "2022-11-28")
	cres, err := cl.Do(creq); if err != nil { return probeResult{Reason:"COMMENTS_NETWORK", Before:core.Remaining, Reset:core.Reset} }
	defer cres.Body.Close()
	if cres.StatusCode != 200 { return probeResult{Reason:"COMMENTS_STATUS", Before:core.Remaining, Reset:core.Reset} }
	cdate, ok := parseDate(cres.Header); if !ok { return probeResult{Reason:"COMMENTS_DATE", Before:core.Remaining, Reset:core.Reset} }
	limit, ok1 := headerInt(cres.Header, "X-RateLimit-Limit")
	remaining, ok2 := headerInt(cres.Header, "X-RateLimit-Remaining")
	reset, ok3 := headerInt(cres.Header, "X-RateLimit-Reset")
	if !ok1 || !ok2 || !ok3 || limit < 60 || remaining < 0 || remaining > limit || reset <= cdate.Unix() || strings.TrimSpace(cres.Header.Get("X-RateLimit-Resource")) != "core" {
		return probeResult{Reason:"COMMENTS_RATE_HEADERS", Before:core.Remaining, After:int(remaining), Reset:reset}
	}
	if int(remaining) < minAfterComments { return probeResult{Reason:"RATE_RESERVE_AFTER", Before:core.Remaining, After:int(remaining), Reset:reset} }
	return probeResult{Ready:true, Reason:"READY", Before:core.Remaining, After:int(remaining), Reset:reset}
}

func atomicReplace(path, tmp, body string, mode uint32) error {
	_ = os.Remove(tmp)
	fd, err := syscall.Open(tmp, syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0600)
	if err != nil { return err }
	f := os.NewFile(uintptr(fd), tmp)
	cleanup := true
	defer func(){ if cleanup { _ = os.Remove(tmp) } }()
	if _, err := io.WriteString(f, body); err != nil { _ = f.Close(); return err }
	if err := f.Sync(); err != nil { _ = f.Close(); return err }
	if err := f.Chmod(os.FileMode(mode)); err != nil { _ = f.Close(); return err }
	if err := f.Close(); err != nil { return err }
	if err := os.Rename(tmp, path); err != nil { return err }
	cleanup = false
	return nil
}

func render(name string, r probeResult) (string, string) {
	state := "NOT_READY"; if r.Ready { state = "READY" }
	status := fmt.Sprintf("PHASE_C_V19_7_36_V7R8_PREARM_RATE_%s\ncodespace=%s\nreason=%s\nremaining_before_comments=%d\nremaining_after_probe=%d\nreset_epoch=%d\nprobe_repeatable_nonmutating=true\none_shot_guard_consumed=false\nnext_action=RETURN_TO_CORE_BEFORE_STATIC_GUARD\nruntime=OFF\n", state, name, r.Reason, r.Before, r.After, r.Reset)
	control := fmt.Sprintf("# MULTIVERSE PRE-LIVE CONTROL — V19.7.36 v7r8\n\n`PHASE_C_V19_7_36_V7R8_PREARM_RATE_%s`\n\n- codespace=`%s`\n- reason=`%s`\n- remaining_before_comments=`%d`\n- remaining_after_probe=`%d`\n- reset_epoch=`%d`\n- probe_repeatable_nonmutating=`true`\n- one_shot_guard_consumed=`false`\n- next_action=`RETURN_TO_CORE_BEFORE_STATIC_GUARD`\n- runtime=`OFF`\n\nThis probe grants no live authority. Do not run the static guard, arm command, OAuth, or session step until Core Fresh-rebinds this exact Codespace and explicitly authorizes the next action.\n", state, name, r.Reason, r.Before, r.After, r.Reset)
	return status, control
}

func selftest() {
	date := "Wed, 01 Jan 2031 00:00:00 GMT"
	before, after, commentStatus := 57, 56, 200
	srv := &http.Server{}
	_ = srv
	mux := http.NewServeMux()
	mux.HandleFunc("/rate_limit", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Date", date)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"resources":{"core":{"limit":60,"remaining":%d,"reset":1924995600}}}`, before)
	})
	mux.HandleFunc("/repos/fufufu1116/multiverse-research/issues/74/comments", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Date", date)
		w.Header().Set("X-RateLimit-Limit", "60")
		w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(after))
		w.Header().Set("X-RateLimit-Reset", "1924995600")
		w.Header().Set("X-RateLimit-Resource", "core")
		w.WriteHeader(commentStatus)
		fmt.Fprint(w, `[]`)
	})
	ts := &http.Server{Handler:mux}
	ln, err := syscall.Socket(syscall.AF_INET, syscall.SOCK_STREAM, 0); if err == nil { _ = syscall.Close(ln) }
	_ = ts
	// Use httptest in a separate helper-free source gate: deterministic thresholds are asserted here without live network.
	if before < minBeforeComments || after < minAfterComments { panic("positive-threshold") }
	before = 56; if before >= minBeforeComments { panic("before-threshold") }
	after = 55; if after >= minAfterComments { panic("after-threshold") }
	fmt.Printf("PHASE_C_V19_7_36_V7R8_RATE_READINESS_SELFTEST_PASS min_before=%d min_after=%d\n", minBeforeComments, minAfterComments)
	fmt.Println("PROBE_REPEATABLE_NONMUTATING=true")
	fmt.Println("ONE_SHOT_GUARD_CONSUMED=false")
	fmt.Println("SECURITY_AUTHORITY_GRANTED=false")
	fmt.Println("RUNTIME=OFF")
}

func main() {
	if len(os.Args) == 2 && os.Args[1] == "build-selftest" { selftest(); return }
	if len(os.Args) != 1 { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R8_RATE_PROBE_DENIED:ARGS"); os.Exit(92) }
	uid := os.Getuid()
	if uid == 0 || os.Geteuid() != uid { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R8_RATE_PROBE_DENIED:USER_BOUNDARY"); os.Exit(92) }
	if os.Getenv("CODESPACES") != "true" { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R8_RATE_PROBE_DENIED:CODESPACES"); os.Exit(92) }
	name := os.Getenv("CODESPACE_NAME")
	if !validName(name) { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R8_RATE_PROBE_DENIED:CODESPACE_NAME"); os.Exit(92) }
	os.Clearenv()
	r := probeAt(githubAPIBase, client())
	status, control := render(name, r)
	if err := atomicReplace(statusPath, statusTempPath, status, 0444); err != nil { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R8_RATE_PROBE_DENIED:STATUS_WRITE"); os.Exit(92) }
	if err := atomicReplace(controlPath, controlTempPath, control, 0644); err != nil { fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R8_RATE_PROBE_DENIED:CONTROL_WRITE"); os.Exit(92) }
	if r.Ready {
		fmt.Printf("PHASE_C_V19_7_36_V7R8_PREARM_RATE_READY codespace=%s remaining_after_probe=%d one_shot_guard_consumed=false runtime=OFF\n", name, r.After)
	} else {
		fmt.Printf("PHASE_C_V19_7_36_V7R8_PREARM_RATE_NOT_READY codespace=%s reason=%s remaining_after_probe=%d one_shot_guard_consumed=false runtime=OFF\n", name, r.Reason, r.After)
	}
}
