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

For `SOURCE_REF` and `PUBLIC_EVIDENCE_REF`, TASK_v2 also validates at task-creation time that the manifest ref exists in `source_refs`, has a non-null source digest, and carries the exact same digest. This prevents an internally inconsistent task from being sent to an advisory provider.

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

Assignment / Result v2 boundary

`MULTIVERSE_RESEARCH_ASSIGNMENT_v1` binds one exact TASK_v2 to one advisory target:
- exact task SHA256 and snapshot;
- exact provider/model/role;
- exact adapter digest;
- assignment creation time;
- execution mode;
- research-network ceiling;
- provider transport policy reference;
- compute/output ceilings that may narrow but never widen the task;
- attestation requirement;
- explicit nonauthority.

TASK_v1 cannot be assigned under this contract.

`SYNTHETIC_OFFLINE` forbids provider transport and live attestation.

`LIVE_ADVISORY` is only a declarative repository contract at this stage. It requires an explicit provider-transport policy reference and attestation requirement, but this package still performs no live provider execution.

`MULTIVERSE_RESEARCH_RESULT_v2` adds exact assignment SHA256 binding. Result provider/model/role must match the exact assignment, and the result cannot predate assignment creation.

Historical RESULT_v1 validation remains unchanged.

Model target policy

`MULTIVERSE_MODEL_TARGET_POLICY_v1` validates the exact model target for one Assignment v1 before any live provider transport is permitted by later layers.

The first-pilot profile accepts only `PINNED_OR_STABLE` model classification. Alias, preview, experimental, and unknown classifications fail closed.

The classification must carry an exact evidence reference and SHA256. This package does not infer provider model stability from a model-name string alone.

The policy requires:
- alias_allowed = false;
- preview_allowed = false;
- experimental_allowed = false;
- resolved_model_id_required = true;
- stable_provider_api_required = true.

Observed provider model identity must exactly match the requested model ID under this first-pilot contract.

Model-target policy proves only target/provenance constraints. It does not prove truth, model quality, or fully reproducible provider serving infrastructure.

Claude Messages offline transport adapter

The repository also includes a **credential-free, network-free renderer/parser** for Anthropic Claude Messages.

The renderer binds:
- exact assignment model;
- exact canonical provider-neutral prompt JSON;
- exact JSON response schema through `output_config.format.type = json_schema`;
- fixed first-smoke max_tokens;
- stream = false;
- no tools or MCP servers;
- no credential material.

The Claude Messages API is treated as stateless: the full canonical prompt is sent in the user message for the bounded single-turn smoke.

The parser preserves:
- provider message ID;
- observed model ID;
- native stop reason;
- normalized termination state;
- output text;
- input/output tokens;
- exact usage metadata SHA256;
- exact raw response SHA256.

Bounded stop normalization:
- end_turn + text -> COMPLETED;
- end_turn + empty -> PROVIDER_EMPTY;
- refusal or refusal stop details -> PROVIDER_REFUSED;
- max_tokens / model_context_window_exceeded / stop_sequence -> PROVIDER_TRUNCATED;
- tool_use / pause_turn -> fail closed because the first-pilot capability policy forbids tool execution.

If provider usage metadata reports any nonzero server-tool execution, parsing fails closed.

This adapter performs no API call and contains no credential value or credential transport implementation.

Gemini stable-v1 offline transport adapter

The repository includes a **credential-free, network-free renderer/parser** for the first Google Gemini smoke candidate.

The renderer targets the stable Gemini Interactions API v1 surface and binds:
- exact assignment model;
- exact canonical provider-neutral prompt JSON;
- exact JSON response schema;
- api_version = v1;
- store = false;
- stream = false;
- background = false;
- no tools field;
- fixed first-smoke max output token ceiling;
- no credential material.

The parser preserves:
- provider response ID;
- observed model ID;
- native terminal status;
- normalized termination state;
- output text;
- input/output token counts;
- exact usage metadata SHA256;
- exact raw provider response SHA256.

Current Gemini status normalization for the bounded unary smoke profile:
- completed + text -> COMPLETED;
- completed + empty output -> PROVIDER_EMPTY;
- incomplete -> PROVIDER_TRUNCATED;
- failed/cancelled -> TRANSPORT_FAILURE;
- in_progress/requires_action -> reject as nonterminal.

The parser deliberately preserves observed model drift rather than silently rewriting it; the execution receipt/model-target validator is responsible for fail-closing a LIVE_ATTESTED mismatch.

This adapter performs no API call and contains no credential value or credential transport implementation.

Minimum live-provider smoke profile

`MULTIVERSE_LIVE_PROVIDER_SMOKE_PROFILE_v1` binds the exact repository-side chain for the first separately authorized provider call.

The profile requires:
- exactly one provider;
- exactly one assignment;
- exactly one attempt;
- synthetic-only data;
- JSON-only structured output;
- non-streaming;
- no protected data;
- no live business effect;
- no Runtime activation;
- no adoption authority.

It binds the exact fanout plan, assignment, model-target policy, capability policy, and request envelope.

The repository test suite includes an end-to-end **contract simulation** that validates the entire chain through an unverified receipt without making any real provider API call. It must not be interpreted as live-provider proof or identity attestation.

Actual provider transport remains a separate authority boundary.

Termination normalization and execution receipt

`MULTIVERSE_PROVIDER_TERMINATION_RECORD_v1` normalizes provider-native completion outcomes while preserving the provider-native reason, response identifier when available, usage counts, exact usage-metadata digest, and response-received time.

Normalized states:
- COMPLETED;
- PROVIDER_REFUSED;
- PROVIDER_BLOCKED;
- PROVIDER_TRUNCATED;
- PROVIDER_EMPTY;
- TRANSPORT_FAILURE.

Transport failure may legitimately have no provider response ID. Other normalized states require one.

`MULTIVERSE_PROVIDER_EXECUTION_RECEIPT_v1` binds the complete execution chain:
- exact task;
- exact assignment;
- exact request envelope;
- exact termination record;
- exact submission ID;
- observed provider/model identity;
- provider response ID and response-content SHA256;
- exact final RESULT_v2 SHA256;
- exact adapter SHA256;
- monotonic request/response/result/receipt timestamps;
- attestation state.

`LIVE_ATTESTED` requires the observed model ID to match the exact requested stable/pinned model target. `LIVE_PROVIDER_ID_UNVERIFIED` may preserve an advisory response but explicitly does not authenticate the provider model identity.

Termination-to-result mapping is fail-closed. Refusal/block maps to REFUSED; truncation/empty/transport failure maps to INFRA_FAILURE; only completed provider termination can map to COMPLETED.

Receipt binding proves execution provenance only. It grants no truth or adoption authority.

Provider-neutral prompt and request envelope

`MULTIVERSE_PROVIDER_NEUTRAL_PROMPT_v1` contains no provider/model target. The same exact TASK_v2 + requested role + response-schema digest produces the same canonical research prompt regardless of which provider/model assignment receives it.

The prompt binds:
- exact task SHA256;
- exact snapshot;
- exact requested role;
- exact objective;
- deterministic evidence-manifest view;
- exact response-schema SHA256;
- explicit nonauthority.

`MULTIVERSE_PROVIDER_REQUEST_ENVELOPE_v1` is the first live-transport preparation contract. It requires a LIVE_ADVISORY Assignment but performs no provider call itself.

The envelope binds:
- exact task and assignment;
- exact model-target policy;
- exact capability policy;
- exact provider-neutral prompt;
- exact provider transport policy reference;
- exact outbound payload SHA256;
- first-smoke synthetic-only objective/egress classification;
- classification evidence reference and SHA256;
- exact egress evidence set equal to the task evidence manifest.

The first smoke profile rejects non-synthetic objective/egress declarations. Classification is itself a bound provenance assertion; this repository layer does not independently inspect semantic data sensitivity.

Provider capability policy

`MULTIVERSE_PROVIDER_CAPABILITY_POLICY_v1` binds the exact Assignment v1 and exact Model Target Policy v1 to the first-pilot capability ceiling.

The first-pilot capability profile requires:
- tools = NONE;
- provider retrieval/search = NONE;
- code execution = NONE;
- file access = NONE;
- provider memory = NONE;
- function calling = NONE;
- structured output = JSON_ONLY;
- streaming = false.

The policy is repository-only. It authorizes no provider call by itself.

Any change to the bound model-target policy changes the capability binding and invalidates a stale capability policy.

Fanout plan / batch completeness

`MULTIVERSE_RESEARCH_FANOUT_PLAN_v1` is validated against the exact Assignment v1 objects it plans. It does not accept opaque hashes without assignment validation.

The plan binds one exact task/snapshot to a canonical sorted set of exact assignment SHA256 values.

Fanout v1 fails closed on:
- duplicate assignment IDs;
- duplicate assignment SHA256 values;
- duplicate logical provider/model/role targets;
- plan/assignment-set mismatch;
- plan creation before any included assignment.

The same provider/model may be assigned different requested roles; those are distinct advisory identities but remain one provider/model for Aggregate v2 diversity accounting.

`MULTIVERSE_RESEARCH_BATCH_SUMMARY_v1` distinguishes:
- planned assignments;
- observed terminal results;
- completed assignments;
- noncompleted observed assignments;
- exact missing assignment SHA256 values.

An INFRA_FAILURE/REFUSED/UNSUPPORTED result counts as observed but never as completed. An unplanned result or a second result for the same assignment fails closed.

Batch completeness is descriptive only and grants no adoption authority.

Consensus

Consensus is descriptive only.

Aggregate v2 diversity accounting

`MULTIVERSE_RESEARCH_AGGREGATE_v1` remains unchanged for historical compatibility.

`MULTIVERSE_RESEARCH_AGGREGATE_v2` adds explicit diversity accounting without treating provider/model/role advisory identities as independent models.

Aggregate v2 separates observed from completed diversity:
- observed/completed provider-model-role advisory identities;
- observed/completed provider-model identities;
- observed/completed providers.

A non-COMPLETED advisory result may increase observed coverage but never completed research diversity.

At claim level, Aggregate v2 separates:
- advisory identity position counts;
- provider/model position-presence counts;
- provider position-presence counts;
- role-conditioned divergence inside one provider/model;
- cross-model divergence;
- cross-provider divergence.

Position-presence counts are not votes and may overlap when one provider/model takes different positions in different requested roles.

The historical descriptive label remains advisory-identity scoped. Aggregate v2 explicitly records `descriptive_label_scope = ADVISORY_IDENTITY`.


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
