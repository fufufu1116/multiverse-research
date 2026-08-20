# KEIRIN Batch 1 — LAB REVIEW REQUEST v1

Review target PR: #3
Exact review head: `18c0a4c89c886a09e47e0e8aa9911a2ec1f6f76c`
Base accepted Multiverse main: `460e46440edecf90bfd4028b085ad28c0bd3327c`

## Scope

This is a Keirin research review, not a Multiverse architecture reopen.
Review the Digital Twin reality calibration classification and the C0/C1/N1 W0-W4 synthetic stress design.

Primary files:
- `v3/historical_all_market/governance/DIGITAL_TWIN_REALITY_CALIBRATION_REGISTRY_v1.json`
- `v3/historical_all_market/new_lineage/validate_reality_calibration_registry_v1.py`
- `v3/historical_all_market/new_lineage/digital_twin_stress_grid_v1.py`
- `v3/historical_all_market/new_lineage/c0_c1_n1_multiworld_stress_v1.py`
- `v3/historical_all_market/governance/KEIRIN_C0_C1_N1_MULTIWORLD_STRESS_RECEIPT_20260820_v1.json`

## Scientific firewall

Must remain unchanged:
- `ECON_HOLDOUT1000 = SEALED`
- DEV2000 C new-lineage rescue prohibited
- same-lineage B/C rescue tuning prohibited
- scientific segment C scoring count = 0
- untouched validation unopened
- RESULT/PAYOUT access unauthorized

Do not request or open protected result/payout data for this review.

## Known Core result — do not trust blindly

Core's local reconstruction run used three fixed seeds (`20260820`, `20260821`, `20260822`), 48 synthetic races per scenario, 10 assumption scenarios (two per W0-W4 family), and exact ordered-top3 expected log loss/KL/Brier diagnostics.

The fixed architecture proxies were NOT retuned after seeing the first result.
Across all three seeds the scenario-win pattern was identical:
- C0: 9 / 10 scenarios
- C1: 0 / 10
- N1: 1 / 10 (`W2_CONDITIONAL_LINE_STRONG`)

Core interpretation is deliberately conservative:
- adding line fields is not automatically useful;
- naive fixed-coefficient C1 currently degrades this synthetic grid;
- N1 only shows structural advantage when conditional line dependence is sufficiently strong;
- NONE of this is real-keirin predictive evidence.

## Disclosed assurance limit

The receipt explicitly says `native_branch_runtime_execution = PENDING`.
Core syntax-checked the new files and executed an equivalent local reconstruction against the current Digital Twin/top3 API logic, but does NOT claim a GitHub-hosted/native runtime executed the exact branch bytes.

Lab must decide whether this assurance is sufficient for this working research stage and what exact native/conformance check is required before any promotion.

## Required attacks

1. **Calibration taxonomy**
   - Did any unmeasured frequency/effect accidentally become `VERIFIED_REALITY`?
   - Are Yahoo/social/editorial sources correctly limited to sensor/discovery roles?
   - Could result snippets or hindsight leak through the proposed calibration path?

2. **Stress-grid fairness**
   - Does the truth generator structurally favor C0, C1, or N1?
   - Are W0-W4 ranges adversarial enough, or are important plausible failure worlds missing?
   - Is two scenarios per family enough for this stage?
   - Are line/wind/bank/disruption/heavy-tail assumptions clearly synthetic rather than pseudo-calibration?

3. **Model-proxy fairness**
   - Is C0 too strong or C1/N1 too weak because of arbitrary proxy coefficients?
   - Does C1 use line features in a scientifically meaningful architecture comparison, or is this merely a bad hand-built coefficient test?
   - Does N1's conditional construction unfairly mirror the synthetic truth generator?
   - Should any model-family conclusion be prohibited until a preregistered synthetic train/cal split fits coefficients without using stress-test worlds for tuning?

4. **Scoring**
   - Expected ordered-top3 log loss, KL regret, and joint Brier are used before economics.
   - Check support/mass logic and whether another proper score or calibration diagnostic is materially required now.

5. **Sample weighting**
   - The underlying synthetic race generator still contains uncalibrated class/race/line priors.
   - The stress harness cycles bank/wind and explicitly denies population-frequency claims.
   - Decide whether that is sufficient for architecture stress or whether race/class/line composition must also be balanced/stratified before trusting the synthetic diagnostic.

6. **Runtime assurance**
   - Specify the smallest exact native/conformance run required before promotion.
   - Do not convert a tooling inconvenience into a demand for unnecessary infrastructure.

7. **Next-step discipline**
   - No C1/N1 promotion from this receipt.
   - No coefficient retuning merely to win this grid.
   - No untouched validation opening.
   - Identify the smallest next experiment that most reduces model-architecture uncertainty.

## Required output

Return:

- `LAB_REVIEWED_HEAD: 18c0a4c89c886a09e47e0e8aa9911a2ec1f6f76c`
- `LAB_VERDICT: PASS / PASS_WITH_FIXES / MATERIAL_BLOCK`
- `CALIBRATION_REGISTRY: PASS / FIX_REQUIRED`
- `STRESS_GRID_FAIRNESS: PASS / FIX_REQUIRED`
- `MODEL_PROXY_FAIRNESS: PASS / FIX_REQUIRED`
- `SCORING: PASS / FIX_REQUIRED`
- `SAMPLE_WEIGHTING: PASS / FIX_REQUIRED`
- `RUNTIME_ASSURANCE: SUFFICIENT_FOR_WORKING_STAGE / NATIVE_RUN_REQUIRED_NOW`
- any current scientific/material blocker
- any minor safe fix
- exact next experiment
- `UNTOUCHED_VALIDATION_MAY_OPEN: NO`

Do not demand that synthetic evidence prove real edge. The goal is to falsify architecture mistakes before touching new real validation.
