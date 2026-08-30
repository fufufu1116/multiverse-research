# v19.7.16 executable-v2 — Independent Lab re-review binding

Status: NONCANONICAL / REVIEW ONLY / NO LIVE AUTHORITY.

Prior Lab FIX_REQUIRED: PR #74 comment 5466434776.
Review the branch exact head produced by this binding commit and its exact tree via GitHub Fresh Read; do not infer CURRENT from this document.

Remediation intent:
1. whole-loader transcript assertions are now mechanical in the harness and require a separately reproduced Lab transcript bundle; Core-authored contract alone cannot PASS;
2. scenario selection no longer relies on selector variables surviving env -i; fixture protocol requires scenario-specific filesystem images selected before complete-loader entry;
3. case-run is aligned to that filesystem-image protocol and rejects unsupported byte-identical fallback115 representation;
4. consolidated diagnostic chain, case-run, fixture protocol, matrix contract, harness, immutable dependency proof and freeze are all members of the exact review unit;
5. immutable recovery-head runner remains dependency truth, not candidate-branch runner copy.

Independent Lab must Fresh Read and independently determine whether the architecture actually satisfies Revision B. It must not treat this binding as proof.

No Codespace/live/OAuth/device flow, Step4, --apply, production/main/ruleset mutation, writer secret, merge, workflow dispatch, Runtime operation or activation authorized. Runtime OFF.
