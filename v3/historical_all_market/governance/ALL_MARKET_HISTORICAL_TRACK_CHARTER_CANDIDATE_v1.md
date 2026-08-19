# Multiverse Hybrid v3.0 — All-Market Historical Economic Track Charter Candidate v1

Status: `CANDIDATE / NOT YET INDEPENDENTLY AUDITED / NO ECONOMIC CANDIDATE SCORED`

## 1. Objective

Return Multiverse to its original economic research objective:

**Use only information available before race start to estimate event/ticket probabilities, compare them with the market prices that existed for the historical race, select or reject wagers, construct ticket portfolios, allocate bankroll, and then settle against later official result/payout data.**

The target is NOT winner-hit rate alone. Winner probability is an upstream component of multi-position / ticket probability.

The long-run operating goal is same-day PRE decision support. Multi-day future forecasting is not a present requirement.

## 2. Lineage boundary

This is a NEW research track. It does NOT reopen, rescue, or rewrite closed v2.7 / v2.8 / v2.9 lineages.

Their failures and diagnostics remain evidence. Their trial counts and closures remain immutable.

Shadow250-v2 also remains preserved with selected=0 / screen=0 / prospective-v3-trial=0. Its source engineering is reusable later for same-day live operation, but Shadow250 is NOT the current primary scientific line.

## 3. Immutable historical inputs reused

Only already-frozen / hash-verifiable development artifacts may enter this track initially:

- frozen DEV2000 Universe;
- frozen DEV2000 PRE table;
- frozen Candidate A + B1a historical Prediction Lock CSV;
- later-authorized DEV2000 RESULT-only artifact;
- RESULT provenance containing per-race raw payload SHA-256;
- SHA-bound historical `showResult` raw quarantine;
- old Economic-E1 prelock only as governance/scientific precedent, not as authority to score newly admitted markets.

No model refit is authorized by this Charter.

## 4. Lessons explicitly absorbed from Shadow250-v2

The following are imported as process/safety principles, NOT as new predictive features:

- Fail-Closed on ambiguity;
- raw-byte SHA / provenance binding;
- source-role separation;
- no silent fallback;
- parser/runtime canaries before bulk execution;
- explicit canonicalization;
- evidence receipts for both PASS and failure;
- independent Gemini audit before scientifically consequential promotion;
- frozen implementation identities (Git blobs / SHA-256);
- no implicit repair after outcome inspection.

## 5. All-market scope

A race may contribute only the wager markets that are actually present/sold in its SHA-bound historical raw page.

Candidate market universe:

1. `3rentan` — 3連単
2. `3renhuku` — 3連複
3. `2shatan` — 2車単
4. `2shahuku` — 2車複
5. `wide` — ワイド
6. `2wakutan` — 2枠単, only when sold
7. `2wakuhuku` — 2枠複, only when sold

No unsold market may be synthesized.

## 6. Buying-method scope

Elementary ticket probabilities are the primitive layer. Buying methods are portfolio constructors over elementary tickets.

The track must eventually admit and compare, under preregistered finite candidate families:

- single-ticket / one-point;
- top-K ticket sets;
- BOX;
- 流し / wheel (axis + opponents, including ordered-position variants where meaningful);
- formation (position-specific candidate sets);
- multiple tickets inside one market;
- cross-market portfolios;
- explicit NO-BET.

A portfolio constructor may never alter the underlying elementary ticket probability or official payout definition.

## 7. Sequential stages

### Stage 0 — All-market raw recovery / market-availability audit

Purpose: data recovery only.

Allowed:
- verify each raw payload against frozen provenance SHA;
- detect which markets were actually sold;
- parse complete closing-price catalogs;
- preserve Wide price as `[low, high]` interval;
- parse official refund catalogs;
- parse market timestamps;
- record field size and market availability;
- record frame-table metadata without yet using it for model probability.

Prohibited:
- model probability calculation;
- EV calculation;
- ROI / profit scoring;
- threshold selection;
- bankroll simulation;
- candidate ranking.

Stage-0 diagnostic/recovery work consumes no new economic scientific trial.

### Stage 1 — Ticket-probability engine

Preregister and validate market probability mappings before economic scoring.

Baseline candidates may include:
- frozen winner probabilities + Plackett–Luce (PL) joint-order baseline;
- explicitly preregistered conditional second/third models;
- pairwise/listwise/direct-market alternatives where justified.

Required additions:
- Wide pair hit probability = probability both cars occupy top 3;
- frame exacta/quinella probability = sum of distinct-car order/top2 probabilities mapped into the official frame ticket.

No result/payout may fit probability parameters.

### Stage 2 — Price semantics / calibration / uncertainty

Must explicitly handle:
- point odds markets;
- Wide interval odds without silently replacing them by a midpoint;
- overround / implied probability diagnostics;
- calibration and uncertainty.

Primary Wide decision semantics must be preregistered. Conservative lower-bound EV is a candidate; midpoint may be sensitivity only unless separately justified and audited.

### Stage 3 — Edge / decision families

Finite preregistered candidates may include:
- raw EV;
- implied-probability edge;
- log-odds edge;
- capped / winsorized edge;
- calibrated/shrunk/Bayesian edge;
- uncertainty-adjusted edge.

No best-looking threshold may be selected after seeing the same evaluation outcomes without proper development/validation separation.

### Stage 4 — Race / market quality and NO-BET gates

Possible factors must be preregistered and validated, including field size, model uncertainty, disagreement, odds completeness, abnormal flags, and market quality.

### Stage 5 — Ticket portfolio / buying-method construction

Evaluate finite preregistered constructors, including single, top-K, BOX, wheel/流し, formation and cross-market portfolios.

Correlation between tickets from the same race must be modeled at the race-outcome level; ticket count is not independent diversification.

### Stage 6 — Bankroll / risk allocation

Evaluate bankroll paths and capital allocation with at least:
- fixed unit baseline;
- fractional-risk candidates (including fractional Kelly only if scientifically justified);
- per-ticket cap;
- per-race exposure cap;
- cross-market exposure cap;
- tail / high-odds cap where justified;
- reserve / no-bet behavior.

Report ROI, profit, hit behavior, max drawdown, longest losing sequence, ruin/depletion risk, turnover, and concentration in top winning races.

### Stage 7 — Time-based walk-forward / untouched validation

No final strategy may be promoted from pooled in-sample economic fit alone.

Only after historical development/validation survives may the project return to same-day Shadow Live using timestamped PRE prices.

## 8. Anti-cherry-picking / evidence rules

- finite candidate families must be frozen before their scored comparison;
- all tested candidates and thresholds must be logged;
- failed candidates cannot be resurrected because later data look favorable;
- market verdicts must be reported individually before cross-market portfolio aggregation;
- a strong aggregate cannot hide a failing market;
- extreme EV is never trusted automatically;
- report sensitivity to removal of largest winning races;
- report profit concentration;
- report max drawdown and chronological bankroll path;
- missing market/price data are not imputed unless a future preregistered lineage explicitly allows it.

## 9. Data/firewall rules

- `ECON_HOLDOUT1000` remains SEALED.
- No HOLDOUT Result / Payout / Price / scoring.
- No future/real-time data are required for the current historical track.
- Historical current-profile replay remains prohibited.
- Payout/RESULT cannot be used to refit Candidate A/B1a or to manufacture market probability.
- A raw page may be re-parsed offline because its exact bytes are already content-addressed and frozen.

## 10. Immediate gate

Before full 2000-race Stage-0 recovery:

1. freeze this Charter Candidate;
2. freeze exact legacy-asset reuse registry;
3. freeze exact all-market registry;
4. freeze exact Stage-0 offline parser Git blob;
5. demonstrate canaries across stored field-size/market-availability patterns;
6. obtain independent Gemini audit.

Until that audit, no new all-market economic scoring or strategy optimization is authorized.
