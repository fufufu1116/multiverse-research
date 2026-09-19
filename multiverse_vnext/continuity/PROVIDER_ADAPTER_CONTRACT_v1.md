# MULTIVERSE Provider Adapter Contract v1

Status: `CANDIDATE_ONLY`
Runtime: `OFF`
Parent/control: #394
Implementation: #596
Candidate: #597

## Purpose

Define the smallest provider-neutral interface needed for a future failover executor without binding MULTIVERSE to ChatGPT, Gemini, Claude, Codex, or any other provider.

This document is an interface contract, not an authorization to call providers, create credentials, spend money, or enable Runtime.

## Authority model

- Canonical GitHub state is authoritative.
- A provider adapter is an executor, never an authority source.
- A continuity packet is a bootstrap artifact, never authority.
- Provider-reported success is not downstream-effect proof.
- Existing Owner Gates, independent review, and production controls remain in force.

## Adapter capabilities

A compatible provider adapter MAY expose these logical operations:

1. `accept_bootstrap(packet)` — ingest a compact continuity packet without treating it as authority.
2. `fresh_read(canonical_refs)` — read the canonical repository/control surfaces.
3. `reconstruct_state()` — derive current mission/state from Fresh Read plus packet navigation hints.
4. `execute_owner_free_step(step)` — perform only a step already permitted by existing authority.
5. `emit_checkpoint(checkpoint)` — persist durable progress before consequential effects when required.
6. `emit_receipt(receipt)` — record execution result and observed downstream state.
7. `report_blocker(blocker)` — return an explicit blocker instead of guessing or expanding authority.

No adapter may infer permission from capability availability.

## Provider-neutral state machine

```text
AVAILABLE
  |
  | task assigned
  v
BOOTSTRAP -> FRESH_READ -> STATE_RECONSTRUCTED
                         |
                         +--> AUTHORITY_CHECK --blocked--> BLOCKED
                         |
                         v
                    EXECUTABLE_STEP
                         |
          +--------------+--------------+
          |                             |
      no side effect              consequential effect
          |                             |
          v                             v
      CHECKPOINT                    CHECKPOINT
          |                             |
          v                             v
       EXECUTE --------------------> VERIFY
                                      |
                           +----------+----------+
                           |                     |
                         VERIFIED            UNVERIFIED
                           |                     |
                           v                     v
                         RESUME               FAIL_CLOSED
```

Provider interruption or free-tier exhaustion transitions the executor to `UNAVAILABLE`, not the project to an error state:

```text
EXECUTOR_ACTIVE -> PROVIDER_UNAVAILABLE -> HANDOFF_READY
HANDOFF_READY -> REPLACEMENT_PROVIDER -> BOOTSTRAP
```

## Required handoff payload

The handoff MUST preserve, at minimum:

- protocol version;
- repository and canonical branch;
- observed canonical SHA;
- canonical control and implementation pointers;
- active candidate/review pointers;
- current mission;
- completed steps;
- first uncommitted step;
- side-effect states and receipts;
- blockers and Owner Gates;
- exact next action;
- generated timestamp.

Secrets are prohibited.

## Fail-closed rules

The adapter MUST stop rather than guess when:

- canonical state cannot be Fresh Read;
- the packet SHA conflicts with current canonical state and the difference is consequential;
- a one-shot side effect is `UNVERIFIED`;
- required authority is missing or ambiguous;
- an external dependency is unavailable and no owner-free recovery path exists.

A provider outage or free-tier limit alone is not permission to replay an uncertain side effect.

## Free-tier / provider exhaustion semantics

A provider's context, turn, quota, rate, or availability limit is modeled as executor transport state. It does not invalidate canonical project state.

The system therefore aims for:

`provider limit -> checkpoint -> compact handoff -> replacement executor -> Fresh Read -> resume`

not:

`provider limit -> Owner reconstructs project -> research stops`.

This contract does not bypass provider limits. It reduces their blast radius.

## Future implementation boundary

A later implementation may add concrete adapters or automatic routing, but only after separately authorized infrastructure exists for provider credentials, runtime execution, spend controls, logging, and governance. Those are outside this candidate.
