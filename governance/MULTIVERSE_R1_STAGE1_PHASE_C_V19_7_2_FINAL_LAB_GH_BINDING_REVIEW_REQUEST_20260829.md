# FINAL LAB MICRO RE-REVIEW REQUEST — R1 STAGE 1 PHASE C v19.7.2 GH BINARY BINDING

Role: Independent Lab / 独立検証室

Fresh Read GitHub first. Do not use Core/prior Lab/Auditor conclusions as substitutes for independent judgment.

Repo: `fufufu1116/multiverse-research`
PR: `#74`

Predecessor Lab result: comment `5460729983`
Predecessor reviewed head: `d6d625c9d536f116fcd3e6ae2ff081d29cbbd20e`
Predecessor verdict: `FIX_REQUIRED`

The sole remaining material blocker identified there was the unsupported hard-coded `GH_BIN=/usr/bin/gh` binding. The memfd/same-shell design and other v19.7.1 remediation items were PASS at design level.

Review these new exact artifacts:

1. GH binding remediation design:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_2_GH_BINDING_REMEDIATION_20260829.md`
commit `5f951d1de6257c00133bf3d1d10cb7c63280936d`

2. Revised exact auth/scope/admin nonmutating gate:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_GATE_20260829.py`
commit `864202e5821755d4adfbf897c6f0420b83f04211`
blob `8436ccb6d0c9f7799546bba43116d3fa56bf8159`

Independently verify:
- current recovery head / canonical main / PR state Fresh;
- `/usr/bin/gh` hard-code is gone;
- PATH must equal exactly `/usr/local/bin:/usr/bin:/bin:/usr/local/python/current/bin`;
- `shutil.which("gh", path=CONTROLLED_PATH)` must succeed;
- result must be absolute, regular-file, executable;
- `shutil.which("gh")` under the current exact PATH must equal the explicit controlled-PATH resolution;
- the already-resolved absolute `gh_bin` is then used for both API subprocesses under the same controlled PATH;
- no fallback, alternate gh, alias/function, PATH widening, silent substitution, or unreviewed hard-coded path exists;
- this exact contract is consistent with the Fresh canonical Codespaces trust model that uses `shutil.which("gh")` + `gh` under controlled environment;
- only GET `/user` and GET `/repos/fufufu1116/multiverse-research` occur;
- exact login, exact scope-set equality `{repo, read:org, gist}`, repository admin=true, and nonmutation semantics remain intact;
- success marker is exactly `PHASE_C_V19_7_2_AUTH_SCOPE_ADMIN_NONMUTATING_PASS`;
- all failures are fail-closed exit 91 with fixed STOP/delete prefix.

Do not silently substitute another path/binding. If this controlled-PATH contract is not sufficiently bound or introduces another material issue, return FIX_REQUIRED and state exactly why.

Required verdict:
`LAB_V19_7_2_GH_BINDING_VERDICT: PASS | FIX_REQUIRED`
`UNRESOLVED_MATERIAL_ITEMS: ...`
`CAN_CORE_BUILD_NEW_EXACT_V19_7_FULL_SEQUENCE_AFTER_THIS_VERDICT: YES | NO`
`CAN_PROCEED_DIRECTLY_TO_AUDITOR_NOW: NO`
`CAN_PRESENT_TO_OWNER_NOW: NO`
`CAN_CREATE_NEW_CODESPACE_NOW: NO`
`CAN_DELIVER_TERMINAL_COMMAND_NOW: NO`
`CAN_START_OAUTH_NOW: NO`
`CAN_RUN_AUTHENTICATED_API_OR_STEP3_NOW: NO`
`CAN_DELIVER_STEP4_OR_APPLY_NOW: NO`
`PRODUCTION_MUTATION_AUTHORIZED_NOW: NO`
`RUNTIME_ACTIVATION_AUTHORIZED_NOW: NO`

Write the result back to PR #74.

This is review only. Do not create a Codespace, deliver/execute terminal commands, start OAuth/device flow, run authenticated API or Step3, run Step4/--apply, mutate production/main/rulesets, touch writer keys/secrets, merge, or operate Runtime. Runtime remains OFF.
