# v19.7.16 Whole-Loader Fixture Protocol v2 — Revision C V6

Status: REVIEW-ONLY / NONLIVE / NONCANONICAL.

For outer classes 103..112 only, Independent Lab must execute the complete exact loader blob `396c5f99c8837b4bc946a76effe1e19cd391b7d0` from first byte using the frozen case-run. No reviewer-authored SCENARIO_ROOT, MANIFEST.sha256, repo-seed, network redirect, environment selector, mutable external fixture, or proof-relevant reviewer filesystem property is permitted.

The frozen case-run accepts only numeric target 103..112. It creates all ephemeral namespace plumbing itself from exact frozen candidate bytes and the immutable recovery-head runner object after exact blob/SHA-256 verification. `bwrap --unshare-all` removes network. Exact loader bytes are unchanged. The frozen Git shim is mounted at loader-visible `/usr/local/bin/git` and deterministically supplies clone/repository observations for 106..110 without delegating HTTPS clone to network Git. Case 104 precreates exact ROOT; case 103 removes Codespaces inputs. Cases 111/112 mount the frozen SHA shim at exact `/usr/bin/sha256sum`.

Case 105 is deterministic and host-filesystem independent: `/dev/shm` remains the case-run-created tmpfs, and a frozen exact `stat` shim is mounted only for case 105 at loader-visible `/usr/local/bin/stat`. For ordinary stat operations it delegates to `/usr/bin/stat`; for exactly the filesystem-type query `stat -f -c %T <path>` used by the unchanged loader's TMPFS_TRUST gate, it returns reviewed value `ext2/ext3`. Thus the unchanged loader observes a non-tmpfs/non-ramfs filesystem type and deterministically emits the 105 marker/status. The case-run verifies the exact stat-shim Git blob before mounting it. No ambient temporary-directory filesystem type is used as evidence.

The whole-loader harness mechanically invokes this case-run itself for every 103..112 case and compares observed outer rc/stdout/stderr/control data to the frozen transcript contract. This is `BYTE_IDENTICAL_COMPLETE_LOADER` evidence only.

Production-positive 113 is not synthetic fixture evidence. It is the exact immutable recovery-head object proof plus exact loader static/mechanical binding required by Revision C. 114/success are only `GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT`, with proof-relevant fail()/mark() and boundary bytes mechanically extracted from exact loader source and compared against frozen expected transformation digests. Fallback115 is only `SYNTHETIC_FALLBACK_EQUIVALENT`. Evidence classes are non-interchangeable.

No network, OAuth/device flow, Codespace/live execution, Step4, `--apply`, production/main/ruleset mutation, writer secret, merge, workflow dispatch, or Runtime operation is permitted. Runtime OFF.
