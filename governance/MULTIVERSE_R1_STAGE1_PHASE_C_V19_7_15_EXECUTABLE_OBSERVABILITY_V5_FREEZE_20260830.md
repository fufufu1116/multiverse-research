# MULTIVERSE R1 STAGE 1 PHASE C v19.7.15 EXECUTABLE OBSERVABILITY v5b OPTION-B FREEZE

Status: DRAFT / INDEPENDENT REVIEW REQUIRED / NO LIVE AUTHORITY
Runtime: OFF

## Governing review inputs
- Independent Lab readiness FIX_REQUIRED: PR #74 comment `5465194791`
- Core revised requirements: PR #74 comment `5465211734`
- Independent Lab readiness PASS: PR #74 comment `5465218420`
- Core post-readiness conformance: PR #74 comment `5465238751`
- Independent Lab runner-output boundary Option B: PR #74 comment `5465272657`
- exact revised-requirements head/tree: `3ba0746eeac2f769a89e69ac5dfeb040084518c3` / `be55473c801c7032700482361ee81c6c4605297b`
- revised-requirements artifact blob: `66662a3f27b947ca6cb2c7f2645c62f19ba7c5e9`

## Candidate lineage
- branch: `agent/r1-stage1-phase-c-v19-7-15-executable-v5b`
- predecessor v5 freeze head/tree: `4aea0e10dea1ae0fc368ed120476a0d19f434aa3` / `48525beeb309d20092edebb99417247fe238402f`
- Option-B harness commit: `b6d5cefc5c179ddfa4bfb0d2f7a911c7baf79825`
- Option-B chain commit: `a2ae984e496e16d5347e130557c985a28558fc1c`
- pre-freeze artifact-set tree: `2934e474fe7bd64ad38e8930ca4e4a929ef2513a`

### Owner-facing exact loader — unchanged from v5
- path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_ACTION_V5_20260830.txt`
- Git blob: `2d7bf6010509febcfbaaaa5e9b89d53c0c347205`
- bytes: `5588`
- SHA-256: `ee71fd11219b97c3b54443638291f59fc4f1db7c6916a344c5be17e48f5b69e4`
- internal LF count: `0`
- final LF: `NO`
- shell lines: `1`
- direct-copy source: exact independently reviewed repository artifact only
- Core manual reconstruction/retyping/splitting/normalization/recomposition: prohibited

### Deterministic builder — unchanged from v5
- path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_BUILDER_V5_20260830.py`
- Git blob: `300702ae9aa1a23cb7239779dd4202adc89fa0a8`
- bytes: `1558`
- SHA-256: `b326e3320256c24988edc76c89cff37cb8f312fc987971a75a3f55b70a445ec4`
- deterministic output remains byte-for-byte identical to the exact loader

### Source-bound synthetic / transport harness — Option B amended
- path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_PRE_OAUTH_LOADER_HARNESS_V5_20260830.py`
- Git blob: `f637343865697a54de0188898386ec009630798e`
- bytes: `9759`
- SHA-256: `77cb9daafae815728b292ab40f89037c1f2cfa5e510202bcb4b2826479e87547`
- complete Bash parse required
- every nonempty strict byte prefix tested for Bash parse failure
- source-bound pre-handoff negative boundaries retain empty stdout + exact single fixed stderr marker + nonzero exit
- existing-file and symlink-collision fixtures remain distinct
- SHA command failure and SHA mismatch remain distinct classes
- prelaunch/read/parse remains strict marker-only failure
- runtime-nonzero fixture now uses a harmless runner that emits fixed synthetic stdout and stderr after `PHASE_C_V19_7_15_RUNNER_START`, then exits nonzero
- fixture requires preservation of child output followed by `PHASE_C_V19_7_15_FAIL_RUNNER_RETURN`, loader nonzero, and exactly one child invocation
- no OAuth/network/device-code activity is exercised by the synthetic fixture
- harmless controlled runner success transition remains covered

## Option-B output / authority boundary
`PHASE_C_V19_7_15_RUNNER_START` is the one-way loader-to-runner output/ownership handoff marker.

Before that marker, the loader fixed-marker-only containment contract governs loader-controlled failures. After that marker, stdout/stderr is governed only by the exact historical reviewed runner bytes and their reviewed OAuth/device-code secrecy contract. No blanket runtime redirect or buffering is introduced.

`PHASE_C_V19_7_15_FAIL_RUNNER_RETURN` is retained with deliberately narrow semantics only:
- `RUNNER_START` was already emitted;
- the exact runner process returned nonzero;
- loader terminates nonzero/fail-closed;
- no loader retry or fallthrough occurs.

It does NOT prove empty stdout, marker-only stderr, absence of prior runner output, root-cause identification, suppression of OAuth/device-flow output, or device-code secrecy by itself.

Any historical-runner byte drift requires a new independent review. Historical PASS is evidence only and does not auto-approve changed bytes.

A zero runner return creates no reusable returned-shell authority. The next action, if separately authorized later, must be the frozen post-OAuth clean-shell reentry path. An ordinary returned shell is not reusable authority.

### Consolidated chain — Option B amended
- path: `governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_15_CONSOLIDATED_DIAGNOSTIC_CHAIN_V5_20260830.json`
- Git blob: `62c4e9b15fb6e71babb274f78c2a15d01661bb53`
- bytes: `4852`
- SHA-256: `56816c413d05fcbdd75f7749ad4762c1a5f4496bf29154941c7e31821770e76b`
- exact unit: fresh dedicated Codespace -> exact frozen pre-OAuth loader -> `RUNNER_START` handoff -> historical reviewed runner-owned OAuth/device-code output contract -> post-OAuth clean-shell reentry -> trusted Python -> Step2.6 -> exact effective scopes/admin gate -> unchanged NONMUTATING Step3 -> STOP/delete
- intermediate success creates no authority
- root cause remains `INDETERMINATE`

## v19.7.14 Step3 preserved unchanged
- action blob: `c9459751e4b50c70fde1b94413b9c441dfbfccc4`
- bytes: `792`
- SHA-256: `1ddda0b2588793a409aa1f32dff73687bfaab8ac1d2a7bb5604e615bb1e4dfe9`
- immutable fetch commit: `84ec02fcaf79f86e0757ad356d62fb6f9d31e42d`
- diagnostic blob: `4f2718f448fc8367775be16bcbb3b06cb59f6047`
- trusted Python flags: `-I -S -B`
- same verified bytes execution / no mutable reread / NONMUTATING only / no Step4 / no `--apply`

## Nonauthority
This freeze authorizes only a NEW Independent Lab executable-candidate review. It does not authorize Auditor review, Owner presentation, Codespace creation, OAuth/device flow, device-code handling, live Step3, Step4, `--apply`, production/main/ruleset mutation, writer-key/secret operation, merge, workflow dispatch, Runtime operation, or Runtime activation.

Consumed Owner receipts remain nonreusable. Runtime remains OFF.

The final exact review head/tree containing this freeze must be Fresh-bound externally in the Lab request.
