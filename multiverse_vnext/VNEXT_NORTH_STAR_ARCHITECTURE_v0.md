# MULTIVERSE vNext — North Star Architecture v0

Status: WORKING_ARCHITECTURE_CANDIDATE — NOT_CONSTITUTION — NOT_ACCEPTED  
Owner Directive: MULTIVERSE NORTH STAR / ARCHITECTURE CLOSURE  
North Star: **Owner-governed, evidence-grounded, recoverable, self-improving autonomous operating system.**

## 0. Architecture Closure Rule

This document defines a durable logical architecture, not a frozen list of vendors or features.

A new AI, tool, source, security technique, workflow, or idea MUST first be classified as one of:
- `MODULE_CANDIDATE`
- `PROVIDER_ADAPTER_CANDIDATE`
- `SOURCE_ADAPTER_CANDIDATE`
- `UPGRADE_CANDIDATE`
- `IDENTITY_OR_CONSTITUTION_CHANGE_CANDIDATE`

If the proposal fits an existing module/adapter boundary without changing a Multiverse invariant, Architecture Closure remains intact.  
"New technology exists" is not evidence that the architecture was incomplete.

A current version may be declared done when its explicit Definition of Done is satisfied. Future improvements are queued as `NEXT_VERSION_CANDIDATE`; they do not keep the current version permanently unfinished.

## 1. Owner / System Boundary

### Owner

The Owner retains:
- purpose and values;
- risk tolerance;
- constitutional changes;
- material irreversible decisions;
- protected-data/holdout gates;
- new-spend gates where governance requires;
- final approval where the permission model requires human authorization.

The Owner is **not** the routine router, researcher, file clerk, reviewer, recovery operator, or integration engineer.

### Multiverse

Subject to permission, evidence, audit and recovery controls, Multiverse should progressively own:
- information discovery;
- source/evidence normalization;
- knowledge formation;
- memory/state management;
- planning and reasoning;
- execution;
- verification and falsification;
- independent audit routing;
- provenance and evidence management;
- version/change management;
- security and recovery;
- AI/provider coordination;
- resource/cost optimization;
- opportunity discovery;
- self-observation;
- self-improvement.

## 2. Multiverse Identity Invariants

These are provider-independent identity candidates. A tool swap alone MUST NOT change them.

1. `OWNER_SOVEREIGNTY`
2. `EVIDENCE_BEFORE_CONFIDENCE`
3. `PROVENANCE`
4. `FAIL_CLOSED`
5. `REPRODUCIBILITY`
6. `RECOVERABILITY`
7. `ROLE_SEPARATION`
8. `REVERSIBILITY`
9. `PORTABILITY`
10. `LEAST_OWNER_BURDEN`
11. `COST_AWARENESS`
12. `CONTINUOUS_EVOLUTION`

Interpretation:
- Continuous evolution means controlled change, not perpetual incompleteness.
- Owner sovereignty means final authority, not routine manual operation.
- Evidence before confidence means uncertainty may remain explicit (`UNKNOWN`, `STALE`, `OFFLINE_UNAVAILABLE`) rather than fabricated.
- Recoverability means project state can be reconstructed even when a chat, runtime, provider, or working copy is lost.

Changing an identity invariant is a `CONSTITUTIONAL_OWNER_GATE` candidate and cannot enter production through ordinary self-evolution.

## 3. Logical Institution Model

The initial logical institution map is deliberately separable from physical providers.

| Logical institution | Japanese operating name | Core responsibility | Must remain independent from |
|---|---|---|---|
| CORE | 司令塔 | intent decomposition, routing, planning, coordination, state transitions | final independent audit |
| SOURCE_INTELLIGENCE | 情報探索網 | discover, classify, contradict, corroborate and normalize sources | canonical truth by popularity |
| KNOWLEDGE_BASE | 知識基盤 | claim/evidence/contradiction/confidence/knowledge graph | raw source dumping |
| VAULT | 記録庫 | canonical identity, SHA, provenance, evidence custody, version/recovery anchors | experiment advocacy |
| EXECUTION | 実行機関 | execute approved reversible work through tools/adapters | permission policy authorship |
| LAB | 検証室 | experiments, falsification, benchmark, gap analysis, simplification | production promotion authority |
| AUDITOR | 監査室 | Freeze/Promotion/Release final review | implementation ownership |
| DEFENSE_RECOVERY | 防衛・復旧局 | threat controls, secrets, incident response, disaster recovery, safe mode | unilateral canonical promotion |
| OPPORTUNITY | 機会探索局 | future value/revenue/use-case discovery | bypassing evidence/permission gates |
| RESOURCE | 資源管理局 | cost, quota, latency, compute/tool allocation | deciding truth from cost alone |
| CONNECTION | 接続局 | provider/tool/source adapters and capability registry | Multiverse identity |
| EVOLUTION | 進化局 | controlled self-change lifecycle and upgrade candidate queue | bypassing Lab/Auditor/Owner gates |

### Compression rule

The table describes **logical responsibilities**, not a mandate for twelve permanent chats, services, agents, or paid products.

Lab MUST identify:
- duplicate responsibilities;
- unnecessary permanent role separation;
- roles that can share one implementation while retaining logical audit boundaries;
- roles whose separation is materially required.

A role may be physically co-hosted if its evidence, permission and audit boundary remains explicit. Formal independence claims require genuinely independent review context where governance demands it.

## 4. Provider / Tool / Source Adapter Boundary

ChatGPT, Gemini, Claude, Local AI, search engines, browsers, GitHub, Drive, Replit, Dify and future systems are **providers/tools/sources**, not Multiverse itself.

### Adapter contract

Every adapter candidate SHOULD expose, as applicable:
- `adapter_id`
- `adapter_type`
- `provider`
- `capabilities`
- `input_contract`
- `output_contract`
- `permission_scope`
- `data_exposure_scope`
- `cost_or_quota_model`
- `availability_state`
- `provenance_method`
- `failure_modes`
- `fallback_adapter`
- `export_format`
- `lock_in_risk`
- `degraded_mode_behavior`

Canonical Multiverse state MUST be representable in open, inspectable formats independent of any single provider.

Provider loss is an operational degradation event, not an identity loss event.

## 5. Planes and Core Objects

### Control Plane
Owns:
- Owner directives;
- permission policy;
- routing;
- version state;
- change gates;
- autonomy level;
- safe mode.

### Evidence / Knowledge Plane
Owns:
- sources;
- claims;
- evidence;
- contradictions;
- confidence;
- knowledge objects;
- source trust;
- freshness and temporal validity.

### Execution Plane
Owns:
- tool calls;
- external side effects;
- reversible operations;
- receipts;
- idempotency/CAS where possible.

### Assurance Plane
Owns:
- verification;
- Lab benchmarks;
- red-team evidence;
- audit;
- acceptance receipts;
- rollback evidence.

### Recovery Plane
Owns:
- canonical pointers;
- immutable receipts;
- manifests;
- physical mirrors;
- bootstrap;
- recovery capsule;
- restore tests.

### Evolution Plane
Owns:
- proposals;
- impact analysis;
- sandbox/canary;
- version migration;
- dependency change;
- promotion/rollback.

No plane may silently promote itself to canonical authority.

## 6. Knowledge / Evidence Graph

Canonical knowledge is not a pile of links.

Minimum conceptual chain:

`SOURCE -> CLAIM -> EVIDENCE -> CONTRADICTION -> CONFIDENCE -> KNOWLEDGE_OBJECT -> HYPOTHESIS/RULE/DECISION`

Each material node SHOULD support:
- stable ID;
- source/provenance locator;
- observed/published/available/retrieved times where relevant;
- evidence level;
- support/contradict relation;
- applicable scope;
- permission/research-use status;
- freshness state;
- derived-from links;
- supersession links.

Source trust is contextual, claim-specific and revisable. Community sources may be high-value sensors without becoming automatic proof.

## 7. Threat Model

Minimum threat classes:
- stale-state overwrite / split brain;
- provider/account outage;
- account compromise;
- unauthorized side effects;
- secret leakage;
- malicious or poisoned source content;
- prompt/tool injection through external content;
- provenance loss;
- evidence tampering;
- accidental deletion;
- corrupted recovery copy;
- dependency compromise;
- runaway automation;
- quota/cost exhaustion;
- false confidence under offline/degraded conditions;
- privilege accumulation;
- review-role collapse;
- protected scientific data leakage;
- hindsight/result leakage;
- owner-fatigue attacks caused by excessive manual gates.

Controls MUST be layered: least privilege, explicit permission scopes, immutable receipts, CAS/version checks, role separation, evidence validation, recovery roots, monitoring, safe mode and rollback.

## 8. Permission Model

Permissions are capability-based and default-deny for material side effects.

Suggested risk classes:
- `P0_READ_PUBLIC_OR_CANONICAL` — routine reversible reads.
- `P1_REVERSIBLE_INTERNAL_WRITE` — branch/draft/noncanonical writes with receipts.
- `P2_EXTERNAL_OR_SHARED_WRITE` — external communication or shared state mutation.
- `P3_MATERIAL_OPERATION` — material architecture, security, data lifecycle, production promotion.
- `P4_OWNER_GATE_REQUIRED` — protected data, new spend when gated, constitutional change, major irreversible operation, contractual/external commitment, final release where required.
- `P5_PROHIBITED` — bypassing access controls; unauthorized holdout/result leakage; actions forbidden by law/terms/governance.

Autonomy level does not increase the maximum allowed permission class. It changes how much work may proceed **within** an already permitted envelope.

Every material side effect SHOULD produce an auditable receipt containing actor/role, intent, permission class, inputs, target, preconditions, result, provenance and rollback pointer when applicable.

## 9. Secrets Management

North Star requirements:
- no secrets embedded in canonical artifacts;
- provider credentials remain in provider-approved secret stores/keychains/environment facilities;
- least privilege and shortest practical scope;
- secret identifiers may be referenced, secret values may not;
- rotation/revocation procedure documented;
- secret exposure incident triggers Defense/Recovery handling;
- recovery capsule contains instructions and identifiers, not plaintext credentials;
- adapters must declare what data is exposed to providers.

L5 does not mean autonomous secret acquisition. Privileged credentials remain governed capabilities.

## 10. Disaster Recovery / Recovery Capsule

A Recovery Capsule is the minimal provider-portable set sufficient to reconstruct project state.

Minimum contents:
- stable bootstrap locator;
- canonical repository/state identity;
- accepted/current version pointer;
- state generation/supersession chain;
- artifact manifest with raw SHA-256;
- critical decision/permission receipts;
- adapter registry or reconstruction instructions;
- recovery root locators;
- protected-boundary metadata without protected payloads;
- version migration/rollback instructions;
- current known degraded dependencies;
- human-readable "resume here" instruction.

Requirements:
- one logical canonical authority;
- multiple physical recovery roots for material accepted state;
- mirrors are explicitly non-authoritative;
- restore is verified by hashes and canonical ancestry;
- periodic non-destructive restore rehearsal;
- chat loss is a recovery event, not a project reset.

## 11. Offline / Degraded Mode

When a provider/tool/source is unavailable:
1. continue with local/canonical evidence where permissions allow;
2. substitute an adapter if capability-equivalent and safe;
3. mark freshness-dependent outputs `STALE`, `UNKNOWN`, or `OFFLINE_UNAVAILABLE`;
4. do not fabricate fresh facts;
5. queue blocked work for later or route to another permitted adapter;
6. retain enough state to resume deterministically.

Provider failure MUST NOT silently downgrade evidence requirements or permissions.

## 12. Observability

Minimum system health signals:
- current version / state generation;
- open Owner Gates;
- open material review blocks;
- adapter availability and quota state;
- stale or unknown critical evidence;
- failed CAS/state writes;
- recovery-root health / last restore test;
- pending migrations;
- security incidents;
- cost/quota trend;
- automation failures;
- unresolved contradictions;
- next exact action.

Owner-facing observability should compress this to actionable exceptions, not dashboards that create routine burden.

## 13. Change / Dependency / Data Lifecycle Management

### Change management
All material changes use the Self-Evolution Protocol.

### Dependency management
Each dependency records:
- purpose;
- current version/provider;
- criticality;
- compatibility contract;
- replacement/fallback;
- export path;
- known lock-in;
- update trigger;
- security/provenance notes.

A dependency update is not automatically a Multiverse version change unless it changes behavior, evidence, permission, state schema or acceptance claims materially.

### Data lifecycle
Data classes SHOULD declare:
- purpose;
- provenance;
- sensitivity;
- retention;
- deletion authority;
- derived artifacts;
- redistribution/use constraints;
- recovery requirements;
- expiry/freshness behavior.

Deletion of material evidence/state is reversible where feasible and must not destroy required audit/recovery lineage.

## 14. Version Migration and Rollback

Each accepted version MUST declare:
- source version;
- target version;
- schema/data migration steps;
- preconditions;
- validation checks;
- rollback trigger;
- rollback procedure;
- irreversible elements, if any;
- evidence/receipt location.

Rollback returns to a known valid state; it does not erase audit history.

Migration and rollback must preserve protected scientific boundaries.

## 15. Cost / Quota Management

Default: `NEW_SPEND_DEFAULT = NO`.

Resource management optimizes:
1. correctness/safety;
2. recoverability;
3. Owner burden;
4. cost;
5. latency/convenience.

Existing subscriptions, free quotas, open formats and local/source-independent processing are preferred when they satisfy requirements.

Quota exhaustion of an optional external reviewer cannot block the mainline unless that review is an explicit acceptance dependency.

## 16. Mobile-First UX

Owner default surface is iPhone-first and low-interaction.

Target behaviors:
- one-tap/open-link handoff where available;
- otherwise one clean copy-paste block;
- downloadable artifact when a file transfer is required;
- Owner receives decisions/exceptions, not clerical steps;
- errors/screenshots may be pasted to Core for classification;
- "続行" and "これ変じゃない？" remain valid lightweight commands.

The architecture must not require the Owner to routinely operate Git, shells, manifests or provider consoles.

## 17. Human Override / Emergency Safe Mode

Owner override can:
- pause automation;
- revoke permissions;
- enter safe mode;
- freeze external writes;
- require manual review;
- select rollback target.

Emergency Safe Mode:
- allows canonical read/recovery/audit operations;
- blocks nonessential external writes and autonomous promotion;
- preserves evidence and logs;
- does not open protected data;
- exits only through an auditable state transition.

## 18. Autonomy Levels

| Level | Name | Meaning |
|---|---|---|
| L0 | OWNER MANUAL | Owner performs most operations manually |
| L1 | ASSISTED | AI advises/drafts; Owner executes routine actions |
| L2 | ORCHESTRATED | Core routes and executes reversible internal work; Owner handles material gates |
| L3 | SEMI-AUTONOMOUS | multi-step workflows execute within scoped permissions with receipts and checkpoints |
| L4 | SUPERVISED AUTONOMY | broad goal-directed operation with exception reporting, canarying and strong audit/recovery |
| L5 | SOVEREIGN CORE | provider-portable autonomous core can maintain state, knowledge, execution, recovery and evolution without dependency on any particular external AI/tool |

North Star = L5.

L5 does **not** mean unlimited permissions, owner displacement, uncontrolled external action, or autonomous constitutional rewrite.  
As autonomy rises, permission precision, audit coverage, recovery strength, observability and rollback requirements must rise too.

## 19. Self-Evolution Interface

Production change follows:

`IDEA -> PROPOSAL -> IMPACT ANALYSIS -> SANDBOX -> BENCHMARK -> RED TEAM -> AUDIT -> OWNER GATE (when material) -> CANARY -> PROMOTION -> MONITOR -> ROLLBACK`

The standalone Self-Evolution Protocol is normative for vNext once accepted.

Ideas from Owner or AI enter the same lifecycle. No "good idea" may directly mutate Production Constitution.

## 20. Version Completion / Definition of Done Principle

Each version has:
- explicit scope;
- explicit non-goals;
- acceptance criteria;
- required review roles;
- required recovery evidence;
- known limitations;
- rollback/migration plan;
- `Definition of Done`.

When all blocking criteria pass, the version may be closed even if further improvements exist.

New improvements become `NEXT_VERSION_CANDIDATE` unless they demonstrate:
- a current-version safety defect;
- a violated identity invariant;
- an acceptance-criteria failure;
- a material recovery/security hole;
- a constitutional contradiction.

"Could be better" alone is not a blocker.

## 21. North Star Structural Completeness Checklist

Before Architecture Closure is claimed, Lab must attack at least:
- threat model;
- permission model;
- secrets management;
- disaster recovery;
- recovery capsule;
- knowledge/evidence graph;
- source trust model;
- provider failure;
- offline/degraded mode;
- observability;
- change management;
- dependency management;
- data lifecycle;
- retention/deletion;
- version migration;
- rollback;
- cost/quota management;
- mobile-first UX;
- human override;
- emergency safe mode;
- provider portability;
- role separation / independence;
- stale-state / split-brain control;
- auditability of autonomous actions;
- owner-burden failure modes.

Lab must classify every gap as:
- `MATERIAL_ARCHITECTURE_GAP`
- `IMPLEMENTATION_GAP_WITH_ARCHITECTURE_COVERAGE`
- `NEXT_VERSION_CANDIDATE`
- `OVERENGINEERING_DUPLICATION`
- `NO_MATERIAL_GAP`

Architecture Closure requires no unresolved `MATERIAL_ARCHITECTURE_GAP`.

## 22. Current -> North Star Roadmap

### Phase A — vNext Closure Foundation
Goal: largest structural risk reduction with minimal Owner cost.
- canonical CAS state;
- immutable identity/provenance;
- deterministic bootstrap;
- dual physical recovery roots;
- North Star Architecture;
- Self-Evolution Protocol;
- explicit vNext Definition of Done;
- Lab Architecture Gap Analysis;
- final acceptance audit.
Target autonomy: strong L2 foundation.

### Phase B — Provider-Neutral Conversation/Execution Bus
- standard request/response/receipt objects;
- adapter registry;
- capability/permission metadata;
- automatic pickup of role outputs where platform permits;
- manual copy-paste only as fallback.
Target autonomy: L2 -> L3.

### Phase C — Knowledge/Evidence Graph
- structured claims/evidence/contradictions;
- freshness/source-trust model;
- decision provenance;
- source registry evolution.
Target autonomy: L3.

### Phase D — Observability / Resource / Defense
- exception-first health state;
- quota/cost routing;
- safe mode;
- secrets/dependency governance;
- periodic restore/canary tests.
Target autonomy: robust L3.

### Phase E — Controlled Self-Evolution
- proposal queue;
- sandbox/benchmark/red-team automation;
- canary/promotion/rollback automation;
- next-version candidate registry.
Target autonomy: L3 -> L4.

### Phase F — Sovereign Core
- local/provider-portable core state/knowledge/recovery/evolution functions;
- external AI/search/browser/tools become replaceable capability adapters;
- degraded/offline operation with explicit freshness limits.
Target autonomy: L4 -> L5.

Do not implement all phases in vNext. vNext only installs the minimum foundation required to make later phases additive rather than architectural rewrites.

## 23. vNext Closure Boundary

vNext is not "all of North Star implemented."

vNext is complete when its explicit DoD proves:
- architecture closure at the logical level;
- safe provider-neutral extension points;
- canonical/recovery integrity;
- controlled self-evolution;
- bounded permission/autonomy model;
- no unresolved material architecture gap;
- exact Keirin resume remains protected;
- future ideas can be queued without reopening vNext.

After vNext acceptance, Multiverse core modification pauses except for:
- critical defect/security/recovery incidents;
- required acceptance rollback;
- explicitly promoted next-version work.

Then Keirin resumes from the latest legitimate verified canonical Keirin state, not from chat memory and not from an older pause receipt if superseded.

END
