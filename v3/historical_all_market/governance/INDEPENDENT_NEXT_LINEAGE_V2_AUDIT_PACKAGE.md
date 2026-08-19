# Independent Audit Package — Multiverse Keirin Next-Lineage v2

Audit type: MATERIAL SCIENTIFIC / ARCHITECTURE / DATA-RIGHTS GATE
Date: 2026-08-19 JST
Repository: `fufufu1116/multiverse-research`

Status before audit: `NOT FROZEN / NOT EXECUTABLE / NO NEW VALIDATION OPENED`

## 0. Hard boundaries

The parent lineage is closed as:

`NO_B_VALIDATED_CONFIGURATION`

Current protected state:
- current DEV2000 C is NOT available for new-lineage rescue or new untouched-validation claims;
- `scientific_segment_c_scoring_count = 0` under the parent Stage-7 evaluator;
- `ECON_HOLDOUT1000 = SEALED`;
- no same-lineage B/C rescue tuning;
- no unauthorized RESULT/PAYOUT access;
- no unverified artifact may be treated as confirmed;
- no unauthorized network collection;
- no scraping/access-control/CAPTCHA/WAF/rate-limit bypass;
- no external provider contact, account, purchase or contract without Owner approval.

This package asks for design review only. It does not authorize any of the above.

## 1. Why v2 exists

After the closed parent failure, three independent architecture reviews (Claude, Gemini, separate ChatGPT) were synthesized and then checked against current code/governance and official keirin structure documentation.

Accepted lessons include:
- current winner->Plackett-Luce expansion is a legitimate structural null/control but must not be presumed to be the final top-3 generator;
- A/B output agreement cannot protect against a structural error shared by both models/downstream PL;
- ticketwise `min(pA,pB)` is a lower envelope, not generally a coherent normalized probability distribution;
- Wide event-probability semantics and unit-mass quote-shape diagnostics must be explicitly separated;
- race regime must be explicit before line modeling;
- line data require source-specific observation timestamps/provenance;
- H is a genuine missing PRE candidate in the current registry;
- PRE availability and decision/action availability are separate requirements;
- proper probability scoring must precede economic optimization;
- FLAT100/simple economics should precede Kelly and portfolio optimization;
- tail profit concentration and underwater duration are core evaluation criteria.

Not established:
- PL caused the parent B failure;
- any quoted 70% line-explanation statistic;
- any fixed same-line one-two base rate;
- nested PL is automatically sufficient;
- bucketwise isotonic calibration should be default;
- portfolio optimization should be introduced before probability validation.

Reference:
`v3/historical_all_market/governance/TRI_MODEL_ARCHITECTURE_REVIEW_LESSONS_LEARNED_v1.md`
commit `d9178e35dccd7492e82622b078cd3dbd50119a74`

## 2. Parent diagnostic facts that may motivate hypotheses but may not rescue the parent

Burned A/B diagnostics showed:
- apparent A profit was dominated entirely by one 457.9x 3rentan return event;
- no A_TOP10 configuration passed B;
- selected high-odds 3rentan regions materially overpredicted expected hit counts relative to observed hits;
- realized selected-region hits were much closer to market-implied expectations than frozen model expectations;
- a simple market-offset residual using only existing Candidate-A/B1a outputs did not robustly beat market-only in B.

These observations may motivate new-family hypotheses, but may not be used to retune B/C or claim that PL is the proven cause.

## 3. Source/provenance design under audit

Reference:
`NEW_LINEAGE_STAGE0_STRUCTURE_PROVENANCE_SCHEMA_AUDIT_v1.md`
commit `fdb0b8372f1e09121e134f64e928c347a589c778`

Candidate structural fields:
- `race_regime`
- `line_group_id`
- `line_position`
- `line_size`
- `is_singleton`
- `num_lines`
- `line_source`
- `line_snapshot_timestamp`
- `line_observation_type`
- `H`

Already present in NEXTGEN registry but not active in frozen DEV2000:
- `nige/makuri/sashi/mark`
- line fields / line aggregate candidates
- bank length / home straight / cant
- weather / temperature / wind.

Candidate line observation distinction:
- `LEGSHOW_OBSERVED_LINE`
- `PRE_EVENT_EXPECTED_LINE`
- post-race reconstructed line = prohibited as PRE.

Candidate regime distinction:
- `STANDARD_ORIGINAL_LINE_KEIRIN`
- `INTERNATIONAL_FIXED_PACER`
- `UNKNOWN_OR_OTHER` => fail-closed for line-dependent family.

Race regime must come from the actual race rule/program; it must not be inferred only from sex or class because current men's KEIRIN ADVANCE can use international-style fixed-pacer rules.

## 4. Data-rights/provider state under audit

References:
- `NEW_LINEAGE_STAGE0_SOURCE_TRANSPORT_AUDIT_v1.md`
- `NEW_LINEAGE_SOURCE_PROVIDER_SELECTION_DRAFT_v1.md`
- `NEW_LINEAGE_PROVIDER_RIGHTS_MATRIX_v1.md`

Public research currently supports:

### JKA / KEIRIN.JP / VIS
- official upstream information system exists;
- 2028VIS explicitly contains data-link/internet-information components and closed-network connections including private sites;
- public KEIRIN.JP surfaces exist;
- public site policy restricts copying/reuse outside legally permitted uses such as private use/quotation;
- no public self-service open-data/API license compatible with bulk ML was found in this audit.

Verdict: official authorized feed is the preferred route, but access/rights are not proven.

### Team-Nave
- keirin AI prediction product and CTC betting API are publicly confirmed;
- full database APIs exist publicly for horse racing and boat racing;
- an equivalent public keirin database/data-feed product was not found.

Verdict: promising inquiry candidate, not an admitted feed.

### WINTICKET
- current AI prediction documentation states use of tens of thousands of past race results and lineup information;
- current `line power` numerically evaluates line strength.

Verdict: legitimate modern operational architecture benchmark/context; NOT an admitted training source and NOT proof that Multiverse N1 works.

Current global provider verdict:

`NO_PROVIDER_YET_ADMITTED_FOR_NEW_LINEAGE_COLLECTION`

## 5. Source-independent PRE interface implemented before provider selection

References:
- `v3/historical_all_market/new_lineage/PRE_INTERFACE_SCHEMA_DRAFT_v1.json`
  commit `ce405e4aded9d2a033ed29f6cd123e8d92dda02f`
- `v3/historical_all_market/new_lineage/validate_pre_structure_v1.py`
  commit `1ad9155ab4654e2656c67318bfa15c7ca326086e`
- synthetic no-real-race fixture:
  `v3/historical_all_market/new_lineage/fixtures/SYNTHETIC_STANDARD_PRE_v1.json`
  commit `e2d7d09ec94063edb1df3e15f47d16413726e43a`

The interface intentionally does not encode a specific provider. Provider admission remains a separate rights/provenance gate.

Fail-closed structural invariants include:
- unique active rider/car identity;
- line membership exactly once;
- line positions contiguous from zero;
- line size consistency;
- singleton equivalence to line size one;
- line snapshot at/before decision time;
- regime source at/before decision time;
- SHA-addressable raw provenance fields;
- unknown/international regime cannot silently enter a standard-line model.

## 6. Probability architecture candidates under audit

Reference:
`NEW_LINEAGE_C0_C1_N1_PROBABILITY_ARCHITECTURE_DRAFT_v1.md`
commit `fdbac43ceaba8adf66f289c1969b0e83ffe826e8`

### C0 — frozen current PL control

Purpose:
- structural null/control;
- do not rewrite its behavior after seeing new outcomes.

### C1 — line-augmented PL

Purpose:
- add admitted direct line/race-regime PRE information to runner utilities while retaining PL top-order mechanics;
- isolate feature-value from architecture-value.

### N1 — line-conditional top-3

Candidate factorization:

`P(i,j,k|X) = P1(i|X) * P2(j|i,X) * P3(k|i,j,X)`

Primary relational features should remain low-freedom/deterministic:
- same line;
- line position;
- relative position gap;
- leader/follower relation;
- line size;
- singleton;
- race regime;
- simple preregistered line-relative strength transforms only if admitted.

Primary causal/falsification question:

Does explicit conditional dependence improve rank-2 and rank-3 out-of-time probability quality over C1 when the PRE information basis is comparable?

N1 is not allowed to win merely because of development ROI.

## 7. Probability Object Contract under audit

Reference implementation:
`v3/historical_all_market/new_lineage/probability_object_contract_v1.py`
commit `b85bcbcab5351fb98bf46747e5c8c9dc34f5156c`

The sole sporting source of truth for the official ticket probabilities is the normalized ordered top-3 joint distribution.

Required mass identities:
- ordered top3 / 3rentan = 1;
- 3renhuku = 1;
- 2shatan = 1;
- 2shahuku = 1;
- Wide overlapping event-probability vector = 3;
- sold frame markets = 1 after deterministic car->frame aggregation.

All markets must be exact marginalizations/aggregations of the same joint object.

A lower envelope such as ticketwise `min(pA,pB)` must not be labeled or consumed as a coherent probability distribution.

## 8. N2/N3 status

### N2 — market-residual top3

Candidate only after actionable market transport is proven.

Required market semantics:
- market snapshot observed at a frozen decision time before wager commitment;
- same snapshot semantics in development/validation/live operation;
- final/post-decision closing price prohibited as a live BUY input unless it was actually available at the frozen decision time;
- market-only baseline must be beaten on proper probability scoring before economic optimization.

### N3 — initiative mixture

Deferred.

Do not introduce until N1 supports the need for additional structural state. Dynamic switch/reattach remains experimental.

## 9. Validation protocol under audit

Reference:
`NEW_LINEAGE_TRAIN_CAL_FINAL_VALIDATION_PROTOCOL_DRAFT_v1.md`
commit `0b3ef8ccf6d0d6c1bb30ec4ad30b9eec5d9dfc91`

Candidate split:

`TRAIN -> CAL -> FINAL VALIDATION`

strict chronological blocks.

TRAIN:
- model fit;
- if needed, time-aware CV only inside TRAIN.

CAL:
- regularization / low-dimensional calibration / shrinkage / uncertainty / final BUY semantics;
- all tunable semantics frozen before FINAL.

FINAL:
- one-shot;
- any result-responsive model/threshold change burns FINAL for that lineage.

Probability architecture is selected before economic policy.

Primary probability diagnostics:
- winner NLL;
- rank2 conditional NLL;
- rank3 conditional NLL;
- joint top3 NLL;
- calibration;
- expected vs observed hits in preregistered diagnostic slices.

No numeric pass threshold is yet frozen.

## 10. First economic test candidate

To reduce research degrees of freedom:
- FLAT100 primary;
- candidate maximum one elementary ticket per race;
- probability architecture must not be selected by ROI;
- Kelly secondary only after coherent calibrated probabilities pass untouched validation;
- portfolio optimization deferred until probability quality and simple economics pass.

Required stability/concentration reporting includes:
- weekly/monthly P&L and positive fractions;
- median weekly/monthly return;
- maximum drawdown;
- longest underwater duration in days/races;
- recovery duration;
- largest/top3/top5 winner profit concentration;
- HHI or equivalent concentration measure;
- ROI after removing largest/top3 wins.

## 11. Updated hostile audit questions

Answer every item explicitly.

### Data / provenance / rights

A. Is the separation `publicly visible != machine-transportable != historically point-in-time != legally reusable for ML/operation` sufficient and correctly enforced?

B. Should any public KEIRIN.JP race-card/line surface be admitted before explicit compatible reuse rights are obtained? Identify the narrowest scientifically/legally defensible boundary.

C. Are `line_source`, `line_snapshot_timestamp`, `line_observation_type`, raw provenance SHA and decision timestamp sufficient for mutable-line evidence? What is missing?

D. Is `LEGSHOW_OBSERVED_LINE` vs `PRE_EVENT_EXPECTED_LINE` the correct semantic split, or must these be separate model families/data roles?

E. Is explicit `race_regime` required, and is the proposed standard/international/unknown vocabulary sufficient for the first lineage?

F. Is H a defensible CORE candidate, or should it remain optional until historical point-in-time transport is proven?

G. Does any source-independent schema field accidentally allow post-race reconstruction or present-day profile leakage?

### Architecture

H. Is C0->C1->N1 the cleanest minimal ablation to isolate line-feature value from conditional-order architecture value?

I. Should C1 and N1 share exactly the same P1/winner family to isolate rank2/rank3 architecture? If not, provide a stronger comparison design.

J. Is `P1 * P2|1 * P3|1,2` sufficiently expressive as the first joint-order alternative, while still low enough in freedom to audit?

K. Which minimum relational features are scientifically necessary in N1, and which proposed ones should be removed to prevent overfitting?

L. Is nested/hierarchical PL worth including as a fourth primary architecture, or should it remain secondary to avoid expanding the initial search?

M. What evidence would falsify the hypothesis that explicit line-conditioned rank dependence is useful?

### Probability semantics

N. Is the Probability Object Contract correct, especially Wide total event mass = 3 and all ticket markets derived from one top3 joint object?

O. Are there official ticket/refund/dead-heat/cancellation cases that make a top3 joint source insufficient or require an explicit settlement-state extension?

P. Is banning lower envelopes such as `min(pA,pB)` from the `probability_distribution` type correct? Is there a legitimate way to retain them only as lower scores/decision diagnostics?

### Market

Q. Is N2 scientifically legitimate only if decision-time market snapshots are historically/live transportable under identical semantics?

R. What is the minimal proper-scoring condition needed before a market-residual model may be called incremental information rather than market copying?

S. Should market residual be defined on the ordered 3rentan joint and then marginalized, or is a runner-level offset sufficient as a primary comparator?

### Validation / economics

T. Is TRAIN->CAL->one-shot FINAL sufficient to prevent result-responsive tuning if TRAIN itself uses rolling/nested CV?

U. Which exact primary statistical uncertainty method should compare C1 vs N1 conditional NLL under chronological dependence?

V. Should rank2/rank3 conditional NLL be PRIMARY and economic ROI secondary for initial architecture promotion?

W. Is FLAT100 with <=1 ticket/race the cleanest first economic attribution test, or can it distort valid multi-ticket edge too severely?

X. Which profit-concentration and underwater measures should be hard gates versus descriptive diagnostics?

Y. When, if ever, should fractional Kelly and portfolio optimization become eligible for promotion testing?

### External benchmarks

Z. WINTICKET publicly states that its AI uses historical results plus lineup information and exposes line power. Is it scientifically useful only as architecture context, or should a lawfully obtainable prospective snapshot be a future external prediction comparator?

AA. Team-Nave's keirin AI publishes top-3-related prediction values. Is an external black-box forecast benchmark useful even if its internal training/model is unknown, provided snapshots are lawfully acquired before outcomes?

AB. How should the project prevent external forecast benchmarks from leaking future model-version changes or hindsight into retrospective comparison?

## 12. Required issue format

For every issue:
- ISSUE ID
- affected artifact/section
- severity: `P0_BLOCKER`, `P1_MATERIAL`, `P2_NON_BLOCKING`
- failure scenario
- exact correction
- scientific/statistical/data-rights reason

Do not reward effort or desired profitability.

## 13. Required explicit decisions

Return exactly `ACCEPTABLE`, `REVISE`, or `REJECT` for:

- PARENT_CLOSED_BOUNDARY
- DEV2000_C_NEW_LINEAGE_PROHIBITION
- ECON_HOLDOUT1000_SEALED
- SOURCE_RIGHTS_SEPARATION
- PROVIDER_ADMISSION_GATE
- MUTABLE_LINE_PROVENANCE_CONTRACT
- RACE_REGIME_CONTRACT
- H_FEATURE_STATUS
- C0_C1_N1_ABLATION
- N1_CONDITIONAL_TOP3_FACTORIZATION
- PROBABILITY_OBJECT_CONTRACT
- WIDE_EVENT_MASS_3_SEMANTICS
- LOWER_ENVELOPE_NOT_DISTRIBUTION
- N2_DECISION_TIME_MARKET_RULE
- TRAIN_CAL_FINAL_PROTOCOL
- PROPER_SCORING_BEFORE_ECONOMICS
- FLAT100_MAX1_FIRST_ECONOMIC_TEST
- KELLY_SECONDARY
- PORTFOLIO_OPTIMIZER_DEFERRED
- EXTERNAL_PREDICTION_BENCHMARK_POLICY

## 14. Final verdict

Exactly one:

`APPROVE`
`CONDITIONAL APPROVE`
`REJECT`

APPROVE does NOT authorize:
- provider contact/purchase;
- data collection;
- DEV2000 C use;
- ECON_HOLDOUT1000 opening;
- wagering.

End with:
- strongest case AGAINST this design;
- most dangerous shared assumption;
- most likely hidden leakage route;
- most likely source-rights failure route;
- cleanest falsification experiment;
- exact next action allowed.

`ECON_HOLDOUT1000 = SEALED`
