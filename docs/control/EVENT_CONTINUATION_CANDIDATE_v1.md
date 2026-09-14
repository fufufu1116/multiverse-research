# Event Continuation Candidate v1

Status: candidate, repository-only, Runtime OFF.

Goal: reduce avoidable idle time between safe repository workflows by preferring completion events over periodic checks. Periodic checks remain a recovery fallback.

Owner-facing mental model: this should behave like an autosave-enabled game. Important continuation state is externalized as work progresses so a chat/executor loss does not mean project-state loss. The analogy is UX only; canonical GitHub remains the authority.

Candidate components:
- completion-event evaluation via `workflow_run`;
- deterministic idempotency key for duplicate suppression;
- fail-closed stopping on upstream failure or Owner Gate;
- repository-only continuation queue model;
- expiring executor lease so another executor can recover abandoned work;
- completion receipts and outcome state;
- idle-time metrics: average wait, maximum wait, ready/leased/gate-blocked counts;
- Runtime OFF enforcement in the queue model.

Target continuation sequence:
1. upstream safe work completes;
2. completion event is detected;
3. result is verified;
4. safe next stage is enqueued once;
5. one executor claims it with a time-bounded lease;
6. executor completes and records outcome, or another executor reclaims after lease expiry;
7. true Owner Gates remain stopped;
8. periodic monitoring exists only as missed-event/recovery fallback.

Current limitation: this PR proves the state machine and event receiver as a Candidate. It does not yet grant authority to persist adopted canonical queue mutations on main or dispatch external providers. Integration/adoption remains separately governed.

This candidate does not activate production, provider, credential, spend, deployment, merge, adoption, or other live authority.
