# MULTIVERSE Automation Policy Change-Control v6 — Candidate

## Purpose

v6 is a Candidate-only change-control layer stacked on the independently validated
repository-reviewed policy source v5. v5 proved exact reviewed policy bytes can be
bound into the relay adapter. v6 addresses the next gap: **future policy changes
must not silently become authority**.

v6 does not apply policy, write GitHub, mutate main, contact a provider, spend
money, use secrets, adopt Core/Keirin, or activate Runtime.

## Frozen predecessor

- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `040d37f0a4e426cf2e119706484c90cbb48f0e56`
- base PR #86 exact head: `e803723309a045086287e613f924a90a880b5a3b`
- v5 manifest SHA-256: `51f9b4030da3f6fdf38c6ea85e765b450721898049c66764e1a6a216404c319f`
- v5 Independent Lab PASS: `5523435184`
- v5 Independent Auditor PASS: `5523829487`
- v5 Candidate closure: `5523892150`

These IDs are repository review provenance for Independent Lab/Auditor to Fresh
verify. The runtime loader does not claim remote GitHub comment authenticity.

## Decision model

Every proposed policy change is classified deterministically:

- `NO_CHANGE`: exact canonical policy content is unchanged.
- `CANDIDATE_REVIEW_REQUIRED`: no new allowed binding or protected authority is
  added, but identity rotates or the allowed binding set narrows. The change
  still requires a new exact Candidate review before any later adoption.
- `OWNER_GATE_REQUIRED`: any allowed binding is added/substituted, canonical
  repo/main changes, Candidate-only is disabled, authority keys change or become
  true, bindings are malformed/empty/duplicated, the document shape widens, or
  the proposed source branch fails the same conservative Candidate branch-shape
  validation used by the validated v4 binding policy.

`may_apply` is **always false**. v6 is a classifier/journal only.

## Durable replay

`PolicyChangeControlStore` uses SQLite WAL + synchronous FULL, schema 4, and
`BEGIN IMMEDIATE` for both first-time schema/metadata initialization and decision
creation. This serializes two independent first-open connections before either can
observe-and-insert missing schema/meta rows, so initialization converges instead
of leaking raw UNIQUE/locking failures. Exact replay of the same request ID and
same canonical proposed bytes returns the same durable decision. A conflicting
replay under the same request ID fails closed.

The DB pins:

- exact v6 baseline bytes/SHA;
- exact v5 source bytes/SHA.

The v5 adapter expects DB schema 3 and therefore rejects the v6 schema-4 decision
DB rather than bypass-opening it as a relay DB.

## Independent Lab remediation

The first v6 Independent Lab review (`5524112187`) returned `FIX_REQUIRED` with
two bounded Candidate-only findings. The remediation changes only new v6 code,
tests, and this documentation:

1. source-policy identity now validates `source_branch` through the established
   `CandidateBindingPolicy` branch-shape rules, so malformed identities such as
   `agent/` route `OWNER_GATE_REQUIRED` rather than Candidate review;
2. schema-4 initialization is now wrapped in an immediate write transaction and
   a new test starts two independent connections against an empty DB to exercise
   the first-open race directly.

The historical pre-remediation Lab result remains evidence only. Any remediated
head requires a new exact push CI, new freeze, and new Independent Lab review.

## Security / authority ceiling

v6 can route a non-widening proposal toward **future independent review**. It
cannot approve or apply it.

Any widening, canonical-main move, repo move, Candidate-only removal, authority
change, malformed/unknown shape, or invalid source-branch identity becomes
`OWNER_GATE_REQUIRED`.

This does **not** establish canonical policy issuance authority, production
change-control, merge readiness, live-provider exactly-once behavior, or a
generic permission to rotate policy.

## Explicit nonauthority

- merge: NO
- PR #86 mutation: NO
- canonical main/ruleset mutation: NO
- policy apply: NO
- policy widening: NO
- canonical/production/Core/Keirin adoption: NO
- live provider integration/contact: NO
- provider spend: NO
- secret/writer-key use: NO
- protected Keirin data: NO
- workflow dispatch/rerun: NO
- Runtime activation: NO

Required sequence remains exact push CI -> freeze -> Independent Lab ->
Independent Auditor -> Candidate closure. Any canonical policy issuance or
application is a separate later Owner-gated transaction.
