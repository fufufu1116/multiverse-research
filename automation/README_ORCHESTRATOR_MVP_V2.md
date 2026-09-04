# MULTIVERSE Automation Candidate Lane — Orchestrator MVP v2 remediation

Status: CANDIDATE / NONCANONICAL / NO PRODUCTION AUTHORITY.

v2 supersedes v1 for review. v1 is retained as history and must not be used as the current review target.

## Why v2 exists

Implementer-side adversarial pre-review found four material proof gaps before Independent Lab:

1. v1 demo evidence bound `candidate_head` to precursor Sprint head `6c71b952...`, not the exact MVP review head.
2. a crash after a worker completed but before the orchestrator's post-call checkpoint could cause the role to execute again without a stable idempotency identity.
3. transient/diff/execution budgets could be widened by a caller even though they were described as prespecified ceilings.
4. execution time was measured only after return; a hung role call had no hard process timeout.

## v2 remediation

- task/review/implementation results bind to exact `candidate_head`;
- `BindingVerifier` is mandatory at orchestration entry;
- LAB/AUDIT require `reviewed_head == candidate_head` and nonempty evidence refs;
- stable `operation_key(task, role, semantic_generation)` survives crash recovery;
- worker adapter must declare `replay_safe=true`;
- deterministic fixture worker durably deduplicates successful work by operation key;
- failure injection covers crash **after worker return / before orchestrator checkpoint** and proves worker execution count remains exactly one after stale recovery;
- role execution is isolated in a child process; parent enforces hard execution timeout and terminates the child on overrun;
- parent updates SQLite heartbeat while child runs;
- semantic <=2, transient <=3, diff <=500, execution <=300s, heartbeat <=300s, spend ==0 are all widening-denied mechanically;
- Owner Gate summaries use bounded reason codes rather than raw worker output.

The MVP execution environment is Linux and uses the multiprocessing `fork` start method. The parent remains the sole SQLite orchestration-state writer; child role workers do not write the orchestration database.

State vocabulary remains exactly the 10 domain-neutral states frozen in v1.

## Exact-head mechanical gate

Independent Lab must Fresh Read PR #82, then on the exact checked-out head run:

`python automation/mechanical_gate_orchestrator_mvp_v2.py --expected-head <PR82_HEAD> --canonical-main <FRESH_MAIN>`

The gate fails if local Git HEAD differs from the supplied exact PR head. The exact-head environment is passed into the E2E test, which requires the DONE result to carry that same candidate head.

## Boundary

No live LLM/provider call, no provider spend, no secret, no protected Keirin data, no workflow dispatch, no main/ruleset/production mutation, no merge and no Runtime activation. Production/Core/Keirin adoption remains a separate later gate.
