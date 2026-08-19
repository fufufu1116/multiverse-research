# Multiverse Hybrid v3.0 — Independent Gemini Governance Audit: scheduled_start Post-Activation Gap v1

## Audit posture

Perform a hostile, independent governance audit of a **post-Activation implementation gap discovered before the first Shadow250-v2 prospective screen**.

Repository: `fufufu1116/multiverse-research`

Do not assume ChatGPT's proposed fix is valid. Do not silently repair anything.

This audit MUST NOT access, request, infer, or score ECON_HOLDOUT1000 RESULT/PAYOUT/Price.

## Current frozen/active state

Shadow250-v2 has completed:

- independent Gemini final verdict: `APPROVE`
- Final Source Set Freeze
- Final Selection Rule Freeze
- Genesis Final Freeze
- Freeze Self Verification: `PASS`
- Separate Activation

Activation JST:
`2026-08-19T11:38:23.685300+09:00`

Current scientific state remains:

- Shadow250-v2 selected races = `0`
- prospective Shadow screen count = `0`
- prospective v3 scientific trial = `0`
- first Prediction Lock = NOT EXECUTED
- ECON_HOLDOUT1000 = `SEALED`
- global scoring / Lane-E / final-v3 proof / wagering = `UNAUTHORIZED`

No prospective race has been screened, selected, predicted, substituted, or outcome-checked.

## Frozen Selection Rule relevant text

`SHADOW250_V2_SELECTION_RULE_FINAL_FREEZE_v1.json`

Core SHA-256:
`26459bbe8db0766918a7511069f0c13354fb8b75d952a1633bbc3b8325f099d6`

It freezes:

- membership = first 250 races satisfying every frozen PRE-only gate after activation;
- activation constraint = scheduled_start strictly after activation timestamp;
- ordering = scheduled_start ascending, venue_code ascending, race_no ascending.

However, after Activation and before race 1, ChatGPT discovered that the Final Freeze does **not explicitly bind an executable source/extractor for `scheduled_start`**.

This is the exact governance issue to adjudicate.

# 1. Evidence discovered without consuming a Shadow screen

A source-discovery-only diagnostic was run after Activation.

Receipt:
`v3/prospective_shadow250_v2/runtime_receipts/SHADOW250_V2_FIRST_PROSPECTIVE_DISCOVERY_v1.json`

At the diagnostic time, the Tamano official race-PDF discovery page had zero matching `20260820/20260821/20260822` PDF links.

The receipt explicitly records:

- purpose = POST_ACTIVATION_SOURCE_DISCOVERY_ONLY_NOT_A_SCREEN
- matching_count = 0
- scheduled_start_resolved = false
- screen_decision_made = false
- shadow_screen_consumed = false
- scientific_trial_consumed = false
- prediction_executed = false
- HOLDOUT accessed = false.

Therefore no race-order decision was made from this discovery.

# 2. PRE-only scheduled-start diagnostic

To determine whether a new external source was necessary, ChatGPT probed an already-held historical Tamano official PDF **only inside the same frozen PRE clips** used by the frozen Tamano parser.

Receipt:
`v3/prospective_shadow250_v2/runtime_receipts/SHADOW250_V2_SCHEDULED_START_PREONLY_PROBE_v1.json`

Purpose:
`GOVERNANCE_DIAGNOSTIC_ONLY_NOT_A_SCREEN`

Historical sample:
- race date `2026-07-24`
- raw PDF SHA-256 `a2328d364eec4308adb7024efbb0b0fc7851472dc72a3fad465b5fa5cdc24317`
- all 12 races yielded exactly one PRE text `発走 HH:MM`
- times were strictly increasing by race number:
  - R1 10:53
  - R2 11:17
  - R3 11:43
  - R4 12:10
  - R5 12:37
  - R6 13:04
  - R7 13:33
  - R8 14:03
  - R9 14:33
  - R10 15:05
  - R11 15:41
  - R12 16:25

No RESULT/PAYOUT/Price was accessed. No Shadow screen/trial was consumed.

This evidence suggests `scheduled_start` can be derived as **selection-order metadata from the already-admitted Tamano PRE PDF source**, rather than adding KEIRIN.JP or another provider.

# 3. Candidate-only extractor — NOT ACTIVE

File:
`v3/prospective_shadow250_v2/tamano_scheduled_start_metadata_candidate_v1.py`

Git blob:
`31aa09d68f68656e6f8b134c2ead28e3bc00b1c1`

The file explicitly says:
`NOT ACTIVE. MUST NOT be used for screening until independent governance adjudication.`

Candidate behavior:

1. hard-binds the already-frozen Tamano parser v4 Git blob:
   `397ed3c8839b1ad4ffa4835924dd759397e2124c`;
2. reuses frozen transport binding and frozen PRE clips;
3. emits no predictive field;
4. for each of the frozen 12 race blocks, reads a narrow band around the bottom/program metadata area;
5. requires exactly one regex match `発走 HH:MM` per race;
6. binds that time to the already-bound race date in JST;
7. requires all 12 race numbers exactly once;
8. requires strictly increasing scheduled_start across R1..R12;
9. any missing/ambiguous/nonmonotonic case => `PRE_INELIGIBLE_SOURCE_GAP` / Fail-Closed;
10. metadata role is `NON_PREDICTIVE_SELECTION_ORDER_ONLY`;
11. the executable main path refuses prospective use and allows only `--synthetic` until governance approval.

# 4. Historical replay validation completed in parallel

Before moving into the first prospective race, ChatGPT independently verified the existing DEV2000 historical PRE -> pre-result Prediction Lock -> later RESULT chain.

Record:
`v3/prospective_shadow250_v2/governance/DEV2000_HISTORICAL_REPLAY_INDEPENDENT_VERIFICATION_v1.json`

Verified input hashes:

- DEV2000 Universe CSV SHA-256:
  `eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1`
- DEV2000 PRE_TABLE CSV SHA-256 from pre-result lock:
  `25303ed3a7bce2bbc1c681823cbe9d009e3d3c5f07ef669a43fd6cf1ea86af73`
- frozen prediction CSV SHA-256:
  `772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51`
- later-authorized RESULT-only JSONL SHA-256:
  `df2ba679895400d2a07d72f501fbaf52c1bd60d1128e16560a0bb66ebaa27884`

Prediction/result race sets are exactly equal at 2,000 races.

DEV1000 `dev_index 1..1000` independently reproduces the pre-existing Phase-A report exactly:

Candidate A:
- Brier `0.10149539331217405`
- binary logloss `0.3375980238720246`
- ECE10 `0.026033620923127398`

B1a_RECONSTITUTED_v1:
- Brier `0.0999370871068068`
- binary logloss `0.33233806423376144`
- ECE10 `0.00785937912627017`

This historical replay is diagnostic validation only. It does not alter Shadow250-v2, model weights, eligibility, or trial counts.

# 5. Required hostile governance questions

A. Does the omission of an executable `scheduled_start` extractor from the already-Final-Frozen Selection Rule constitute a P0/P1 defect that invalidates the current active Shadow250-v2 before race 1?

B. Is reading `発走 HH:MM` from the **same already-admitted Tamano official PRE PDF and same PRE-only clips** a new source, source role, adapter, or selection-rule change?

C. Or is it a permissible implementation completion of the already-frozen semantic field `scheduled_start`, because the Selection Rule already explicitly depends on that field and no source/provider is added?

D. Does adding executable code after Final Freeze, even if it only materializes already-frozen non-predictive ordering metadata from an existing source, necessarily violate `DO_NOT_EDIT` and require another new Shadow universe?

E. Distinguish carefully:
- changing scientific eligibility/order semantics;
- adding a new provider/source role;
- implementing an already-frozen ordering variable from the already-admitted source.

F. Does the candidate's requirement of one unique `発走 HH:MM` per race + full 12R coverage + strict monotonicity sufficiently fail closed on Tamano template drift?

G. Is the candidate extraction band too broad or capable of reading prior-performance/post-result content? If so, specify an exact safer geometry/invariant.

H. Must the `scheduled_start` extraction occur inside the <=120-second source window, or may it be parsed from the same already-captured Tamano PDF bytes without a second network capture?

I. Since race dates after 2026-08-19 are necessarily after Activation by calendar date, is exact scheduled_start still mandatory for same-day ordering among R1..R12? Confirm that race_no may NOT silently replace the frozen primary scheduled_start ordering field.

J. Does the historical DEV2000 replay legitimately remain diagnostic with Shadow selected/screen/trial counts all zero?

K. Has any post-Activation diagnostic already consumed a screen merely by checking the Tamano discovery page? The supplied receipts say no race decision was made; audit that classification.

# 6. Universe-boundary decision — MUST answer explicitly

Return exactly one:

`CURRENT_SHADOW250_V2_MAY_CONTINUE_WITH_SCHEDULED_START_IMPLEMENTATION_COMPLETION`

or

`CURRENT_SHADOW250_V2_MUST_HALT_AND_NEW_UNIVERSE_REQUIRED_BEFORE_RACE_1`

If continuation is allowed, state the exact preconditions before first screen, including whether:

- candidate extractor Git blob `31aa09d68f68656e6f8b134c2ead28e3bc00b1c1` must be independently live-tested on the first available post-Activation Tamano PDF;
- a governance addendum/freeze binding is required;
- Final Freeze manifest must be superseded/rebound or only supplemented;
- the original Activation timestamp may remain valid;
- no race can be screened until the exact extractor is bound.

If a new universe is required, state whether Shadow250-v2 must close with selected=0/screen=0/trial=0 and whether a new Activation timestamp is required.

# 7. Required issue format

For every issue provide:

- ID
- exact file/section
- failure scenario
- effect on membership/order/features/Prediction Lock
- exact correction
- severity: `P0_BLOCKER` / `P1_MATERIAL` / `P2_NON_BLOCKING`
- whether `NEW_UNIVERSE_REQUIRED_BEFORE_RACE_1`

# 8. Required explicit state confirmation

Before final verdict state:

- `ECON_HOLDOUT1000 = SEALED`
- `Shadow250-v2 selected races = 0`
- `prospective Shadow screen count = 0`
- `prospective v3 scientific trial = 0`
- `first prospective Prediction Lock = NOT EXECUTED`
- `global scoring = UNAUTHORIZED`
- `wagering = UNAUTHORIZED`

# 9. Final verdict

Return exactly one:

`APPROVE`

`CONDITIONAL APPROVE`

`REJECT`

`APPROVE` requires no unresolved P0/P1 and must include the explicit universe-boundary decision above.

`CONDITIONAL APPROVE` = DO NOT SCREEN RACE 1 / DO NOT PREDICT RACE 1.

`REJECT` = HALT CURRENT SHADOW250-v2 / DO NOT SCREEN RACE 1.

ECON_HOLDOUT1000 remains SEALED under every verdict.
