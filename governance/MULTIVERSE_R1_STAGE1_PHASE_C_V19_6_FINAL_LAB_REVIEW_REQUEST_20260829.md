# FINAL INDEPENDENT LAB REVIEW REQUEST — R1 STAGE 1 PHASE C v19.6 STEP1 DIRECT FETCH/VERIFY/EXECUTE

Role: Independent Lab / 独立検証室.

Perform a GitHub Fresh Read before judgment. Do not use Core, prior Lab, prior Auditor, chat history, memory, or summaries as substitutes for independent judgment.

## Exact review head
Review recovery head `1d2bb0e5045f054a77eb247f113e34172cd6a2da`.

Expected canonical main at request construction: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`.

## Review objects
Manifest:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_6_STEP1_DIRECT_FETCH_EXEC_MANIFEST_20260829.md`

New v19.6 action:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_6_SUCCESSOR_PREOAUTH_STEP1_FETCH_EXEC_ACTION_20260829.txt`

Expected action identity:
- commit containing action: `2297d91d87cae11183e7ef4110c11b13b50b70d1`
- blob `9b8e9450a867dc1948f08c972ee2e7eb611c3e63`
- UTF-8 bytes `998`
- SHA-256 `d6fb7547f70d176965e0d811dce96efab22b400d08eb2649f2b9dc7e40296610`
- internal LF `0`
- final LF `NO`

Immutable target:
- commit `26e2f36104b83c565fec3db158d103a4d799aeba`
- path `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_3_COMPLETE_EMITTED_ACTION_20260829.txt`
- blob `c3010cd8e51f47e5225c124f3e4ba6762ba0f7ef`
- bytes `23454`
- SHA-256 `a4ee76a4cfe994fd0e1bc4f999bb3eff97934c04d54843f6edd2bb855b0feee6`
- internal LF `0`
- final LF `NO`

Predecessor closure evidence: PR #74 comment `5460387443`.

## Independent checks required
1. Fresh current branch/main binding and no unexplained drift.
2. Recompute exact new action blob/bytes/SHA/LF properties from Fresh content.
3. Confirm direct URL is pinned to the exact immutable commit/path, not a mutable branch/tag.
4. Confirm no downloaded bytes execute before all required byte count, SHA-256, Git blob SHA-1, and LF checks pass.
5. Confirm `/usr/local/python/current/bin/python` verifier is appropriate only after the already-reviewed Action B trusted-Python PASS boundary.
6. Review `/usr/bin/curl` flags and determine whether the fetch path is acceptably fail-closed and HTTPS-pinned for this purpose.
7. Independently determine whether executing the verified immutable artifact through `/bin/bash "$f"` preserves the reviewed Step1 semantics sufficiently for this PRE-OAUTH session. This is a required substantive judgment, not assumed by Core.
8. Confirm temp-file deletion/failure markers/exit behavior are fail-closed.
9. Confirm successor sequence has no ad-hoc command insertion, RETRIEVAL, repair/resume, retype/reconstruction, or blind retry.
10. Confirm delivery-time Fresh+mechanical gate applies to A/B/v19.6 action itself; the long Step1 artifact is verified in Codespace before execution rather than reconstructed in chat.
11. Confirm v19.5 Owner approval is consumed/nonreusable and a new Independent Auditor PASS + new explicit Owner one-shot approval are required before another Codespace.
12. Confirm OAuth/device flow, authenticated API, Step3, Step4, `--apply`, production/main/ruleset mutation, writer-key/secret, merge, and Runtime remain outside scope.

Do not create a Codespace. Do not deliver or execute terminal commands. Do not run the artifact. Do not perform OAuth/API/Step3/Step4/`--apply`/production/main/ruleset/writer-secret/merge/Runtime actions.

## Required verdict fields
`LAB_V19_6_STEP1_DIRECT_FETCH_EXEC_VERDICT: PASS | FIX_REQUIRED`
`CANONICAL_BINDING`
`V19_6_ACTION_IMMUTABLE_BINDING`
`IMMUTABLE_TARGET_PINNING`
`PRE_EXECUTION_FULL_BYTE_VERIFICATION`
`TRUSTED_PYTHON_DEPENDENCY`
`HTTPS_FETCH_FAIL_CLOSED`
`BASH_FILE_EXECUTION_SEMANTIC_EQUIVALENCE`
`TEMPFILE_AND_FAILURE_CLEANUP`
`FULL_SEQUENCE_COMPLETENESS`
`DELIVERY_TIME_MECHANICAL_GATE`
`OLD_APPROVAL_CONSUMED_NONREUSABLE`
`OAUTH_AND_PRODUCTION_EXPLICITLY_OUT_OF_SCOPE`
`UNRESOLVED_MATERIAL_ITEMS`
`CAN_PROCEED_TO_INDEPENDENT_AUDITOR: YES | NO`
`CAN_CREATE_NEW_CODESPACE_NOW: NO`
`CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
`RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`

Write the result back to PR #74.

Runtime remains OFF.
