# v19.7.16 Whole-Loader Fixture Protocol v2 — Revision C V4

Status: REVIEW-ONLY / NONLIVE / NONCANONICAL.

For outer classes 103..112 only, Independent Lab must execute the complete exact loader blob `396c5f99c8837b4bc946a76effe1e19cd391b7d0` from first byte using the frozen case-run. No reviewer-authored SCENARIO_ROOT, MANIFEST.sha256, repo-seed, network redirect, environment selector, or mutable external fixture is permitted.

The frozen case-run accepts only the numeric target 103..112. It creates all ephemeral namespace plumbing itself from exact frozen candidate bytes and the immutable recovery-head runner object after exact blob/SHA-256 verification. `bwrap --unshare-all` removes network. The exact loader bytes are unchanged. The frozen Git shim is mounted at the loader-visible `/usr/local/bin/git` and deterministically supplies clone/repository observations for 106..110 without delegating HTTPS clone to network Git. Case 105 uses a non-tmpfs `/dev/shm` bind; case 104 precreates exact ROOT; case 103 removes Codespaces inputs. Cases 111/112 mount the frozen SHA shim at exact `/usr/bin/sha256sum`.

The whole-loader harness mechanically invokes this case-run itself for every 103..112 case and compares observed outer rc/stdout/stderr/control data to the frozen transcript contract. This is `BYTE_IDENTICAL_COMPLETE_LOADER` evidence only.

Production-positive 113 is not synthetic fixture evidence. It is the exact immutable recovery-head object proof plus exact loader static/mechanical binding required by Revision C. 114/success are only `GENERATED_POST_TRUST_BOUNDARY_EQUIVALENT`, with proof-relevant fail()/mark() and boundary bytes mechanically extracted from exact loader source and compared against frozen expected transformation digests. Fallback115 is only `SYNTHETIC_FALLBACK_EQUIVALENT`. Evidence classes are non-interchangeable.

No network, OAuth/device flow, Codespace/live execution, Step4, `--apply`, production/main/ruleset mutation, writer secret, merge, workflow dispatch, or Runtime operation is permitted. Runtime OFF.
