# Multiverse Hybrid v3.0 — Next-Lineage Data Collision & Calendar Audit Plan v1

Status: PRE-EXECUTION AUDIT PLAN — NO OUTCOME ACCESS AUTHORIZED
Date: 2026-08-19 JST

## Purpose

Before designating any new historical development/validation universe, prove its calendar coverage and exposure status without looking at outcomes to choose favorable races.

## Required candidate inputs

For every candidate universe considered, materialize only membership metadata first:
- race_id
- race_date
- venue_code
- immutable source/universe identifier

No RESULT/PAYOUT/Settlement may be opened merely to perform this collision audit.

## Collision sets

Candidate race IDs must be compared against, at minimum:

1. DEV2000 all 2000 races
2. current DEV2000 Segment C membership even though it remains unscored
3. all older economic TUNE/VALID/DEV datasets whose outcomes were previously used
4. SIM100 diagnostic races/dates
5. Shadow250-v1/v2 membership if any race was ever selected
6. result canaries/probes and ad-hoc result-access test races
7. `ECON_HOLDOUT1000` membership, if and only if membership identity can be compared without opening any sealed Price/PAYOUT/RESULT content

## Classification

Each candidate race receives exactly one exposure label:

- `UNTOUCHED_MEMBERSHIP_CANDIDATE`
- `EXPOSED_DEVELOPMENT_ONLY`
- `PROHIBITED_HOLDOUT_COLLISION`
- `PROHIBITED_SIM_SHADOW_COLLISION`
- `UNKNOWN_EXPOSURE_FAIL_CLOSED`

Unknown exposure may not be silently treated as untouched.

## Calendar requirements candidate

The development/validation universe must report:
- first race date
- last race date
- inclusive calendar days
- distinct race dates
- distinct ISO weeks
- distinct calendar months
- race count per week/month

Design candidate minimum:
- >=16 calendar weeks covered
- >=4 calendar months represented

Final market-specific active-week/month counts are evaluated later from actual decisions; membership coverage alone does not prove active betting opportunity.

## NEXTGEN5000 status

Frozen parent SHA:
`dd2045cc609c37c08a9e65ba4f80ab121803d0749440a7023394e431a1678781`

Existing evidence shows its R4501–R5000 batch begins on 2026-04-29. The exact final locked date and full collision status have not yet been proven here. Therefore NEXTGEN5000 is **NOT automatically admitted** as the new long-horizon development universe.

A separate exact artifact inspection must prove:
- first/last locked date
- 5000 unique race IDs
- collision counts by the above classes
- whether the calendar target is met

## Selection rule

If a candidate historical universe fails calendar coverage or has material unknown exposure, do not cherry-pick a favorable subset after outcomes are known.

Instead:
- reject that candidate universe, or
- classify it wholly/partially as exposed development under a result-independent membership rule,
- designate a genuinely untouched future/OOS set separately.

## Firewall

This plan authorizes no new result retrieval, payout retrieval, price retrieval, model fitting, scoring, HOLDOUT access, or wagering.

`ECON_HOLDOUT1000 = SEALED`
