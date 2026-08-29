# MULTIVERSE R1 STAGE 1 PHASE C — v19.5 SUCCESSOR PRE-OAUTH FULL-SEQUENCE MANIFEST

Status: DRAFT / REVIEW ONLY / NOT LIVE AUTHORITY
Runtime: OFF

## Purpose
Freeze the complete operator-visible sequence for exactly one successor PRE-OAUTH preparation-only Codespace session after the stale-v5 delivery incident. This manifest does not authorize a Codespace or any terminal delivery. It exists so the whole sequence can be independently reviewed before any new live session.

## Canonical bindings
- canonical repo: `fufufu1116/multiverse-research`
- canonical main: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- canonical tree: `3d47741b4863411e5c36cb4c28925ac455ab6441`
- v19.4 reviewed incident/rebind head: `3b8e867c0f51c00e5778669cfe47229796185429`
- v19.4 Auditor request head: `d220703527cfb010f5c6b1ca72139e2edb777b9c`
- Independent Lab PASS: PR #74 comment `5460217706`
- Independent Auditor PASS: PR #74 comment `5460251668`
- stale-v5 incident record: PR #74 comment `5460186458`
- consumed/nonreusable prior Owner receipt: PR #74 comment `5460132360`

## Historical-authority exclusion
No v3/v4/v5/v10 terminal text, old Owner receipt, chat/history text, memory, summary, screenshot transcription, manual reconstruction, or prior operator command is live authority for this successor session. The Step0 and Step0.5 actions below are newly frozen v19.5 artifacts and must be reviewed as new exact bytes; semantic similarity to historical actions gives them no authority.

## Frozen action A — v19.5 Step0 clean-shell entry
Path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_5_SUCCESSOR_PREOAUTH_STEP0_ACTION_20260829.txt`
- Git blob: `78d9fab6ab41cb5222795bc968818735b98ee5e7`
- UTF-8 bytes: `357`
- SHA-256: `e47ae2a26a50c56c9c539813fd8dcf9419a3c19303c9b914bbd63929de98872e`
- internal LF count: `0`
- final LF: `NO`
- semantics: replace the current terminal process with an `env -i`, no-profile/no-rc Bash; fixed trusted PATH includes `/usr/local/python/current/bin`; fixed memory-backed HOME/GH_CONFIG_DIR names; preserve only Codespaces identity variables needed for later gates.

## Frozen action B — v19.5 Step0.5 trusted-Python binding check
Path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_5_SUCCESSOR_PREOAUTH_STEP0_5_ACTION_20260829.txt`
- Git blob: `6319ed105440c4c2c8db968290f018853fed77d6`
- UTF-8 bytes: `392`
- SHA-256: `54dcf138be14d6a696c4eaebed29e374b14cb34eae838de751057ceed7f77d51`
- internal LF count: `0`
- final LF: `NO`
- required success marker: `PHASE_C_TRUSTED_PYTHON_BINDING_PASS`
- failure: either predicate failure prints the fixed failure marker and exits `89`; session is terminal STOP/delete/no retry.

## Frozen action C — immutable v19.3 complete emitted Step-1 transport action
Path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_3_COMPLETE_EMITTED_ACTION_20260829.txt`
- immutable artifact commit: `26e2f36104b83c565fec3db158d103a4d799aeba`
- Git blob: `c3010cd8e51f47e5225c124f3e4ba6762ba0f7ef`
- UTF-8 bytes: `23454`
- SHA-256: `a4ee76a4cfe994fd0e1bc4f999bb3eff97934c04d54843f6edd2bb855b0feee6`
- internal LF count: `0`
- final LF: `NO`
- semantic shape: exact reviewed `INIT -> CHUNK 00..12 -> ASSEMBLE -> SOURCE`
- required terminal success marker from the authoritative SOURCE transport: `PHASE_C_STEP1_CHUNKED_TRANSPORT_AND_SOURCE_PASS`
- RETRIEVAL is not part of this session action and is not embedded in the artifact.

## Complete operator-visible sequence for this one session
This is the entire allowed session. Nothing may be inserted between these steps.

1. Only after this manifest receives Independent Lab PASS, Independent Auditor PASS, and a new explicit Owner one-shot approval, create exactly one new GitHub Codespace from canonical `main`.
2. Before any terminal command, Core Fresh Reads canonical main and the immutable sources for actions A/B/C. Any drift or inability to verify means STOP/delete Codespace/no command delivery.
3. Core mechanically verifies action A exact blob, byte count, SHA-256, zero internal LF, and no final LF; then delivers action A by direct clipboard once. Owner pastes it once with no edit/split/retype.
4. If action A does not cleanly enter the expected no-profile/no-rc Bash epoch, STOP/delete Codespace/no retry. No ad-hoc diagnostic command is permitted.
5. Core Fresh Reads and mechanically verifies action B immediately before delivery. Owner pastes action B once with no edit/split/retype.
6. Only exact marker `PHASE_C_TRUSTED_PYTHON_BINDING_PASS` permits continuation. Any other result, missing marker, syntax error, session loss, terminal replacement, or unexpected output is STOP/delete Codespace/no retry.
7. Core Fresh Reads immutable artifact commit `26e2f36104b83c565fec3db158d103a4d799aeba` immediately before delivery of action C and mechanically verifies exact blob, `23454` bytes, SHA-256, zero internal LF, and no final LF. No regeneration or reconstruction is permitted.
8. Owner pastes action C exactly once by direct clipboard. No split/edit/retype/reconstruction/retry.
9. Only exact final marker `PHASE_C_STEP1_CHUNKED_TRANSPORT_AND_SOURCE_PASS` permits classification of action C as successful. Any nonzero/failure marker, missing final marker, session loss, transport error, or unexpected prompt transition is terminal STOP/delete Codespace/no retry. Read-only RETRIEVAL may not be improvised; it requires separate reviewed authority if evidence retrieval is needed after a failure.
10. After successful action C, STOP. Do not start OAuth. Do not run authenticated API. Do not run Step3 or Step4. Owner deletes the Codespace. Core records a durable nonsecret PRE-OAUTH preparation receipt only after Owner confirms deletion.

## Delivery-time mechanical gate
Immediately before every security-critical delivery A/B/C, Core must Fresh-fetch the exact immutable source and mechanically verify the bound blob/bytes/SHA-256/LF properties. Chat/history, copied prior messages, memory, manual retyping, reconstruction, regeneration, or visual transcription are prohibited. Verification failure is `STOP / NO DELIVERY`.

## Session-loss and no-retry contract
Any command mismatch, syntax error, missing required marker, unexpected output that prevents exact classification, shell/session loss, accidental extra operator input, or inability to complete a delivery gate consumes the one-shot session. Delete that Codespace and return for review. No repair, resume, second paste, alternative terminal, or blind retry is authorized.

## OAuth/device-code boundary
OAuth/device flow is explicitly OUT OF SCOPE for this v19.5 session. Therefore no device code should be displayed. If any authentication/device-code prompt appears unexpectedly, STOP immediately, do not transmit any code or screenshot/photo/OCR/transcription, delete the Codespace, and return for review. The existing device-code secrecy rule remains binding.

## Explicit nonauthority
This manifest itself authorizes no Codespace and no terminal delivery. Even after later approval, the session authority described here ends after successful action C and Codespace deletion. It does NOT authorize OAuth/device flow, authenticated GitHub API, Step3, Step4, `--apply`, provision fence, Environment mutation, writer-key/secret generation/storage/readback, production/main/ruleset mutation, merge, Runtime branch/state/tasks/Sources/scheduler, activation receipt/tag, workflow dispatch, or Runtime activation.

## Review progression
`NEXT_ALLOWED_GATE: INDEPENDENT_LAB_REVIEW_ONLY`

Runtime remains OFF.
