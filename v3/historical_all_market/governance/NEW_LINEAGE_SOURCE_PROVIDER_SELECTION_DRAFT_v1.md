# Multiverse Keirin — New Lineage Source / Provider Selection Draft v1

Status: PROVIDER RESEARCH DRAFT — NOT AUTHORIZATION / NOT A SCIENTIFIC FREEZE
Date: 2026-08-19 JST

## Goal

Identify a lawful, reproducible and point-in-time transport route for the PRE/decision data required by C1/N1/N2 without assuming that a publicly visible webpage can be bulk-collected or operationally reused.

No provider listed here is admitted until exact rights, data fields, timestamps and transport are verified.

## Required coverage

Ideal provider/feed coverage:

1. immutable race identity / venue / start time / field / withdrawal state;
2. race regime (`STANDARD_ORIGINAL_LINE_KEIRIN` vs `INTERNATIONAL_FIXED_PACER` etc.);
3. rider race-card PRE fields including score/class/style/rates/S/B/H and maneuver counts if available;
4. line formation and order with observation type and timestamp, preferably observed leg-show lineup;
5. bank master context;
6. timestamped weather/wind;
7. actionable pre-decision odds snapshots for all sold official markets;
8. later settlement/result through a strictly separated outcome namespace;
9. contract/terms permitting the intended research, storage, model training and eventual operational use.

A provider need not supply everything if multiple sources can be joined under compatible point-in-time/provenance contracts, but each field must have a single declared source of truth.

## Candidate P0 — JKA / official authorized information-system route

### Evidence

JKA publicly documents VIS / 2028VIS as the central keirin information system and describes data linkage among event operations, betting/payment, information provision and connected sites. The 2028VIS network procurement explicitly includes velodromes, off-track sites, private sites and JKA on a closed network.

### Strengths

- closest possible source of truth;
- likely strongest identity/timing semantics;
- ideal for race regime, official racecard, odds/results if an authorized feed/license is available.

### Unknowns

- no public open-data/API license found in this audit;
- no published self-service feed contract found for an individual research project;
- observed leg-show line data as a structured field not proven;
- costs/eligibility/terms unknown.

### Status

`TOP_PRIORITY_CONTACT_OR_LICENSE_ROUTE_NOT_YET_PROVEN`

A public procurement contact for the information-system department exists, but it is not automatically a data-licensing contact. Do not send an external inquiry without Owner authorization if direct outreach becomes necessary.

## Candidate P1 — authorized/licensed third-party keirin data provider

### Team-Nave

Current public product material states that Team-Nave develops public-racing APIs/database/cloud/betting systems. It currently lists:

- `Cycle Telephone Center Internet Bet API (CTC-API)` for keirin;
- `KeiRin Tips Ai` computer prediction product;
- OddsPark betting API;
- explicit database APIs for horse racing and boat racing.

CTC-API documentation proves a functioning credentialed keirin betting API, but the exposed function page is for bet/deposit/balance operations and does NOT prove a keirin race-data database feed.

The public product list currently does not show a keirin DataBase API analogous to its horse/boat database APIs.

Team-Nave's horse database API documentation explicitly distinguishes business/commercial use as requiring separate consultation/contract, which is useful evidence that provider-side licensing paths can exist; it does not prove equivalent rights for keirin data.

### Questions that would need explicit provider answer

- Is there a licensed keirin race-data feed/API not publicly listed?
- Does it contain historical and live race-card values at point-in-time state?
- Does it contain `H`, maneuver counts, race regime, line grouping/order, and line observation timestamp/type?
- Does it provide odds snapshots, which markets, and server/provider timestamps?
- May data be stored, used for ML training/research and eventual private operational betting decisions?
- Is historical backfill available with true historical PRE state rather than current profile values?
- What are rate limits, retention terms and fees?

### Status

`PROMISING_CONTACT_CANDIDATE_BUT_DATA_FEED_NOT_PROVEN`

## Candidate P1b — official betting / media private sites

Examples of current private betting/media ecosystems may include authorized internet betting services and major keirin media/forecast sites.

These sites are useful for:

- understanding what information modern users receive pre-race;
- benchmarking current AI/forecast products;
- potentially identifying licensed commercial data partners.

They are NOT automatically acceptable collection sources. A consumer UI or authenticated betting account is not a data license or API contract.

Required before admission:

- provider terms permit intended access/storage/use;
- stable transport/API/feed exists;
- point-in-time timestamps are explicit;
- data provenance to official/authorized source is understood.

Status: `BENCHMARK_AND_PROVIDER_DISCOVERY_ONLY`.

## Candidate P2 — specialist forecast / expected-line sources

Professional newspapers, former-rider/expert services and specialist media can be valuable for:

- `PRE_EVENT_EXPECTED_LINE`;
- rider comments;
- forecast/market-intelligence baseline;
- benchmarking human domain knowledge.

But an expected line is a different probability/information object from `LEGSHOW_OBSERVED_LINE`.

Required:

- exact publication timestamp;
- permission/license for storage/model use;
- historical archive semantics;
- source identity retained.

Status: `OPTIONAL_AUXILIARY_SOURCE_NOT_CORE_TRUTH`.

## Rejected / insufficient routes

### Public KEIRIN.JP scraping by default

Not authorized merely because pages are visible. Current site policy imposes reuse restrictions, and no public open-data license was found.

### Post-race reconstruction

Result articles/video-derived line, switch or position trajectory is prohibited as a PRE input for the target race.

### Unofficial scraped datasets without rights/provenance

May be useful for hypothesis discovery only. They do not become canonical training inputs unless upstream provenance, point-in-time state, rights and exact bytes are independently proven.

### Circumvention

No authentication bypass, CAPTCHA/WAF avoidance, rate-limit evasion, endpoint reverse-engineering whose use violates terms, or credential sharing.

## Cross-sport provider benchmark

JRA/JRA-VAN demonstrates a useful governance pattern: structured licensed racing data can have explicit consumer/developer and separate business/commercial-use arrangements. This is a process benchmark only; it does not grant rights to keirin data.

## Current provider decision

No source is yet `AUTHORIZED_FOR_COLLECTION`.

Priority order:

1. determine whether an official/JKA-authorized feed/license path is realistically obtainable;
2. investigate a licensed third-party provider such as Team-Nave for actual keirin data-feed coverage and permitted ML/use rights;
3. if neither covers observed line data, identify licensed specialist source for `PRE_EVENT_EXPECTED_LINE` and decide scientifically whether expected-line is sufficient for C1/N1 or whether the model must wait for prospective observed-line capture through an authorized route;
4. use modern AI/forecast products only as benchmarks until their data/output usage rights and point-in-time semantics are clear.

## External-contact boundary

Directly contacting JKA/providers may reveal information unavailable publicly and is likely the fastest resolution if web research is exhausted. Because it creates an external communication and may imply commercial/licensing discussion, the actual message should not be sent without explicit Owner approval.

No purchase/subscription/contract should be made without Owner approval.

## Parallel work while provider route is unresolved

Safe work that can continue now:

- C0/C1/N1 probability architecture specification;
- Probability Object Contract and cross-market invariants;
- TRAIN/CAL/FINAL validation protocol;
- source-independent parser/interface schemas using synthetic fixtures;
- modern prediction-method benchmark research;
- independent audit package drafting.

Current DEV2000 C remains untouched.
`ECON_HOLDOUT1000 = SEALED`.

END OF DRAFT
