# FINAL LAB BUILD-PLAN REVIEW REQUEST — R1 STAGE 1 PHASE C v19.7 OAUTH-TO-NONMUTATING-STEP3 SUCCESSOR

Independent Lab only. Fresh Read GitHub before judging CURRENT/NOW/LATEST. Core conclusions are evidence only, never the Lab verdict. Review only; do not create a Codespace, deliver terminal commands, start OAuth, run authenticated API, run Step3, run Step4, use `--apply`, mutate production/main/ruleset, handle writer secrets, merge, or activate Runtime.

## Exact review target
- repo: `fufufu1116/multiverse-research`
- canonical main expected from immediate Core Fresh Read: `74ea95e59ac0654e1a0c1f811a178b3eef7b073c`
- v19.6.1 final deletion closure: PR #74 comment `5460591186`
- exact v19.7 build-plan head: `74d23624599749e7fa780e5aef742732783133a7`
- exact build-plan path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_OAUTH_TO_NONMUTATING_STEP3_SUCCESSOR_BUILD_PLAN_20260829.md`

Fresh source evidence named by the build plan must be independently refetched, including v4/v6/v7/v8/v10 governance and current v19.5/v19.6.1 PRE-OAUTH artifacts.

## Review purpose
Determine whether the v19.7 build plan is a sound and complete basis for Core to construct a NEW immutable full-sequence OAuth-to-NONMUTATING-Step3 successor manifest, while keeping all historical terminal text nonauthoritative and keeping Step4/`--apply`/production/Runtime outside scope.

This review is intentionally BEFORE exact v19.7 action emission. PASS authorizes only Core to build the exact immutable action set and then submit that exact full sequence for another independent Lab review. PASS does not authorize Owner presentation or live execution.

## Independent review questions
1. Is the next authority boundary correctly limited to new Codespace -> PRE-OAUTH A/B/Step1 -> OAuth/device flow -> post-OAuth trust reentry -> exact auth/scope gates -> NONMUTATING Step3 -> STOP/delete, excluding Step4/apply?
2. Is it correct that historical v3/v4/v5/v10 terminal text/chat reconstruction remains excluded from live authority and that all future terminal actions must be NEW immutable v19.7 artifacts?
3. Are v4 two-epoch OAuth semantics, v10 device-code secrecy acknowledgements, v8 post-OAuth Python bootstrap ordering, v7 integrity transport and v6 Step3 semantics the correct source-evidence chain to re-materialize?
4. Is the device-code boundary safe: no screenshot/OCR/copied output/transcription/code; only `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED`, then only reviewed Enter after Fresh authority check; only first-party GitHub device UI; then `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED`?
5. Must Git-credential-helper prompt presence/answer semantics be re-frozen explicitly in the successor full sequence, including fail-closed handling if the expected prompt does not appear?
6. Is the proposed post-OAuth order correct: env-i reentry -> pure-shell trusted-Python binding proof -> verified Step2.6 transport -> exact post-OAuth PASS -> technical auth/effective-scope/admin checks -> Step3?
7. Does the successor need any additional technical gate before authenticated API/Step3 beyond those identified in v10/v8/v4, especially exact effective scopes `{repo, read:org, gist}` and repository-admin identity?
8. Are nonsecret device acknowledgements correctly treated only as progress evidence, never as proof of authentication/scope/admin authority?
9. Is the no-newline-assumption rule sufficient, or must every long/state-sensitive successor action use an integrity-preserving in-memory/direct-fetch mechanism rather than the historical tempfile transport? Identify any TOCTOU or mutable-path concern introduced by reusing v7 design.
10. Given the v19.6 TOCTOU finding, should v19.7 prohibit verified-tempfile-then-reopen patterns entirely and require same-bytes in-memory verify/execute for Step2.6/Step3 as well? Treat this as material if applicable.
11. Is STOP/delete/no-retry on any prompt mismatch, code disclosure, transport failure, auth/scope mismatch, missing marker, unexpected output, shell loss or delivery-gate failure sufficient and correctly scoped?
12. Does the build plan preserve Step4/`--apply`, fence, Environment, writer key/secret, production/main/ruleset mutation, merge and Runtime as explicit NO?
13. Are any CURRENT source bindings stale or silently rebound? Fresh-check canonical main, PR #74 state, recovery lineage and all named immutable source blobs.
14. Identify every material item Core must fix before exact action emission.

## Required verdict
- `LAB_V19_7_BUILD_PLAN_VERDICT: PASS | FIX_REQUIRED`
- `UNRESOLVED_MATERIAL_ITEMS: ...`
- `CAN_CORE_BUILD_EXACT_V19_7_FULL_SEQUENCE_NOW: YES | NO`
- `CAN_PROCEED_DIRECTLY_TO_AUDITOR_NOW: NO`
- `CAN_PRESENT_TO_OWNER_NOW: NO`
- `CAN_CREATE_NEW_CODESPACE_NOW: NO`
- `CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
- `CAN_START_OAUTH_NOW: NO`
- `CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
- `CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
- `PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
- `RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`

Write the independent result back to PR #74.

Runtime remains OFF.
