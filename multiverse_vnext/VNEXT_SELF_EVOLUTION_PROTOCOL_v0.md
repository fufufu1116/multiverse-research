# MULTIVERSE SELF-EVOLUTION PROTOCOL v0

Status: WORKING_NORMATIVE_CANDIDATE — NOT_ACCEPTED  
Applies to: material changes to Multiverse architecture, governance-controlled behavior, state schemas, security, permission, recovery, adapters with material behavior, and acceptance-critical dependencies.

## 1. Principle

Multiverse may improve itself, but it may not silently redefine itself.

An Owner idea and an AI idea enter the same controlled lifecycle. Direct mutation of Production Constitution or accepted canonical behavior from an unreviewed idea is prohibited.

Classification itself is part of governance. A change author cannot make a change safe merely by labeling it `MINOR_REVERSIBLE`.

## 2. Lifecycle

`IDEA -> PROPOSAL -> IMPACT_ANALYSIS -> SANDBOX -> BENCHMARK -> RED_TEAM -> AUDIT -> OWNER_GATE_IF_REQUIRED -> CANARY -> PROMOTION -> MONITOR -> ROLLBACK_OR_CLOSE`

### IDEA
Record:
- problem/opportunity;
- proposer;
- expected benefit;
- evidence/uncertainty;
- affected modules/invariants.

No production effect.

### PROPOSAL
Define:
- scope/non-goals;
- interfaces touched;
- migration needs;
- permission class;
- cost/quota effect;
- Owner-burden effect;
- success/failure criteria;
- rollback concept.

### IMPACT_ANALYSIS
Check:
- identity invariants;
- security/threat model;
- permission/authorization enforcement;
- recovery;
- scientific/firewall constraints;
- privacy/terms/permissions;
- dependency/lock-in;
- source/evidence semantics;
- role independence;
- cost;
- mobile UX;
- backward compatibility.

Classify:
- `MINOR_REVERSIBLE`;
- `MATERIAL_REVIEW_REQUIRED`;
- `CONSTITUTIONAL_OWNER_GATE`;
- `SECURITY_RECOVERY_BLOCK`;
- `COST_GATE`;
- `SOURCE_PERMISSION_GATE`.

Classification MUST use an accepted, pinned rule-set generation. If classification evidence is missing, ambiguous, stale, or contradictory, classification fails closed to at least `MATERIAL_REVIEW_REQUIRED`.

The following are automatically **not Fast-Path eligible** and are at least `MATERIAL_REVIEW_REQUIRED` unless a stronger gate applies:
- identity invariant changes;
- permission policy, authorization-decision schema, permission ceiling, grant/revocation semantics, or Owner-Gate semantics;
- security controls, Emergency Safe Mode, recovery authority, recovery guarantees, or rollback authority;
- the classifier, Fast Path eligibility rules, audit gates, promotion gates, acceptance criteria, or Self-Evolution Protocol itself;
- canonical state authority, state schema, CAS/supersession semantics, or version precedence;
- protected scientific/firewall boundaries;
- irreversible external operations, contractual commitments, or gated spend;
- data handling changes that materially widen exposure, retention, redistribution, or deletion authority.

A proposer/implementer MAY supply classification evidence but MUST NOT be the sole authority establishing Fast Path eligibility for its own change.

### SANDBOX
Change must first exist outside accepted production state unless emergency governance explicitly allows otherwise.

Requirements:
- isolated branch/workspace;
- no protected data consumption unless separately authorized;
- no irreversible external effects;
- reproducible inputs;
- receipts.

### BENCHMARK
Measure predefined criteria. Prefer proper scoring, invariants, reliability, failure diagnostics, resource cost and Owner burden over vanity metrics.

A benchmark designed after seeing the result cannot retroactively become preregistered evidence.

### RED TEAM
Actively search for:
- rollback failure;
- stale-state overwrite;
- privilege escalation;
- provider lock-in;
- injection/data poisoning;
- audit bypass;
- classifier/Fast-Path bypass;
- recovery corruption;
- cost/quota failure;
- misleading success metrics;
- hidden Owner burden;
- role collapse;
- scientific leakage.

### AUDIT
Independent-enough reviewer checks whether evidence supports promotion claims and whether required gates were actually satisfied.

Implementation owner cannot unilaterally certify final promotion when governance requires independent audit.

### OWNER GATE
Required when the current permission/governance model classifies the change as material to Owner sovereignty, constitution, protected evidence, major irreversible operation, external commitment/contract, or gated spend.

Owner Gate asks for a decision, not routine implementation.

### CANARY
Production-like, bounded exposure:
- limited scope;
- explicit duration/exit criteria when relevant;
- enhanced observability;
- rollback ready;
- no automatic scope expansion.

### PROMOTION
Promotion requires:
- target version identified;
- accepted evidence;
- migration receipt;
- canonical state transition using CAS/supersession;
- artifact identities pinned;
- rollback pointer;
- required audit/Owner approvals recorded;
- an authorization decision valid for the exact promotion operation.

### MONITOR
Observe:
- correctness;
- safety;
- recovery health;
- cost/quota;
- Owner burden;
- regressions;
- provider failures;
- new contradictions.

### ROLLBACK
Trigger when predefined failure/safety criteria occur or required evidence becomes invalid.

Rollback:
- returns to a known valid state;
- preserves audit history;
- cannot silently erase failed-change evidence;
- rechecks protected boundaries;
- produces a rollback receipt.

## 3. Fast Path

A Fast Path may exist only for `MINOR_REVERSIBLE` changes that:
- do not match any automatic-material trigger in the pinned classification rule set;
- do not change identity invariants;
- do not widen permissions, exposure, retention or irreversible authority;
- do not alter security, Safe Mode, recovery, rollback, classifier, Fast Path, audit, acceptance, promotion or protected scientific boundaries;
- do not introduce spend/external commitments;
- are fully reversible;
- retain audit evidence.

Fast Path eligibility MUST have a `FAST_PATH_ELIGIBILITY_RECEIPT` containing:
- classifier rule-set generation/digest;
- exact change identity;
- affected interfaces;
- automatic-material-trigger evaluation;
- author/implementer identity;
- eligibility witness identity or deterministic classifier identity;
- result and reason codes.

The change author/implementer alone cannot produce a sufficient Fast Path eligibility decision for its own change. Eligibility requires either:
1. a deterministic classifier operating under an already accepted pinned rule set whose rules the change does not modify; or
2. a reviewer/witness not acting as the change author/implementer.

If the classifier, rule set, evidence, witness independence, or affected scope is unknown, the result is `FAST_PATH_DENIED_FAIL_CLOSED` and the change routes to material review.

Fast Path may compress Sandbox/Benchmark/ordinary Review only after eligibility is established. It can never skip canonical CAS, receipts, prohibition checks, authorization enforcement, or required Owner Gates.

## 4. Emergency Path

Emergency Safe Mode may authorize containment before full lifecycle completion when needed to stop ongoing damage.

Emergency actions:
- minimize privileges and external writes;
- preserve evidence;
- favor reversible containment;
- never open protected scientific data merely for diagnosis;
- require post-incident audit and normalization through the standard lifecycle.

Emergency containment is not permanent promotion. Safe Mode cannot be used to grant broader authority than normal governance permits.

## 5. Version Boundary

Every proposal declares destination:
- `CURRENT_VERSION_DEFECT_FIX`
- `NEXT_VERSION_CANDIDATE`
- `EXPERIMENT_ONLY`
- `CONSTITUTIONAL_CHANGE_CANDIDATE`

If the current version already satisfies its DoD and the idea is merely beneficial, default destination is `NEXT_VERSION_CANDIDATE`.

## 6. Acceptance Evidence

A promoted material change should be reconstructable from:
- proposal;
- impact analysis;
- classification rule-set identity and classification receipt;
- sandbox identity;
- benchmark evidence;
- red-team findings;
- audit verdict;
- Owner Gate receipt if required;
- canary evidence;
- authorization decision;
- promoted commit/artifact hashes;
- migration receipt;
- rollback pointer;
- monitor status.

## 7. Anti-Self-Approval Rule

No role may create a change, determine by itself that the change is non-material, define the only success metric, perform the only review, and grant promotion.

For Fast Path, classification independence/determinism is mandatory as defined above. For material change, implementation ownership and final promotion authority remain separated.

Where platform limits prevent true simultaneous independence, the system must explicitly mark the independence limitation rather than pretend it does not exist.

## 8. Provider Changes

Swapping ChatGPT/Gemini/Claude/local model/search/browser/GitHub/Drive/Replit/Dify or another provider is normally an adapter/dependency change.

It becomes a material Multiverse change only if it alters:
- canonical identity/state semantics;
- permission exposure;
- evidence/provenance guarantees;
- recovery guarantees;
- accepted behavior/performance claims;
- cost/lock-in beyond allowed envelope;
- data handling or security model.

## 9. Closure

A self-evolution cycle ends as one of:
- `PROMOTED_AND_MONITORED`
- `ROLLED_BACK`
- `REJECTED`
- `DEFERRED_NEXT_VERSION`
- `UNKNOWN_INSUFFICIENT_EVIDENCE`

No cycle remains "almost done forever" without an explicit state.

END
