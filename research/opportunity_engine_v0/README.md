# Opportunity Engine v0 — Research Prototype

Status: RESEARCH PROTOTYPE ONLY  
Runtime: OFF

This package builds the decision core before any UI/avatar/gamification work.

## Current rules

A candidate must be rejected or held back when evidence is not verified, mandatory competitor research is incomplete, deception or unverified personal/scandal claims are required, legal risk is too high, the product is largely replaceable by general AI without proprietary/action-completion edge, no payer/purchase intent is clear, a short-lived demand window is too short for the build, a short-lived candidate has no exit trigger, or fewer than three future steps are modeled.

Passing candidates are scored on payer clarity, attention, purchase intent, why-now, why-not-before, proprietary edge, action completion, reusable assets, distribution, competition, incumbent-crush risk, AI substitutability, legal risk, human burden, payback and demand-window fit.

The revenue-route heuristic compares advertising, affiliate, one-time, subscription, transaction-fee and internal-asset routes.

Portfolio ranking implements the doctrine: research broadly, deploy narrowly. At most one passing candidate is assigned `FOCUS`; other passing candidates remain `HOLD_AFTER_RESEARCH` until the focus candidate is resolved.

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

## Safety / authority boundary

No live web/SNS/news ingestion, external provider/API call, credential use, purchases, posting, affiliate enrollment, ad spend, personal-data profiling, publication, canonical adoption or Runtime activation is included or authorized by this prototype.
