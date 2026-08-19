# Multiverse Hybrid v3.0 — Independent Gemini Governance Re-Audit
## All-Market Historical Economic Track — Stage 0 Remediated v2

Repository: `fufufu1116/multiverse-research`

Audit snapshot commit (audit THIS snapshot, before this prompt file itself):
`3a6453576b00d7715b05caa11bac3db42c8a2701`

Parent independent audit artifact blob:
`af11fac1ab7115ae376f2109141669a1ef088408`

Parent verdict: `CONDITIONAL APPROVE`

This is a hostile independent re-audit. Do not silently repair or infer acceptance.
Do NOT evaluate profitability. Do NOT access ECON_HOLDOUT1000.

---

## 1. Scientific state at this snapshot

- All-Market Historical Track scientific trial count = `0`
- bulk 2000-race PRICE recovery = `NOT STARTED`
- bulk SETTLEMENT recovery = `NOT STARTED`
- Stage 1 ticket-probability modeling = `NOT STARTED`
- Stage 2 EV/price-rule evaluation = `NOT STARTED`
- Stage 5 portfolio construction = `NOT STARTED`
- bankroll simulation = `NOT STARTED`
- economic candidate evaluated = `false`
- ROI computed for this new track = `false`
- `ECON_HOLDOUT1000 = SEALED`
- HOLDOUT RESULT/PAYOUT/Price access = `false`
- Shadow250-v2 remains separate and preserved at selected=0 / screen=0 / prospective-v3 trial=0.

The immediate question is ONLY whether Stage-0 PRICE-only bulk recovery may begin.

---

## 2. Parent audit issues to re-adjudicate

### ISSUE-ALLM-01 — core-market hard requirement / selection bias
Parent severity: `P1_MATERIAL`.

Parent required correction:
- do not reject a race merely because a specific market is absent;
- detect each market independently;
- recover only actually present/sold markets.

### ISSUE-ALLM-02 — Price/Settlement firewall absent
Parent severity: `P0_BLOCKER`.

Parent required correction:
- separate Price Recovery executable from Settlement Recovery executable;
- Price output must contain no RESULT/PAYOUT/refund;
- Settlement use must remain post-rule-freeze only.

### ISSUE-ALLM-03 — exact 5-car canary missing
Parent severity: `P1_MATERIAL`.

Parent required correction:
- run a 5-car raw canary and issue evidence.

---

## 3. Remediation binding

Canonical remediation record:
`v3/historical_all_market/governance/ALL_MARKET_STAGE0_REMEDIATION_RECEIPT_v2.json`
Git blob:
`5f9660219eb35c0038dad67ad4c39f8c0bec5925`

### PRICE executable
Path:
`v3/historical_all_market/kdreams_price_catalog_recovery_v1.py`

Exact Git blob:
`f94a08a3ea7c0a4f110dc0df82433eecc25b0cf8`

Tested-source SHA-256:
`aa2b533c192d176680c30d92a7c66dd5681cc24f53eeacf232aaef062a3a1ca1`

Role:
`MARKET_AVAILABILITY_AND_CLOSING_PRICE_ONLY`

It outputs:
- raw SHA provenance
- independent per-market availability
- actually sold market list
- inferred active car-number set
- closing-price catalogs
- per-market odds timestamps
- raw frame labels when frame markets are sold
- Wide `[low, high]` interval without midpoint

It does NOT parse or emit:
- refund table
- RESULT
- PAYOUT
- settlement values
- model probability
- EV
- ROI

### SETTLEMENT executable
Path:
`v3/historical_all_market/kdreams_settlement_recovery_v1.py`

Exact Git blob:
`b8b8ab0e0904541bd6fc45e7fe415d323e63ec45`

Tested-source SHA-256:
`8454d5016f57b8b1a23e035c42b4737d4824fdb8c05ddf452dd9b35b91ebe8b8`

Role:
`OFFICIAL_REFUND_SETTLEMENT_ONLY`

It does NOT parse/emit closing-odds catalogs.
Its operational use is explicitly:
`POST_RULE_FREEZE_SETTLEMENT_ONLY`.

Bulk Settlement recovery is still `PROHIBITED` now.

Firewall self-check:
`v3/historical_all_market/runtime_receipts/ALL_MARKET_STAGE0_FIREWALL_SELF_CHECK_v1.json`
Git blob:
`dfc6a4d1e48fc13c6afacbe589fe3f761800d42a`
Status: `PASS`.

---

## 4. ISSUE-ALLM-01 remediation: independent market presence + active sold car set

The PRICE executable no longer hard-requires the legacy four core car markets + Wide.
Each of the seven markets is detected independently and only present markets are parsed.

Synthetic missing-market test:
- start with exact archived 7-car raw;
- remove Wide content + Wide status nodes only;
- parser does NOT reject the whole race;
- remaining sold markets are recovered normally.

However, remediation testing found an additional historical page structure important for bulk correctness:

Raw SHA:
`75aae0b328db67a5bec995e7eec25ecf63e5797e35f83ba12c689972c74aeb35`
Canonical page:
`https://keirin.kdreams.jp/toyohashi/racedetail/4520260304010005/`

Its numeric odds catalogs correspond to an actually sold/active six-car set:
`[1,2,3,4,6,7]`

Recovered complete counts:
- 3連単 = 120 = 6P3
- 2車単 = 30 = 6P2
- 3連複 = 20 = C(6,3)
- 2車複 = 15 = C(6,2)
- Wide = 15 = C(6,2)

Therefore the PRICE parser no longer uses nominal pre-race field size as the primary bulk completeness invariant.
Instead:
1. infer `active_car_numbers` from the actual ticket keys in each sold car-number market;
2. require all sold car-number markets to agree on the same active-car set;
3. require every sold car-number catalog to contain the complete combinatorial ticket set for that inferred active-car count;
4. `expected_n_cars` remains optional and is used only as an external canary assertion (e.g. the known 5-car canary), not as the normal bulk rule.

A synthetic removal of one numeric price from an otherwise complete catalog is rejected Fail-Closed as incomplete.

Price regression evidence:
`v3/historical_all_market/runtime_receipts/ALL_MARKET_STAGE0_PRICE_PARSER_REGRESSION_v3.json`
Git blob:
`441200deaca73f0830d978cbc8ae0b870f2b9c76`
Status: `PASS`.

Gemini must decide whether this active-sold-car-set rule is scientifically preferable and sufficient for Stage-0 bulk recovery, or whether another invariant is required.

---

## 5. Ticket-identity repairs discovered during remediation

These are parser semantic corrections, not strategy tuning. No EV/ROI/model candidate was evaluated.

### 5.1 3連単 matrix orientation
The old combined parser interpreted Kdreams 3連単 matrix axes as:
- row = second place
- column = third place

Regression against official ticket/refund semantics showed this was reversed.

Corrected semantics:
- fixed table header = first place
- column header = second place
- row header = third place

Checks after correction:
- archived 7-car raw: `1-2-3` closing odds = `3.4`
- archived 9-car raw: `2-5-7` closing odds = `38.4`

The latter matches the semantic ticket that settled at 3,840 yen per 100 yen in the separate settlement regression; this is used only as ticket-key parser consistency evidence, not ROI scoring.

Gemini must determine whether this is a valid ticket-identity repair and whether it requires any additional pre-bulk canary.

### 5.2 3連複 rowspan continuation
A historical raw exposed a state bug:
a two-number row can establish a new second-car group even when that row's price cell is blank. The following one-number rows inherit that second car.

Old behavior updated the second-car state only after requiring a nonblank price, causing duplicate/misidentified tickets.

Corrected behavior updates rowspan grouping state before blank-price filtering.
The problematic raw now recovers the exact complete 6-active-car catalogs listed above.

Gemini must decide whether this parser correction is acceptable for bulk Stage 0.

---

## 6. Exact archived 7-car / 9-car regression evidence

### 7-car
Race ID:
`3820260410010003`

Archived raw SHA:
`24551faf351c8216b3d4ceda249b9a369ecdae62f0baf87dcfe91f979ac46285`

PRICE counts:
- 3連単 210
- 2車単 42
- 3連複 35
- 2車複 21
- Wide 21

Frame markets absent.
Active car set = `[1,2,3,4,5,6,7]`.
PASS.

### 9-car
Race ID:
`2620260409010001`

Archived raw SHA:
`fb83738b6d2e88f6b56bb6dc5647c1f8803932c3c2709d8c93fb7bfcee987c54`

PRICE counts:
- 3連単 504
- 2車単 72
- 3連複 84
- 2車複 36
- Wide 36
- 2枠単 33
- 2枠複 18

Active car set = `[1,2,3,4,5,6,7,8,9]`.
PASS.

---

## 7. ISSUE-ALLM-03: 5-car canary evidence and exact question

Canonical legacy 5-car canary race:
`2320260324030005`
(Toride, 2026-03-26, 5R)

Legacy E1 recorded archived raw SHA:
`7ec10e859838091a3bec6d51711cacde36607cef2771eb2dfc3d9872cfffe9d0`

That archived gzip could not be re-addressed through the current Drive connector's folder-indexing interface during this remediation. Do NOT infer that it is lost or altered; only exact re-fetch through the current connector was unavailable.

Therefore an independent GitHub Actions canary fetched the CURRENT official historical page for the SAME canonical race and ran the exact bound PRICE parser.

Evidence:
`v3/historical_all_market/runtime_receipts/ALL_MARKET_STAGE0_FRESH_OFFICIAL_5CAR_PRICE_CANARY_v1.json`
Git blob:
`55f58be453563bcf2ed7cfe3cc9b2c42007fe79c`

Exact PRICE parser blob used:
`f94a08a3ea7c0a4f110dc0df82433eecc25b0cf8`

Result: `PASS`

Observed active cars:
`[1,2,3,4,5]`

Counts:
- 3連単 60
- 2車単 20
- 3連複 10
- 2車複 10
- Wide 10
- frame markets absent

No RESULT/PAYOUT/refund/EV/ROI output.

Latest fresh raw SHA:
`a2cfc26e3e7891391e59ab1ac69b43216a655493310269e7d55a459bbd056934`

It does NOT equal the legacy archived raw SHA.
Moreover repeated fresh official fetches of the same URL produced different fresh raw SHA values while the same 5-car price structure/counts remained stable, showing that the live historical HTML contains dynamic bytes.

Gemini MUST choose exactly one for ISSUE-ALLM-03:

`FRESH_OFFICIAL_SAME_RACE_5CAR_CANARY_SATISFIES_STAGE0_STRUCTURE_REQUIREMENT`

or

`EXACT_ARCHIVED_5CAR_RAW_MUST_BE_RELOCATED_BEFORE_BULK`

If the latter, bulk PRICE recovery remains prohibited and state the exact reason byte identity is required for the canary despite 7/9 archived regression plus same-race fresh official 5-car structure PASS.

---

## 8. Settlement parser dead-heat / multi-refund invariants

Settlement regression evidence:
`v3/historical_all_market/runtime_receipts/ALL_MARKET_STAGE0_SETTLEMENT_PARSER_REGRESSION_v1.json`
Git blob:
`47dea8164154242726577a6c996c8ebc6815ae9d`

Status:
`PASS_TEST_ONLY_OPERATIONALLY_LOCKED`

Verified on archived 7/9 raw structure.
Synthetic invariants:
- distinct additional valid refund ticket is preserved;
- same ticket + same refund may collapse idempotently;
- same ticket + conflicting refund is `FAIL_CLOSED`.

This does NOT authorize bulk settlement recovery.

Gemini must explicitly confirm that Settlement remains forbidden operationally until Stage 1–6 decision rules are frozen, even if PRICE-only Stage 0 bulk is approved.

---

## 9. Hostile questions

A. Is ISSUE-ALLM-01 fully resolved by independent market presence plus inferred active sold-car-set completeness, without introducing a new selection bias?

B. Should nominal pre-race field size be forbidden as a bulk hard count invariant when the odds page itself exposes a smaller internally complete active sold-car set?

C. Is cross-market active-car-set equality + exact combinatorial catalog completeness sufficient Fail-Closed validation?

D. Is ISSUE-ALLM-02 fully resolved by the exact separate executable blobs and separate outputs?

E. Does the mere physical presence of RESULT/PAYOUT elsewhere in the shared SHA-bound post-race raw remain acceptable when the PRICE executable contains no parser/output path for those fields?

F. Is the 3連単 second/third-axis correction a valid ticket-identity repair rather than outcome-driven tuning?

G. Is the 3連複 rowspan state correction a valid structural parsing repair?

H. Does the fresh official same-race 5-car canary satisfy ISSUE-ALLM-03, or is archived-byte identity mandatory?

I. Are repeated fresh SHA changes of the same official page consistent with dynamic HTML and therefore evidence that fresh-vs-archived raw SHA mismatch alone should not invalidate a structural canary?

J. May Stage-0 PRICE-only recovery now run across the 2000 historical development races using their existing SHA/provenance-bound archived raws, with trial count remaining zero?

K. Must PRICE bulk output exclude every settlement/refund field and be stored in a separate artifact namespace? Confirm.

L. Must Settlement bulk remain prohibited until all Stage 1–6 decision rules are pre-registered/frozen? Confirm.

M. Should a post-bulk PRICE recovery quality report be required before Stage 1, including counts of recovered races, per-market availability, active-car-count distribution, Fail-Closed exclusions, and zero access to settlement output?

N. If any newly encountered raw structure fails the exact parser, confirm Fail-Closed diagnosis/remediation + re-audit rather than silent fallback.

---

## 10. Required explicit decisions

Return each exactly as ACCEPTABLE / NOT_ACCEPTABLE or the requested enum.

1. `ISSUE-ALLM-01`: RESOLVED / NOT_RESOLVED
2. `ISSUE-ALLM-02`: RESOLVED / NOT_RESOLVED
3. `ISSUE-ALLM-03`: choose exactly one of the two enums in Section 7
4. PRICE parser blob `f94a08a3...`: ACCEPTABLE / REQUIRES_CORRECTION
5. SETTLEMENT parser blob `b8b8ab0e...` firewall role: ACCEPTABLE / REQUIRES_CORRECTION
6. active sold-car-set inference: ACCEPTABLE / NOT_ACCEPTABLE
7. 3連単 ticket-axis correction: ACCEPTABLE / NOT_ACCEPTABLE
8. 3連複 rowspan correction: ACCEPTABLE / NOT_ACCEPTABLE
9. PRICE-only 2000-race Stage-0 bulk recovery: AUTHORIZED / NOT_AUTHORIZED
10. Settlement bulk now: MUST_REMAIN_PROHIBITED / MAY_RUN_NOW
11. Stage-0 scientific trial count = 0: ACCEPTABLE / NOT_ACCEPTABLE
12. `ECON_HOLDOUT1000 = SEALED`

If PRICE bulk is authorized, state the exact mandatory output firewall and post-bulk quality gates before Stage 1.

---

## 11. Issue format

For every new/residual issue:
- ID
- exact file/section
- failure scenario
- impact on market availability / ticket identity / price / probability / EV / settlement
- exact correction
- severity: P0_BLOCKER / P1_MATERIAL / P2_NON_BLOCKING
- re-audit required: YES / NO

---

## 12. Final verdict

Return EXACTLY one:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

`APPROVE` means ONLY:
- exact remediated Stage-0 PRICE recovery design is accepted;
- PRICE-only bulk recovery of the 2000 historical development races may begin;
- trial count remains zero;
- a post-bulk recovery/quality audit must occur before Stage 1.

It does NOT authorize:
- Settlement bulk before Stage 1–6 decision-rule freeze;
- Stage 1 ticket-probability modeling;
- Stage 2 EV optimization;
- Stage 5 portfolio construction;
- bankroll optimization;
- HOLDOUT access;
- live wagering.

Under every verdict, `ECON_HOLDOUT1000` remains `SEALED`.
