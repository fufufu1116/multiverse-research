# Multiverse Hybrid v3.0 — Independent Gemini Audit Package
## All-Market Historical Economic Track — Stage 0 v1

## Audit posture

Perform a hostile, independent governance/data-engineering audit. Do not optimize for approving ChatGPT's design. Do not silently repair defects. If exact repository artifacts/blobs cannot be inspected, do not return APPROVE.

Repository: `fufufu1116/multiverse-research`

This is a NEW research track. It does **not** reopen v2.7/v2.8/v2.9. It does not score ECON_HOLDOUT1000.

### Scientific state at audit entry

- new All-Market Historical Track scientific trial count = `0`
- no new economic candidate evaluated
- no new threshold selected
- no bankroll simulation executed
- `ECON_HOLDOUT1000 = SEALED`
- no HOLDOUT RESULT / PAYOUT / Price / scoring
- Shadow250-v2 remains preserved at selected=0 / screen=0 / prospective-v3-trial=0 and is not the current primary scientific line

---

# 1. User objective / reorientation

The project's primary economic objective is not winner-hit rate alone.

Target research pipeline:

`historical PRE -> ticket probability -> historical price -> edge/EV -> buy/no-bet -> ticket portfolio -> bankroll allocation -> later RESULT/PAYOUT settlement`

All officially sold historical wager markets must be admissible, including Wide. Buying methods must eventually include single, BOX, 流し/wheel, formation, multi-ticket, cross-market and NO-BET.

Real-time/future operation is intentionally deferred until historical economic research survives. Shadow250 source engineering and governance lessons are preserved for later same-day operation.

Reorientation record:
`v3/historical_all_market/governance/REORIENTATION_RECEIPT_v1.json`
Git blob: `4455b1cee2d896eba58ceea5626ef5b1b8a1344e`

Audit whether this reorientation legitimately creates a new research track without altering the scientific meaning/trials/outcomes of closed lineages.

---

# 2. Charter candidate

File:
`v3/historical_all_market/governance/ALL_MARKET_HISTORICAL_TRACK_CHARTER_CANDIDATE_v1.md`

Git blob:
`11e1ee7d6f8cf3b855f09fc978e6e69d42e09549`

Key stages:

- Stage 0: stored raw recovery / market availability only; **no model probability, EV, ROI, candidate ranking or bankroll simulation**
- Stage 1: ticket-probability engine
- Stage 2: price semantics / calibration / uncertainty
- Stage 3: edge/decision families
- Stage 4: quality/no-bet gates
- Stage 5: buying-method / portfolio constructors
- Stage 6: bankroll/risk allocation
- Stage 7: chronological walk-forward / untouched validation
- only later: same-day Shadow Live using timestamped PRE prices

Hostile question A:
Does this staged design sufficiently prevent outcome-driven strategy adaptation, or are additional pre-registration/firewall gates required before Stage 0 or Stage 1?

---

# 3. Immutable legacy asset reuse

File:
`v3/historical_all_market/governance/LEGACY_ASSET_REUSE_REGISTRY_v1.json`

Git blob:
`057ab1af291d1e985629680eb8a65e3cfd4be350`

Registered immutable assets include:

- `DEV2000_UNIVERSE_v1.csv`
  SHA-256 `eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1`
- `DEV2000_PRE_TABLE_v1.csv`
  SHA-256 `25303ed3a7bce2bbc1c681823cbe9d009e3d3c5f07ef669a43fd6cf1ea86af73`
- frozen Candidate A + B1a predictions
  SHA-256 `772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51`
- later-authorized RESULT-only JSONL
  SHA-256 `df2ba679895400d2a07d72f501fbaf52c1bd60d1128e16560a0bb66ebaa27884`
- RESULT provenance JSONL
  SHA-256 `0e9dbba0bf0427bd1b5903c196a93a31678375170e6d5164b3d8d8f052ca97f1`
- legacy Economic-E1 Prelock ZIP used only as scientific/governance precedent
  SHA-256 `db06d5cf1468d236131245c0c8d66791a21ae059b788938270bb8e5f1924cd4c`

Historical replay has independently reproduced the DEV1000 Phase-A sporting metrics from frozen PRE-result predictions and later RESULT; it is diagnostic evidence only.

Hostile questions B-D:

B. Is it scientifically valid for a new economic track to reuse these immutable historical artifacts while keeping old v2.7/v2.8/v2.9 closures immutable?

C. Does reusing the already-frozen Candidate A/B1a Prediction Lock avoid model-refit leakage, provided RESULT/PAYOUT never fit probability parameters?

D. Are any listed assets too contaminated by prior economic exploration to be used for **development** in this new track, requiring a stricter development/validation split or new untouched validation later?

---

# 4. All-market registry

File:
`v3/historical_all_market/governance/ALL_MARKET_REGISTRY_CANDIDATE_v1.json`

Git blob:
`1d0c8ad4d0b07346f4124913e99afed4ccf0563a`

Candidate markets, only when actually sold in that race's SHA-bound raw:

1. `3rentan` — 3連単
2. `3renhuku` — 3連複
3. `2shatan` — 2車単
4. `2shahuku` — 2車複
5. `wide` — ワイド
6. `2wakutan` — 2枠単
7. `2wakuhuku` — 2枠複

Buying methods are later portfolio constructors over elementary tickets, including single, top-K, BOX, 流し/wheel, formation, same-market multi-ticket, cross-market portfolios, and NO-BET.

### Wide

Historical closing quote is stored as an interval `[low, high]`, not silently reduced to midpoint.
Stage 0 preserves the interval only.
No Wide EV rule is authorized yet.
A candidate later primary decision rule is conservative lower-bound EV, but this is not frozen by Stage 0.

### Frame markets

Stage 0 parses only published frame prices/refunds and retains raw frame-label metadata.
Stage 1 car-to-frame probability aggregation is not yet authorized.
Same-frame tickets such as `4-4` / `4=4` may exist and require distinct-car event mapping later.

Hostile questions E-I:

E. Is the seven-market registry complete and scientifically appropriate when admission is per-race actual market availability rather than hard-coded by field size?

F. Is treating Wide as interval price and prohibiting midpoint/point EV at Stage 0 sufficient?

G. Should the future Wide primary rule be lower-bound EV, interval dominance, robust decision theory, or another preregistered rule? Do not optimize using observed payout results.

H. Is representing BOX/流し/formation as portfolio constructors over de-duplicated elementary tickets the correct abstraction?

I. For frame bets, what exact Stage-1 invariants are required to verify car->frame mapping, including same-frame tickets and total probability mass = 1?

---

# 5. Stage-0 exact offline parser

File:
`v3/historical_all_market/kdreams_all_market_offline_parser_v1.py`

Git blob:
`297adbc42a6bf593502f55fcd002beb4190469e2`

The exact GitHub blob was also `git hash-object` verified against the locally executed canary source.

Properties:

- offline only / no network;
- verifies raw SHA-256 against frozen per-race provenance;
- requires confirmed-odds page marker;
- detects market content/status nodes;
- parses complete closing-odds catalogs;
- preserves Wide low/high intervals;
- parses frame markets only when present;
- parses official refund catalogs;
- parses per-market timestamp strings;
- outputs market availability and raw provenance;
- does not compute model probability;
- does not compute EV;
- does not score ROI/profit;
- does not rank candidates.

### Known deliberate strictness / possible weaknesses

1. It currently requires the four core car markets + Wide to exist; this may false-reject unusual legitimate pages rather than false-accept them.
2. `parse_refunds` must be reviewed against dead-heats and unusual multi-refund structures.
3. 2枠単 matrix orientation assumes Kdreams column=first frame / row=second frame; canary winning-ticket consistency supports this but does not prove all templates.
4. Exact new-parser canaries currently cover 7-car and 9-car structures; an exact 5-car raw canary from old E1 provenance has not yet been independently re-located in current Drive indexing.
5. The same stored post-race raw physically contains **closing odds and later result/refund data**. The parser currently can parse both in one execution, although Stage 0 does not score them.

Hostile questions J-O:

J. Does parsing a SHA-bound **post-race archived page** to recover historical closing odds create unacceptable future leakage, even when closing odds are treated only as historical `B_CLOSING_PRICE`, model probabilities were frozen independently before RESULT, and no live executable-price claim is made?

K. Because odds and refunds coexist in the raw, should Stage 0 be split into **two separately bound executables/artifacts**: (1) price/availability recovery that cannot emit result/refund, and (2) settlement/refund recovery used only after candidate rules are frozen? Is that split required before bulk 2000 recovery?

L. If a split is required, may both passes use the identical content-addressed post-race raw bytes, provided code-level field access is segregated and scientific stage ordering is enforced?

M. Is the current hard requirement for core markets acceptable Fail-Closed strictness, or must market admission be fully availability-driven to avoid systematic selection bias?

N. Are 7-car + 9-car exact canaries sufficient to authorize bulk Stage-0 recovery, or is a new exact 5-car canary mandatory before bulk work?

O. What exact dead-heat/refund invariants are required before settlement recovery can be trusted?

---

# 6. Exact canary evidence

Receipt:
`v3/historical_all_market/runtime_receipts/ALL_MARKET_STAGE0_CANARY_RECEIPT_v1.json`

Git blob:
`469f4106f3d8e99678ea9bea719829e8b316b38f`

### 7-car canary

Race `3820260410010003`
Raw SHA-256 `24551faf351c8216b3d4ceda249b9a369ecdae62f0baf87dcfe91f979ac46285`

Sold markets:
- 3連単 210 tickets
- 3連複 35
- 2車単 42
- 2車複 21
- Wide 21
- frame markets absent

All winning refund tickets are present in their own parsed price catalog, including all 3 Wide winning pairs.

### 9-car canary

Race `2620260409010001`
Raw SHA-256 `fb83738b6d2e88f6b56bb6dc5647c1f8803932c3c2709d8c93fb7bfcee987c54`

All seven markets sold:
- 3連単 504
- 3連複 84
- 2車単 72
- 2車複 36
- Wide 36
- 2枠単 33
- 2枠複 18

Winning ticket consistency includes:
- 2枠単 `2-4`: parsed odds 9.8; refund 980 yen/100
- 2枠複 `2=4`: parsed odds 3.2; refund 320 yen/100
- 2車単 `2-5`: odds 8.5; refund 850
- 2車複 `2=5`: odds 2.6; refund 260
- 3連複 `2=5=7`: odds 8.4; refund 840
- 3連単 `2-5-7`: odds 132.2; refund 3840
- Wide winners all exist in interval catalogs

Note: closing odds and final refund need not numerically match exactly for every pari-mutuel market; the canary assertion is key identity/coverage, not equality of odds multiplier to final payout multiplier.

Hostile questions P-R:

P. Does the canary evidence sufficiently validate ticket canonicalization and 2枠単 orientation for Stage 0?

Q. Should a wider stratified canary set be frozen before full 2000 recovery (e.g. 5/7/9 cars, dead-heat, frame sold/unsold, large-odds cases)? Specify minimum required strata.

R. Does canary checking refund winners against odds catalogs itself constitute prohibited economic scoring? It is currently classified as parser key-consistency testing only; no candidate model/EV/ROI is evaluated.

---

# 7. Stage-0 scientific trial accounting

Proposed rule:

- parser development / SHA verification / market-availability recovery / catalog cardinality / key-consistency canaries consume **0 economic scientific trials**;
- no candidate probability/edge/threshold/portfolio/bankroll rule may be evaluated at Stage 0;
- full 2000-race market catalog recovery, if audit-approved, remains data recovery rather than a scored economic trial;
- scientific trial accounting begins only when a preregistered economic candidate family is evaluated on an outcome-bearing development/validation set.

Hostile question S:
Is this trial-accounting boundary scientifically defensible, or should any use of refund keys—even parser-consistency-only—consume a trial or be firewalled into a later stage?

---

# 8. Required issue format

For every issue provide:

- ID
- exact file/section
- exact failure scenario
- impact on data membership / prices / ticket identity / later probability / EV / settlement
- exact correction
- severity: `P0_BLOCKER` / `P1_MATERIAL` / `P2_NON_BLOCKING`
- whether correction changes track semantics/source role and requires another independent re-audit

---

# 9. Required explicit decisions

Before verdict, state:

1. New All-Market Historical Track without reopening v2.7/v2.8/v2.9: ACCEPTABLE / NOT_ACCEPTABLE
2. Immutable legacy artifact reuse: ACCEPTABLE / CONDITIONAL / NOT_ACCEPTABLE
3. Shadow250 lessons reused only as process/infrastructure: ACCEPTABLE / NOT_ACCEPTABLE
4. Seven-market per-race availability registry: ACCEPTABLE / NOT_ACCEPTABLE
5. Wide interval preservation / no midpoint at Stage 0: ACCEPTABLE / NOT_ACCEPTABLE
6. Buying methods as elementary-ticket portfolio constructors: ACCEPTABLE / NOT_ACCEPTABLE
7. Stage-0 parser Git blob `297adbc...`: ACCEPTABLE / REQUIRES_CORRECTION
8. SHA-bound post-race raw used to recover historical closing prices: ACCEPTABLE / CONDITIONAL / NOT_ACCEPTABLE
9. Price-vs-settlement executable/artifact split before bulk recovery: REQUIRED / RECOMMENDED / NOT_REQUIRED
10. 7/9-car canary evidence: SUFFICIENT_FOR_BULK_STAGE0 / ADDITIONAL_CANARIES_REQUIRED
11. Stage-0 trial count = 0: ACCEPTABLE / NOT_ACCEPTABLE
12. ECON_HOLDOUT1000 = SEALED

Then state whether full 2000-race Stage-0 recovery is authorized before Stage-1 probability modeling.

---

# 10. Final verdict

Return EXACTLY one:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

`APPROVE` means Stage-0 bulk recovery may proceed under the audited exact artifacts and stated firewall.

`CONDITIONAL APPROVE` means do NOT perform full 2000-race bulk recovery until all P0/P1 preconditions are completed and, where required, re-audited.

`REJECT` means halt this Stage-0 design.

Under every verdict:

- no new economic candidate scoring is authorized;
- no Stage-1 ticket probability promotion is authorized;
- no bankroll optimization is authorized;
- no HOLDOUT access is authorized;
- `ECON_HOLDOUT1000` remains SEALED.
