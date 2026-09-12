# KEIRIN_CURRENT_STATE v1

Updated: 2026-09-12 JST
Authority: continuity pointer only; Fresh GitHub read required on resume.
Runtime: OFF
Automatic betting: OFF

## Objective
競輪研究を、チャット容量・ストリーミング中断に依存せず継続し、前向き検証と大量シミュレーションで実用水準へ近づける。

## Operating model
- Chat is ephemeral execution UI, not long-term state storage.
- Durable state is split into CURRENT_STATE / RULE_REGISTRY / EXPERIMENT_LEDGER / datasets-artifacts.
- Detailed outputs belong in repository/files; chat returns compact status only.

## Current continuity work
- Issue #377 defines capacity-proof operating protocol.
- This file is the compact resume pointer.
- Fixed research rules live in `KEIRIN_RULE_REGISTRY.md`.
- Experiment summaries append to `KEIRIN_EXPERIMENT_LEDGER.md`.

## Resume procedure
1. Fresh Read Issue #377 and these three continuity files.
2. Fresh Read the active Keirin research branch/issues/artifacts before treating any historical SHA/count/progress as CURRENT.
3. Continue all Owner-free research without waiting.
4. Checkpoint after each meaningful experiment batch and before chat migration.
5. Keep user-facing replies short; store large tables/logs/results outside chat.

## Known immutable operating constraints
See `KEIRIN_RULE_REGISTRY.md`; chat summaries must not silently override it.

## Open work
- Keirin lane should reconcile its latest active research state into this compact pointer.
- Existing historical datasets/experiment artifacts should be referenced by IDs/paths rather than copied into chat.
- Continue scientific validation toward practical prediction/purchase-decision quality.

## Owner action
None for continuity preparation.
