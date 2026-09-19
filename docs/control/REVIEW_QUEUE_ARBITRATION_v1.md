# MULTIVERSE Sole Control Review Queue Arbitration v1

Status: CANDIDATE — repository-only
Parent: #504
Control: #394
RUNTIME: OFF

## Purpose
Centralize Independent Lab / Independent Auditor request arbitration under Sole Control (Owner-facing: 軍師) without weakening any existing Owner Gate, one-shot rule, request binding, role separation, or fail-closed behavior.

## Responsibility boundary
Lane chats (特殊部隊, 百人将, AI研究, システム改善, 本城/アプリ, 対話室 and future lanes) may prepare Candidates, evidence, tests, exact review envelopes and a requested review type. They must not directly instruct Owner to create a Buildkite Independent Lab/Auditor Build.

Sole Control is the only Owner-facing Build arbitration surface. It Fresh Reads canonical state, records a queue item, determines eligibility, creates/receipts the required Owner Gate, and—only after exact authority—issues the complete manual Build packet.

Independent Lab and Independent Auditor remain independent reviewers. Sole Control never becomes the final independent auditor.

## Durable queue item
Each item binds:
- queue_id (deterministic digest-derived identifier)
- source lane
- review type: LAB or AUDITOR
- PR / branch / exact head / exact tree / exact base / Fresh main
- exact review request_id and request SHA256
- exact Owner Gate reference
- priority and deterministic creation sequence
- explicit dependencies
- state
- one_shot_consumed
- Build reference after creation
- exact bound result after review

Chat text is never queue authority. Canonical GitHub durable records are.

## States
`WAITING -> OWNER_GATE_REQUIRED -> AUTHORIZED -> CONSUMED -> PASS|FAIL`

Additional terminal/control states: `BLOCKED`, `SUPERSEDED`.

`RUNNING` is permitted for external telemetry, but one-shot consumption occurs at Build creation, before outcome is known.

## One-shot atomicity
At Build creation, the item must atomically become `one_shot_consumed=true` and leave pre-Build states. PASS, FAIL, infrastructure failure, publisher false-red, UI interruption, or chat interruption never restores the one-shot authority. Retry/Rebuild/rerun requires a completely new formal Gate and new queue item/request binding where governance permits.

## Arbitration
First-come is not sufficient. Eligible items are selected deterministically by:
1. safety/dependency eligibility (all required queue dependencies PASS),
2. review resource availability,
3. explicit Control priority (higher first),
4. creation sequence (older first),
5. queue_id as stable final tiebreaker.

Priority itself must be assigned from explicit evidence: safety/infrastructure repair, dependency-unblocking impact, existing approved Gate readiness, time sensitivity, and lane criticality. Priority does not bypass governance.

## Resource exclusion
Independent Lab and Independent Auditor are separate resource classes. Within each resource class, execution is exclusive by default: at most one AUTHORIZED/RUNNING/CONSUMED item may exist. Parallelism inside a resource class is forbidden until a separately reviewed proof demonstrates result isolation and Buildkite configuration safety.

LAB and AUDITOR may only overlap when their exact governance/dependency contracts independently allow it; this document does not authorize such overlap automatically.

## Fresh validation before Owner instructions
Immediately before asking Owner to create a Build, Sole Control must revalidate:
- queue item exact envelope and state;
- canonical main/ruleset;
- PR open/draft/unmerged state;
- branch/head/tree/base binding;
- exact request comment and SHA;
- no existing exact current trusted result;
- Gate exact token/authority and unconsumed state;
- no active same-resource queue collision;
- all dependencies PASS.

Any drift/mismatch/duplicate/stale result => fail closed; supersede/rebind rather than guessing.

## Owner manual action packet
Only Sole Control sends this packet. It must include in one message:
- 操作場所
- 開くリンク
- Pipeline
- Branch
- Commit
- Message
- Environment variables
- 押すボタン
- 押してはいけない操作
- 完了後ここへ何と返すか

Lane chats route review requests to canonical GitHub and continue safe work; they do not compete for Owner attention.

## Result isolation
A result may satisfy an item only if request_id, request SHA256, review type, PR/head/tree/base/main and trusted producer contract match the exact review envelope. Results from another lane, PR, Gate, request revision or review class must never be reused.

## Backward compatibility
The existing `MULTIVERSE_REVIEW_REQUEST_v1`, fixed dispatcher, Independent Lab/Auditor identities, existing Gate contracts and review results remain valid. v1 Review Queue is an orchestration layer above them, not a replacement for dispatcher verification.

Existing in-flight requests may be enrolled as queue items only after Fresh reconstruction of their exact current state. No previously consumed Build authority is revived by enrollment.

## Interruption resilience
Queue state and one-shot consumption are durable commit points. If chat/stream/UI interruption occurs, Fresh Read the canonical queue record and external result before any action. RECEIPTED/CONSUMED work is never replayed.

## Non-authority
This candidate grants no Build, Retry/Rebuild/rerun, external Steps/settings mutation, merge/adoption, main/ruleset mutation, provider/credential/spend/live effect, Runtime activation, or weakening of independent review.