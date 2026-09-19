# MULTIVERSE Provider-Independent Continuity v1

**Status:** CANDIDATE_ONLY  
**Parent/control:** Issue #394  
**Implementation issue:** #596  
**Runtime:** OFF

## Purpose

ChatGPT conversation limits, context exhaustion, streaming interruption, temporary unavailability, or free-tier turn limits must not become a project-state failure. Chat is a replaceable execution surface. The durable project state lives outside the chat and is reconstructed by Fresh Read.

This protocol makes the minimum recovery packet small enough to hand to another AI such as Gemini, while keeping authority and evidence outside the packet itself.

## Core invariants

1. **CHAT != CANONICAL STATE.** Conversation history is disposable working context.
2. **PACKET != AUTHORITY.** A continuity packet is a pointer/bootstrapping aid, never an authority receipt.
3. **FRESH READ BEFORE ACTION.** A replacement AI must re-read the canonical repository/control surfaces before consequential work.
4. **RESUME, DON'T REPLAY.** Continue from the first uncommitted step; never repeat an already receipted one-shot effect.
5. **UNCERTAINTY FAILS CLOSED.** If side-effect state is uncertain, mark it `UNVERIFIED`, inspect canonical evidence, and do not retry blindly.
6. **NO SECRET MIGRATION.** Credentials, tokens, private keys, cookies, and personal secrets never enter continuity packets or Git.
7. **PROVIDER NEUTRAL.** The protocol names capabilities and evidence, not a mandatory AI vendor.
8. **NO AUTHORITY EXPANSION.** Switching providers does not create Runtime, spend, credential, production, merge/adoption, Buildkite, or external-provider authority.

## Recovery levels

### L0 — Chat survives

Keep working normally. Persist important intent/checkpoints before consequential or long-running work.

### L1 — Context/turn pressure

Compress the working context into the compact bootstrap packet. Preserve canonical pointers, current task, checkpoint, blockers, and next action. Drop transcript bulk first.

### L2 — Chat unavailable / limit reached

Open the continuity packet in another AI. The replacement AI performs Fresh Read of the canonical sources and resumes from the first uncommitted step.

### L3 — Primary AI unavailable

Use any compatible executor that can read the repository and follow this protocol. Gemini is one possible replacement, not a hard dependency.

### L4 — Canonical service unavailable

Do not invent state from memory. Use the latest locally retained verified packet/checkpoint if available, mark freshness explicitly, and remain fail-closed for consequential effects until canonical state can be re-read.

## Compact bootstrap packet

The generated packet should contain only:

- protocol version;
- generation timestamp;
- repository and default branch;
- latest observed main SHA;
- canonical control issue(s);
- current continuity implementation issue;
- active candidate/review pointers;
- current task;
- last committed checkpoint;
- uncommitted/uncertain side effects;
- blockers / Owner Gate requirements;
- exact next action;
- a warning that all volatile claims require Fresh Read.

It should not contain the full chat transcript.

## Replacement-AI startup procedure

1. Read this protocol.
2. Read the compact bootstrap packet.
3. Fresh Read the repository default branch and every cited canonical control/review record.
4. Compare the packet's observed SHA/state with Fresh Read.
5. If they differ, discard stale volatile fields and rebuild the packet from Fresh evidence.
6. Identify the first uncommitted step.
7. Check authority boundaries and any Owner Gate.
8. Continue only within existing authority.
9. Persist the next checkpoint before any consequential one-shot/external effect.
10. After an interruption, verify side-effect state before resuming or retrying.

## ChatGPT free-tier exhaustion handling

A provider usage limit is treated as **executor unavailability**, not as project loss. The project must therefore be able to continue from GitHub without requiring the Owner to reconstruct the conversation.

The protocol does **not** bypass or extend a provider's usage limits. It reduces dependence on those limits by externalizing state and making replacement execution deterministic.

Automatic provider switching is intentionally not part of this candidate because it would require external credentials, provider calls, and runtime authority. A later adapter may implement it under the existing governance model.

## Checkpoint format

Every durable checkpoint should answer:

```text
checkpoint_id:
created_at:
canonical_base_sha:
mission:
completed_steps:
first_uncommitted_step:
side_effects:
  - effect:
    state: NONE | ATTEMPTED | VERIFIED | UNVERIFIED
    receipt:
    downstream_proof:
owner_gate:
blockers:
next_action:
```

`VERIFIED` requires downstream evidence appropriate to the effect. Provider transport receipts such as `PUBLISHED`, `SUCCESS`, or `DEPLOYED` are not sufficient by themselves.

## Machine-assisted packet generation

Use:

`python tools/build_continuity_packet.py`

The generator reads public canonical GitHub surfaces and emits a small Markdown packet. It is deliberately dependency-free and can run outside ChatGPT. A replacement AI can also reproduce the same Fresh Read manually if Python execution is unavailable.

## Acceptance criteria for v1

- A new AI can identify the repository, canonical branch, control issue, active continuity issue, and current candidate work without chat history.
- A provider outage/limit does not require the Owner to summarize prior work.
- Stale packet data is explicitly detected by SHA/state comparison.
- Uncertain external effects cannot be silently replayed.
- No secrets are required in the packet.
- No new Runtime/provider/spend/credential authority is created.
- The implementation remains useful if ChatGPT, Gemini, or another provider is replaced.

## Explicit non-goals

- bypassing provider rate/usage limits;
- scraping or automating a provider account without authorization;
- storing credentials in Git;
- automatic wagering or other consequential external actions;
- self-adoption, self-merge, or independent-audit bypass;
- treating chat output, generated packets, or provider status as canonical authority.
