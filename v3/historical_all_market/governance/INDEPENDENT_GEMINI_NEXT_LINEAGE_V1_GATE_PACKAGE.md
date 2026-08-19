# Independent Gemini Audit Package — Multiverse Next-Lineage v1

Audit type: MATERIAL SCIENTIFIC / GOVERNANCE GATE
Date: 2026-08-19 JST
Repository: `fufufu1116/multiverse-research`

## 1. Candidate under audit

`v3/historical_all_market/governance/NEXT_LINEAGE_V1_DESIGN_CANDIDATE.md`

Git blob:
`3c7815dd7f639d632d0aebf49c633c1effeccf2f`

Status before audit:
`NOT FROZEN / NOT EXECUTABLE`

## 2. Exact diagnostic evidence

`STAGE7_AB_POSTMORTEM_EXACT_DIAGNOSTICS_RECEIPT_v1.json`
Git blob:
`fd13575a0eb14b3b01d565646e35a05d3a12f59c`

`NEXT_LINEAGE_STAGE0_DIAGNOSTIC_RECONCILIATION_v1.md`
Git blob:
`18f082ff6f14b0642be1643a5852929161d6e42c`

`NEXT_LINEAGE_DATA_COLLISION_AND_CALENDAR_AUDIT_PLAN_v1.md`
Git blob:
`8f9bc7fd70bca114d814f6fef5ab539d1e504f18`

Parent Stage-7 prereg:
`STAGE7_TIME_SPLIT_SELECTION_VALIDATION_PREREG_v1.md`
Git blob:
`0cb70520777d4ac9d00ddd90b888df1f403c3a7e`

## 3. Closed parent result

Parent lineage result:
`NO_B_VALIDATED_CONFIGURATION`

Settlement bulk was independently authorized for frozen Stage 7.

Segment A Top10 was selected under preregistered rules.
No A_TOP10 configuration passed Segment B.
The Stage-7 evaluator did not open/score Segment C.

For the new lineage, DEV2000 Segment C is now explicitly retired from any new untouched-validation claim because it belonged to the prior lineage and its settlement catalog was physically recovered under the prior audit, even though it was never scored by the selection evaluator.

`ECON_HOLDOUT1000 = SEALED`.

## 4. Key exact postmortem facts

Leading Segment-A path:
- 148 bet races
- stake 18,900 JPY
- return 45,790 JPY
- net ROI +142.275%
- hit tickets = 1
- positive active days 1/15
- positive active ISO weeks 1/4
- 100% of realized return came from one 3rentan ticket
- winning ticket odds 457.9

Segment B G20/SINGLE/FK10 group:
- 44 bet races
- stake 5,100 JPY
- return 0
- net ROI -100%
- hits 0
- positive days 0/8
- positive weeks 0/2

Segment B G25/SINGLE/FK10 group:
- 54 bet races
- stake 6,200 JPY
- return 0
- net ROI -100%
- hits 0
- positive days 0/8
- positive weeks 0/2

A_TOP10 overwhelmingly selected high-odds 3rentan SINGLE tickets.

Interpretation that is ALLOWED before this audit:
- rare-jackpot / return-concentration failure is strongly supported
- temporal stability failed in the observed parent path
- raw-EV overstatement is a material concern, but a causal probability-model failure is not yet proven
- PL misspecification remains an important falsification target, not an established cause

## 5. Prior governance principles reused as candidate inputs

The Multiverse project previously developed, in older closed lines, the following ideas before this latest A/B result:
- sequential bounded search instead of unrestricted Cartesian search
- maximum 64 scientific executions / 12 full policies as a candidate budget
- expanding-window temporal validation
- market-specific promotion, no pooled masking
- 2-car evidence floor around 300 bet races
- 3-car evidence floor around 500 bet races
- >=10 positive-return race events
- one-race concentration limit
- leave-largest-win and top-3-win removal tests
- dependence-aware bootstrap / FWER
- PL as baseline rather than truth
- Equal Stake primary, Kelly sensitivity only after edge validation

These are not cited as proof of correctness. They are evidence that the new candidate is not inventing every safeguard post hoc solely from the latest failure.

## 6. New operational objective requiring hostile review

The Owner clarified that a losing individual day is acceptable if performance is positive and stable across longer horizons such as weeks/months.

The candidate therefore adds explicit weekly/monthly stability gates.

Candidate weekly gate:
- >=12 active ISO weeks
- positive active-week share >=50%
- median active-week net ROI >0
- max consecutive losing active weeks <=4

Candidate monthly gate:
- >=4 active months
- 3/4 positive, or >=60% positive if >4 months
- median active-month net ROI >0
- no one month >60% of total development net profit

Candidate development calendar minimum:
- >=16 calendar weeks
- >=4 calendar months

These values are NOT yet frozen. Challenge them quantitatively.

## 7. Candidate search structure

Hard candidate budget:
- <=64 scientifically distinct Stage1–5 executions
- <=12 full economic policies in final development comparison
- <=3 survivors from any stage

Stage 1:
- F1 PL baseline using frozen sporting probabilities
- F2 at most one dependence-aware joint-order family if scientifically ready and pre-frozen; otherwise do not invent it during the run

Stage 2 max 3:
- identity
- fold-local logistic calibration
- fold-local isotonic subject to support gate

Stage 3 max 2:
- calibrated EV baseline
- deterministic uncertainty/tail-shrunk edge

Stage 4 max 2 filter families × max2 points:
- model disagreement/uncertainty
- odds-tail/price fragility with a result-independent or TRAIN-only threshold

Stage 5 max 3:
- market-specific TOP1 equal stake
- market-specific TOP3 equal stake with same-race cap
- diversified cross-market portfolio only from independently passing markets

Stage 6:
- Equal Stake primary
- fractional Kelly 0.10 sensitivity only after edge validation

## 8. Candidate market-level promotion floors

2-car markets:
- >=300 unique bet races / decisions

3-car markets:
- >=500 unique bet races / decisions

Every promoted market:
- >=10 distinct positive-return race events
- net profit >0
- net ROI >0
- lower dependence-aware 95% net-ROI bound >0
- primary FWER <=0.05
- no market failure hidden by pooled portfolio ROI

Tail hard-gate candidate:
- no single race >=50% total development net profit
- top-1 winning race removed => net profit still >0
- top-3 winning races removed => net profit still >0

Drawdown candidate:
- <=25% normalized starting bankroll

## 9. Candidate inference design

- chronological expanding-window 5 folds
- activity in >=4/5 folds
- positive net ROI in >=3/5 folds
- median fold net ROI >0
- no fold >60% development net profit

Headline uncertainty candidate:
- 10,000 resamples
- calendar-week block or another audited time-aware block method
- fixed seed
- 95% CI
- dependence-aware primary FWER <=0.05

Ticket-level iid bootstrap is prohibited.

## 10. Data-boundary candidate

Before any new dataset is admitted:
- membership-only collision audit
- calendar coverage report
- exposure classification
- unknown exposure = FAIL-CLOSED

Collision checks include DEV2000, old economic datasets, SIM100, Shadow, canaries/probes, and holdout membership where membership can be compared without opening sealed outcome/economic content.

NEXTGEN5000 is NOT automatically admitted. Existing evidence indicates R4501–R5000 begins on 2026-04-29, but its exact end date and all collision classes still require proof.

## 11. Required hostile audit questions

Answer every item explicitly.

A. Is it scientifically legitimate to use A/B failure evidence to redesign a NEW lineage while permanently prohibiting current DEV2000 C and keeping final untouched evidence separate?

B. Is retiring current DEV2000 C from all new-lineage validation claims appropriately conservative, or is a different status required?

C. Are 16 calendar weeks / 4 months sufficient for a system whose operational claim includes weekly/monthly stability? If not, give exact replacement minimums and reasons.

D. Are the proposed weekly gates (12 active weeks, >=50% positive weeks, median weekly ROI >0, <=4 consecutive losing weeks) statistically and operationally defensible? If not, supply exact corrected rules.

E. Are the monthly gates (>=4 months, 3/4 or >=60% positive, median >0, month-profit concentration <=60%) defensible? If too few months, give exact replacement.

F. Do weekly/monthly gates create redundant multiple testing with fold gates? Specify which should be PRIMARY vs descriptive to control researcher degrees of freedom.

G. Is <=64 scientific executions / <=12 full policies sufficiently bounded? If not, give a lower exact cap and stage allocation.

H. Should Stage 1 REQUIRE a non-PL family because D2 is a priority falsification target, or is PL-only acceptable until a scientifically defensible alternative with PRE provenance exists?

I. Are identity/logistic/isotonic an appropriate bounded calibration set? State the exact minimum support needed for isotonic or recommend exclusion.

J. Is an odds-tail gate legitimate when the motivating failure involved an odds-457.9 winner? How must the threshold be defined to avoid post-hoc outcome tuning?

K. Are 300/500 bet-race floors and >=10 positive-return events sufficient for heavy-tail keirin markets? Tighten if needed.

L. Is the hard top-3-wins-removed-positive rule scientifically justified, or overly destructive to genuine sparse-market edge? Give exact alternative if rejected.

M. Is >=50% positive active weeks a valid promotion condition for 3rentan, or does it incorrectly reject a legitimate high-variance positive-EV strategy? Reconcile statistical validity with the Owner's actual objective of useful week/month profitability.

N. Is Equal Stake as primary and FK0.10 sensitivity-only the right risk-policy ordering?

O. Is <=25% drawdown a defensible promotion floor? If not, give exact alternative.

P. Is calendar-week block bootstrap with only the minimum candidate coverage statistically adequate? If not, specify minimum number of weeks and exact preferred resampling unit/method.

Q. Which dependence-aware primary FWER method is appropriate for this bounded staged search? State a concrete recommended primary method.

R. Are Wide and frame markets correctly withheld from initial promotion while still allowed as diagnostics?

S. Does the data collision/calendar plan sufficiently prevent rebranding exposed data as untouched?

T. Is there any route by which the candidate could silently tune against current DEV2000 C or `ECON_HOLDOUT1000`? If yes, give exact blocker correction.

U. Does this design actually optimize for generalizable weekly/monthly profitability rather than merely creating more gates that can themselves be overfit?

V. Identify the strongest plausible explanation that the apparent A edge was spurious.

W. Identify the most dangerous remaining assumption in the next-lineage candidate.

X. State evidence that would falsify each major design hypothesis: PL adequacy, calibration benefit, edge shrinkage benefit, weekly/monthly stability, and tail robustness.

## 12. Required issue format

For every issue:
- ISSUE ID
- affected section
- severity: `P0_BLOCKER`, `P1_MATERIAL`, `P2_NON_BLOCKING`
- failure scenario
- exact correction text / replacement numeric value
- scientific/statistical reason

Do not reward project effort, ambition, complexity, or desired profitability.
Assume a hidden flaw may exist.
A negative answer is acceptable.

## 13. Required explicit decisions

Return each exactly as one of `ACCEPTABLE`, `REVISE`, `REJECT` unless another value is requested:

- RESULT_AWARE_NEW_LINEAGE_BOUNDARY
- DEV2000_C_RETIREMENT
- CALENDAR_COVERAGE_MINIMUM
- WEEKLY_STABILITY_GATE
- MONTHLY_STABILITY_GATE
- FIVE_FOLD_TEMPORAL_GATE
- SEARCH_BUDGET_64_12
- STAGE1_PL_BASELINE_AND_F2_POLICY
- CALIBRATION_SET
- EDGE_TRANSFORM_SET
- ODDS_TAIL_GATE_SEMANTICS
- MARKET_SPECIFIC_300_500_10_FLOORS
- TOP1_TOP3_JACKPOT_ROBUSTNESS
- EQUAL_STAKE_PRIMARY
- FK10_SENSITIVITY_ONLY
- MAX_DRAWDOWN_25PCT
- TIME_AWARE_BOOTSTRAP_DESIGN
- PRIMARY_FWER_METHOD
- DATA_COLLISION_CALENDAR_PLAN
- NEXTGEN5000_AUTO_ADMISSION = MUST_BE `PROHIBITED` unless exact audit evidence is already sufficient
- CURRENT_DEV2000_C_NEW_LINEAGE_USE = MUST_BE `PROHIBITED`
- ECON_HOLDOUT1000 = MUST REMAIN `SEALED`

## 14. Final verdict

Exactly one:

`APPROVE`
`CONDITIONAL APPROVE`
`REJECT`

Interpretation:
- APPROVE: candidate may be converted into a frozen new-lineage protocol after exact approved corrections (if none) and code-level preflight; does NOT authorize HOLDOUT opening or wagering.
- CONDITIONAL APPROVE: NOT FREEZABLE; corrections require re-audit.
- REJECT: redesign required.

End with:
- strongest case AGAINST
- plausible spurious-success explanation
- most dangerous assumption
- unresolved unknowns
- exact next action allowed

`ECON_HOLDOUT1000 = SEALED`
