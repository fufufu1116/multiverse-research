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

Execution-time attestation binding

`MULTIVERSE_EXECUTION_TIME_ATTESTATION_v1` represents a time observation produced by the later Control execution boundary. Repository validation requires its source to be `CONTROL_RUNTIME_CLOCK`, binds a source-observation SHA256, and limits recording delay to 60 seconds.

`MULTIVERSE_CATALOG_FRESHNESS_TIME_BINDING_v1` requires the catalog freshness receipt's `checked_at` to exactly equal the attested Control-runtime time.

This prevents a later live preparation from making an old catalog appear fresh merely by supplying an arbitrary earlier checked_at value.

The repository contract does not prove that a clock source is trustworthy by itself. Trust in the source must come from the separately authorized Control execution boundary. The attestation and binding grant no provider-call, credential, spend, live-execution, adoption, or Runtime authority.

Provider pre-execution evidence bundle

`MULTIVERSE_PROVIDER_PRE_EXECUTION_BUNDLE_v1` closes a repository-side generation-mixing gap immediately before any separately authorized provider call.

It binds one exact chain:
- frozen pre-live Candidate head and seal blob;
- one exact first-provider pilot dry-run plan;
- one exact provider/model catalog snapshot;
- one exact catalog freshness receipt;
- one exact pilot/freshness binding;
- one exact Control-runtime time attestation;
- one exact catalog-freshness/time binding.

The bundle fails closed if a valid object from a different Candidate head, seal, provider/model, catalog generation, or attested check time is mixed into the chain.

The bundle is evidence only. It keeps provider-call, credential, spend, live-execution, adoption, and Runtime authority false/OFF. Trust in `CONTROL_RUNTIME_CLOCK` still comes only from a separately authorized Control execution boundary.

Catalog freshness guard

`MULTIVERSE_PROVIDER_CATALOG_FRESHNESS_v1` requires the provider/model/pricing snapshot used for a later live call to have been checked within the previous 24 hours.

It fails closed if:
- the check time is before the snapshot time;
- the snapshot is older than 24 hours;
- the configured freshness window is wider than 24 hours;
- an explicit provider pricing-valid-through date has expired;
- the snapshot contents change after the freshness receipt was made.

`MULTIVERSE_FIRST_PROVIDER_PILOT_FRESHNESS_BINDING_v1` binds one exact pilot dry-run plan to one exact fresh-catalog receipt.

Freshness never authorizes the provider call, credentials, spend, or live execution. Runtime remains OFF.

If the 24-hour window has elapsed, official provider information must be observed again and a new dated snapshot/freshness receipt produced before later live transport preparation.

First-provider pilot dry-run plan

`MULTIVERSE_FIRST_PROVIDER_PILOT_DRY_RUN_v1` is a repository-only preparation object for the later, separately authorized Phase B first-provider pilot.

It binds:
- exact frozen pre-live Candidate head and seal blob;
- exact dated provider catalog snapshot SHA256;
- exact selected provider/model catalog entry;
- exactly one provider, one planned call, and one attempt;
- exact input/output token ceilings;
- exact catalog-derived maximum cost estimate;
- synthetic-only data;
- JSON-only output.

It explicitly requires provider-call, credential, and spend authority while keeping all three authorization fields false.

It also requires:
- no network execution in repository;
- no credential material in repository;
- live_execution_performed = false;
- Runtime OFF;
- adoption_authority = false.

`build_pilot_candidate_matrix` exposes both current bounded candidates for comparison without selecting either one and without creating selection or spend authority.

This dry-run object is advisory research only. It is not an Owner Gate, machine review request, provider call, credential grant, or spend authorization.

Dated provider model catalog snapshot

`PROVIDER_MODEL_CATALOG_SNAPSHOT_20260908.json` records the official-provider facts used to choose bounded first-smoke candidates on 2026-09-08.

Smoke candidates:
- Google Gemini: `gemini-3.8-flash` — stable/GA, structured JSON supported.
- Anthropic Claude: `claude-haiku-4-5-20251001` — pinned dated model ID, structured JSON supported.

The snapshot stores price rates as integer USD micro-units per million tokens and official documentation references.

At the first-smoke ceilings of 32768 input tokens and 4096 output tokens:
- Gemini 3.8 Flash estimated maximum token charge: USD 0.039936 under the observed introductory rates.
- Claude Haiku 4.5 estimated maximum token charge: USD 0.053248 under the observed current rates.

These are repository-side estimates, not spend authorization and not a bill prediction. Provider pricing may change, so a live execution must Fresh-check pricing and authority before transport.

Live provider readiness report

`MULTIVERSE_LIVE_PROVIDER_READINESS_REPORT_v1` converts the fully validated repository-side preparation chain into one explicit readiness state:

`READY_FOR_SEPARATE_PROVIDER_AUTHORITY`

A readiness report means the repository contract is ready for a separately authorized smoke call. It explicitly records:
- repository_contract_ready = true;
- provider_call_authorized = false;
- credential_authorized = false;
- spend_authorized = false;
- live_execution_performed = false;
- Runtime = OFF;
- adoption_authority = false.

The report binds the exact smoke-profile SHA, provider-transport-binding SHA, and execution-preparation SHA.

Any attempt to turn one of the authority/execution fields true inside the repository report fails closed.

Live execution preparation guard

`MULTIVERSE_LIVE_PROVIDER_EXECUTION_PREP_v1` is the last repository-only guard before an actual provider call.

It binds the exact smoke profile and exact provider transport binding, then constrains the proposed first call to:
- one exact provider host;
- one exact provider operation;
- provider-API-only network scope;
- external credential handle reference only;
- no credential material in the repository;
- exactly one attempt;
- input token ceiling <= 32768;
- output token ceiling <= 4096;
- proposed cost ceiling <= USD 1.00;
- Runtime OFF;
- no live business effect;
- no protected data.

Provider targets:
- Google Gemini -> `generativelanguage.googleapis.com`, stable-v1 interaction creation;
- Anthropic Claude -> `api.anthropic.com`, Messages v1 creation.

The preparation object explicitly requires separate provider-call, credential, and spend authority. It cannot grant those authorities itself.

Validator distinction:
- credential identifiers and network-client execution markers remain forbidden;
- provider hostnames may appear only as declarative allowlist data in the execution-preparation guard, tests, validator, or documentation;
- provider adapters/bindings remain renderer/parser-only and contain no provider hostname transport target or network client invocation.

Provider observation binding

`MULTIVERSE_PROVIDER_OBSERVATION_BINDING_v1` closes the receive-side repository gap between a provider-specific parsed observation and the durable termination/receipt records.

For Gemini and Claude it requires exact equality for:
- provider response ID;
- normalized termination state;
- input/output usage counts;
- exact usage metadata SHA256;
- exact provider response SHA256;
- exact observed model ID.

The binding first validates the termination record and execution receipt, then proves that the provider parser observation is the same execution represented by those durable records.

For `LIVE_PROVIDER_ID_UNVERIFIED`, model drift may be preserved, but the observation and receipt must still carry the same exact observed model ID. Unverified does not mean unbound.

This layer performs no provider call and grants no authority.

Provider transport binding

`MULTIVERSE_PROVIDER_TRANSPORT_BINDING_v1` closes the repository-side gap between the abstract request envelope and the exact provider-specific payload.

For Gemini and Claude it:
- re-renders the exact provider request from the validated task/assignment/policies/prompt/schema;
- requires the supplied render object to match that exact renderer output;
- requires no credential material in the render;
- computes SHA256 over the exact provider request body;
- requires that SHA256 to equal `REQUEST_ENVELOPE.outbound_payload_sha256`;
- binds the exact request-envelope SHA and exact render SHA.

This lets the repository prove that the payload sealed in the request envelope is exactly the payload prepared for provider transport, without performing the transport itself.

Cross-provider tests additionally prove that Gemini and Claude receive the same exact canonical provider-neutral prompt bytes and the same exact response schema, even though their API wrappers differ.

Provider transport binding still authorizes no network call or credential use.

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
