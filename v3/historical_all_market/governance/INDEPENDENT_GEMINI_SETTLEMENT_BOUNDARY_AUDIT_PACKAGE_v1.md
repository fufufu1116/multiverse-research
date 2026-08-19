# Multiverse Hybrid v3.0 — Independent Gemini Settlement-Boundary Audit Package v1

## AUDIT INSTRUCTION

Act as an independent hostile scientific/governance auditor. Do not optimize, rescue, or redesign this experiment unless a defect requires it. Your job is to decide whether the frozen pre-Settlement state is sufficiently outcome-blind and deterministic to authorize the first DEV2000 economic Settlement opening.

Repository: `fufufu1116/multiverse-research`

**AUDIT THIS EXACT SNAPSHOT ONLY:**

`a0360b1c5622b0664e8180186a40eca9827fc63e`

Do NOT audit the later commit that adds this audit prompt. The snapshot above is the frozen evidence state to be judged.

Date: 2026-08-19 JST
Track: All-Market Historical Economic Track

---

## 1. Boundary being audited

The project has completed and frozen all pre-outcome economic decision layers for DEV2000:

- Stage 0: historical closing-price recovery
- Stage 1: ticket-probability engine
- Stage 2: price/probability EV diagnostics
- Stage 3: finite elementary-ticket filter family
- Stage 4: two-model conservative consensus and race-level disagreement gates
- Stage 5: finite portfolio/buying-method templates
- Stage 6: finite bankroll/stake policies
- Stage 7: chronological A/B/C selection and untouched-test protocol, preregistered before Settlement

No economic Settlement, payout-based scoring, realized ROI, or post-outcome policy tuning has yet been performed in this track.

This audit asks whether **DEV2000 Settlement bulk may now be opened solely for the already-frozen Stage-7 historical evaluation**.

`ECON_HOLDOUT1000` is outside this authorization and MUST remain SEALED.

---

## 2. Prior independent-audit condition

The prior Stage-0 independent Gemini re-audit ended `APPROVE`, but explicitly held:

- PRICE-only 2000-race bulk: authorized
- Settlement bulk: `MUST_REMAIN_PROHIBITED`
- the prohibition persists until Stage 1–6 decision rules are frozen
- `ECON_HOLDOUT1000 = SEALED`

The Stage 1–6 prerequisite is now claimed satisfied. This audit is the one high-level boundary review before lifting the DEV2000 Settlement prohibition for the frozen Stage-7 evaluation only.

---

## 3. Frozen evidence and exact bindings

### Stage 2 canonical catalog

Canonical Stage-2 output SHA-256:

`34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc`

Canonical size: 557,500,538 bytes
Canonical rows: 4,000 race/model rows

Stage-2 engine Git blob:

`9f240c758cb2596e9c67a5214c4e2c610eb82769`

Stage-2 rules include:

- normal markets: `raw_EV = model_probability * closing_odds - 1`
- Wide primary price = frozen `low` odds
- Wide `high` price = diagnostic only
- no RESULT / PAYOUT / Settlement / realized ROI

### Exact local Stage-2 reconstruction

Because the Drive connector cannot directly download the 557 MB canonical file, No.3 reconstructed Stage 2 from the exact frozen Stage-0 and Stage-1 inputs using the exact Stage-2 semantics.

Receipt:

`v3/historical_all_market/runtime_receipts/STAGE2_LOCAL_EXACT_RECONSTRUCTION_RECEIPT_v1.json`

It records:

- Stage-0 PRICE input SHA-256 `2ca98097f74e5282fdc9c91629083f39bef4dafb94a1fc4f7e510acadefc407b`
- Stage-1 probability input SHA-256 `6348d9af2a535578cf454afca52ea2c944cb6c50cab87f6e6ffa75149880b526`
- reconstructed Stage-2 SHA-256 exactly equals canonical SHA `34ad32...530dc`
- exact byte size 557,500,538
- rows 4,000
- no outcome access

### Stage 3

Preregistration:

`v3/historical_all_market/governance/STAGE3_TICKET_FILTER_FAMILY_PREREG_v1.md`

Git blob:

`ba4175bb044bcacfa66a7b8d089e92c04762b2e6`

Frozen profiles, common to all seven markets:

- `P00`: EV >= 0.00 and shape-edge ratio >= 1.00
- `P05`: 0.05 / 1.05
- `P10`: 0.10 / 1.10
- `P20`: 0.20 / 1.20
- `P35`: 0.35 / 1.35
- `P50`: 0.50 / 1.50
- `P100`: 1.00 / 2.00

No profile is selected as profitable pre-Settlement.

A prior Colab/Drive runtime interruption in expanded Stage-3 CSV writing was classified and superseded; scientific semantics were unchanged.

Resumable Stage-3 runtime blob:

`91922c3f2f3da4f2af00e8e6ffcba2c6eaf041df`

Local auto-completion receipt:

`v3/historical_all_market/runtime_receipts/STAGE3_AUTO_LOCAL_COMPLETION_RECEIPT_v1.json`

Status `PASS`, 2,000 races / 4,000 race-model rows, no profile promotion, no outcome access.

### Stage 4

Preregistration:

`v3/historical_all_market/governance/STAGE4_CONSENSUS_AGREEMENT_GATE_PREREG_v1.md`

Git blob:

`f5bb38e97dd2543842308f9b8ee401957d2e5216`

Ticket-level conservative consensus:

- `consensus_probability = min(p_candidate_a, p_b1a)`
- `consensus_raw_ev = min(raw_ev_candidate_a, raw_ev_b1a)`
- `consensus_shape_edge_ratio = min(shape_edge_ratio_candidate_a, shape_edge_ratio_b1a)`

Canonical race disagreement:

`TV3 = 0.5 * sum_t |pA_3rentan(t) - pB_3rentan(t)|`

Frozen gates:

- `G0`: no TV cap, but two-model ticket consensus still required
- `G20`: TV3 <= 0.20
- `G25`: TV3 <= 0.25
- `G30`: TV3 <= 0.30

Observed pre-result gate pass counts on 2,000 races:

- G0 = 2000
- G20 = 1261
- G25 = 1694
- G30 = 1821

These counts are structural diagnostics only, not profitability results.

### Stage 5

Preregistration:

`v3/historical_all_market/governance/STAGE5_PORTFOLIO_TEMPLATE_PREREG_v1.md`

Git blob:

`f13b5aa5584d260d30032c269cfc205a312f2426`

Seven deterministic portfolio templates:

1. `SINGLE`
2. `TOP1_PER_MARKET`
3. `TOP3_PER_MARKET`
4. `TOP5_PER_MARKET`
5. `BOX3`
6. `WHEEL1x3`
7. `FORMATION_2x3x4`

Car structural ranking uses conservative win score `min(Candidate A, B1a)`, tie-broken by mean probability then car number.

Frame markets reuse the exact Stage-1 unique 7/8/9-car frame-map inference from official published frame-ticket key sets. Same-frame frame tickets are allowed only when actually published by the official catalog and allowed by the template.

Stage-3 × Stage-4 × Stage-5 = 196 pre-bankroll configurations.

### Stage 6

Preregistration:

`v3/historical_all_market/governance/STAGE6_BANKROLL_RISK_POLICY_PREREG_v1.md`

Git blob:

`7dc0ac09440755ad1c43959237c0d975be11b245`

Starting historical bankroll: 100,000 JPY
Minimum unit: 100 JPY
No borrowing / no negative bankroll
Chronological race-by-race settlement

Frozen stake policies:

1. `FLAT100`
2. `RACE2PCT_EQUAL`
3. `FK10_R2`: 10% fractional Kelly, per-ticket cap 0.25%, race cap 2%
4. `FK25_R3`: 25% fractional Kelly, per-ticket cap 0.50%, race cap 3%

Wide always sizes from frozen low odds.

Full frozen search space:

`7 Stage-3 profiles * 4 Stage-4 gates * 7 Stage-5 templates * 4 Stage-6 policies = 784 configurations`

No configuration has yet seen realized Settlement.

### Stage 7

Preregistration:

`v3/historical_all_market/governance/STAGE7_TIME_SPLIT_SELECTION_VALIDATION_PREREG_v1.md`

Git blob:

`0cb70520777d4ac9d00ddd90b888df1f403c3a7e`

Immutable DEV2000 chronological split by `dev_index`:

- A_DEVELOPMENT = 1..1000
- B_VALIDATION = 1001..1500
- C_UNTOUCHED_TEST = 1501..2000

A evaluates all 784 and shortlists top 10 only among configurations satisfying minimum bet-race / drawdown / bankroll gates.

B evaluates only A_TOP10 and freezes one `FINAL_DEV2000_CONFIGURATION` only if B is positive and passes the frozen risk gates.

C is scored exactly once only after that final configuration is frozen.

C has frozen verdict categories and a 10,000-replicate whole-race bootstrap with deterministic seed `20260819`.

No post-C rescue tuning is allowed in the lineage.

`ECON_HOLDOUT1000` remains separate and SEALED regardless of C result.

### Consolidated pre-Settlement acceptance receipt

`v3/historical_all_market/runtime_receipts/STAGE456_PRESETTLEMENT_ACCEPTANCE_RECEIPT_v1.json`

Snapshot head commit:

`a0360b1c5622b0664e8180186a40eca9827fc63e`

It binds Stage 3–7 frozen state and states:

- result_access = false
- payout_access = false
- settlement_access = false
- realized_roi_computed = false
- scientific_trial_count = 0
- `ECON_HOLDOUT1000 = SEALED`
- next boundary = independent high-level audit before Settlement opening

### Settlement parser proposed for post-authorization use

`v3/historical_all_market/kdreams_settlement_recovery_v1.py`

Git blob:

`b8b8ab0e0904541bd6fc45e7fe415d323e63ec45`

Role: official refund/Settlement extraction only.
It is physically separate from the PRICE parser and is not authorized for use unless this audit authorizes the Settlement boundary.

---

## 4. Hostile audit questions A–L

### A. Stage-3 pre-outcome freeze

Is the seven-profile Stage-3 family finite, deterministic, market-common, and sufficiently outcome-blind? Is there any hidden path by which Stage-3 thresholds were chosen using realized outcomes?

### B. Stage-4 consensus and disagreement

Is the `min/min/min` two-model conservative consensus scientifically defensible as a preregistered robust gate rather than hindsight tuning? Is TV3 on normalized 3rentan a defensible race-level disagreement metric? Are G0/G20/G25/G30 outcome-blind and finite?

### C. Stage-5 portfolio semantics

Are SINGLE, TOP-K-per-market, BOX3, WHEEL1x3, and FORMATION_2x3x4 sufficiently deterministic to reproduce? Are car/frame ranking and same-frame handling correct and outcome-blind? Identify any ambiguity that could change realized betting decisions after Settlement opens.

### D. Stage-6 bankroll / risk semantics

Are the four frozen stake policies fully specified, including 100-JPY rounding, race/ticket caps, proportional scaling, bankroll chronology, no-borrowing, and Wide-low-odds usage? Identify any material ambiguity that could allow outcome-conditioned implementation discretion.

### E. Stage-7 chronological validation

Does A(1000) -> B(500) -> one-shot C(500) adequately prevent direct C contamination? Is the rule that C cannot influence selection explicit enough? Is the bootstrap procedure sufficiently preregistered?

### F. Multiple-comparison / finite-search governance

The search space is 784 configurations. Does evaluating 784 on A, narrowing to top 10, validating those on B, then selecting one for one-shot C create any P0/P1 scientific flaw that should block Settlement? Distinguish ordinary development multiple-comparison risk from contamination of untouched C.

### G. Exact local reconstruction

Is the local Stage-2 reconstruction acceptable evidence given that exact frozen inputs and exact engine semantics reproduce the **exact canonical Stage-2 SHA-256 and byte size**? Is the Stage-3 local completion acceptable given that it uses this exact reconstructed Stage-2 state and the already-frozen Stage-3 semantics without outcome access?

### H. Outcome firewall through freeze

Based on the snapshot, is there any evidence that economic RESULT/PAYOUT/Settlement or realized ROI entered Stage 3–7 design before freeze? If there is a concern, identify exact file/path/field and severity.

### I. Settlement executable role

Is settlement parser blob `b8b8ab0e0904541bd6fc45e7fe415d323e63ec45` acceptable for the narrow post-authorization role of recovering official refund/Settlement values while keeping PRICE semantics physically separate?

### J. DEV2000 Settlement authorization

Given that Stage 1–6 decisions and Stage 7 validation are now frozen, may DEV2000 Settlement bulk be opened and used for the frozen Stage-7 evaluation only?

### K. HOLDOUT state

Confirm that `ECON_HOLDOUT1000` must remain SEALED and that this audit must not authorize access to it.

### L. Authorization scope

If you approve, state explicitly that approval covers **only**:

1. DEV2000 Settlement bulk recovery,
2. frozen Stage-7 A/B/C historical evaluation,
3. generation of final DEV2000 OOS result/receipt.

Approval must NOT authorize model refitting, changing Stage 3–7 rules, post-C rescue tuning, HOLDOUT access, live production, or real-money wagering.

---

## 5. Required issue report

List every remaining issue under exactly one severity:

- `P0_BLOCKER`
- `P1_MATERIAL`
- `P2_NON_BLOCKING`

For each issue provide exact evidence/path and the minimum remediation required.

Do not invent issues merely to make the audit look strict.

---

## 6. REQUIRED EXPLICIT DECISIONS

Return each item exactly with one allowed decision token.

1. `STAGE3_FREEZE = ACCEPTABLE | NOT_ACCEPTABLE`
2. `STAGE4_FREEZE = ACCEPTABLE | NOT_ACCEPTABLE`
3. `STAGE5_FREEZE = ACCEPTABLE | NOT_ACCEPTABLE`
4. `STAGE6_FREEZE = ACCEPTABLE | NOT_ACCEPTABLE`
5. `STAGE7_VALIDATION_PROTOCOL = ACCEPTABLE | NOT_ACCEPTABLE`
6. `STAGE2_EXACT_LOCAL_RECONSTRUCTION = ACCEPTABLE | NOT_ACCEPTABLE`
7. `STAGE3_LOCAL_AUTO_COMPLETION = ACCEPTABLE | NOT_ACCEPTABLE`
8. `FINITE_784_CONFIGURATION_SEARCH_AND_SELECTION = ACCEPTABLE | NOT_ACCEPTABLE`
9. `DEV2000_SETTLEMENT_BULK = AUTHORIZED_FOR_FROZEN_STAGE7_ONLY | NOT_AUTHORIZED`
10. `SETTLEMENT_PARSER_b8b8ab0e = ACCEPTABLE | NOT_ACCEPTABLE`
11. `ECON_HOLDOUT1000 = SEALED`
12. `STAGE7_REALIZED_SCIENTIFIC_TRIAL_COUNT_BEFORE_OPEN = 0`

Then give exactly one final verdict token:

`APPROVE`

or

`CONDITIONAL APPROVE`

or

`REJECT`

---

## 7. Interpretation of APPROVE

Even `APPROVE` authorizes only DEV2000 Settlement bulk plus the already-frozen Stage-7 A/B/C evaluation.

It does **not** authorize:

- `ECON_HOLDOUT1000` access
- Candidate A or B1a refit
- new threshold/gate/template/stake policy after outcomes
- reusing Segment C for rescue tuning
- Shadow/live promotion
- production wagering
- real-money betting

END OF AUDIT PACKAGE
