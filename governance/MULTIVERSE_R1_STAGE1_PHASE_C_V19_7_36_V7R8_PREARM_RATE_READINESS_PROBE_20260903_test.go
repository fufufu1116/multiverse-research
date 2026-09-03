package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func testServer(before, after, commentStatus int, resource string) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Date", "Wed, 01 Jan 2031 00:00:00 GMT")
		switch r.URL.Path {
		case "/rate_limit":
			w.Header().Set("Content-Type", "application/json")
			fmt.Fprintf(w, `{"resources":{"core":{"limit":60,"remaining":%d,"reset":1924995600}}}`, before)
		case "/repos/fufufu1116/multiverse-research/issues/74/comments":
			w.Header().Set("X-RateLimit-Limit", "60")
			w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(after))
			w.Header().Set("X-RateLimit-Reset", "1924995600")
			w.Header().Set("X-RateLimit-Resource", resource)
			w.WriteHeader(commentStatus)
			fmt.Fprint(w, `[]`)
		default:
			w.WriteHeader(404)
		}
	}))
}

func TestRateReadinessPositive(t *testing.T) {
	s := testServer(57, 56, 200, "core"); defer s.Close()
	r := probeAt(s.URL, s.Client())
	if !r.Ready || r.Reason != "READY" || r.Before != 57 || r.After != 56 { t.Fatalf("unexpected: %+v", r) }
}

func TestRateReadinessBeforeReserve(t *testing.T) {
	s := testServer(56, 55, 200, "core"); defer s.Close()
	r := probeAt(s.URL, s.Client())
	if r.Ready || r.Reason != "RATE_RESERVE_BEFORE" { t.Fatalf("unexpected: %+v", r) }
}

func TestRateReadinessAfterReserve(t *testing.T) {
	s := testServer(57, 55, 200, "core"); defer s.Close()
	r := probeAt(s.URL, s.Client())
	if r.Ready || r.Reason != "RATE_RESERVE_AFTER" { t.Fatalf("unexpected: %+v", r) }
}

func TestRateReadinessCommentStatus(t *testing.T) {
	s := testServer(57, 56, 403, "core"); defer s.Close()
	r := probeAt(s.URL, s.Client())
	if r.Ready || r.Reason != "COMMENTS_STATUS" { t.Fatalf("unexpected: %+v", r) }
}

func TestRateReadinessResourceClass(t *testing.T) {
	s := testServer(57, 56, 200, "search"); defer s.Close()
	r := probeAt(s.URL, s.Client())
	if r.Ready || r.Reason != "COMMENTS_RATE_HEADERS" { t.Fatalf("unexpected: %+v", r) }
}

func TestRenderNeverGrantsAuthority(t *testing.T) {
	status, control := render("rate-probe-test", probeResult{Ready:true, Reason:"READY", Before:57, After:56, Reset:1924995600})
	for _, s := range []string{status, control} {
		if !containsAll(s, "one_shot_guard_consumed=false", "RETURN_TO_CORE_BEFORE_STATIC_GUARD", "runtime=OFF") { t.Fatalf("missing nonauthority marker: %q", s) }
	}
}

func containsAll(s string, wants ...string) bool {
	for _, want := range wants {
		if !strings.Contains(s, want) { return false }
	}
	return true
}
