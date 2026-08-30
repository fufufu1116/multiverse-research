# v19.7.16 Whole-Loader Fixture Protocol v2

Status: REVIEW-ONLY / NONLIVE / NONCANONICAL.

Independent Lab must execute the complete exact loader blob `396c5f99c8837b4bc946a76effe1e19cd391b7d0` from its first byte in an isolated Linux namespace. The loader bytes MUST NOT be edited, split, copied into fragments, or have fail()/gate control flow replaced.

Scenario selection MUST NOT depend on an environment variable surviving the loader's `/usr/bin/env -i` boundaries. Instead, the isolated namespace supplies a scenario-specific filesystem image before loader entry. Each image controls only external observations made by the unchanged loader: Codespaces marker visibility, pre-existing paths, `/dev/shm` trust properties, Git command results/repository objects, sha256sum behavior, runner parseability, and a synthetic runner boundary. The selected scenario is therefore encoded in immutable fixture filesystem bytes/metadata, not runtime environment propagation.

For each 103..113 case, execute the unchanged complete loader and record exact stdout lines, stderr lines, outer status, child invocation count and retry count. For 114, synthetic child must run once, emit exactly `SYNTHETIC_CHILD_STDOUT` and `SYNTHETIC_CHILD_STDERR`, return nonzero, and outer loader must emit RUNNER_RETURN and return 114. For success, child runs once and returns zero. Fallback 115 must be tested through a review-only complete-source equivalent whose only difference is one unknown marker at a real fail callsite; this case must be explicitly identified as fallback synthetic evidence and must never be represented as byte-identical production loader execution.

The exact expected transcript contract is frozen in `MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_16_WHOLE_LOADER_MATRIX_EVIDENCE_V2_20260830.json`; the harness mechanically validates it. Independent Lab remains responsible for reproducing the cases rather than trusting Core-authored expected records.

No network, OAuth/device flow, production mutation, Step4, `--apply`, writer secret, merge, workflow dispatch, or Runtime operation is permitted by this protocol. Runtime OFF.
