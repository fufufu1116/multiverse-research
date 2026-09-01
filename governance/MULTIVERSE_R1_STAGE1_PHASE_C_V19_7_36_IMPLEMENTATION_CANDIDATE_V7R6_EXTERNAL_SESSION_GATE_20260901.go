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
	"net/url"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const commentsEndpoint = "https://api.github.com/repos/fufufu1116/multiverse-research/issues/74/comments"
const producerPath = "/usr/local/sbin/multiverse-v36-anchor-v7r2"
const imageIdentityPath = "/opt/multiverse/v36/image-identity-v7r3.json"
const requiredApp = "chatgpt-codex-connector"
const requiredUser = "fufufu1116"
const freezePrefix = "MULTIVERSE_V7R6_CANDIDATE_FREEZE "
const receiptPrefix = "MULTIVERSE_V7R6_SESSION_BINDING "
const approvalPrefix = "MULTIVERSE_V7R6_OWNER_APPROVAL_RECEIPT "
const apiHardBudget = 40
const apiReserveRemaining = 8
const pollInterval = 30 * time.Second
const approvalWindow = 10 * time.Minute
const cursorOverlap = 2 * time.Second

type comment struct {
	ID        int64     `json:"id"`
	Body      string    `json:"body"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	User      struct {
		Login string `json:"login"`
	} `json:"user"`
	PerformedVia *struct {
		Slug string `json:"slug"`
	} `json:"performed_via_github_app"`
}
type freezeReceipt struct{ Version, CandidateHead, CandidateTree, ImageIdentitySHA256, ExactPhrase, Runtime string }
type sessionReceipt struct {
	Version, CodespaceName, Challenge, CandidateHead, CandidateTree, ImageIdentitySHA256 string
	CandidateFreezeComment, OwnerApprovalComment                                         int64
	OneShot                                                                              bool
	Runtime                                                                              string
}
type approvalReceipt struct {
	Version, CodespaceName, Challenge, CandidateHead, CandidateTree, ImageIdentitySHA256 string
	CandidateFreezeComment                                                               int64
	ExactPhrase                                                                          string
	OneShot                                                                              bool
	Runtime                                                                              string
}
type apiBudget struct{ Used int }

func die(s string) {
	fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R6_SESSION_GATE_DENIED:"+s)
	os.Exit(92)
}
func isHex(s string, n int) bool {
	if len(s) != n {
		return false
	}
	_, e := hex.DecodeString(s)
	return e == nil
}
func unedited(c comment) bool {
	return !c.CreatedAt.IsZero() && !c.UpdatedAt.IsZero() && c.CreatedAt.Equal(c.UpdatedAt)
}
func evidenceBound(c comment) bool {
	return unedited(c) && c.User.Login == requiredUser && c.PerformedVia != nil && c.PerformedVia.Slug == requiredApp
}
func ownerBound(c comment) bool {
	return unedited(c) && c.User.Login == requiredUser && c.PerformedVia == nil
}
func linePayload(body, prefix string) ([]byte, bool) {
	for _, l := range strings.Split(body, "\n") {
		if strings.HasPrefix(l, prefix) {
			return []byte(strings.TrimPrefix(l, prefix)), true
		}
	}
	return nil, false
}
func httpClient() *http.Client {
	return &http.Client{Transport: &http.Transport{Proxy: nil, TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12}}, Timeout: 10 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
}

func (b *apiBudget) before() error {
	if b.Used >= apiHardBudget {
		return errors.New("api-hard-budget")
	}
	b.Used++
	return nil
}
func rateState(h http.Header) error {
	if r := strings.TrimSpace(h.Get("X-RateLimit-Remaining")); r != "" {
		n, e := strconv.Atoi(r)
		if e != nil {
			return errors.New("rate-remaining-invalid")
		}
		if n <= apiReserveRemaining {
			return errors.New("rate-budget-reserve")
		}
	}
	return nil
}
func getCommentsPage(cl *http.Client, b *apiBudget, page int, since *time.Time) ([]comment, http.Header, error) {
	if e := b.before(); e != nil {
		return nil, nil, e
	}
	q := url.Values{}
	q.Set("per_page", "100")
	q.Set("page", strconv.Itoa(page))
	if since != nil {
		q.Set("since", since.UTC().Format(time.RFC3339))
	}
	r, e := http.NewRequest("GET", commentsEndpoint+"?"+q.Encode(), nil)
	if e != nil {
		return nil, nil, e
	}
	r.Header.Set("Accept", "application/vnd.github+json")
	r.Header.Set("X-GitHub-Api-Version", "2022-11-28")
	x, e := cl.Do(r)
	if e != nil {
		return nil, nil, e
	}
	defer x.Body.Close()
	h := x.Header.Clone()
	if x.StatusCode == 429 || x.StatusCode == 403 && (h.Get("Retry-After") != "" || h.Get("X-RateLimit-Remaining") == "0") {
		return nil, h, errors.New("rate-limited")
	}
	if x.StatusCode != 200 {
		return nil, h, fmt.Errorf("http:%d", x.StatusCode)
	}
	if e = rateState(h); e != nil {
		return nil, h, e
	}
	var z []comment
	if e = json.NewDecoder(io.LimitReader(x.Body, 8<<20)).Decode(&z); e != nil {
		return nil, h, e
	}
	return z, h, nil
}
func headerDate(h http.Header) (time.Time, error) {
	d := h.Get("Date")
	if d == "" {
		return time.Time{}, errors.New("date-missing")
	}
	t, e := http.ParseTime(d)
	if e != nil {
		return time.Time{}, e
	}
	return t.UTC(), nil
}
func githubServerNow(cl *http.Client, b *apiBudget) (time.Time, error) {
	_, h, e := getCommentsPage(cl, b, 1, nil)
	if e != nil {
		return time.Time{}, e
	}
	return headerDate(h)
}
func merge(dst map[int64]comment, z []comment) {
	for _, c := range z {
		dst[c.ID] = c
	}
}
func snapshot(dst map[int64]comment) []comment {
	out := make([]comment, 0, len(dst))
	for _, c := range dst {
		out = append(out, c)
	}
	return out
}
func fullComments(cl *http.Client, b *apiBudget) (map[int64]comment, time.Time, error) {
	out := make(map[int64]comment, 600)
	var watermark time.Time
	for p := 1; p <= 100; p++ {
		z, h, e := getCommentsPage(cl, b, p, nil)
		if e != nil {
			return nil, time.Time{}, e
		}
		merge(out, z)
		d, e := headerDate(h)
		if e != nil {
			return nil, time.Time{}, e
		}
		if d.After(watermark) {
			watermark = d
		}
		if len(z) < 100 {
			return out, watermark, nil
		}
	}
	return nil, time.Time{}, errors.New("comment-pagination-limit")
}
func deltaComments(cl *http.Client, b *apiBudget, state map[int64]comment, cursor time.Time) (time.Time, error) {
	since := cursor.Add(-cursorOverlap)
	watermark := cursor
	for p := 1; p <= 100; p++ {
		z, h, e := getCommentsPage(cl, b, p, &since)
		if e != nil {
			return cursor, e
		}
		merge(state, z)
		d, e := headerDate(h)
		if e != nil {
			return cursor, e
		}
		if d.After(watermark) {
			watermark = d
		}
		if len(z) < 100 {
			return watermark, nil
		}
	}
	return cursor, errors.New("comment-pagination-limit")
}

func imageIdentity() (string, error) {
	f, e := os.Open(imageIdentityPath)
	if e != nil {
		return "", e
	}
	defer f.Close()
	st, e := f.Stat()
	if e != nil {
		return "", e
	}
	if st.Sys().(*syscall.Stat_t).Uid != 0 || st.Mode().Perm()&0022 != 0 || !st.Mode().IsRegular() {
		return "", errors.New("identity-class-c")
	}
	b, e := io.ReadAll(io.LimitReader(f, 1<<20))
	if e != nil {
		return "", e
	}
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:]), nil
}
func parseFreeze(c comment) (freezeReceipt, bool) {
	if !evidenceBound(c) {
		return freezeReceipt{}, false
	}
	b, ok := linePayload(c.Body, freezePrefix)
	if !ok {
		return freezeReceipt{}, false
	}
	var f freezeReceipt
	if json.Unmarshal(b, &f) != nil {
		return freezeReceipt{}, false
	}
	if f.Version != "V19.7.36-v7r6" || !isHex(f.CandidateHead, 40) || !isHex(f.CandidateTree, 40) || !isHex(f.ImageIdentitySHA256, 64) || f.ExactPhrase != "FREEZE V19.7.36 v7r6 CANDIDATE" || f.Runtime != "OFF" {
		return freezeReceipt{}, false
	}
	return f, true
}
func findFreeze(cs []comment, id int64, identity string) (freezeReceipt, error) {
	matches := 0
	var chosen freezeReceipt
	found := false
	for _, c := range cs {
		f, ok := parseFreeze(c)
		if !ok || f.ImageIdentitySHA256 != identity {
			continue
		}
		matches++
		if c.ID == id {
			chosen = f
			found = true
		}
	}
	if !found {
		return freezeReceipt{}, errors.New("freeze-missing")
	}
	if matches != 1 {
		return freezeReceipt{}, errors.New("freeze-ambiguous")
	}
	return chosen, nil
}
func parseApproval(c comment, s sessionReceipt, issued time.Time) (approvalReceipt, bool) {
	if !ownerBound(c) || c.CreatedAt.Before(issued) {
		return approvalReceipt{}, false
	}
	b, ok := linePayload(c.Body, approvalPrefix)
	if !ok {
		return approvalReceipt{}, false
	}
	var a approvalReceipt
	if json.Unmarshal(b, &a) != nil {
		return approvalReceipt{}, false
	}
	ok = a.Version == "V19.7.36-v7r6" && a.CodespaceName == s.CodespaceName && a.Challenge == s.Challenge && a.CandidateHead == s.CandidateHead && a.CandidateTree == s.CandidateTree && a.ImageIdentitySHA256 == s.ImageIdentitySHA256 && a.CandidateFreezeComment == s.CandidateFreezeComment && a.ExactPhrase == "APPROVE V19.7.36 v7r6 ONE-SHOT LIVE" && a.OneShot && a.Runtime == "OFF"
	return a, ok
}
func selectReceipt(cs []comment, name, challenge, identity string, issued time.Time) (sessionReceipt, error) {
	matches := 0
	var got sessionReceipt
	for _, c := range cs {
		if !evidenceBound(c) {
			continue
		}
		b, ok := linePayload(c.Body, receiptPrefix)
		if !ok {
			continue
		}
		var s sessionReceipt
		if json.Unmarshal(b, &s) != nil {
			continue
		}
		if s.Version != "V19.7.36-v7r6" || s.CodespaceName != name || s.Challenge != challenge || s.ImageIdentitySHA256 != identity || !s.OneShot || s.Runtime != "OFF" || !isHex(s.CandidateHead, 40) || !isHex(s.CandidateTree, 40) {
			continue
		}
		f, e := findFreeze(cs, s.CandidateFreezeComment, identity)
		if e != nil || f.CandidateHead != s.CandidateHead || f.CandidateTree != s.CandidateTree {
			continue
		}
		approvalCount := 0
		var approvalID int64
		for _, a := range cs {
			if _, ok := parseApproval(a, s, issued); ok && !a.CreatedAt.After(c.CreatedAt) {
				approvalCount++
				approvalID = a.ID
			}
		}
		if approvalCount != 1 || approvalID != s.OwnerApprovalComment {
			continue
		}
		matches++
		got = s
	}
	if matches == 1 {
		return got, nil
	}
	if matches > 1 {
		return sessionReceipt{}, errors.New("ambiguous")
	}
	return sessionReceipt{}, errors.New("missing")
}
func waitReceipt(cl *http.Client, b *apiBudget, name, challenge, identity string, issued time.Time) (sessionReceipt, error) {
	state, cursor, e := fullComments(cl, b)
	if e != nil {
		return sessionReceipt{}, e
	}
	deadline := time.Now().Add(approvalWindow)
	for {
		if s, e := selectReceipt(snapshot(state), name, challenge, identity, issued); e == nil {
			return s, nil
		} else if e.Error() == "ambiguous" {
			return sessionReceipt{}, e
		}
		if !time.Now().Before(deadline) {
			return sessionReceipt{}, errors.New("timeout")
		}
		time.Sleep(pollInterval)
		cursor, e = deltaComments(cl, b, state, cursor)
		if e != nil {
			return sessionReceipt{}, e
		}
	}
}

func mkComment(id int64, created time.Time, prefix string, v any, owner bool) comment {
	b, _ := json.Marshal(v)
	var c comment
	c.ID = id
	c.CreatedAt = created
	c.UpdatedAt = created
	c.Body = prefix + string(b)
	c.User.Login = requiredUser
	if !owner {
		c.PerformedVia = &struct {
			Slug string `json:"slug"`
		}{Slug: requiredApp}
	}
	return c
}
func projectedRequests(initialPages, polls, deltaPages int) int {
	return 1 + initialPages + polls*deltaPages
}
func selftest() {
	t := time.Unix(2000000000, 0).UTC()
	head := strings.Repeat("a", 40)
	tree := strings.Repeat("b", 40)
	image := strings.Repeat("c", 64)
	challenge := strings.Repeat("d", 32)
	f := freezeReceipt{"V19.7.36-v7r6", head, tree, image, "FREEZE V19.7.36 v7r6 CANDIDATE", "OFF"}
	a := approvalReceipt{"V19.7.36-v7r6", "cs1", challenge, head, tree, image, 1, "APPROVE V19.7.36 v7r6 ONE-SHOT LIVE", true, "OFF"}
	s := sessionReceipt{"V19.7.36-v7r6", "cs1", challenge, head, tree, image, 1, 2, true, "OFF"}
	base := []comment{mkComment(1, t, freezePrefix, f, false), mkComment(2, t.Add(time.Second), approvalPrefix, a, true), mkComment(3, t.Add(2*time.Second), receiptPrefix, s, false)}
	if _, e := selectReceipt(base, "cs1", challenge, image, t); e != nil {
		panic("positive")
	}
	tests := [][]comment{}
	add := func(x []comment) { tests = append(tests, x) }
	x := append([]comment{}, base...)
	x[0].UpdatedAt = x[0].UpdatedAt.Add(time.Second)
	add(x)
	x = append([]comment{}, base...)
	x[1].UpdatedAt = x[1].UpdatedAt.Add(time.Second)
	add(x)
	x = append([]comment{}, base...)
	x[2].UpdatedAt = x[2].UpdatedAt.Add(time.Second)
	add(x)
	x = append([]comment{}, base...)
	x[1].PerformedVia = &struct {
		Slug string `json:"slug"`
	}{Slug: requiredApp}
	add(x)
	x = append([]comment{}, base...)
	x = append(x, mkComment(4, t.Add(time.Second), approvalPrefix, a, true))
	add(x)
	x = append([]comment{}, base...)
	s2 := s
	s2.CandidateHead = strings.Repeat("e", 40)
	x[2] = mkComment(3, t.Add(2*time.Second), receiptPrefix, s2, false)
	add(x)
	x = append([]comment{}, base...)
	s2 = s
	s2.CandidateTree = strings.Repeat("e", 40)
	x[2] = mkComment(3, t.Add(2*time.Second), receiptPrefix, s2, false)
	add(x)
	x = append([]comment{}, base...)
	x[1] = mkComment(2, t.Add(-time.Second), approvalPrefix, a, true)
	add(x)
	x = append([]comment{}, base...)
	a2 := a
	a2.Challenge = strings.Repeat("e", 32)
	x[1] = mkComment(2, t.Add(time.Second), approvalPrefix, a2, true)
	add(x)
	x = append([]comment{}, base...)
	s2 = s
	s2.CodespaceName = "other"
	x[2] = mkComment(3, t.Add(2*time.Second), receiptPrefix, s2, false)
	add(x)
	x = append([]comment{}, base...)
	s2 = s
	s2.ImageIdentitySHA256 = strings.Repeat("e", 64)
	x[2] = mkComment(3, t.Add(2*time.Second), receiptPrefix, s2, false)
	add(x)
	x = append([]comment{}, base...)
	x = append(x, mkComment(4, t.Add(3*time.Second), receiptPrefix, s, false))
	add(x)
	x = append([]comment{}, base...)
	x = append(x, mkComment(5, t, freezePrefix, f, false))
	add(x)
	for i, z := range tests {
		if _, e := selectReceipt(z, "cs1", challenge, image, t); e == nil {
			panic(fmt.Sprintf("negative-%d", i))
		}
	}
	req := projectedRequests(6, 17, 1)
	if req != 24 || req >= apiHardBudget || req >= 60 {
		panic(fmt.Sprintf("minute-8-9-rate-budget:%d", req))
	}
	req = projectedRequests(6, 20, 1)
	if req != 27 || req >= apiHardBudget || req >= 60 {
		panic(fmt.Sprintf("ten-minute-rate-budget:%d", req))
	}
	var b apiBudget
	for i := 0; i < apiHardBudget; i++ {
		if e := b.before(); e != nil {
			panic("budget-early")
		}
	}
	if e := b.before(); e == nil {
		panic("budget-not-enforced")
	}
	h := http.Header{}
	h.Set("X-RateLimit-Remaining", strconv.Itoa(apiReserveRemaining))
	if e := rateState(h); e == nil {
		panic("rate-reserve-not-enforced")
	}
	fmt.Println("PHASE_C_V19_7_36_V7R6_SESSION_GATE_NEGATIVE_SELFTEST_PASS")
	fmt.Printf("PHASE_C_V19_7_36_V7R6_RATE_BUDGET_SELFTEST_PASS minute_8_5_requests=24 ten_minute_requests=27 hard_budget=%d reserve=%d\n", apiHardBudget, apiReserveRemaining)
}
func main() {
	if len(os.Args) == 2 && os.Args[1] == "build-selftest" {
		selftest()
		return
	}
	if os.Geteuid() != 0 {
		die("EUID")
	}
	if os.Getenv("CODESPACES") != "true" {
		die("CODESPACES")
	}
	name := os.Getenv("CODESPACE_NAME")
	if name == "" {
		die("CODESPACE_NAME")
	}
	identity, e := imageIdentity()
	if e != nil {
		die("IMAGE_IDENTITY")
	}
	raw := make([]byte, 16)
	if _, e = rand.Read(raw); e != nil {
		die("RANDOM")
	}
	challenge := hex.EncodeToString(raw)
	cl := httpClient()
	budget := &apiBudget{}
	issued, e := githubServerNow(cl, budget)
	if e != nil {
		die("GITHUB_SERVER_TIME")
	}
	fmt.Printf("PHASE_C_V19_7_36_V7R6_SESSION_CHALLENGE codespace=%s challenge=%s image_identity_sha256=%s\n", name, challenge, identity)
	fmt.Println("PHASE_C_V19_7_36_V7R6_WAITING_FOR_EXTERNAL_SESSION_BINDING")
	s, e := waitReceipt(cl, budget, name, challenge, identity, issued)
	if e != nil {
		die("SESSION_RECEIPT:" + e.Error())
	}
	fmt.Printf("PHASE_C_V19_7_36_V7R6_EXTERNAL_SESSION_BINDING_PASS head=%s tree=%s api_requests=%d\n", s.CandidateHead, s.CandidateTree, budget.Used)
	p, e := os.Open(producerPath)
	if e != nil {
		die("PRODUCER_OPEN")
	}
	defer p.Close()
	st, e := p.Stat()
	if e != nil || st.Sys().(*syscall.Stat_t).Uid != 0 || st.Mode().Perm()&0022 != 0 || !st.Mode().IsRegular() {
		die("PRODUCER_CLASS_C")
	}
	cmd := exec.Command("/proc/self/fd/3")
	cmd.ExtraFiles = []*os.File{p}
	cmd.Env = []string{"CODESPACES=true", "CODESPACE_NAME=" + name, "LANG=C", "LC_ALL=C"}
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if e = cmd.Run(); e != nil {
		if x, ok := e.(*exec.ExitError); ok {
			os.Exit(x.ExitCode())
		}
		die("PRODUCER_EXEC")
	}
}
