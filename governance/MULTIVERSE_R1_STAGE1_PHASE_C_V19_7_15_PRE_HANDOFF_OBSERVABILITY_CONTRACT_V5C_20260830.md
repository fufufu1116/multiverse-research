# MULTIVERSE R1 STAGE 1 PHASE C v19.7.15 PRE-HANDOFF OBSERVABILITY CONTRACT v5c

Status: DRAFT / INDEPENDENT REVIEW REQUIRED / NO LIVE AUTHORITY
Runtime: OFF

## Governing inputs
- Independent Lab executable PASS on predecessor v5b: PR #74 comment `5465318530`
- Independent Auditor FIX_REQUIRED on predecessor v5b: PR #74 comment `5465342027`
- predecessor exact head/tree: `6f832e0adc685e6b2bebefd823680b1c9d704922` / `6b3a0237f3a9ce5ce1fa35772680a7967b474a47`

## Material correction
The predecessor review request over-strengthened the pre-`PHASE_C_V19_7_15_RUNNER_START` negative-path stdout requirement to `stdout == empty`. That statement is not true for the exact loader because the loader intentionally emits fixed reviewed `PHASE_C_V19_7_15_PASS_*` success markers after completed gates.

The corrected contract is:

1. Before `PHASE_C_V19_7_15_RUNNER_START`, loader-controlled output is fixed-marker-only.
2. For a failure at gate N, stdout may contain only the exact ordered prefix of fixed reviewed `PHASE_C_V19_7_15_PASS_*` markers emitted by gates that completed before N.
3. The failing gate emits exactly one fixed allowlisted failure marker on stderr and exits nonzero, with no retry or fallthrough.
4. No dynamic tool, Git, shell, path, environment, exception, hash, or runner diagnostic may escape before `RUNNER_START`.
5. A failure at the first platform gate has empty stdout because no success gate has completed yet.
6. `PHASE_C_V19_7_15_RUNNER_START` remains the Option-B one-way output/ownership handoff. After that marker the exact historical reviewed runner owns its reviewed interactive output/OAuth-device-code contract.

## Exact pre-handoff success-marker order
The exact loader's fixed success markers before `RUNNER_START` are, in order:

1. `PHASE_C_V19_7_15_PASS_PLATFORM_CODESPACES`
2. `PHASE_C_V19_7_15_PASS_FRESH_PATHS`
3. `PHASE_C_V19_7_15_PASS_TMPFS_TRUST`
4. `PHASE_C_V19_7_15_PASS_GIT_CONTROL`
5. `PHASE_C_V19_7_15_PASS_CANONICAL_MAIN`
6. `PHASE_C_V19_7_15_PASS_RECOVERY_HEAD`
7. `PHASE_C_V19_7_15_PASS_REPO_STATE`
8. `PHASE_C_V19_7_15_PASS_RUNNER_TRUST`
9. `PHASE_C_V19_7_15_PASS_RUNNER_SHA256`

Then the loader emits `PHASE_C_V19_7_15_RUNNER_START` and transfers output ownership to the exact historical reviewed runner.

## Auditor blocker closure requirement
A whole-source proof must inspect the exact frozen loader, not only isolated failing fragments, and establish for every pre-handoff failure class that:

- every earlier stdout-producing loader marker is one of the fixed reviewed PASS markers above and appears in exact source order;
- the expected stdout transcript for that failure is exactly the prefix of those fixed PASS markers that precedes the failing gate;
- the failure marker is fixed and allowlisted;
- no later PASS marker or `RUNNER_START` can occur after the failing command because `fail()` exits immediately;
- all relevant external-command diagnostics remain suppressed/captured as already frozen;
- no dynamic stdout/stderr channel is introduced.

The existing isolated synthetic fixtures remain useful for exact fixed stderr marker behavior at each boundary, but they are not by themselves the whole-loader stdout proof.

## Preserved boundaries
- exact loader bytes are unchanged from v5b unless separately reviewed;
- exact historical runner blob remains `bc2b638b0db7fa8a0c23f0988cd9946f9e24b590`;
- Option-B `RUNNER_START` handoff remains unchanged;
- v19.7.14 NONMUTATING Step3 blob remains `c9459751e4b50c70fde1b94413b9c441dfbfccc4`;
- root cause remains `INDETERMINATE`;
- consumed Owner receipts remain nonreusable;
- no live or production authority is created.

No Codespace, OAuth/device flow, device-code handling, credential/token operation, live Step3, Step4, `--apply`, production/main/ruleset mutation, writer secret, merge, workflow dispatch, Runtime operation, or Runtime activation is authorized.