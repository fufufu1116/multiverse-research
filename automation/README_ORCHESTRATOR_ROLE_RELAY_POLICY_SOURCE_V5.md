# MULTIVERSE Automation — Reviewed Policy Source v5 Candidate

This Candidate is stacked on independently validated Role Relay Policy v4.

## Problem closed at this stage

v4 proved that a separately supplied `CandidateBindingPolicy` cannot be widened by task input and is pinned in SQLite. It deliberately did **not** define where that policy comes from.

v5 removes raw policy construction from the v5 RoleWorker interface. The adapter accepts only a reviewed JSON manifest path, while the expected manifest SHA-256, source branch and canonical-main binding are compiled into the reviewed v5 implementation.

Reviewed source:
- branch: `agent/automation-orchestrator-policy-source-v5-20260903-v1`
- canonical main: `040d37f0a4e426cf2e119706484c90cbb48f0e56`
- manifest: `automation/MULTIVERSE_AUTOMATION_REVIEWED_POLICY_SOURCE_V5.json`
- exact manifest SHA-256: `51f9b4030da3f6fdf38c6ea85e765b450721898049c66764e1a6a216404c319f`

Changing manifest bytes without changing/reviewing the compiled identity fails closed. The v5 DB also pins source bytes identity plus the derived v4 policy fingerprint and uses schema version 3 so the v4 adapter cannot bypass-open it.

## Proof ceiling

This is still Candidate-only. It proves repository-reviewed policy-source identity for the v5 adapter. It does not grant canonical adoption, define a production deployment actor, contact a live provider, prove arbitrary-provider exactly-once, spend money, use credentials, modify Core/Keirin, or activate Runtime.

Any canonical deployment or future policy rotation remains a separate Owner-gated exact-head Lab/Auditor transaction.
