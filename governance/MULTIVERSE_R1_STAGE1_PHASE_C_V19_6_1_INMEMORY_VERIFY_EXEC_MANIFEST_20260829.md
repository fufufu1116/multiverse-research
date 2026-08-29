# MULTIVERSE R1 Stage 1 Phase C v19.6.1 — In-Memory Verify/Execute Manifest

Status: FROZEN CANDIDATE / PRE-OAUTH / NO LIVE AUTHORITY
Date: 2026-08-29 JST

## Purpose
Remediate the sole material blocker identified by Independent Lab comment `5460425176`: verify→execute TOCTOU in v19.6 caused by verifying a tempfile pathname and later reopening that mutable pathname with `/bin/bash "$f"`.

## Canonical / predecessor binding
- canonical main at Core Fresh Read: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- v19.6 Lab result: `5460425176` = `FIX_REQUIRED`
- predecessor v19.5 consumed closure: `5460387443`
- old Owner approval remains consumed and nonreusable.

## v19.6.1 action
Path:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_6_1_STEP1_INMEMORY_VERIFY_EXEC_ACTION_20260829.txt`

Immutable action commit:
`0a045e3841045afdef4be0a7460dc3836095e413`

Expected identity:
- blob: `01648decd0f6b23c07f5393f0090f96e3a876f94`
- UTF-8 bytes: `947`
- SHA-256: `aae5dd7951b292de1057837cf23d87a25611fedb0e47f0adeab15a00791f08ee`
- internal LF: `0`
- final LF: `NO`

## Immutable Step1 target
- commit: `26e2f36104b83c565fec3db158d103a4d799aeba`
- path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_3_COMPLETE_EMITTED_ACTION_20260829.txt`
- blob: `c3010cd8e51f47e5225c124f3e4ba6762ba0f7ef`
- bytes: `23454`
- SHA-256: `a4ee76a4cfe994fd0e1bc4f999bb3eff97934c04d54843f6edd2bb855b0feee6`
- internal LF: `0`
- final LF: `NO`

## TOCTOU remediation mechanism
The v19.6.1 action does not create, verify, or execute a tempfile pathname.

A trusted Python process, whose exact binary binding must already have passed Action B, performs the entire security-critical handoff:
1. invokes exact `/usr/bin/curl` against the immutable raw GitHub commit/path and captures stdout directly into Python bytes object `d`;
2. if curl fails, emits `PHASE_C_STEP1_FETCH_STOP_DELETE_CODESPACE` and exits `89`;
3. computes and checks on that same in-memory `d`: exact length 23454, exact SHA-256, exact Git blob SHA-1, and absence of LF;
4. if any identity predicate fails, emits `PHASE_C_STEP1_IMMUTABLE_BINDING_MISMATCH_STOP_DELETE_CODESPACE` and exits `89`;
5. only after all predicates pass, launches `/bin/bash` and supplies that same `d` object as Bash stdin using `subprocess.run(["/bin/bash"], input=d)`;
6. exits with the child Bash return code.

There is no verified pathname to replace and no pathname reopen between verification and execution. The bytes checked are the bytes supplied as Bash stdin.

## Sequence
A future session, if and only if independently approved and separately Owner-authorized, is exactly:
`new dedicated Codespace -> reviewed Action A -> clean shell -> reviewed Action B -> PHASE_C_TRUSTED_PYTHON_BINDING_PASS -> v19.6.1 action -> PHASE_C_STEP1_CHUNKED_TRANSPORT_AND_SOURCE_PASS -> STOP -> Owner deletes Codespace`

No command may be inserted. No retry/repair/resume is authorized. Any mismatch, fetch failure, syntax error, missing expected marker, unexpected output preventing exact classification, shell/session loss, accidental extra input, or delivery-gate failure consumes the future session and requires STOP/delete.

## Delivery gate
Immediately before any future terminal delivery, Core must Fresh Read current authority and Fresh-fetch the exact immutable action source, mechanically verifying blob/bytes/SHA-256/internal-LF/final-LF. Chat/history reconstruction, manual retyping, regeneration, substitution, or splitting is prohibited.

## Explicit exclusions
This candidate does not authorize Codespace creation, terminal delivery/execution, OAuth/device flow, authenticated API, Step3, Step4, `--apply`, production/main/ruleset mutation, writer-key/secret operations, merge, or Runtime activation. Runtime remains OFF.

## Review requirement
Independent Lab must re-review this exact v19.6.1 remediation. Only Lab PASS may permit an Independent Auditor request. Only subsequent Auditor PASS may permit Core to present a new one-shot Owner authorization decision.
