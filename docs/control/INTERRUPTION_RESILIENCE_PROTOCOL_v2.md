# MULTIVERSE Interruption Resilience Protocol v2

Status: CANDIDATE — repository-only; requires normal review/adoption.
Control: #394
Runtime: OFF

## Problem
Owner reports frequent response streaming interruption / stop across multiple project chats. Chat transport continuity is not a reliable persistence layer. MULTIVERSE must remain resumable even when a model response, chat session, connector call, or UI stream terminates unexpectedly.

## System invariant
CHAT/STREAM LOSS != PROJECT STATE LOSS.

A chat is a replaceable command console, never the authoritative journal. Consequential state must be durably receipted outside the stream before relying on prose delivery.

## Mandatory protocol for every MULTIVERSE lane after Fresh Read
1. **Fresh authority first.** Read canonical main, Control #394, the lane CURRENT/PRIMARY authority, active Gates/blockers, and relevant durable receipts. Never reconstruct changing state from the last visible assistant sentence alone.
2. **Receipt before narration.** After each consequential mutation or accepted Owner token, write a compact durable receipt to the canonical issue/PR before producing a long Owner-facing explanation whenever permissions permit.
3. **Commit-point model.** Treat work as ordered commit points. A commit point is complete only when its durable external evidence is Fresh-readable. On interruption, resume from the first uncommitted point; do not replay receipted actions.
4. **Idempotency / one-shot safety.** Never repeat Build, payment, provider, credential, production, merge, or other one-shot action merely because the response stream stopped. Fresh-check receipts and external state first. Uncertain side effect => fail closed.
5. **Compact checkpoint.** At genuine Owner Gates and before any high-risk/manual action, canonicalize: exact object IDs, SHA/tree/request hash, authority scope, consumed/unconsumed state, prohibited retries, next safe action, Runtime state. Do not depend on screenshots unless the required fact exists only in inaccessible UI.
6. **No giant handoff.** New chats bootstrap from compact canonical state + Fresh Read. Handoffs and prior chat text are recovery hints, not current authority.
7. **Queue switching.** A blocked lane does not stop MULTIVERSE. If waiting on an external event or Owner Gate, continue other safe owner-free work unless governance requires role separation.
8. **Short Owner output.** Do not make the Owner wait through long streaming narration. Perform work first, persist receipts, then return a compact result + fixed status board. Detailed evidence belongs in canonical records and can be expanded on request.
9. **Cross-lane inheritance.** 軍師, システム改善, 百人将, 特殊部隊, AI研究, 本城/アプリ, 対話室, and future lanes must Fresh-read this rule once formally adopted and apply it locally without requiring Owner to repeat the complaint.
10. **Regression duty.** If an interruption exposes repeated loss/replay/confusion, search historical same-class incidents and convert the failure into a deterministic preflight/regression or explicit control invariant before another scarce Owner-gated attempt.

## Resume algorithm
On any unexpected stream/session interruption:
- Fresh Read canonical authority and the affected external system state.
- Determine the last durable commit point.
- Classify every intended action as RECEIPTED / NOT_RECEIPTED / UNCERTAIN.
- RECEIPTED: never replay.
- NOT_RECEIPTED: continue if still authorized and safe.
- UNCERTAIN: fail closed and verify externally before action.
- Continue owner-free work without asking the Owner to reconstruct prior state.
- Return only the new result, any genuine Owner Gate, and the fixed status board.

## Transport-layer limitation
This protocol cannot guarantee that the ChatGPT client/network will never interrupt token streaming. It removes streaming continuity as a correctness dependency: an interrupted response should cost presentation time, not project state or duplicate real-world actions.

## Adoption boundary
Repository-only candidate. No Runtime activation, provider/spend/live effect, credential change, external Build, merge, or ruleset mutation is authorized by this document.
