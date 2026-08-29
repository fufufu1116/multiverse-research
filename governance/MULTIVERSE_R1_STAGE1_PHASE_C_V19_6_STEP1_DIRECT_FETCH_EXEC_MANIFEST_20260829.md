# MULTIVERSE R1 Stage 1 Phase C v19.6 — Step1 Direct Fetch/Verify/Execute Manifest

## Purpose
Replace the failed chat-delivery path for the 23,454-byte immutable v19.3 Step1 action with one short, reviewable terminal action that fetches the immutable file directly from GitHub by exact commit, verifies its complete byte identity inside the Codespace, and only then executes it.

This is a successor authority proposal only. It does not authorize a Codespace or terminal execution now.

## Predecessor closure
PR #74 closure comment `5460387443` records v19.5 as consumed and fail-closed: Action A success reported, Action B success reported, Action C not delivered/not executed, Codespace deleted, no retry, Runtime OFF.

## Canonical bindings at construction
- expected canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- predecessor recovery head: `94b5ef5f47d394ed5a090c8be6415ab65d99e14a`
- v19.6 Step1 fetch-exec action commit: `2297d91d87cae11183e7ef4110c11b13b50b70d1`
- action path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_6_SUCCESSOR_PREOAUTH_STEP1_FETCH_EXEC_ACTION_20260829.txt`
- action blob: `9b8e9450a867dc1948f08c972ee2e7eb611c3e63`
- action UTF-8 bytes: `998`
- action SHA-256: `d6fb7547f70d176965e0d811dce96efab22b400d08eb2649f2b9dc7e40296610`
- action internal LF: `0`
- action final LF: `NO`

## Immutable Step1 target
The direct fetch URL is pinned to immutable commit `26e2f36104b83c565fec3db158d103a4d799aeba` and exact path `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_3_COMPLETE_EMITTED_ACTION_20260829.txt`.

The downloaded bytes must satisfy all of these before execution:
- byte count exactly `23454`
- SHA-256 exactly `a4ee76a4cfe994fd0e1bc4f999bb3eff97934c04d54843f6edd2bb855b0feee6`
- Git blob SHA-1 exactly `c3010cd8e51f47e5225c124f3e4ba6762ba0f7ef`
- no LF byte anywhere, which implies internal LF `0` and final LF `NO`

Verification is performed with the already-bound trusted Python path `/usr/local/python/current/bin/python` after Action B has emitted `PHASE_C_TRUSTED_PYTHON_BINDING_PASS`.

## Fetch and fail-closed behavior
- fetch uses `/usr/bin/curl`
- HTTPS only via `--proto '=https'` and `--tlsv1.2`
- redirects allowed only because raw.githubusercontent.com delivery can require normal HTTPS handling
- fetch failure emits `PHASE_C_STEP1_FETCH_STOP_DELETE_CODESPACE` and exits `89`
- immutable binding mismatch emits `PHASE_C_STEP1_IMMUTABLE_BINDING_MISMATCH_STOP_DELETE_CODESPACE` and exits `89`
- temporary file is removed on fetch failure, verification failure, and after execution
- no downloaded bytes are executed until every binding check passes

## Execution semantics
After successful full-byte verification only, `/bin/bash "$f"` executes the exact downloaded immutable v19.3 Step1 artifact. Its authoritative success boundary remains `PHASE_C_STEP1_CHUNKED_TRANSPORT_AND_SOURCE_PASS`.

The child-shell execution is deliberate: no post-Step1 shell state is needed because the PRE-OAUTH authority unit ends immediately on success. Independent Lab and Auditor must explicitly determine whether this execution mode preserves the reviewed Step1 semantics.

## Proposed future one-shot sequence
Only after Independent Lab PASS, Independent Auditor PASS, and a new explicit Owner one-shot approval:

`new dedicated Codespace -> v19.5 Action A -> expected clean shell -> v19.5 Action B -> PHASE_C_TRUSTED_PYTHON_BINDING_PASS -> v19.6 Step1 direct fetch/verify/execute action -> PHASE_C_STEP1_CHUNKED_TRANSPORT_AND_SOURCE_PASS -> STOP -> Owner deletes Codespace`

Nothing may be inserted. No ad-hoc diagnosis, RETRIEVAL, repair, resume, second paste, or blind retry.

Immediately before future delivery of A, B, and the v19.6 action, Core must Fresh-fetch the exact immutable action file and mechanically verify its blob, bytes, SHA-256, internal-LF, and final-LF properties. Any mismatch or inability to verify is STOP / NO DELIVERY.

Any terminal mismatch, syntax error, missing required marker, unexpected output preventing exact classification, shell/session loss, accidental extra input, fetch failure, verification failure, or delivery-gate failure consumes that future one-shot session: STOP, delete Codespace, no retry.

## Explicit exclusions
OAuth/device flow, authenticated API, Step3, Step4, `--apply`, production/main/ruleset mutation, writer-key/secret operations, merge, Runtime branch/state/tasks/Sources/scheduler, activation receipt/tag, workflow dispatch, and Runtime activation are outside this authority unit and remain unauthorized.

Any unexpected authentication/device-code prompt is terminal STOP. No device code, screenshot/photo, OCR, or transcription may be sent to Core/chat at that boundary.

Runtime remains OFF.
