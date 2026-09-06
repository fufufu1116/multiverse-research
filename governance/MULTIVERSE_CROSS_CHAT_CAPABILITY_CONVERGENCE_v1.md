# MULTIVERSE Cross-Chat Capability Convergence v1

Status: CANDIDATE / NOT YET ADOPTED.

Purpose

This common operating layer prevents active MULTIVERSE chats from remaining on incompatible old shared procedures after the system improves.

The durable rule is:

Fresh canonical GitHub and the latest adopted common operating baseline outrank chat memory, old handoffs, and locally remembered common procedures.

Domain knowledge is different. Keirin-specific research stays with Keirin. Core-specific implementation context stays with Core. Runtime-specific infrastructure context stays with Runtime. What converges is the shared operating interface.

Required resume behavior

Every active MULTIVERSE chat must, on resume:

1. Fresh Read canonical GitHub before claiming CURRENT or NOW.
2. Fresh Read convergence state in Issue #93.
3. Read the latest adopted common operating baseline.
4. Replace superseded common procedures with the latest adopted procedure.
5. Preserve domain-specific research state unless a separate domain artifact supersedes it.
6. Never ask the Owner to manually courier common protocol updates between chats.

Shared review infrastructure

MULTIVERSE Independent Lab and MULTIVERSE Independent Auditor are shared infrastructure.

During dispatcher migration they are single-writer control-plane managed.

After fixed-dispatcher installation:
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

Phase 1: repository Candidate.
Phase 2: Independent Lab -> T1 -> Independent Auditor -> T2 -> Owner adoption.
Phase 3: separate one-time authority to install the fixed Lab and Auditor pipeline definitions.
Phase 4: prove a preserved pending review (PR148 LIVE evidence is the planned first target) routes without editing Steps.
Phase 5: release the migration lock in Issue #93 and prohibit legacy per-chat Step replacement.

Owner workload target

After installation, routine review YAML copy/paste count is zero.

A New Build may still require selecting the Candidate branch until a later automatic-trigger successor is separately reviewed and adopted. That is a future optimization and is not claimed by v1.

Authority ceiling

This Candidate grants no merge, canonical main mutation, ruleset mutation, workflow dispatch/rerun, provider mutation, Runtime activation, production, protected-data access, live business effect, or spend.

Runtime remains OFF.
