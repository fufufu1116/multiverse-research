# Multiverse Keirin — Provider / Rights / Benchmark Matrix v1

Status: PUBLIC-RESEARCH MATRIX — NOT COLLECTION AUTHORIZATION / NOT SCIENTIFIC FREEZE
Date: 2026-08-19 JST

## Purpose

Separate four questions that must never be conflated:

1. Does a source visibly contain useful keirin information?
2. Is there a machine-transportable interface/feed?
3. Is historical point-in-time state preserved with timestamps?
4. Are storage, model-training and operational reuse rights explicitly compatible with the project?

Public visibility alone answers only question 1.

## A. JKA / KEIRIN.JP / VIS

Provider class: `OFFICIAL_UPSTREAM`

Verified public evidence:
- JKA operates VIS for keirin business operations.
- 2028VIS contains common data-link functions and an internet-information subsystem including KEIRIN.JP.
- 2028VIS network documentation states that data centers and sites including velodromes, off-track outlets, private sites and JKA are connected through a closed network.
- KEIRIN.JP provides public race/search/race-card surfaces.

Rights evidence:
- KEIRIN.JP site policy states that text, illustrations, photos, video and other information are legally protected; copying/reuse is not allowed except uses permitted by law such as private copying/quotation.
- commercial use beyond private use without authorization is explicitly rejected.

Current verdict:
- semantic/source-definition research: `ALLOWED_FOR_AUDIT`
- automated bulk historical collection for ML: `NOT_AUTHORIZED`
- open/public self-service data license: `NOT_FOUND`
- official authorized feed may exist upstream/for contracted parties, but public access terms are `NOT_PROVEN`.

Potential route:
- formal inquiry to JKA / appropriate information-system or licensing contact, only after Owner approval.

## B. Team-Nave

Provider class: `AUTHORIZED_THIRD_PARTY_CANDIDATE`

Verified public evidence:
- Team-Nave currently provides keirin products including `KeiRin Tips Ai` and `CTC-API`.
- It provides full database APIs for horse racing and boat racing, including explicit business-plan licensing language for commercial use.
- Public product listings reviewed in this audit do NOT expose an equivalent keirin database API.
- CTC-API is an internet betting API and must not be misclassified as a keirin historical structural-data feed.

Current verdict:
- keirin prediction product: `CONFIRMED`
- keirin betting API: `CONFIRMED`
- keirin database / timestamped line / H / odds-history feed: `NOT_PROVEN`
- ML research / commercial reuse terms for any non-public keirin feed: `NOT_PROVEN`

Potential route:
- exact product/coverage inquiry after Owner approval.

## C. WINTICKET

Provider class: `MODERN_OPERATIONAL_PREDICTION_BENCHMARK`

Verified public evidence:
- WINTICKET states that its keirin AI prediction model uses tens of thousands of historical race results and lineup (`並び`) information.
- It exposes a `line power` feature that numerically evaluates line strength.
- WINTICKET states that AI prediction, odds, rider information, past race information and other decision-support information are provided to users.

Scientific meaning:
- This is independent operational evidence that modern keirin prediction practice considers lineup/line structure valuable.
- It does NOT prove that Multiverse N1 is correct, that PL is wrong, or that any particular line feature improves out-of-time likelihood.

Current verdict:
- design benchmark: `ADMISSIBLE_AS_EXTERNAL_CONTEXT`
- training-data source: `NOT_ADMITTED`
- prediction-output harvesting for model training: `NOT_AUTHORIZED`
- future clean external comparator: `POSSIBLE_ONLY_WITH_EXPLICITLY_COMPATIBLE_ACCESS/USE SEMANTICS`

## D. Team-Nave KeiRin Tips Ai

Provider class: `MODERN_OPERATIONAL_PREDICTION_BENCHMARK`

Verified public evidence:
- marketed as fully computer-generated keirin prediction based on learned keirin data;
- publishes values described as probabilities involving top-3 outcomes.

Scientific meaning:
- supports maintaining an external benchmark family for top-3 probability-oriented systems if lawful prediction snapshots can ever be acquired prospectively.
- marketing examples and past-hit examples must never be used as scientific performance evidence.

Current verdict:
- architecture/market landscape reference: `ADMISSIBLE`
- validated comparator accuracy: `NOT_ESTABLISHED`
- automatic collection/training reuse: `NOT_AUTHORIZED`

## E. Cross-sport provider lessons

Team-Nave's horse-racing and boat-racing products demonstrate a useful rights/transport pattern:
- paid API;
- documented schema;
- historical/real-time interfaces;
- separate business-use contract language.

This is evidence for what a scientifically transportable keirin provider contract SHOULD look like, not evidence that the same keirin product currently exists.

## Required minimum coverage before a provider may be admitted

For C1/N1 sporting development:
- race identity;
- active riders;
- race regime;
- point-in-time line grouping/order OR an explicitly labeled expected-line object;
- exact source timestamp;
- raw provenance identity/hash;
- existing sporting PRE fields or enough raw inputs to reproduce them;
- historical point-in-time H/B/S and maneuver fields if included.

For N2 / economic live transport:
- all above as applicable;
- actionable odds snapshot at a preregistered decision timestamp;
- historical development snapshots generated under the same semantics;
- explicit distinction between decision price and final settlement payout.

For all provider classes:
- permission/license compatible with storage, automated processing, model training/evaluation, and intended operational use;
- no requirement to evade authentication, CAPTCHA, WAF or rate limits;
- stable identity/timestamp/version fields;
- reproducible failure handling.

## Current source verdict

`NO_PROVIDER_YET_ADMITTED_FOR_NEW_LINEAGE_COLLECTION`

Reason:
No currently verified public candidate simultaneously proves structural PRE coverage, historical point-in-time semantics, machine transport, and compatible reuse/training rights.

This is a source/rights blocker, not evidence that the information does not exist.

END
