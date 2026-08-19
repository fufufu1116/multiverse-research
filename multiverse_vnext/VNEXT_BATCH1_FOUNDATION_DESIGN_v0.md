# Multiverse vNext — Batch 1 Foundation Design v0

Status: WORKING CANDIDATE — REVIEW BRANCH — NOT ACCEPTED / NOT FROZEN
Date: 2026-08-20 JST

## 0. Scope and firewall

This Batch builds the minimum durable spine for Multiverse vNext while Keirin is safely paused.

It does **not** modify the Keirin scientific lineage, consume untouched evidence, open `ECON_HOLDOUT1000`, score DEV2000 C for new-lineage rescue, access protected RESULT/PAYOUT material, authorize new spending, or replace constitutional governance.

The protected restart point is recorded in:

`multiverse_vnext/VNEXT_KEIRIN_PAUSE_RECEIPT_20260820_v1.json`

A later legitimately verified canonical Keirin milestone may supersede that receipt; older packets or memory may not roll the project backward.

---

## 1. vNext foundation invariants

### I1 — CHAT LOSS != PROJECT STATE LOSS
A chat may disappear without destroying the ability to reconstruct project state.

### I2 — One logical canonical authority, multiple physical recovery roots
Avoid split-brain state. GitHub remains the primary logical canonical authority for small text/code/governance/state unless a later accepted governance change explicitly replaces that role.

At the same time, no single chat, runtime, GitHub object, Drive object, device, or vendor account may be the only physical place from which an irreplaceable accepted project state can be reconstructed.

Recovery redundancy must therefore mirror or package sufficient canonical state without creating multiple competing authorities.

### I3 — Verified newer state wins
Precedence for conflicting project state:

1. latest verified canonical GitHub / verified immutable artifact;
2. active Owner Directive;
3. recovery handoff / bootstrap receipt;
4. role packet / prior constitution;
5. conversation memory.

A lower layer may not silently overwrite a newer verified state.

### I4 — Fail closed on protected boundaries
If holdout, permission, source timing, freeze identity, or provenance is ambiguous, do not infer permission.

### I5 — Evidence objects are typed
A source, claim, hypothesis, decision, probability object, lower envelope, review, and verdict are not interchangeable.

### I6 — External AI is optional transport/review capacity
Gemini, Claude, search engines, and future tools are adapters. Core project state, evidence structure, workflow, and recovery must remain usable without them.

### I7 — Owner is not Routine Operator
The normal Owner interaction target is: `続行`, `これ変じゃない？`, an error/screenshot, or an actual Owner Gate decision.

### I8 — NEW_SPEND_DEFAULT = NO
Use existing ChatGPT, Gemini plan, Claude free quota, GitHub, Drive, Replit, iPhone, TXT/JSON/Markdown before proposing spend.

---

## 2. Minimal state architecture

Use five logical object classes. They may share files when small; the object boundaries matter more than file count.

### A. STATE
What is true now.

Minimum fields:
- state_id / version
- updated_at
- phase
- canonical base / branch / commit
- active freezes and protected boundaries
- current next gate
- unresolved material questions
- owner gates currently open
- superseded state pointers

### B. ARTIFACT
What exists and how it is identified.

Minimum fields:
- artifact_id
- role
- locator(s)
- content hash where bytes are available
- created_at / retrieved_at
- provenance
- acquisition_purpose_at_time_of_acquisition when relevant
- later_research_use when relevant
- mutable vs immutable
- canonical / working / fallback status
- protection class

Do not rewrite acquisition purpose retroactively. Later research use is a separate field and does not automatically change permissions, copyright, terms, access-control, privacy, or redistribution boundaries.

Evidence ladder:

`REFERENCED -> LOCATED -> READABLE -> BYTE_ACCESSIBLE -> HASH_VERIFIED -> CANONICAL`

### C. EVIDENCE / KNOWLEDGE
What supports or contradicts a claim.

Minimum fields:
- claim_id
- claim text
- source_id(s)
- evidence tier
- support / contradict / context-only
- primary / secondary / community / signal
- applicability boundary
- confidence
- contradictions
- unknowns
- measurable hypothesis if promotion is possible

### D. MESSAGE / REVIEW
How AI roles exchange work.

Minimum message envelope:
- message_id
- from_role
- to_role
- request_type
- state_ref
- artifact_refs
- question / task
- constraints / prohibitions
- expected response type
- created_at

Minimum review response:
- response_id
- request_ref
- reviewer_role
- findings
- evidence_refs
- failure modes
- what_would_change_my_mind
- classification
- recommended action

### E. DECISION
Why a change was or was not made.

Minimum fields:
- decision_id
- proposal
- evidence refs
- contradicting refs
- alternatives considered
- decision class
- reversible?
- cost impact
- owner gate required?
- verdict
- effective state ref

---

## 3. Recovery architecture

### 3.1 Recovery roots

**GitHub**
- primary logical canonical authority for small text/code/governance/state under current governance
- immutable receipts/checkpoints
- review trail where concise

**Google Drive**
- heavy artifacts, ZIP/CSV/large execution products
- recovery mirror/package for accepted milestone state when required by acceptance criteria
- each heavy artifact must have a GitHub-side pointer/identity receipt when material

**iPhone Cold Snapshot**
- optional export bundle at major accepted milestones
- intended for catastrophic account/service loss, not daily sync
- open formats only where practical

**Bootstrap file**
A small restart instruction that points to Current State, manifest, recovery instructions, acceptance/freeze status, and the canonical-authority rule.

A mirror or snapshot is a recovery copy, not an independent competing source of truth unless governance explicitly promotes it.

### 3.2 Recovery test, not backup theater

A backup is not considered sufficient merely because files exist somewhere.

Acceptance candidate must demonstrate at least these restore scenarios using non-destructive rehearsal:

1. New Chat, no useful conversation history.
2. Current runtime missing.
3. Drive heavy artifact temporarily unavailable.
4. One GitHub working file accidentally deleted but available in Git history / other root.
5. External AI unavailable.
6. Search/Web unavailable when no fresh external fact is required.

For fresh facts with no source, degrade explicitly to:
`UNKNOWN`, `STALE`, or `OFFLINE_UNAVAILABLE`.

### 3.3 Recovery correctness rule

Reconstruction target is project state, not verbatim deleted-chat recovery.
Never claim that a deleted chat can always be restored.

---

## 4. Source Intelligence Engine

### 4.1 Source roles

`TIER_A_PRIMARY_AUTHORITATIVE`
- laws, official rules, original papers/datasets, official statistics/specifications, primary records.

`TIER_B_STRONG_SECONDARY`
- strong expert institutions, review literature, high-quality specialist reporting, well-corroborated technical explanation.

`TIER_C_REFERENCE_ORIENTATION`
- Wikipedia, general references, summaries used for terminology, orientation, and discovery.

`TIER_D_COMMUNITY_EXPERIENCE`
- forums, Reddit, Yahoo!知恵袋, 5ch/legacy boards, blogs, comments, public social posts, product/app reviews, practitioner anecdotes.
- useful for tacit knowledge, failure discovery, minority views, usage gaps, and hypothesis generation.

`TIER_E_UNVERIFIED_SIGNAL`
- anonymous/single-source rumor or provenance-poor claim.
- may trigger investigation; must not be promoted to fact without evidence.

Tier is an evidence role, not a permanent platform label. A newly useful source type may be proposed as a `SOURCE_REGISTRY_CANDIDATE`; the Source Universe is not closed by this initial list.

### 4.2 Discovery -> Proof pipeline

For material claims discovered from any source:

`DISCOVER -> CLAIM_EXTRACT -> SOURCE_RECORD -> CLASSIFY -> PRIMARY_SEARCH -> INDEPENDENT_CORROBORATION -> CONTRADICTION_SEARCH -> MEASURABLE_HYPOTHESIS -> TEST/AUDIT -> PROMOTE/REJECT/UNKNOWN`

Community sources are therefore sensors, not automatic truth and not automatic trash.

### 4.3 Contradiction-first rule

For important claims, actively search for:
- failed replications
- exceptions
- contrary primary evidence
- adverse user experience
- alternative causal explanations
- regime boundaries
- stale-version effects

No majority vote becomes proof.

### 4.4 Source record candidate

A material Source Object should support:

```json
{
  "source_id": "...",
  "source_type": "official|paper|dataset|technical|media|community|video|social|other",
  "tier": "A|B|C|D|E",
  "title": "...",
  "author_or_org": "...",
  "locator": "...",
  "retrieved_at": "...",
  "published_at": "...",
  "available_at": "...",
  "claim": "...",
  "evidence_level": "...",
  "primary_or_secondary": "...",
  "stance": "support|contradict|context|discovery_only",
  "acquisition_purpose_at_time_of_acquisition": "...",
  "later_research_use": "...",
  "applicable_terms": "...",
  "archive_or_reference": "...",
  "notes": "..."
}
```

Acquisition purpose and later research use must remain distinct and truthful. A later research use does not retroactively authorize acquisition, copying, redistribution, automation, or access that was otherwise restricted.

Do not archive or reproduce content beyond rights/terms/technical permission.
No authentication, CAPTCHA, WAF, or rate-limit bypass.

### 4.5 Knowledge distillation

Do not hand the Owner a link pile.
Compress:

`RAW SOURCE -> CLAIM -> EVIDENCE -> CONTRADICTION -> CONFIDENCE -> KNOWLEDGE OBJECT -> RULE/HYPOTHESIS/DECISION`

Owner-facing result should answer:
- what is known;
- what is uncertain;
- what contradicts it;
- what matters;
- what test or decision comes next.

---

## 5. AI Interop / Conversation Bus

Do not require direct realtime AI-to-AI conversation.
Use vendor-neutral artifacts so roles can exchange:

`STATE -> REQUEST -> EVIDENCE -> REVIEW -> DECISION -> RESPONSE`

Preferred transport order:
1. GitHub for short durable structured objects / diffs;
2. Drive for heavy bundles;
3. direct chat paste only when connector/transport is unavailable and the payload is small;
4. Replit automation only after repeated manual relay burden is observed.

Avoid creating an orchestrator before the workflow proves it needs one.

Role routing:
- routine research/design/implementation -> CORE
- canonical/SHA/recovery -> VAULT
- failure/benchmark/complexity/cost -> LAB
- material architecture/scoring/baseline dispute -> independent review candidate
- freeze/promotion/release -> AUDITOR
- optional vendor-independent red team -> Claude when useful; quota must not block progress
- spend/holdout/irreversible/contract/external contact/constitutional -> OWNER GATE

---

## 6. Self-Audit engine

At every Material Batch/Milestone, automatically classify discovered issues as one of:

- `NO_MATERIAL_ISSUE`
- `MINOR_AUTOFIX_CANDIDATE`
- `MATERIAL_REVIEW_REQUIRED`
- `RECOVERY_RISK`
- `COST_GATE`
- `SOURCE_PERMISSION_GATE`
- `CONSTITUTIONAL_OWNER_GATE`

Minimum recurring attack checklist:
- stale assumption
- contradiction
- canonical drift
- missing SHA/provenance
- single point of failure
- backup without restore proof
- tool duplication
- unnecessary spend
- unnecessary owner interaction
- iPhone-hostile workflow
- source monoculture / confirmation bias
- benchmark gap
- role-independence gap
- simpler/faster/cheaper alternative
- silent vendor lock-in
- unbounded artifact proliferation

Minor safe fixes may be automated.
Material changes require review.
Constitutional changes require Owner Gate.

---

## 7. Cost and iPhone UX

### Cost guardrail

Any new paid proposal must present:
1. problem;
2. free/existing alternatives tried or evaluated;
3. why they are insufficient;
4. initial and recurring price;
5. expected measurable benefit;
6. lock-in / exportability;
7. cancellation path.

No approval => no spend.

### iPhone interaction target

Normal Batch completion should not require the Owner to:
- compare SHAs manually;
- decide which AI role receives a task;
- retype long prompts;
- move many files individually;
- inspect raw logs unless an actual error cannot be resolved otherwise.

When an external role is needed, Core must provide exactly:
- recipient role;
- why;
- ordered attachments;
- one ready-to-send instruction;
- minimum Owner operation;
- where the response returns.

---

## 8. Portability / Sovereignty

vNext should prefer:
- TXT
- Markdown
- JSON
- CSV where tabular
- ZIP for transport bundles
- SHA-256 identity when byte verification matters
- documented directory/pointer conventions

Vendor-native features may improve UX but must not be the only representation of material state.

External facts require a source adapter. If adapters are unavailable, the system must preserve internal state and explicitly mark fresh-fact limitations rather than fabricate.

---

## 9. Batch-1 acceptance-test skeleton

Batch-1 is ready for formal acceptance review only if all are demonstrated or explicitly waived by the required authority:

1. **Keirin firewall test** — no protected scientific state changed.
2. **New-chat bootstrap test** — reconstruct active Multiverse phase from durable artifacts without relying on conversation memory.
3. **State precedence test** — a stale handoff cannot overwrite newer verified state.
4. **Recovery-root test** — at least two independent usable physical recovery roots for material accepted state, with one logical canonical authority and a restore procedure.
5. **Source object test** — one Tier A claim and one Tier D discovery can be recorded without conflating evidence strength or acquisition purpose with later research use.
6. **Contradiction test** — a knowledge object can retain supporting and contradicting evidence simultaneously.
7. **Interop test** — Core can issue one structured review request and ingest a role response without requiring direct AI-to-AI realtime conversation.
8. **Self-audit test** — Materiality classifier correctly routes at least one minor, one material, one recovery, and one Owner Gate scenario.
9. **Offline degradation test** — fresh-fact absence yields `UNKNOWN/STALE/OFFLINE_UNAVAILABLE`, not fabrication.
10. **Owner burden test** — a normal routing event is executable from iPhone with one minimal send operation when external human relay is unavoidable.
11. **Cost test** — no new paid dependency is required for the foundation path.
12. **Artifact discipline test** — no duplicate file is created when an existing stable object can be updated safely with Git history.

---

## 10. Review gates for this Batch

### Next: VAULT
Review only:
- pause receipt identity and correctness;
- GitHub/current-state precedence;
- one logical canonical authority vs multiple physical recovery roots;
- recovery roots and SPOFs;
- mutable vs immutable policy;
- SHA/provenance claims;
- whether the design can reconstruct state without chat memory.

### Then: LAB
Review only after Vault findings are available:
- overengineering;
- needless tools/files;
- restore-test realism;
- source bias and contradiction handling;
- acquisition-purpose / research-use boundary handling;
- iPhone burden;
- cost creep;
- ambiguous acceptance criteria;
- easier/faster/cheaper design.

### Not yet: AUDITOR
Do not request formal vNext acceptance until Core has incorporated Vault + Lab findings and produced an acceptance candidate.

### Gemini / Claude
Not required for routine Batch-1. Use only if Vault/Lab expose a material architecture dispute where independent model diversity is likely to add value.

---

## 11. Current routing verdict

`CORE_BUILD -> VAULT_REVIEW -> LAB_REVIEW -> CORE_REVISE`

Owner Gate is not currently required.

END
