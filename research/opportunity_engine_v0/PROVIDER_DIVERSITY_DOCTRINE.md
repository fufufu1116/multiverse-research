# Opportunity Engine v0 — Provider Diversity Doctrine

Status: RESEARCH PROTOTYPE ONLY  
Runtime: OFF

## Purpose

Role diversity is not the same as model diversity, and model diversity is not the same as provider diversity. A single assistant can productively simulate multiple roles, but those roles may share the same training biases, blind spots, refusal patterns, priors, architecture and provider incentives.

Opportunity Engine must therefore avoid treating multiple role labels from the same underlying model as independent votes.

## Independence rules

1. One provider/model playing three roles is one provider-model voice, not three independent models.
2. Two models from the same provider provide more diversity than one model, but they are still not cross-provider review.
3. Material positive/no-blocker confidence should require cross-provider challenge when such a review is available under MULTIVERSE governance.
4. Negative evidence is asymmetric: one evidence-bound HIGH/CRITICAL blocker may stop or downrank a candidate even if it comes from a single provider. Diversity is required to increase confidence, not to permit ignoring warnings.
5. Majority vote never establishes truth. Cross-provider disagreement routes to falsification or new evidence.
6. Cross-provider agreement is still not approval. It only supports readiness for the next governed gate.
7. Provider identity, model identity and role identity must remain explicit in stored results so later calibration can discover systematic model/provider bias.
8. Do not pay for extra providers merely to create cosmetic consensus. Paid review should be used when expected decision value exceeds the cost and cheaper evidence cannot resolve the uncertainty.
9. Prefer official/deterministic evidence over model opinion for legal, financial, safety, administrative or other high-stakes claims.
10. Provider availability is replaceable. Google Gemini, OpenAI, Anthropic or other services are examples of independent model families/providers, not hard-coded strategic dependencies.

## Cost-aware escalation

Default research may begin with one available model/provider for cheap exploration. Escalate when the decision becomes more material, uncertainty remains high, or a candidate approaches real spend/publication/execution. A practical escalation ladder is:

single-model exploration -> same-provider adversarial roles/models -> cross-provider challenge -> mechanical/primary-source falsification -> governed gate.

The Opportunity Engine should learn whether a second or third provider actually changes decisions enough to justify its cost. Provider spend itself becomes an experimentally measured leverage/cost variable.

## Local-compute / MacBook posture

Future owner hardware may increase local repository testing, simulation, data processing, caching, offline evaluation and model experimentation capacity. Local compute must be treated as an optional replaceable capability, not an assumption required for correctness. The engine should remain able to operate in reduced form without the hardware and should not expose protected credentials or bypass MULTIVERSE provider/spend gates merely because local hardware is available.

A future MacBook can therefore function as a private training ground / test range: run larger simulations, replay historical cases, benchmark scoring changes, preflight provider packets and maintain local caches before any governed external or live effect.

## UI note

A future commander/unit UI may visualize provider diversity as different advisers, scouts or strategists, but the visual metaphor must not imply false independence. If three advisers are the same underlying provider/model, the system should make that correlation visible rather than presenting them as three independent endorsements.
