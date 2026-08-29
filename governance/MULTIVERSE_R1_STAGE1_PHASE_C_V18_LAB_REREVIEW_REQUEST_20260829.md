# FINAL LAB RE-REVIEW REQUEST — R1 STAGE 1 PHASE C v18 JOURNAL-PRESERVING SINGLE-PASTE RECOVERY

Status: DRAFT / INDEPENDENT REVIEW REQUIRED / NOT LIVE AUTHORITY
Runtime: OFF

Fresh-read the recovery branch and independently review the exact v18 candidate file:
- `tools/multiverse_r1_stage1_phase_c_step1_single_paste_v18.py`

This is remediation for Independent Lab FIX_REQUIRED comment `5459644897`.

Required independent checks:
1. Fresh-read authoritative manifest Part A comment `5420731105` and Part B comment `5420744033`; do not trust Core summaries.
2. Confirm the candidate retrieves the exact public manifest bodies and rejects any INIT / CHUNK-template / ASSEMBLE / SOURCE decoded byte/hash mismatch before execution.
3. Independently rederive the unchanged Step1 payload: 4687 bytes / SHA-256 `bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74`; RFC4648 base64 6252 chars / SHA-256 `f7c353761edf26a0ddeb25a129a7b152a16cf587bf5b620b6421863aa25418b2`; exact 13 chunk boundaries/hashes.
4. Verify the candidate compresses only operator interaction: internally the exact authoritative order remains INIT -> CHUNK 00..12 -> ASSEMBLE -> SOURCE, with the journal-dominant predecessor checks, O_EXCL/O_NOFOLLOW file trust, fsync/reread, exact journal sequence proof, ASSEMBLED_INTEGRITY_PASS, durable SOURCE_START, same-current-parent-shell source, durable SOURCE_COMPLETE, original-RC preservation and fixed nonsecret fallback behavior unchanged.
5. Verify failure at any stage cannot advance to a later stage and cannot grant continuation.
6. Verify no OAuth command, authenticated GitHub API call, Step4, `--apply`, production mutation, main/ruleset mutation, writer-key/secret operation, merge, Runtime activation or Runtime state change is embedded or authorized.
7. Run harmless local positive and negative tests where possible, including: payload mutation, manifest/action hash mismatch, missing/duplicate/out-of-order journal event, prior chunk file/event disagreement, preexisting/symlink target, assembly mismatch, SOURCE precondition failure, SOURCE nonzero, and evidence-commit failure. No live Codespace/OAuth/API/production/Runtime action.
8. Re-evaluate the second blocker from comment `5459644897`: whether this v18 artifact itself qualifies as the required complete frozen single-paste implementation, or whether a separately frozen exact emitted one-line action (UTF-8 bytes/SHA-256/blob/immutable commit) is still mandatory. Do not waive this requirement. If it is still mandatory, return FIX_REQUIRED with the smallest exact remediation.

Return exactly one independent verdict: PASS or FIX_REQUIRED, with evidence and exact reviewed commit/blob identities. If PASS, state explicitly whether Independent Auditor may review the same exact frozen artifact. If FIX_REQUIRED, do not authorize Auditor, Owner presentation, Codespace, OAuth, API probe, production mutation, merge, or Runtime.
