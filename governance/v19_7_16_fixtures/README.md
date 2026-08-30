# v19.7.16 Revision C frozen review fixtures — V6

NONLIVE / NONCANONICAL / evidence class `BYTE_IDENTICAL_COMPLETE_LOADER` for 103..112 only.

Independent Lab does not author a SCENARIO_ROOT, MANIFEST.sha256, repo-seed, redirect, or other proof-relevant input. The frozen case-run accepts only the target code 103..112. It mechanically materializes a temporary read-only fixture from this candidate's exact frozen shim bytes, the requested numeric case, and the immutable recovery-head runner object after exact blob/SHA-256 verification.

Network is unavailable inside `bwrap --unshare-all`. The exact loader's HTTPS clone observation is intercepted only by the frozen Git shim at loader-visible `/usr/local/bin/git`; clone/repository observations for 106..110 never delegate to network Git. Cases 111/112 additionally bind the frozen SHA shim to the loader's absolute `/usr/bin/sha256sum`.

Case 105 no longer depends on the reviewer's temporary-directory filesystem type. `/dev/shm` remains deterministic tmpfs, while a frozen `stat` shim is mounted only for case 105 at loader-visible `/usr/local/bin/stat`. It delegates all ordinary metadata queries to `/usr/bin/stat`, but for exactly `stat -f -c %T <path>` it returns the reviewed non-tmpfs value `ext2/ext3`, forcing the unchanged loader's TMPFS_TRUST gate to fail with outer 105. The stat shim bytes are exact review-unit members and are Git-blob checked by case-run before use. Case 104 precreates exact ROOT; case 103 removes Codespaces inputs.

The case-run obtains the runner only from immutable recovery head `19a14cfd019cceab199571b5d03d4dd0ba5bcd22`, path `governance/MULTIVERSE_R1_STAGE1_PHASE_C_PRE_OAUTH_CONTINUITY_RECOVERY_RUNNER_20260827_v1.sh`, verifies blob `bc2b638b0db7fa8a0c23f0988cd9946f9e24b590` and SHA-256 `f4d91bb6fc73fbc236c49f0b364788ef8e7461850ff1bba1dd058d471e5468c2`, then materializes those exact bytes for the byte-identical loader trust gates. Candidate-branch runner bytes are not authority.

113 is not a fixture case: it is immutable-object static/mechanical production-positive proof. 114/success use only `GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT`. 115 uses only `SYNTHETIC_FALLBACK_EQUIVALENT`. Evidence classes are non-interchangeable.

No network/live/OAuth/Step4/--apply/production mutation/merge/workflow/Runtime authority. Runtime OFF.
