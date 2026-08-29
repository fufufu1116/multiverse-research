# FINAL INDEPENDENT LAB RE-REVIEW REQUEST — R1 STAGE 1 PHASE C v19.6.1 IN-MEMORY VERIFY/EXECUTE TOCTOU REMEDIATION

Role: Independent Lab / 独立検証室

Fresh Read required. Do not use Core conclusions as your verdict.

## Trigger
Independent Lab comment `5460425176` returned `LAB_V19_6_STEP1_DIRECT_FETCH_EXEC_VERDICT: FIX_REQUIRED` solely because v19.6 verified a mutable tempfile pathname and later `/bin/bash "$f"` reopened that pathname, leaving verify→execute TOCTOU.

## Candidate under review
Manifest head parent candidate:
`44fe911479748d5f991afe6fc48923b077302080`

Manifest:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_6_1_INMEMORY_VERIFY_EXEC_MANIFEST_20260829.md`

Action:
`governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_6_1_STEP1_INMEMORY_VERIFY_EXEC_ACTION_20260829.txt`

Action immutable commit:
`0a045e3841045afdef4be0a7460dc3836095e413`

Expected action identity:
- blob `01648decd0f6b23c07f5393f0090f96e3a876f94`
- 947 UTF-8 bytes
- SHA-256 `aae5dd7951b292de1057837cf23d87a25611fedb0e47f0adeab15a00791f08ee`
- internal LF 0
- final LF NO

Immutable Step1 target remains:
- commit `26e2f36104b83c565fec3db158d103a4d799aeba`
- blob `c3010cd8e51f47e5225c124f3e4ba6762ba0f7ef`
- 23454 bytes
- SHA-256 `a4ee76a4cfe994fd0e1bc4f999bb3eff97934c04d54843f6edd2bb855b0feee6`
- no LF

## Exact remediation to judge
v19.6.1 removes the tempfile/pathname execution handoff entirely.

The already-trusted exact Python binary:
- runs exact `/usr/bin/curl` against the immutable commit/path;
- captures curl stdout directly into in-memory bytes object `d`;
- verifies byte count, SHA-256, Git blob SHA-1, and LF condition on `d`;
- on success invokes `subprocess.run(["/bin/bash"], input=d)`;
- therefore Bash stdin is populated from the same verified bytes object, with no pathname reopen between verification and execution.

Please independently determine whether this closes the material verify→execute TOCTOU identified in comment `5460425176`, and whether child Bash via verified stdin preserves the already-accepted PRE-OAUTH Step1 semantics.

Also independently review fetch failure handling, identity mismatch failure, inherited Action A/B environment dependency, exact sequence completeness, no-retry/fail-closed boundary, delivery-time mechanical gate, and old-approval nonreuse.

Required verdict:
`LAB_V19_6_1_INMEMORY_VERIFY_EXEC_VERDICT: PASS | FIX_REQUIRED`

If PASS:
`CAN_PROCEED_TO_INDEPENDENT_AUDITOR: YES`

If not PASS:
`CAN_PROCEED_TO_INDEPENDENT_AUDITOR: NO`

Do not create a Codespace. Do not deliver or execute terminal commands. Do not execute the artifact. Do not start OAuth/device flow, authenticated API, Step3, Step4, `--apply`, production/main/ruleset mutation, writer-key/secret, merge, or Runtime. Runtime remains OFF.

Write the result back to PR #74.
