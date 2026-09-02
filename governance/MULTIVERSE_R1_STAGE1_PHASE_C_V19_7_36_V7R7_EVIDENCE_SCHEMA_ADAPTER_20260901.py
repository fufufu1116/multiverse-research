#!/usr/bin/env python3
"""Deterministic review-only v7r7 evidence-contract adapter for the exact inherited v7r6 gate.

The adapter accepts exactly one reviewed inherited source blob. It first performs the exact-counted
v7r6->v7r7 external evidence literal substitutions, then injects narrowly bounded strict evidence
object-shape decoding plus a synchronous terminal-status hook before the existing typed
value/provenance/deadline/binding checks. General gate control logic is otherwise not rewritten.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

RC = 92
EXPECTED_INHERITED_GIT_BLOB = "f2c3f1023a453bfe5ee43c7d978de9728c5a2dc8"
SUCCESSOR_VERSION = "V19.7.36-v7r7"

REPLACEMENTS = (
    ("MULTIVERSE_V7R6_CANDIDATE_FREEZE ", "MULTIVERSE_V7R7_CANDIDATE_FREEZE ", 1),
    ("MULTIVERSE_V7R6_SESSION_BINDING ", "MULTIVERSE_V7R7_SESSION_BINDING ", 1),
    ("MULTIVERSE_V7R6_OWNER_APPROVAL_RECEIPT ", "MULTIVERSE_V7R7_OWNER_APPROVAL_RECEIPT ", 1),
    ("V19.7.36-v7r6", "V19.7.36-v7r7", 6),
    ("FREEZE V19.7.36 v7r6 CANDIDATE", "FREEZE V19.7.36 v7r7 CANDIDATE", 2),
    ("APPROVE V19.7.36 v7r6 ONE-SHOT LIVE", "APPROVE V19.7.36 v7r7 ONE-SHOT LIVE", 2),
)

LEGACY_EVIDENCE_LITERALS = tuple(old for old, _, _ in REPLACEMENTS)
SUCCESSOR_EVIDENCE_LITERALS = tuple(new for _, new, _ in REPLACEMENTS)


def deny(code: str, detail: str = "") -> "NoReturn":
    suffix = f":{detail}" if detail else ""
    print(f"PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_DENIED:{code}{suffix}", file=sys.stderr)
    raise SystemExit(RC)


def git_blob_sha1(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def replace_exact(text: str, old: str, new: str, expected_count: int, code: str) -> str:
    count = text.count(old)
    if count != expected_count:
        deny(code, f"got={count}:expected={expected_count}")
    return text.replace(old, new)


def harden_object_shape(text: str) -> str:
    api_budget_anchor = "type apiBudget struct{ Used int }\n"
    strict_key_block = r'''type apiBudget struct{ Used int }

var freezeExactKeys = []string{"Version", "CandidateHead", "CandidateTree", "ImageIdentitySHA256", "ExactPhrase", "Runtime"}
var sessionExactKeys = []string{"Version", "CodespaceName", "Challenge", "CandidateHead", "CandidateTree", "ImageIdentitySHA256", "CandidateFreezeComment", "OwnerApprovalComment", "OneShot", "Runtime"}
var approvalExactKeys = []string{"Version", "CodespaceName", "Challenge", "CandidateHead", "CandidateTree", "ImageIdentitySHA256", "CandidateFreezeComment", "ExactPhrase", "OneShot", "Runtime"}
'''
    text = replace_exact(text, api_budget_anchor, strict_key_block, 1, "STRICT_KEYSET_ANCHOR")

    permissive_line_payload = r'''func linePayload(body, prefix string) ([]byte, bool) {
	for _, l := range strings.Split(body, "\n") {
		if strings.HasPrefix(l, prefix) {
			return []byte(strings.TrimPrefix(l, prefix)), true
		}
	}
	return nil, false
}
'''
    strict_line_payload = r'''func linePayload(body, prefix string) ([]byte, bool) {
	var found []byte
	count := 0
	for _, l := range strings.Split(body, "\n") {
		if strings.HasPrefix(l, prefix) {
			count++
			if count > 1 {
				return nil, false
			}
			found = []byte(strings.TrimPrefix(l, prefix))
		}
	}
	return found, count == 1
}
func strictEvidencePayload(body, prefix string, exactKeys []string) ([]byte, bool) {
	b, ok := linePayload(body, prefix)
	if !ok {
		return nil, false
	}
	dec := json.NewDecoder(strings.NewReader(string(b)))
	tok, err := dec.Token()
	if err != nil {
		return nil, false
	}
	delim, ok := tok.(json.Delim)
	if !ok || delim != '{' {
		return nil, false
	}
	allowed := make(map[string]struct{}, len(exactKeys))
	for _, key := range exactKeys {
		allowed[key] = struct{}{}
	}
	seen := make(map[string]struct{}, len(exactKeys))
	for dec.More() {
		tok, err = dec.Token()
		if err != nil {
			return nil, false
		}
		key, ok := tok.(string)
		if !ok {
			return nil, false
		}
		if _, ok := allowed[key]; !ok {
			return nil, false
		}
		if _, duplicate := seen[key]; duplicate {
			return nil, false
		}
		seen[key] = struct{}{}
		var raw json.RawMessage
		if err := dec.Decode(&raw); err != nil {
			return nil, false
		}
	}
	tok, err = dec.Token()
	if err != nil {
		return nil, false
	}
	delim, ok = tok.(json.Delim)
	if !ok || delim != '}' || len(seen) != len(exactKeys) {
		return nil, false
	}
	if _, err := dec.Token(); err != io.EOF {
		return nil, false
	}
	return b, true
}
'''
    text = replace_exact(text, permissive_line_payload, strict_line_payload, 1, "STRICT_LINE_PAYLOAD_ANCHOR")

    text = replace_exact(text, "b, ok := linePayload(c.Body, freezePrefix)", "b, ok := strictEvidencePayload(c.Body, freezePrefix, freezeExactKeys)", 1, "STRICT_FREEZE_CALL")
    text = replace_exact(text, "b, ok := linePayload(c.Body, approvalPrefix)", "b, ok := strictEvidencePayload(c.Body, approvalPrefix, approvalExactKeys)", 1, "STRICT_APPROVAL_CALL")
    text = replace_exact(text, "b, ok := linePayload(c.Body, receiptPrefix)", "b, ok := strictEvidencePayload(c.Body, receiptPrefix, sessionExactKeys)", 1, "STRICT_SESSION_CALL")

    positive_anchor = r'''	if _, e := selectReceipt(base, "cs1", challenge, image, t, approvalDeadline); e != nil {
		panic("positive")
	}
	tests := [][]comment{}
'''
    strict_selftests = r'''	if _, e := selectReceipt(base, "cs1", challenge, image, t, approvalDeadline); e != nil {
		panic("positive")
	}
	if _, ok := parseFreeze(base[0]); !ok {
		panic("strict-positive-freeze")
	}
	if _, ok := parseApproval(base[1], s, t, approvalDeadline); !ok {
		panic("strict-positive-owner-approval")
	}
	strictReject := func(label string, z []comment) {
		if _, e := selectReceipt(z, "cs1", challenge, image, t, approvalDeadline); e == nil {
			panic("strict-evidence-" + label)
		}
	}
	mutate := func(c comment, old, new, label string) comment {
		if !strings.Contains(c.Body, old) {
			panic("strict-mutation-anchor-" + label)
		}
		c.Body = strings.Replace(c.Body, old, new, 1)
		return c
	}
	z := append([]comment{}, base...)
	z[0].Body = strings.TrimSuffix(z[0].Body, "}") + ",\"Unexpected\":\"x\"}"
	strictReject("unknown-key", z)
	z = append([]comment{}, base...)
	z[2] = mutate(z[2], "\"Version\":", "\"version\":", "alternate-case")
	strictReject("alternate-case-key", z)
	z = append([]comment{}, base...)
	z[1] = mutate(z[1], "\"Runtime\":\"OFF\"", "\"Runtime\":\"BROKEN\",\"Runtime\":\"OFF\"", "duplicate-key")
	strictReject("duplicate-json-key", z)
	z = append([]comment{}, base...)
	z[2].Body = z[2].Body + "\n" + z[2].Body
	strictReject("duplicate-same-prefix-line", z)
	z = append([]comment{}, base...)
	z[0] = mutate(z[0], ",\"Runtime\":\"OFF\"", "", "missing-key")
	strictReject("missing-key", z)
	z = append([]comment{}, base...)
	z[2] = mutate(z[2], "\"OneShot\":true", "\"OneShot\":\"true\"", "malformed-value")
	strictReject("malformed-value", z)
	z = append([]comment{}, base...)
	z[0].Body = z[0].Body + "{}"
	strictReject("trailing-object", z)
	z = append([]comment{}, base...)
	z[1].PerformedVia = &struct {
		Slug string `json:"slug"`
	}{Slug: requiredApp}
	strictReject("provenance-mismatch", z)
	tests := [][]comment{}
'''
    text = replace_exact(text, positive_anchor, strict_selftests, 1, "STRICT_SELFTEST_ANCHOR")

    marker_anchor = '\tfmt.Println("PHASE_C_V19_7_36_V7R6_SESSION_GATE_NEGATIVE_SELFTEST_PASS")\n'
    text = replace_exact(
        text,
        marker_anchor,
        '\tfmt.Println("PHASE_C_V19_7_36_V7R7_STRICT_EVIDENCE_OBJECT_SHAPE_SELFTEST_PASS")\n' + marker_anchor,
        1,
        "STRICT_SELFTEST_MARKER_ANCHOR",
    )

    die_anchor = r'''func die(s string) {
	fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R6_SESSION_GATE_DENIED:"+s)
	os.Exit(92)
}
'''
    die_sync = r'''func die(s string) {
	v7r7TerminalFailClosedSync()
	fmt.Fprintln(os.Stderr, "PHASE_C_V19_7_36_V7R6_SESSION_GATE_DENIED:"+s)
	os.Exit(92)
}
'''
    text = replace_exact(text, die_anchor, die_sync, 1, "SYNC_TERMINAL_DIE_ANCHOR")
    return text


def adapt_bytes(raw: bytes) -> bytes:
    actual = git_blob_sha1(raw)
    if actual != EXPECTED_INHERITED_GIT_BLOB:
        deny("INHERITED_GATE_BLOB", actual)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        deny("INHERITED_GATE_UTF8")

    for old, new, expected_count in REPLACEMENTS:
        count = text.count(old)
        if count != expected_count:
            deny("REPLACEMENT_COUNT", f"{old!r}:got={count}:expected={expected_count}")
        text = text.replace(old, new)

    for legacy in LEGACY_EVIDENCE_LITERALS:
        if legacy in text:
            deny("LEGACY_EVIDENCE_LITERAL_REMAINS", repr(legacy))
    for successor in SUCCESSOR_EVIDENCE_LITERALS:
        if successor not in text:
            deny("SUCCESSOR_EVIDENCE_LITERAL_MISSING", repr(successor))

    text = harden_object_shape(text)

    required_logic = (
        "apiHardBudget = 40",
        "apiReserveRemaining = 8",
        "pollInterval = 30 * time.Second",
        "approvalWindow = 10 * time.Minute",
        "cursorOverlap = 2 * time.Second",
        "c.CreatedAt.After(approvalDeadline)",
        "requiredApp = \"chatgpt-codex-connector\"",
        "ownerBound(c comment)",
        "evidenceBound(c comment)",
        "findFreeze(cs []comment",
        "selectReceipt(cs []comment",
        "STRICT_APPROVAL_WINDOW_SELFTEST_PASS",
        "RATE_HEADERS_FAIL_CLOSED_SELFTEST_PASS",
        "PAGINATION_RACE_SELFTEST_PASS",
        "strictEvidencePayload(c.Body, freezePrefix, freezeExactKeys)",
        "strictEvidencePayload(c.Body, receiptPrefix, sessionExactKeys)",
        "strictEvidencePayload(c.Body, approvalPrefix, approvalExactKeys)",
        "PHASE_C_V19_7_36_V7R7_STRICT_EVIDENCE_OBJECT_SHAPE_SELFTEST_PASS",
        "v7r7TerminalFailClosedSync()",
    )
    for needle in required_logic:
        if needle not in text:
            deny("SECURITY_LOGIC_MISSING", needle)

    forbidden_permissive_calls = (
        "b, ok := linePayload(c.Body, freezePrefix)",
        "b, ok := linePayload(c.Body, receiptPrefix)",
        "b, ok := linePayload(c.Body, approvalPrefix)",
    )
    for needle in forbidden_permissive_calls:
        if needle in text:
            deny("PERMISSIVE_EVIDENCE_CALL_REMAINS", needle)

    return text.encode("utf-8")


def selftest(src: pathlib.Path) -> None:
    out = adapt_bytes(src.read_bytes()).decode("utf-8")
    successor_checks = (
        'const freezePrefix = "MULTIVERSE_V7R7_CANDIDATE_FREEZE "',
        'const receiptPrefix = "MULTIVERSE_V7R7_SESSION_BINDING "',
        'const approvalPrefix = "MULTIVERSE_V7R7_OWNER_APPROVAL_RECEIPT "',
        'f.Version != "V19.7.36-v7r7"',
        'a.Version == "V19.7.36-v7r7"',
        's.Version != "V19.7.36-v7r7"',
        '"FREEZE V19.7.36 v7r7 CANDIDATE"',
        '"APPROVE V19.7.36 v7r7 ONE-SHOT LIVE"',
        'freezeReceipt{"V19.7.36-v7r7"',
        'approvalReceipt{"V19.7.36-v7r7"',
        'sessionReceipt{"V19.7.36-v7r7"',
        'var freezeExactKeys = []string{"Version", "CandidateHead", "CandidateTree", "ImageIdentitySHA256", "ExactPhrase", "Runtime"}',
        'var sessionExactKeys = []string{"Version", "CodespaceName", "Challenge", "CandidateHead", "CandidateTree", "ImageIdentitySHA256", "CandidateFreezeComment", "OwnerApprovalComment", "OneShot", "Runtime"}',
        'var approvalExactKeys = []string{"Version", "CodespaceName", "Challenge", "CandidateHead", "CandidateTree", "ImageIdentitySHA256", "CandidateFreezeComment", "ExactPhrase", "OneShot", "Runtime"}',
        'strictReject("unknown-key", z)',
        'strictReject("alternate-case-key", z)',
        'strictReject("duplicate-json-key", z)',
        'strictReject("duplicate-same-prefix-line", z)',
        'strictReject("missing-key", z)',
        'strictReject("malformed-value", z)',
        'strictReject("trailing-object", z)',
        'strictReject("provenance-mismatch", z)',
        'v7r7TerminalFailClosedSync()',
    )
    for needle in successor_checks:
        if needle not in out:
            deny("SUCCESSOR_SELFTEST_WIRING", needle)
    print(
        "PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_SELFTEST_PASS "
        f"inherited_git_blob={EXPECTED_INHERITED_GIT_BLOB} successor_version={SUCCESSOR_VERSION} strict_object_shape=true synchronous_terminalization=true runtime=OFF"
    )
    print("SECURITY_AUTHORITY_GRANTED=false")
    print("RUNTIME=OFF")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        selftest(pathlib.Path(sys.argv[2]))
        return
    if len(sys.argv) != 3:
        deny("ARGS")
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2])
    if not src.is_file():
        deny("SOURCE_MISSING", str(src))
    if dst.exists():
        deny("DESTINATION_PREEXISTS", str(dst))
    adapted = adapt_bytes(src.read_bytes())
    dst.write_bytes(adapted)
    print(
        "PHASE_C_V19_7_36_V7R7_EVIDENCE_SCHEMA_ADAPTER_PASS "
        f"inherited_git_blob={EXPECTED_INHERITED_GIT_BLOB} successor_version={SUCCESSOR_VERSION} strict_object_shape=true synchronous_terminalization=true runtime=OFF"
    )


if __name__ == "__main__":
    main()