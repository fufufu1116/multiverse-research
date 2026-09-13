# Chat Streaming Interruption Resilience v1

Status: repository-only candidate
Owner-facing scope: all MULTIVERSE chats/lanes
Runtime: OFF

## Problem class
Treat unexpected response streaming interruption as distinct from conversation/context capacity exhaustion.

A chat may stop streaming even when capacity is healthy. Keeping the chat UI open or closed must not be treated as a reliability control.

## Invariants

1. **Streaming failure is a delivery failure, not a project-state rollback.**
   Durable project state lives outside the in-flight reply.

2. **Canonical-before-narration for consequential work.**
   Before a gated, one-shot, irreversible, spend-bearing, credential-bearing, production, provider, or otherwise consequential action, persist the exact authority/intent envelope first.

3. **Receipt-before-report after an attempt.**
   Immediately after an external/one-shot attempt, persist attempt/result/consumption evidence before producing a long Owner-facing report.

4. **Fail closed after interruption.**
   If it is uncertain whether an action occurred, do not repeat it. Fresh Read canonical records and external status first.

5. **Resume from first uncommitted step.**
   Recovery order is: canonical main -> Control/current lane -> durable authority/attempt receipts -> external status if needed -> first step lacking durable evidence.

6. **Do not make Owner repeat receipted actions.**
   A valid Owner token/action already durably receipted remains available according to its original scope even if the chat response stream was interrupted afterward.

7. **Compact Owner-visible streaming.**
   Prefer concise final reports. Put detailed logs, large tables, and machine evidence in repository artifacts/comments unless Owner asks to see them inline.

8. **Micro-checkpoint long tool sequences.**
   Persist semantic progress after meaningful mutation/effect boundaries so interruption loses at most the current owner-free micro-step.

9. **No chat-open dependency.**
   Never claim that leaving a chat open guarantees continuation or that closing it causes interruption.

10. **Platform boundary honesty.**
    MULTIVERSE can harden recovery and delivery discipline but cannot directly repair OpenAI/ChatGPT transport, network, or client streaming infrastructure from this repository.

## One-shot safety state machine

`NOT_AUTHORIZED -> AUTHORIZED_NOT_ATTEMPTED -> ATTEMPTED_CONSUMED -> RESULT_RECORDED`

- Persist `AUTHORIZED_NOT_ATTEMPTED` before launch.
- An attempted one-shot moves immediately to `ATTEMPTED_CONSUMED`, regardless of PASS/FAIL.
- After interruption, an uncertain external side effect must be resolved by status/evidence; never move backward and never retry speculatively.

## Output discipline

For normal execution reports:
- short main result first;
- current blocker/Owner action only when genuine;
- detailed evidence by canonical pointer;
- Sengoku progress dashboard last when required by Owner convention.

## Immediate binding example

Gate #445 / PR #444 has durable Owner authority receipt comment `5653910031`. Therefore a later streaming interruption does not require Owner to resend the authorization token. Recovery must resume from that receipt and fresh external/canonical status.

## Non-authority

This protocol grants no Runtime, provider, credential, spend, Build, Retry, Auditor, merge/adoption, production, legal, betting, or other effect authority by itself.

`RUNTIME: OFF`
