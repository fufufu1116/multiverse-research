# Opportunity Engine v0 — Research Prototype

Status: RESEARCH PROTOTYPE ONLY  
Runtime: OFF

This package builds the decision core before any UI/avatar/gamification work.

## Current rules

A candidate must be rejected or held back when evidence is not verified, mandatory competitor research is incomplete, deception or unverified personal/scandal claims are required, legal risk is too high, the product is largely replaceable by general AI without proprietary/action-completion edge, no payer/purchase intent is clear, a short-lived demand window is too short for the build, a short-lived candidate has no exit trigger, or fewer than three future steps are modeled.

Passing candidates are scored on payer clarity, attention, purchase intent, why-now, why-not-before, proprietary edge, action completion, reusable assets, distribution, competition, incumbent-crush risk, AI substitutability, legal risk, human burden, payback and demand-window fit.

The revenue-route heuristic compares advertising, affiliate, one-time, subscription, transaction-fee and internal-asset routes.

Portfolio ranking implements the doctrine: research broadly, deploy narrowly. At most one passing candidate is assigned `FOCUS`; other passing candidates remain `HOLD_AFTER_RESEARCH` until the focus candidate is resolved.

## Casual-post / brainstorm intake

`casual_intake.py` is a bounded gate for extracting commercially useful fragments from casual conversations without treating the whole conversation as trusted knowledge. It can retain reusable business-model patterns, growth mechanisms, monetization structures, constraints, competitor clues and falsifiers while rejecting sensitive personal data, deceptive/evasive tactics and low-value banter.

Concrete claims from casual chat remain explicitly unverified until researched. Provider terms, resale/licensing rights, prices, fees, competition, legal constraints, support burden and demand must be freshly verified before a retained fragment can advance through the normal Opportunity Engine pipeline.

The repository defines the intake contract but does not have background access to other ChatGPT rooms. Actual automatic cross-chat capture requires an authorized conversation/export/event source. Until then, forwarding a useful post into this lane is valid intake and can be stored as a hypothesis immediately.

See `CASUAL_POST_INTAKE_DOCTRINE.md`, `casual_intake.py`, `test_casual_intake.py`, and `cases/casual_post_reseller_value_add_20260911.json`.

## Scale-path layer

A separate scale model prevents a small opportunity from being mistaken for a durable livelihood. Profit thresholds are policy inputs rather than hard-coded assumptions.

It classifies credible ceilings into functional classes:
- `TACTICAL`
- `SUSTAINING`
- `GROWTH`
- `PORTFOLIO`
- `PLATFORM`

A small candidate can still be useful when it pays back quickly or leaves reusable cash/data/distribution/code, but the system must explicitly show whether there is a path to a user-configured sustaining-profit threshold or a higher-scale system.

Scale analysis also records:
- existing-service coverage;
- custom-build share;
- automation ratio;
- owner hours at the forecast ceiling;
- whether scale eventually requires a team, sales calls or inventory;
- the explicit scale steps;
- the main ceiling blocker;
- reversibility.

High reuse of existing systems and low custom-build share are rewarded. Heavy custom infrastructure and hidden human-scaling requirements are flagged.

See `SERVICE_ASSEMBLY.md` for the existing-system-first architecture.

## Economic ladder

The system should not assume every tactical opportunity must become a large business. The intended ladder is:

1. tactical opportunities can create fast cash, evidence, data, distribution or reusable code;
2. repeated winning patterns can be promoted into a sustaining automated system;
3. only validated repeatable systems should receive deeper investment toward growth/portfolio/platform economics;
4. candidates with a low ceiling and no reusable strategic output should not consume focus merely because they are easy to build.

The owner-facing UI may later map these classes to game/rank metaphors, but the core logic keeps ordinary economic terminology.

## Leverage search / force multipliers

A viable candidate is not considered optimized until a separate leverage search is performed. The search covers distribution, automation, AI, monetization, data, reuse, geography, partners/platforms and infrastructure.

The objective is not maximum complexity. It is more output per owner hour and per yen at risk while keeping the one-person-plus-AI operating model intact.

Leverage options are rewarded when they are verified, low-cost, reversible, heavily reuse existing systems, increase automation, create reusable assets or compound learning. They are rejected or penalized when they require deception, high legal risk, teams, sales calls, inventory, dangerous copying exposure, high recurring fixed cost or vendor lock-in.

Claimed multipliers are not naively multiplied. `leverage.py` uses diminishing credit for stacked options because distribution, conversion, automation and monetization effects often overlap. Real observed effects should later replace estimates through the forecast/outcome learning loop.

See `leverage.py`, `test_leverage.py` and `LEVERAGE_DOCTRINE.md`.

## Bounded output monetization

Multiverse itself does not need to be sold for Multiverse to generate revenue. Selected lower-value outputs may be monetized while the discovery/scoring/learning core stays private.

The current research policy is:
- tactical outputs may be sold as time-bounded signals when they have standalone buyer value;
- sustaining outputs may be sold as bounded playbooks when this does not expose the core advantage;
- growth-class outputs may be considered only for limited/bounded licensing when copy and strategic-leakage risk are low;
- portfolio/platform-class opportunities are presumptively retained internally because their option value is higher;
- proprietary outcome data and the core method are never exposed by default;
- if selling an output would create a dangerous direct competitor against an opportunity we can exploit ourselves, retain it internally;
- do not manufacture an information product merely because an output exists: the output must be independently useful to a real buyer.

This creates a second monetization route: execute the best opportunities internally, while selectively selling lower strategic-value slices of the opportunity stream.

See `exposure.py` for the research classifier and `test_exposure.py` for regression cases.

## Durable demand x enabling wave

The engine must distinguish the durability of an underlying human need from the durability of a particular business format, product or interface.

Examples of enduring need categories may include food/convenience, rest/sleep, health, intimacy/relationships, belonging/status, entertainment/escape, money/security, appearance, learning, mobility and time saving. These are research categories, not an assumption that every market serving them is attractive.

Historical analysis should ask:
1. what underlying need persisted;
2. which delivery mechanism became obsolete;
3. what enabling technology changed cost, access, speed or distribution;
4. where early adopters captured value;
5. what incumbents later commoditized;
6. what durable asset remained after the interface changed.

The target intersection is:

`persistent need x verified enabling wave x unmet last-mile gap x low owner burden x survivable competition`

A centuries-old market is not automatically attractive. Direct operation may still fail the owner's constraints because of licensing, regulation, inventory, premises, high-touch customer service or human labor.

Likewise, a new technology is not treated as a real wave merely because it is fashionable. `durability.py` requires multiple independent adoption signals before a wave can rise above speculative status. The engine should prefer being early to verified adoption, not first into unsupported hype.

This layer is intended to complement short-lived opportunity capture: tactical waves can fund and teach the system, while persistent needs intersecting real platform shifts can produce higher-scale candidates.

See `durability.py` and `test_durability.py`.

## Market dynamics and trajectory

The research model also treats market adoption through a diffusion/immunity/evolution lens. This is a metaphor and analytical frame, not literal biology.

`market_dynamics.py` models spread, host fit, habituation, general-AI substitution, incumbent absorption, mutation, recurrence, network effects, embeddedness and mutual value. Harmful dependence and deceptive retention fail closed.

`trajectory.py` connects those dynamics back to the core opportunity decision so a candidate can be classified as reject/watch, short-window capture-and-exit, test-for-durability or durable-build.

The preferred durable pattern is mutual-value / symbiotic adoption: the customer gains continuing value while the business accumulates legitimate data, integration, distribution or workflow value. Exploitative lock-in is not treated as strength.

## Signals and prediction ledger

`signals.py` defines a common evidence-bearing input for news, search, social, product, advertising, rule changes, service changes and public events. Source-less claims are not treated as evidence.

`forecast_ledger.py` freezes a forecast before outcomes using a deterministic SHA-256 commitment. The forecast records source signals, predicted peak window, expected demand life, likely competitor arrival, likely AI/incumbent absorption, several next actions, monetization hypothesis, kill condition and confidence. Settlement later records observed outcomes. This exists to reduce hindsight bias and build a proprietary prediction-versus-reality history.

## Handoff durability

`HANDOFF_DOCTRINE.md` preserves the strategic doctrine for recovery after chat/session context loss. It is orientation, not CURRENT authority. A future session must Fresh Read canonical GitHub and reconcile repository state before continuing.

## Safety / authority boundary

No live web/SNS/news ingestion, external provider/API call, credential use, purchases, posting, affiliate enrollment, ad spend, personal-data profiling, publication, canonical adoption or Runtime activation is included or authorized by this prototype.