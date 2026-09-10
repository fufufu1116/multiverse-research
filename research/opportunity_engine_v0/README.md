# MULTIVERSE Opportunity Engine v0 — research prototype

Status: RESEARCH_PROTOTYPE_ONLY  
Runtime: OFF  
External calls: NONE  
Spend: NONE  
Canonical adoption: NOT AUTHORIZED BY THIS PROTOTYPE

## Purpose

This prototype turns the current business-search doctrine into deterministic gates before any UI work:

1. verify the event/opportunity with evidence;
2. require competitor research before adoption;
3. ask why the opportunity exists now and why it was not already common;
4. check direct competitors, substitutes, free AI/big-tech replacement, and reusable existing systems;
5. reject products that a general AI can almost fully replace unless there is a proprietary edge or real action completion;
6. model who actually pays and whether purchase intent exists;
7. look 3–7 steps ahead, including competitor entry, official replacement, demand decay and exit;
8. allow short-lived opportunities when build time and payback fit inside the remaining demand window;
9. reject deceptive scarcity, misleading longevity, or unverified personal/scandal claims;
10. choose a likely revenue route (advertising, affiliate, one-time, subscription, transaction fee, or internal asset);
11. retain reusable data, distribution, measured outcomes and implementation components when a short-lived opportunity dies.

## Core principle

Research broadly; deploy narrowly. Reuse existing systems before building. UI/gamification is downstream of this engine.

A candidate is not approved just because its score is high. This prototype is evidence for a later governed decision. Material adoption remains an Owner Gate under the repository's current governance.

## Inputs

All 0–5 fields are explicit research judgments, not claims of objective truth. They must be backed by a research packet before a real candidate is promoted.

Important fields include:

- `buyer_clarity`
- `attention`
- `purchase_intent`
- `why_now`
- `why_not_before`
- `competitor_pressure`
- `incumbent_crush_risk`
- `ai_substitutability`
- `proprietary_edge`
- `action_completion`
- `reusable_asset`
- `distribution`
- `legal_risk`
- `human_burden`
- build time, demand lifetime, three profit scenarios, 3–7 future steps, and an exit trigger.

## Hard rejects

The current prototype fails closed when any of the following is true:

- evidence is not verified;
- competitor/substitute/big-tech/"why not already common" research is incomplete;
- deception is required;
- unverified personal/scandal claims are required;
- legal risk is too high;
- a general AI can replace the product and there is no real proprietary or action-completion edge;
- there is no clear payer/purchase intent;
- build time consumes too much of a short-lived demand window;
- a short-lived opportunity lacks an exit trigger;
- fewer than three future steps have been considered.

## Decisions

- `REJECT`: hard gate failed.
- `WATCH`: evidence exists but economics/score are not strong enough.
- `MICRO_TEST`: small reversible test is justified.
- `BUILD_CANDIDATE`: low-case payback and score justify preparing a governed candidate; this is not canonical adoption authority.

## Unit economics

`simulate_unit_economics` converts visitors, conversion rate, contribution profit, advertising revenue and costs into a simple profit estimate. It is deliberately small so low/base/high scenarios can be generated without pretending forecasts are facts.

## Deliberately excluded from v0

- live web/SNS/news ingestion;
- automatic purchases, posting, ad spend or affiliate enrollment;
- credentials;
- personal-data profiling;
- automated legal conclusions;
- UI, avatars, game mechanics;
- canonical adoption or Runtime activation.

Those should remain separate layers and separate gates.
