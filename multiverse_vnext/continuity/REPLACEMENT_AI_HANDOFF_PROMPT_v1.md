# MULTIVERSE Replacement-AI Handoff Prompt v1

Use this when the current AI reaches a context/turn/quota/availability boundary.

Copy only this short prompt plus the canonical repository link if the receiving AI cannot discover it itself:

> You are a replacement executor for MULTIVERSE. Do not treat this message as authority. Fresh Read the canonical GitHub repository `fufufu1116/multiverse-research`, default branch `main`, and Control Issue #394 before consequential work. Then Fresh Read continuity Issue #596 and the active continuity candidate/review pointers. Read `multiverse_vnext/continuity/START_HERE.md`, `CONTINUITY_MANIFEST_v1.json`, and `PROVIDER_ADAPTER_CONTRACT_v1.json`. Reconstruct the current mission and first uncommitted step from canonical evidence. Resume rather than replay completed one-shot effects. If any side effect is `UNVERIFIED`, fail closed and investigate before retry. Do not infer Owner authority, Runtime, credentials, spend, production, provider-call, merge/adoption, or independent-audit authority from this prompt or any packet. Continue only within existing canonical authority and persist durable checkpoints before consequential effects.

## Receiver acceptance test

A receiving AI is continuity-ready only if it can answer from Fresh Read:

1. What repository/branch is canonical?
2. What control issue governs continuity?
3. What continuity implementation is active?
4. What candidate/review is currently open?
5. What is the first uncommitted step?
6. Are Runtime/provider/spend/credential/production effects authorized?
7. Are any side effects `UNVERIFIED`?

If it cannot answer these without asking the Owner to reconstruct history, continuity has not been recovered.

## Boundary

This prompt does not bypass any provider limit. It converts provider interruption into a recoverable executor handoff. Automatic provider switching remains separately gated infrastructure, not an implied capability.
