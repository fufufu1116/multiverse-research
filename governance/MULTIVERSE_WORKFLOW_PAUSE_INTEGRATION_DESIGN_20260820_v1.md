# MULTIVERSE WORKFLOW PAUSE INTEGRATION — DESIGN CANDIDATE v1

Status: `DRAFT_NONCANONICAL_STACKED_ON_PR18`

Purpose: Safe Mode（安全停止）を「設計文書にある」状態から、科学workflow（自動研究実行）の実行直前に必ず効く状態へ最小配線する。

## 1. What is already proven

PR #16 candidate introduced one fail-closed `Pause Guard（停止判定プログラム）` and candidate Safe-Mode state.
PR #17 separated Zero-History orientation from scientific-resume permission.
PR #18 exact-head CI proved the three candidate state surfaces can agree and current Owner pause denies Keirin scientific execution.

This design does **not** change those semantics.

## 2. Gap that remains

A guard library is ineffective if a scientific workflow never invokes it.

The observed PR #15 incident proved this class of gap: an already-armed workflow completed after the Owner pause directive. The immediate PR #15 containment is manual-only, but the systemic problem is wider than one workflow.

## 3. Minimal architecture

Do not create a new constitution or giant orchestrator.

Use two layers only:

1. `tools/multiverse_pause_guard_v1.py`
   - one decision implementation;
   - fail closed on missing/malformed/unknown/stale state;
   - already exists as a reviewed candidate lower in the stack.

2. Workflow preflight（実行前チェック）
   - every governed scientific workflow must invoke the same guard before expensive/protected scientific steps;
   - no workflow-local rewrite of pause semantics;
   - workflow may proceed only on guard exit `0` / ALLOW;
   - guard DENY is a normal safe stop, not a reason to bypass or weaken the state.

Additionally, a policy audit must detect newly added scientific workflows that omit the guard.

## 4. Coverage-first rule

Before wiring, enumerate `.github/workflows/*.yml|yaml` into:

- `SCIENTIFIC_CANDIDATE` — may produce/collect/score/model/simulate/evaluate Keirin or related research artifacts;
- `AUDIT_OR_GOVERNANCE_ONLY` — evidence/recovery/audit checks without scientific execution;
- `UNKNOWN_REVIEW_REQUIRED` — insufficient evidence to call safe.

`UNKNOWN_REVIEW_REQUIRED` is **not** equivalent to safe/exempt.

No workflow becomes exempt merely because its filename is old, static, manual, or currently unused.

## 5. Guard-integration contract

A workflow classified `SCIENTIFIC_CANDIDATE` is conforming only if, before its first scientific side effect or expensive scientific compute, it:

1. checks out an accepted/candidate guard implementation whose identity is pinned by the reviewed change;
2. resolves Safe Mode from the accepted governance state (candidate files are not a future second canonical authority);
3. invokes the guard with its declared domain and `SCIENTIFIC_EXECUTION`;
4. aborts scientific steps on DENY, missing state, malformed state, stale generation, or unknown scope;
5. does not reinterpret exit 42 as success-to-continue;
6. records the observed safe-mode generation/reason in CI logs or a receipt.

## 6. Running-job limitation

A preflight cannot retroactively stop a job that has already passed preflight.

Therefore a mature integration also needs:
- recheck immediately before protected/material side effects;
- provider cancellation adapter where supported;
- if cancellation cannot win the race, output created after a newer pause generation defaults to `QUARANTINED_NOT_ADMITTED` until neutral disposition.

This candidate does not claim provider cancellation is implemented yet.

## 7. Rollout order

1. machine inventory all workflow files;
2. manually attack `UNKNOWN_REVIEW_REQUIRED` and classification false negatives;
3. define exact protected/scientific workflow set;
4. add guard preflight to the smallest required workflow set;
5. add policy CI that fails new/modified scientific workflow PRs if the guard is absent;
6. exact-head test with Safe Mode ON => scientific step must not run;
7. exact-head test with a synthetic test state Safe Mode OFF => benign fixture step may run;
8. only after Lab/Auditor-required review may this be proposed for canonical adoption.

## 8. Scientific firewall

Unchanged:
- `ECON_HOLDOUT1000 = SEALED`
- RESULT/PAYOUT = UNAUTHORIZED
- untouched validation = CLOSED
- model promotion = PROHIBITED
- current DEV2000 C rescue = PROHIBITED
- same-lineage B/C rescue tuning = PROHIBITED
- real-money wagering = OUT_OF_SCOPE
- external provider contact = PROHIBITED unless Owner explicitly reverses

## 9. Current permission

This file authorizes **coverage audit and candidate implementation testing only**.
It does not resume Keirin science and does not authorize opening PR #15 quarantined metrics.

Owner action now: `NONE`.
