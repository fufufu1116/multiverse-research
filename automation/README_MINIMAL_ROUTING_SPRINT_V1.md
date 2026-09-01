# MULTIVERSE Core Automation Candidate Lane — Minimal Routing Sprint v1

Status: CANDIDATE / NONCANONICAL / NO PRODUCTION AUTHORITY  
Base: canonical `main` at branch creation.  
Goal: remove Owner routine transport before building a general orchestrator.

## First target loop

`OWNER REQUEST -> CORE -> MECHANICAL_GATE -> LAB -> AUDITOR -> OWNER_GATE|DONE`

Fix paths are deterministic:

- `MECHANICAL_GATE FAIL -> CORE`
- `LAB FIX_REQUIRED -> CORE`
- `AUDITOR FIX_REQUIRED -> CORE`
- remediation retry ceiling is fixed at 3
- risky remediation routes to `OWNER_GATE`
- retry ceiling exhaustion routes `FAILED_CLOSED`
- PASS never grants production or Runtime authority

The router does not call GitHub, an LLM, a provider, or a workflow. It is a deterministic control component intended to sit between a Fresh-Read/evidence adapter and role executors.

## What is already deterministic in current Phase C design

Fresh inspection of the current Phase C pre-Lab mechanical gate shows substantial deterministic enforcement already exists, including:

- required-file existence/content-type checks
- JSON/Python/Go parsing/build checks
- devcontainer build/user/capability/post-attach invariants
- prohibition of automatic session-gate startup
- exact v7r7 binary/source wiring checks
- inherited pagination/rate/window regression checks
- START_HERE / manual-arm / image-identity invariants
- exact Step3 blob/SHA/size/NONMUTATING binding
- assembly-manifest authority/runtime checks
- negative mechanical requirements
- executable selftests and exact Docker build evidence

This is strong candidate-specific control. The missing layer is generic task state/routing and machine-readable handoff.

## A. Existing deterministic controls

Already implemented/designed in the current Phase C line:

1. exact head/tree/blob/hash binding and frozen evidence;
2. parser/schema-like exact evidence-shape checks;
3. pre-Lab mechanical gate with syntax/build/invariant checks;
4. exact image closure identity and reproducibility evidence;
5. temporal/order checks around attach/manual arm/600-second gate;
6. fail-closed behavior and authority ceilings;
7. review-only/nonmutating Step3 binding;
8. GitHub audit evidence with exact references and provenance checks.

## B. Areas still too dependent on AI/human judgment

Observed process gaps this sprint targets:

1. deciding who receives a PASS/FIX result;
2. transporting SHA/head/request/result references between roles;
3. maintaining retry count and next state;
4. deciding whether a remediation is safe to return to Core without Owner;
5. converting review prose into an exact routing event;
6. creating the next role handoff from Fresh canonical state;
7. distinguishing routine routing from an actual Owner Gate.

Independent Lab/Auditor semantic reasoning remains intentionally AI-assisted; deterministic controls should not pretend to replace it.

## C. Top five additions for the generic PRE-LAB Mechanical Gate

Priority order:

1. **Fresh binding manifest gate** — require canonical main, target branch/head/tree, PR state, artifact refs and authority boundary in one machine-readable snapshot; reject stale/mismatched head.
2. **Forbidden authority/diff gate** — machine reject disallowed main/ruleset/production/secret/external-send/irreversible scope before review routing.
3. **Deterministic task-state/retry gate** — exact allowed transitions, retry budget=3, terminal/fail-closed states, and no LLM-created transition.
4. **Evidence contract gate** — exact required result fields, unique verdict/head fields, evidence completeness/provenance/uniqueness where relevant, and no ambiguous PASS parsing.
5. **Promotion criteria registry** — predeclare task-specific machine tests/invariants before results are observed; PASS cannot be promoted if mandatory executable evidence is absent.

Do not make every task run Phase C's entire heavyweight gate. Generic checks should be cheap; task-specific gates remain composable.

## D. Lab / Auditor as Red Team

LAB should focus on what mechanical checks cannot prove:

- experimental/scientific validity;
- semantic specification compliance;
- leakage/contamination;
- reproducibility interpretation;
- hidden assumptions in implementation behavior;
- counterexamples that satisfy tests but violate intent.

AUDITOR should focus on:

- authority/governance mismatch;
- unsafe interpretation or promotion overclaim;
- cross-system contradictions;
- stale authority/evidence reuse;
- adversarial sequencing and recovery paths;
- missing evidence that machine gates do not know to demand.

Neither role's PASS is treated as proof merely because another AI agrees. Final promotion should prefer executable/deterministic evidence plus adversarial review.

## E. Owner routine work to remove

Automation candidates, in order:

1. parse exact Lab result -> route PASS to Auditor / FIX to Core;
2. parse exact Auditor result -> route PASS to Owner Gate or DONE / FIX to Core;
3. Fresh-read target/main/PR/evidence and generate the task manifest automatically;
4. generate exact role request envelopes from the manifest;
5. track retry budget/evidence refs without chat handoff;
6. escalate only risk-boundary cases to Owner.

The current live session already removed one concrete copy/paste: Core directly routed the verified Lab PASS to an Auditor request on PR #74.

## F. External review classification

### ADOPT

- separate LLM reasoning from deterministic control;
- do not use “another AI passed it” as correctness proof;
- strengthen pre-Lab mechanical rejection of machine-checkable defects;
- move Lab/Auditor toward adversarial Red-Team work;
- require executable/deterministic evidence where practical;
- keep Owner out of routine transport;
- concentrate Owner Gates on high-risk boundaries;
- keep Stable/Candidate promotion with prespecified machine-checkable criteria;
- combine AI exploration + deterministic checks + independent falsification + real execution evidence.

### VERIFY BEFORE ADOPTION

- LangGraph / Temporal full migration: evaluate OWNER_TOUCH_COUNT, TIME_TO_OWNER_VALUE and recovery before adoption;
- DSPy: evaluate overlap/fit with Prompt Evolution Engine; no immediate broad adoption;
- Formal methods: consider only high-value authority/state-transition/invariant surfaces.

### REJECT

- remove all multi-agent structure;
- remove Independent Lab/Auditor;
- treat AI review as useless and delete it;
- assume a framework change alone solves autonomy.

## G. Minimal non-blocking change

This candidate branch adds only:

- a deterministic task router/state machine;
- a machine-readable task-manifest schema;
- a read-only GitHub Fresh-Read manifest builder;
- unit tests for PASS/FIX/risk/retry/head/verdict/Fresh-drift behavior;
- this design note.

No Stable/main replacement, no Runtime activation, no production mutation, no workflow dispatch, no external provider contact, and no new framework.

## Milestones

- M1: remove one Owner AI-to-AI copy/paste — already demonstrated in the current Critical Path by direct Core routing.
- M2: deterministic Lab PASS/FIX routing contract — implemented in this candidate router.
- M3: deterministic Auditor PASS/FIX routing contract — implemented in this candidate router.
- M4: Fresh Read + exact manifest adapter — implemented as a GET-only `api.github.com` builder that rejects target-head drift.
- M5: one low-risk candidate completes the loop without Owner routing — requires an approved execution hook/adapter after review; do not fake this milestone with chat-only claims.

## Safety

This branch is not an execution authority. It does not authorize Runtime activation, production mutation, Step4, `--apply`, main/ruleset mutation, merge, workflow dispatch, writer-key/secret operation, external provider contact/send, spending, real-money wagering, protected Keirin data access, authority expansion, or irreversible operations.
