# MULTIVERSE Cross-Chat Capability Convergence v1

Status: OWNER-ADOPTED REPOSITORY PREPARATION / CANONICALLY INTEGRATED / FIXED SHARED-PIPELINE INSTALLATION PENDING.

Purpose

This common operating layer prevents active MULTIVERSE chats from remaining on incompatible old shared procedures after the system improves.

The durable rule is:

Fresh canonical GitHub and the latest adopted common operating baseline outrank chat memory, old handoffs, and locally remembered common procedures.

Domain knowledge is different. Keirin-specific research stays with Keirin. Core-specific implementation context stays with Core. Runtime-specific infrastructure context stays with Runtime. What converges is the shared operating interface.

Durable adoption and canonical integration

Repository preparation was Owner-adopted at Issue #156 and the exact independently reviewed PR #153 lineage was subsequently integrated into canonical main under Issue #158.

Durable integration binding:
- reviewed PR #153 head: `4a1e093690bedd9d3d5d8eebe6cb98493b7e8123`;
- reviewed tree: `c9d747647a693724d22b142547a3c1600b5c6150`;
- canonical merge commit: `8bb7def5a80217a80a7bf8f4ff5901b101afee63`;
- canonical main tree at integration: the same exact reviewed tree;
- repository-preparation adoption decision: #156 / `5564870064`;
- canonical integration completion: #158 / `5564920334`.

This means the repository-preparation operating model is adopted and canonical. It does not mean the fixed shared Buildkite pipeline installation has been proved complete.

Required resume behavior

Every active MULTIVERSE chat must, on resume:

1. Fresh Read canonical GitHub before claiming CURRENT or NOW.
2. Fresh Read convergence state in Issue #93.
3. Read the latest adopted common operating baseline.
4. Replace superseded common procedures with the latest adopted procedure.
5. Preserve domain-specific research state unless a separate domain artifact supersedes it.
6. Never ask the Owner to manually courier common protocol updates between chats.
7. While migration lock `5561567913` remains active, research lanes must not edit shared Independent Lab/Auditor Steps.

Shared review infrastructure

MULTIVERSE Independent Lab and MULTIVERSE Independent Auditor are shared infrastructure.

During dispatcher migration they are single-writer control-plane managed.

Repository preparation and canonical integration are complete. Fixed shared-pipeline installation remains a separate single-writer control-plane action and is not performed by research/Candidate lanes.

After fixed-dispatcher installation is durably proved:
- their pipeline definitions are immutable per review job;
- research chats do not replace Steps;
- a research chat creates a durable machine-readable review request;
- the build checks out the requested Candidate branch/head;
- the fixed dispatcher discovers the exact-current request from GitHub;
- the generic independent runner performs allowlisted checks;
- the lane-specific GitHub App publishes the result;
- Auditor T2 is produced from the exact published Auditor result.

A review request may declare only allowlisted primitives:
- exact GitHub lineage;
- subtree hashes;
- durable comment bindings;
- source contains/not-contains assertions;
- unittest modules and exact counts;
- validator JSON expectations;
- public HTTPS GET JSON expectations;
- public state-changing-method denial;
- normalized evidence digest;
- secret-value persistence scans.

A review request cannot inject arbitrary shell, Buildkite YAML, Python, credentials, merge commands, provider mutation, or Runtime activation.

Cross-chat upgrade behavior

When a newer common baseline is adopted:
- older chats must stop using the superseded common interface on their next Fresh Read;
- they do not need the Owner to paste a migration message;
- their domain work may continue in parallel;
- already valid exact-head evidence remains valid unless its own lineage drifts;
- only the common workflow interface changes.

Migration sequence

- Phase 1 — repository Candidate: COMPLETE via PR #153.
- Phase 2 — Independent Lab -> T1 -> Independent Auditor -> T2 -> Owner repository-preparation adoption: COMPLETE.
- Phase 2.5 — exact reviewed PR #153 canonical-main integration: COMPLETE via #158.
- Phase 3 — one-time fixed Lab/Auditor shared-pipeline installation under single-writer control-plane authority: PENDING OR NOT YET DURABLY VERIFIED COMPLETE.
- Phase 4 — prove a preserved pending review routes from a durable request without any shared-Step editing: PENDING.
- Phase 5 — release the migration lock in Issue #93 and prohibit legacy per-chat Step replacement: PENDING.

Owner workload target

After installation, routine review YAML copy/paste count is zero.

A New Build may still require selecting the Candidate branch until a later automatic-trigger successor is separately reviewed and adopted. That is a future optimization and is not claimed by v1.

Authority ceiling

This adopted repository-preparation baseline and this metadata-sync Candidate grant no shared-pipeline installation/mutation, merge, canonical main mutation, ruleset mutation, workflow dispatch/rerun, provider mutation, Runtime activation, production, protected-data access, live business effect, or spend.

Runtime remains OFF.

Request identity and same-head supersession

The exact Git head/tree is necessary but not sufficient to identify a review job. Every selected request has a canonical JSON SHA256 that is carried through the dispatcher job, result marker, durable review artifact, publisher receipt, and Auditor/T2 chain.

For one exact lane/repo/PR/head/tree/base/main key:
- the first request has no predecessor digest;
- a later request is valid only when `supersedes_request_sha256` equals the canonical SHA256 of the immediately prior exact request;
- an unchained same-head replacement fails closed;
- an Auditor request binds the exact upstream Lab request SHA256, and T1 also binds that digest.

This preserves newest-exact-current selection while preventing silent same-head recipe replacement or replay.
