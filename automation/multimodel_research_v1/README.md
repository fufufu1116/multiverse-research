# MULTIVERSE Multi-Model Research Federation Phase A v1

Status: CANDIDATE / REPOSITORY-ONLY / NO LIVE PROVIDERS.

Purpose

Create a provider-neutral advisory research layer for external or synthetic research models without granting them adoption or Runtime authority.

Phase A contains:

- strict research task schema;
- strict research result schema;
- explicit task-to-result binding;
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
- any incremental spend.

Task boundary

Tasks contain declarative objectives and allowlisted evidence primitives. They do not contain executable shell/YAML/Python/credential fields.

Results contain:
- explicit model identity;
- exact task/snapshot binding;
- a role that must have been requested by the task;
- evidence primitives constrained by the task allowlist;
- task-bound finding-count and serialized-output budgets;
- SOURCE_REF evidence bound to the task-declared source/digest;
- status;
- structured findings;
- evidence references;
- confidence and uncertainty;
- recommendation;
- validation plan;
- explicit nonauthority.

Consensus

Consensus is descriptive only.

The aggregator may report support-only, oppose-only, unknown-only, or divergent claim groups.

A majority never confers truth or adoption authority.

Aggregate inputs are bound to one exact task/snapshot. One provider/model/role identity contributes at most one distinct result to a task: exact retry duplicates are acknowledged, while conflicting resubmissions from the same identity fail closed. This prevents one advisory identity from inflating descriptive position counts.

Any support/oppose disagreement is retained as UNRESOLVED_DIVERGENCE and routed conceptually to a MECHANICAL_FALSIFICATION_TASK.

Infrastructure failures

INFRA_FAILURE is distinct from FIX_REQUIRED.

An infrastructure error must not be misreported as a Candidate defect.

But an incomplete review cannot become authoritative PASS.

All non-COMPLETED advisory outcomes are preserved in aggregate metadata. INFRA_FAILURE remains separately indexed, while UNSUPPORTED and REFUSED are not silently dropped.

Authority ceiling

No live provider execution, credentials, spend, merge/main/ruleset mutation, workflow dispatch/rerun, Runtime activation, provider effect, production, protected data, or live business effect.

Runtime remains OFF.
