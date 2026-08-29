# MULTIVERSE R1 Stage 1 Phase C v19.7 — OAuth-to-NONMUTATING-Step3 Successor Build Plan

Status: DESIGN CANDIDATE / REVIEW ONLY / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Current binding
Fresh Core read before this candidate:
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- recovery branch pre-write head: `7b2e3a367aa9f0b77ffe06b0a4a486872ce1c782`
- v19.6.1 final deletion closure: PR #74 comment `5460591186`
- v19.6.1 one-shot PRE-OAUTH session: SUCCESS / consumed / Codespace deleted
- Runtime: OFF

## Purpose
Build the next separately reviewed authority unit after successful PRE-OAUTH Step1. The proposed next unit ends after authenticated NONMUTATING Step3 diagnostics. It intentionally does NOT include Step4 or `--apply`.

No terminal command from historical v3/v4/v5/v10 chat/history is live authority. Historical reviewed governance is source evidence only. Any successor live action must be emitted as a new immutable v19.7 action artifact and independently reviewed before Owner presentation.

## Fresh source evidence used by Core
### Current PRE-OAUTH chain already proven live once
- v19.5 Action A source commit `9519b3d63f0aa74a698bdb9511c3b8bc4866a2b1`, blob `78d9fab6ab41cb5222795bc968818735b98ee5e7`
- v19.5 Action B source commit `9519b3d63f0aa74a698bdb9511c3b8bc4866a2b1`, blob `6319ed105440c4c2c8db968290f018853fed77d6`
- v19.6.1 Step1 action commit `0a045e3841045afdef4be0a7460dc3836095e413`, blob `01648decd0f6b23c07f5393f0090f96e3a876f94`, 947 bytes, SHA-256 `aae5dd7951b292de1057837cf23d87a25611fedb0e47f0adeab15a00791f08ee`

### OAuth / post-OAuth reviewed source evidence
Fresh-fetched immutable governance sources:
- v4 OAuth/two-epoch source: commit `2e1db6e3ea9f072cfa7a4e16c4662eb9f6969a68`, file `governance/MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_GATE_V4_IPHONE_OAUTH_SHELL_CONTINUITY_REMEDIATION_20260824_v1.json`, blob `c704f8e57c7c5c418c953ed9615612f70640d232`
- v8 post-OAuth trusted-Python bootstrap source: commit `9928153160692c8ecdcd7a076a472384bc8b20e9`, file `governance/MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_GATE_V8_POST_OAUTH_PYTHON_TRUST_BOOTSTRAP_ORDER_REMEDIATION_20260824_v1.json`, blob `f359b13f37b7251634e5dcb7fdf71130a3b1216d`
- v10 device-code observability/secrecy source: commit `2a981da6120270644241e5127466151a829854e0`, file `governance/MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_GATE_V10_DEVICE_CODE_OBSERVABILITY_REMEDIATION_20260827_v1.json`, blob `ad13faceb819cc6a2353523f0e20613750b63a64`
- v7 verified payload transport source: commit `a9f63b65b6df5ce66194d2e35d7491fe6d3649df`, file `governance/MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_GATE_V7_IPHONE_VERIFIED_PAYLOAD_TRANSPORT_ENVELOPE_20260824_v1.json`, blob `0d8fde6bafac459bf9aa8515181266b2787a2fe6`
- v6 Step3 single-line semantic source: commit `eb0b977750e5ce9b6a02766c74602cdd2a1ad571`, file `governance/MULTIVERSE_R1_STAGE1_PHASE_C_EXECUTION_GATE_V6_IPHONE_POST_OAUTH_SINGLE_LINE_TRANSPORT_HARDENING_20260824_v1.json`, blob `b14f87310a38917281914a9f95d4660db94807da`

## Proposed successor authority boundary
Exact conceptual sequence to be converted into NEW immutable v19.7 action artifacts only after this build-plan review:

`new dedicated Codespace -> new v19.7-bound Action A clean shell -> new v19.7-bound Action B trusted Python -> new v19.7-bound in-memory Step1 -> exact Step1 PASS -> new v19.7 OAuth launch -> Git credential prompt must appear -> Owner explicitly answers No to any Git credential helper setup branch required by the reviewed contract -> one-time device code appears -> Owner reports only DEVICE_CODE_DISPLAYED_NO_CODE_SHARED -> Core Fresh authority check -> Owner performs only reviewed Enter -> first-party GitHub device authorization -> Owner reports only GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED -> return to same Codespace -> no repo command in ordinary shell -> new v19.7 post-OAuth env-i reentry -> new v19.7 post-OAuth pure-shell trusted-Python gate -> new v19.7 Step2.6 verified transport/rehydrate -> exact PHASE_C_POST_OAUTH_CLEAN_SHELL_REENTRY_PASS -> exact effective OAuth scope equality {repo, read:org, gist} and repo-admin/nonmutating gates -> new v19.7 NONMUTATING Step3 -> STOP -> logout/local teardown as separately frozen -> Owner deletes Codespace`

## Device-code secrecy is absolute
While the one-time GitHub code is visible:
- no screenshot/photo/screen recording
- no OCR
- no copied terminal text
- no transcription
- no code characters sent to Core/chat
- only acknowledgement allowed: `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED`
After first-party GitHub confirms connection, only acknowledgement allowed at that boundary: `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED`.
Any disclosure consumes the future one-shot session and requires STOP/delete/no retry.

## Required v19.7 build properties
1. Every operator terminal action must be a NEW immutable v19.7 artifact with exact path/commit/blob/bytes/SHA-256/LF binding.
2. Historical command text is not delivery authority and may not be copied from chat/history.
3. All multiline/state-sensitive payloads must use a reviewed integrity-preserving transport; no iPhone newline-preservation assumption.
4. Post-OAuth Python binding must be proven before any Python loader executes.
5. Step2.6 must re-establish memory-backed roots, zero swap, canonical checkout bytes/modes/status and emit exact PASS before repository Python diagnostics.
6. Auth must be technically checked after OAuth; nonsecret acknowledgements are progress evidence only.
7. Effective OAuth scopes must equal exactly `{repo, read:org, gist}` before Step3.
8. Step3 is NONMUTATING only. It must not create fence, Environment, secret, writer key, ruleset/main mutation, Runtime state/task or any production mutation.
9. No Step4 or `--apply` artifact may be included in this authority unit.
10. Any anomaly, prompt mismatch, missing marker, transport/integrity failure, auth/scope mismatch, shell/session loss or delivery-gate failure consumes the future session: STOP/delete/no retry.
11. Immediately before each future live delivery, Core must Fresh Read current authority and Fresh-fetch/mechanically verify the exact immutable artifact.
12. A complete successor full-sequence manifest with all exact NEW action identities must be frozen and independently Lab + Auditor reviewed before Owner presentation and before a new Codespace.

## Current authority
`CAN_CREATE_NEW_CODESPACE_NOW: NO`
`CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
`CAN_START_OAUTH_NOW: NO`
`CAN_RUN_AUTHENTICATED_API_NOW: NO`
`CAN_RUN_STEP3_NOW: NO`
`CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
`PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
`RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`

Runtime remains OFF.
