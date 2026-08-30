# MULTIVERSE R1 Stage 1 Phase C v19.7.16 — Executable v2 Implementation Plan

Status: DRAFT / NONCANONICAL / REVIEW-ONLY / NO LIVE AUTHORITY

Revision-B readiness authority: PR #74 comment 5465663034.
Requirements branch/head: agent/r1-stage1-phase-c-v19-7-16-exit-code-observability-readiness @ 565287ca68c4b27bdab7e7cf8402dc259403cff8.
Requirements blob: 0928311ea09c2217790845e8104d82f560b4b4f1.

Fresh canonical binding required for candidate:
- main commit: 5c1403c1f5aabb80d29e8c868440aede8888ce61
- main tree: 3d47741b4863411e5c36cb4c28925ac455ab6441

Implementation invariants:
1. Outer-loader host-visible exit namespace is exactly 103..114 for the twelve loader-controlled classes; unknown/unmapped fallback is exactly 115.
2. Historical runner fixed exits and unchanged Step3 fixed exits are mechanically scanned and proven not to occupy 103..115. Dynamic nonzero runner returns after RUNNER_START are encapsulated as outer RUNNER_RETURN=114.
3. The executable loader must preserve the reviewed pre-handoff PASS-marker ordering and Option-B RUNNER_START boundary semantics.
4. Whole-loader failure proof must execute the complete exact loader entrypoint/source for every class 103..114. Direct invocation of fail() or isolated gate fragments does not count.
5. Whole-loader proof must also cover fallback 115, harmless full-loader success through handoff, and Option-B runner-nonzero with exactly one runner invocation and outer 114.
6. Exact changed loader bytes must receive deterministic-builder equality, full Bash parse, exact path/blob/bytes/SHA-256/line-shape proof, and exhaustive nonempty strict-prefix parse failure (or independently equivalent complete transport-truncation proof). Prior v5d evidence is not a substitute.
7. Historical runner dependency is immutable recovery-head dependency: recovery head 19a14cfd019cceab199571b5d03d4dd0ba5bcd22, path governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh, blob bc2b638b0db7fa8a0c23f0988cd9946f9e24b590. Candidate branch-path equality must not be asserted unless independently true.
8. Historical runner interactive OAuth/device-code contract and v19.7.14 Step3 bytes remain unchanged.
9. Device code remains secret: never screenshot, copy, transcribe, OCR, or send it to Core/chat.
10. No Codespace/live execution, Step4, --apply, production/main/ruleset mutation, writer secret, merge, workflow dispatch, Runtime operation, or Runtime activation is authorized by this artifact.

Implementation order:
A. Build changed loader from deterministic builder with 103..115 map and exact current main/tree binding.
B. Build source-bound whole-loader harness using controlled command shims/fixtures while invoking the complete loader entrypoint.
C. Build collision/dependency proof against immutable historical runner and unchanged Step3.
D. Build exact-byte transport/strict-prefix proof against the changed loader itself.
E. Build consolidated diagnostic-chain manifest and freeze manifest with no false branch-path dependency claim.
F. Run Core self-checks only as implementation evidence; self-checks are not Independent Lab approval.
G. Freeze one exact head/tree and request new Independent Lab exact-candidate review.

Runtime: OFF.
