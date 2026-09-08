# MULTIVERSE Multi-Model Research Federation Phase A v1

Status: CANDIDATE / REPOSITORY-ONLY / NO LIVE PROVIDERS.

Purpose

Create a provider-neutral advisory research layer for external or synthetic research models without granting them adoption or Runtime authority.

Phase A contains:

- strict research task schema with UTC creation/source-observation provenance and source-observed-before-task ordering;
- strict research result schema with UTC production provenance and result-produced-after-task ordering;
- explicit canonical task-SHA256-to-result binding;
- task-scoped role/evidence/finding-count/output-size enforcement;
- explicit resource/network constraints;
- synthetic offline adapter;
- exact-result idempotent duplicate acknowledgement;
- claim-level disagreement preservation;
- unresolved divergence routing to mechanical falsification tasks;
- descriptive consensus labels only;
- no vote/majority adoption authority;
- separate PASS / FIX_REQUIRED / INFRA_FAILURE outcome classification;
- fail-closed tests.

Important separation

Research duplicate semantics and governance duplicate semantics are intentionally different.

Advisory research:
- exact duplicate content may be acknowledged idempotently;
- duplicate research evidence may strengthen descriptive convergence;
- minority/contrarian findings remain visible.

Independent Lab / Auditor:
- authoritative exact-current result uniqueness remains fail-closed;
- an advisory majority can never create adoption authority.

Provider boundary

This Phase A Candidate makes no network/API call to Gemini, Claude, Anthropic, Google, or any other external model provider.

It stores no provider credential and contains no live provider adapter.

A future Phase B requires separate authority for:
- actual provider API use;
- provider credentials;
- any incremental spend;
- mechanically authenticated/attested provider-model identity outside the advisory result payload.

Phase A model identity is declarative metadata only. It is not proof that a live external provider actually produced the payload.

Task boundary

Tasks contain declarative objectives and allowlisted evidence primitives. They do not contain executable shell/YAML/Python/credential fields.

Task v2 evidence manifest hardening

This research draft adds `MULTIVERSE_RESEARCH_TASK_v2` while preserving the historical v1 contract unchanged.

TASK_v2 adds an explicit `evidence_manifest`. Each manifest entry binds:
- exact evidence primitive;
- exact ref;
- required non-null SHA256;
- strict UTC observed_at not after task creation.

For TASK_v2, an allowed primitive type alone is not evidence authorization. Every COMPLETED finding must match one exact task-manifest `(primitive, ref, sha256)` entry. Undeclared refs, primitive substitution, null digests, and digest drift fail closed.

TASK_v1 remains historical/synthetic compatibility only and is not silently reinterpreted. Any future live-provider Phase B work must use TASK_v2 or a stronger later contract plus separate provider assignment/attestation boundaries.

Results contain:
- explicit model identity;
- exact task/snapshot binding plus canonical task SHA256;
- strict UTC produced_at provenance;
- a role that must have been requested by the task;
- evidence primitives constrained by the task allowlist;
- task-bound finding-count and serialized-output budgets;
- SOURCE_REF / PUBLIC_EVIDENCE_REF evidence must be task-declared and carry the exact task-declared source digest;
- status;
- structured findings;
- evidence references;
- confidence and uncertainty;
- recommendation;
- validation plan;
- explicit nonauthority.

Consensus

Consensus is descriptive only.

The aggregator may report support-only, oppose-only, support-with-unknown, oppose-with-unknown, unknown-only, or divergent claim groups. UNKNOWN participation is never hidden behind an *ONLY* label.

A majority never confers truth or adoption authority.

Aggregate inputs are bound to one exact task/snapshot/task SHA256. One provider/model/role identity contributes at most one distinct result to a task: exact retry duplicates are acknowledged, while conflicting resubmissions from the same identity fail closed. Within that result, duplicate claim_key entries are rejected, so one identity contributes at most one position to each exact claim key. Claim and noncompleted aggregate entries retain produced_at and result-content-digest provenance.

Aggregation is deterministic over the same logical result multiset: canonical duplicate representatives, duplicate acknowledgements, advisory identities, claim-position entries, and noncompleted entries are ordered independently of caller input order. This keeps aggregate_sha256 reproducible. submission_id is unique within one exact task aggregate, so durable result references cannot alias across advisory identities.

Requested-role coverage is explicit. The aggregate reports per-role unique/completed/noncompleted counts, missing_requested_roles, roles_without_completed_result, requested_role_coverage_complete, and requested_role_completed_coverage_complete. A descriptive claim label never implies that all requested research roles were observed or completed.

Any support/oppose disagreement is retained as UNRESOLVED_DIVERGENCE and routed conceptually to a MECHANICAL_FALSIFICATION_TASK.

Infrastructure failures

INFRA_FAILURE is distinct from FIX_REQUIRED.

An infrastructure error must not be misreported as a Candidate defect.

But an incomplete review cannot become authoritative PASS.

All non-COMPLETED advisory outcomes require an explicit uncertainty/reason, are preserved in aggregate metadata, and contribute to explicit status_counts coverage. INFRA_FAILURE remains separately indexed, while UNSUPPORTED and REFUSED are not silently dropped.

Review routing baseline

The common review interface is the fixed request-only dispatcher baseline activated on Issue #93.

For this Candidate:
- shared Independent Lab / Auditor Steps remain fixed common infrastructure;
- per-job shared Steps replacement is prohibited;
- review is requested through durable machine-readable GitHub metadata;
- exact same-envelope request replacement must follow the immediate-predecessor SHA256 chain;
- Lab -> T1 -> Auditor -> T2 remains separate from adoption authority.

This section changes no Phase A research logic and grants no Build/Retry or adoption authority.

Authority ceiling

No live provider execution, credentials, spend, merge/main/ruleset mutation, workflow dispatch/rerun, Runtime activation, provider effect, production, protected data, or live business effect.

Runtime remains OFF.
