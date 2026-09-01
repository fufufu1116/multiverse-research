#!/usr/bin/env python3
"""Deterministic review-only behavioral selftest for waitReceipt deadline-crossing control flow.

This test never contacts GitHub or any external service. It compiles the exact candidate gate
source in a temporary directory, changing only the poll interval constant from 30s to 200ms so
the same production waitReceipt control path can be exercised quickly with a fake HTTP transport.
"""
from __future__ import annotations
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7R6_EXTERNAL_SESSION_GATE_20260901.go"
RC = 92


def fail(code: str, msg: str) -> None:
    print(f"PHASE_C_V19_7_36_V7R6_POST_SLEEP_POST_DEADLINE_WAIT_PATH_SELFTEST_DENIED:{code}:{msg}", file=sys.stderr)
    raise SystemExit(RC)


def main() -> None:
    if not shutil.which("go"):
        fail("GO_TOOL_UNAVAILABLE", "go")
    src = GATE.read_text()
    old = "const pollInterval = 30 * time.Second"
    new = "const pollInterval = 200 * time.Millisecond"
    if src.count(old) != 1:
        fail("POLL_INTERVAL_SOURCE_BINDING", f"count={src.count(old)}")
    test_src = src.replace(old, new, 1)
    harness = r'''package main

import (
    "bytes"
    "encoding/json"
    "io"
    "net/http"
    "strconv"
    "strings"
    "testing"
    "time"
)

type waitPathTransport struct {
    calls int
    issued time.Time
    deltaDelay time.Duration
    includeEvidence bool
    name string
    challenge string
    identity string
    deltaStarted time.Time
    deltaFinished time.Time
}

func (x *waitPathTransport) RoundTrip(r *http.Request) (*http.Response, error) {
    x.calls++
    h := make(http.Header)
    h.Set("Date", time.Now().UTC().Format(http.TimeFormat))
    h.Set("X-RateLimit-Remaining", "50")
    h.Set("X-RateLimit-Limit", "60")
    h.Set("X-RateLimit-Reset", strconv.FormatInt(time.Now().Add(time.Hour).Unix(), 10))
    var body []byte
    if x.calls == 1 || !x.includeEvidence {
        body = []byte("[]")
    } else {
        x.deltaStarted = time.Now()
        time.Sleep(x.deltaDelay)
        head := strings.Repeat("a", 40)
        tree := strings.Repeat("b", 40)
        app := struct { Slug string `json:"slug"` }{Slug: requiredApp}
        freezePayload, _ := json.Marshal(freezeReceipt{Version:"V19.7.36-v7r6", CandidateHead:head, CandidateTree:tree, ImageIdentitySHA256:x.identity, ExactPhrase:"FREEZE V19.7.36 v7r6 CANDIDATE", Runtime:"OFF"})
        approvalPayload, _ := json.Marshal(approvalReceipt{Version:"V19.7.36-v7r6", CodespaceName:x.name, Challenge:x.challenge, CandidateHead:head, CandidateTree:tree, ImageIdentitySHA256:x.identity, CandidateFreezeComment:1, ExactPhrase:"APPROVE V19.7.36 v7r6 ONE-SHOT LIVE", OneShot:true, Runtime:"OFF"})
        sessionPayload, _ := json.Marshal(sessionReceipt{Version:"V19.7.36-v7r6", CodespaceName:x.name, Challenge:x.challenge, CandidateHead:head, CandidateTree:tree, ImageIdentitySHA256:x.identity, CandidateFreezeComment:1, OwnerApprovalComment:2, OneShot:true, Runtime:"OFF"})
        freeze := comment{ID:1, Body:freezePrefix+string(freezePayload), CreatedAt:x.issued, UpdatedAt:x.issued, PerformedVia:&app}
        freeze.User.Login = requiredUser
        approvalAt := x.issued.Add(500 * time.Millisecond)
        approval := comment{ID:2, Body:approvalPrefix+string(approvalPayload), CreatedAt:approvalAt, UpdatedAt:approvalAt}
        approval.User.Login = requiredUser
        sessionAt := x.issued.Add(time.Second)
        session := comment{ID:3, Body:receiptPrefix+string(sessionPayload), CreatedAt:sessionAt, UpdatedAt:sessionAt, PerformedVia:&app}
        session.User.Login = requiredUser
        body, _ = json.Marshal([]comment{freeze, approval, session})
        x.deltaFinished = time.Now()
    }
    return &http.Response{StatusCode:200, Header:h, Body:io.NopCloser(bytes.NewReader(body)), Request:r}, nil
}

func TestPostSleepPostDeadlineWaitPath(t *testing.T) {
    issued := time.Now().Add(-2 * time.Second)
    name := "codespace-selftest"
    challenge := strings.Repeat("d", 32)
    identity := strings.Repeat("c", 64)
    tr := &waitPathTransport{issued:issued, deltaDelay:400*time.Millisecond, includeEvidence:true, name:name, challenge:challenge, identity:identity}
    cl := &http.Client{Transport:tr, Timeout:2*time.Second}
    b := &apiBudget{}
    deadline := time.Now().Add(500 * time.Millisecond)
    got, err := waitReceipt(cl, b, name, challenge, identity, issued, deadline)
    if err == nil || err.Error() != "timeout" {
        t.Fatalf("expected timeout, got receipt=%+v err=%v", got, err)
    }
    if tr.calls != 2 {
        t.Fatalf("expected initial+delta calls, got %d", tr.calls)
    }
    if tr.deltaStarted.IsZero() || tr.deltaFinished.IsZero() {
        t.Fatalf("delta timing not recorded")
    }
    if !tr.deltaStarted.Before(deadline) {
        t.Fatalf("delta did not begin before deadline: start=%v deadline=%v", tr.deltaStarted, deadline)
    }
    if tr.deltaFinished.Before(deadline) {
        t.Fatalf("delta did not cross deadline: finish=%v deadline=%v", tr.deltaFinished, deadline)
    }
}

func TestRemainingSleepBoundedNearDeadline(t *testing.T) {
    issued := time.Now().Add(-2 * time.Second)
    name := "codespace-selftest"
    challenge := strings.Repeat("e", 32)
    identity := strings.Repeat("f", 64)
    tr := &waitPathTransport{issued:issued, includeEvidence:false, name:name, challenge:challenge, identity:identity}
    cl := &http.Client{Transport:tr, Timeout:2*time.Second}
    b := &apiBudget{}
    start := time.Now()
    deadline := start.Add(50 * time.Millisecond)
    _, err := waitReceipt(cl, b, name, challenge, identity, issued, deadline)
    elapsed := time.Since(start)
    if err == nil || err.Error() != "timeout" {
        t.Fatalf("expected timeout, err=%v", err)
    }
    if tr.calls != 1 {
        t.Fatalf("near-deadline path must time out before delta fetch; calls=%d", tr.calls)
    }
    if elapsed >= 150*time.Millisecond {
        t.Fatalf("remaining-time sleep appears unbounded: elapsed=%v testPoll=%v", elapsed, pollInterval)
    }
}
'''
    with tempfile.TemporaryDirectory(prefix="multiverse-v7r6-waitpath-") as td:
        p = pathlib.Path(td)
        (p / "gate.go").write_text(test_src)
        (p / "gate_wait_test.go").write_text(harness)
        env = dict(os.environ)
        env["CGO_ENABLED"] = "0"
        cp = subprocess.run(
            ["go", "test", "-count=1", "-timeout=10s", "-run", "Test(PostSleepPostDeadlineWaitPath|RemainingSleepBoundedNearDeadline)$", "gate.go", "gate_wait_test.go"],
            cwd=p,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        sys.stdout.write(cp.stdout)
        sys.stderr.write(cp.stderr)
        if cp.returncode != 0:
            fail("GO_BEHAVIORAL_TEST", f"rc={cp.returncode}")
    print("PHASE_C_V19_7_36_V7R6_POST_SLEEP_POST_DEADLINE_WAIT_PATH_SELFTEST_PASS")
    print("RUNTIME=OFF")


if __name__ == "__main__":
    main()
