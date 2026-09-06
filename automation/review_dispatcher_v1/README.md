# MULTIVERSE Immutable Review Dispatcher v1

Status: CANDIDATE / NONCANONICAL.

Goal

Replace per-review editing of the shared Buildkite Steps with a fixed dispatcher.

The dispatcher uses the checked-out Buildkite commit to find exactly one open PR, then scans that PR for the newest exact-current machine-readable request for the requested lane.

Request marker

The comment contains the literal marker:

<!-- MULTIVERSE_REVIEW_REQUEST_V1 -->

followed by one JSON object using schema MULTIVERSE_REVIEW_REQUEST_v1.

The request binds:
- lane;
- repo;
- PR;
- head;
- tree;
- base;
- canonical main;
- proof ceiling;
- execution state;
- declarative recipe;
- explicit nonauthority.

The dispatcher rejects stale main/head/tree/base bindings, multiple exact open PRs, missing requests, and duplicate current results.

Security / independence boundary

The request is declarative. It cannot contain arbitrary shell, YAML, Python, tokens, passwords, credentials, or private keys.

The audit/review step receives no Lab/Auditor GitHub App private key and no DATABASE_URL.

The publisher step skips Candidate checkout, receives only the lane-specific GitHub App private key, and independently fetches the exact canonical dispatcher ref from Fresh canonical main. It does not execute a dispatcher bundle produced by the Candidate audit step.

The Auditor T2 step also skips Candidate checkout, independently fetches the same exact canonical dispatcher ref, verifies the freshly published exact Auditor artifact, rechecks upstream Lab/T1 binding, then publishes T2 using the Auditor identity.

Fixed pipeline installation

The files under buildkite/review_dispatcher_v1 are installation templates.

They intentionally contain no job-specific PR, head, tree, endpoint, evidence digest, or request comment constants.

After the dispatcher is separately reviewed/adopted and merged into canonical main, each shared Buildkite pipeline is installed once.

Each secret-free audit step fetches dispatcher code from origin/main, while the Candidate checkout remains the branch/head being judged. Each later secret-bearing publisher/T2 step independently fetches Fresh canonical main and requires that ref to equal the job-bound dispatcher_ref. No executable dispatcher artifact crosses from Candidate execution into a secret-bearing step.

PUBLIC_HTTP_NO_EFFECT requests additionally fail closed on URL userinfo/query/fragment injection, DNS resolution to private/special addresses, proxy use, and redirects. This prevents the public-HTTP review primitive from silently crossing into a private target boundary.

Concurrency

Different Candidate branches may run concurrent builds on the same fixed pipeline because the pipeline definition is not mutated. Each build discovers only the machine-readable request bound to its own exact checked-out head.

Proof ceiling

This proves a mechanically separated, immutable shared dispatch interface when independently reviewed and installed. It does not prove independent human or organizational ownership.

No merge, main/ruleset mutation, workflow dispatch/rerun, Runtime activation, provider mutation, production, protected data, live effect, or spend authority is included.

Round-3 fail-closed boundaries:
- Auditor upstream must bind the newest exact-current Owner-authored Lab request and its single authentic Lab-App result; an older same-head Lab PASS is not sufficient.
- Candidate source/validator/secret-scan files may not traverse symlinks or escape the exact checkout.
- Candidate unittest/validator subprocesses receive a minimal sanitized environment and are run in a dedicated process group that is terminated after completion.
- PUBLIC_HTTP_NO_EFFECT resolves public addresses first and connects directly to one of those validated IPs while TLS authenticates the original hostname; no second DNS resolution is used for the reviewed connection.
