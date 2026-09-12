# KEIRIN_EXPERIMENT_LEDGER v1

Append-only compact experiment index for scientific continuity.
Do not paste full raw datasets/results here; reference artifact paths/IDs.
Detailed machine-readable ledger on active branch:
`v3/historical_all_market/continuity/KEIRIN_EXPERIMENT_LEDGER_v1.jsonl`

## Entry schema
Each meaningful batch should append:
- experiment_id
- timestamp_jst
- hypothesis/question
- input_dataset_id/path/hash/count
- method/model_version
- hidden_outcome_discipline
- metrics
- concise_result
- conclusion
- rule/finding_candidate
- artifact_paths
- next_action

---

## CONTINUITY-BOOTSTRAP-20260912-01
- timestamp_jst: 2026-09-12
- hypothesis/question: Can Keirin research survive chat interruption/capacity exhaustion without long handoffs?
- input_dataset_id/path/hash/count: N/A (operating-protocol experiment)
- method/model_version: GitHub-externalized continuity v1
- hidden_outcome_discipline: N/A
- metrics: current-state pointer created; rule registry created; append-only ledger created
- concise_result: Durable three-part continuity substrate prepared on dedicated research branch.
- conclusion: Chat can be treated as ephemeral if active Keirin lane checkpoints its live research state/artifact pointers here.
- rule/finding_candidate: Keep boot packets small and move large outputs outside chat.
- artifact_paths: `research/keirin/continuity/KEIRIN_CURRENT_STATE.md`, `KEIRIN_RULE_REGISTRY.md`, `KEIRIN_EXPERIMENT_LEDGER.md`
- next_action: Fresh Read Issue #377 + these three files, then Fresh Read active research branch.

## EXP-500M-POOLED-48-THREE-VENUES
- timestamp_jst: 2026-09-12
- hypothesis/question: Does frozen B1a retain non-collapsing exact-500m ranking signal across multiple venues, and does an A-vs-S subgroup edge replicate?
- input_dataset_id/path/hash/count: `v3/historical_all_market/research_candidates/KEIRIN_500M_FOUR_DAY_THREE_VENUE_ROBUSTNESS_AUDIT_20260912_v1.json`; n=48; 4 full days / 3 venues
- method/model_version: frozen `B1a_RECONSTITUTED_v1`; no retune
- hidden_outcome_discipline: retrospective evidence classes preserved; no odds, post-hoc deletion, length coercion or relabelling
- metrics: top1 22/48=45.83%; winner Top3 37/48=77.08%; weighted log loss 1.57024; A top1=45.0%; S top1=46.43%
- concise_result: Exact-500m ranking signal did not collapse across Omiya/Kochi/Utsunomiya; earlier A>S story disappeared.
- conclusion: Do not subgroup-retune. Retrospective robustness is encouraging but genuine prospective 500m evidence is still required.
- rule/finding_candidate: `NO_STABLE_A_VS_S_DIRECTION` on current 500m evidence.
- artifact_paths: detailed audit path above; per-day artifacts indexed in active machine-readable ledger.
- next_action: Freeze Omiya 2026-09-13 exact-500m R1-R12 PRE card + B1a before outcomes.

## EXP-335M-MAEBASHI-20260815-FULLDAY
- timestamp_jst: 2026-09-12
- hypothesis/question: Does frozen B1a retain ranking signal on exact 335m without coercion to 333.3m?
- input_dataset_id/path/hash/count: `v3/historical_all_market/research_candidates/retrospective_335m_maebashi_20260815_full_day/KEIRIN_MAEBASHI_20260815_335M_B1A_RETROSPECTIVE_FULL_DAY_R1_R9_v1.json`; n=9
- method/model_version: frozen `B1a_RECONSTITUTED_v1`
- hidden_outcome_discipline: PRE fields frozen before separate scoring; retrospective class retained; no odds/retune
- metrics: top1 4/9=44.44%; winner Top3 7/9=77.78%; log loss 1.44593
- concise_result: Initial exact-335m retrospective signal established.
- conclusion: Independent day required before claiming stability.
- rule/finding_candidate: none adopted.
- artifact_paths: path above.
- next_action: execute preregistered second independent day without changing B1a.

## EXP-335M-MAEBASHI-20260809-FULLDAY
- timestamp_jst: 2026-09-12
- hypothesis/question: Does the first 335m full-day result replicate on the chronologically nearest prior independent Maebashi first-day card?
- input_dataset_id/path/hash/count: `v3/historical_all_market/research_candidates/retrospective_335m_maebashi_20260809_full_day/KEIRIN_MAEBASHI_20260809_335M_B1A_RETROSPECTIVE_FULL_DAY_R1_R11_v1.json`; n=11
- method/model_version: frozen `B1a_RECONSTITUTED_v1`; preregistration commit `1eca613cddfdd78a798b8cfbbe1d787bc1566146`; PRE-freeze commit `7f31322035e964355358fe3a0077153c754dd72d`
- hidden_outcome_discipline: complete R1-R11 PRE artifact committed before outcome extraction; no odds/payouts, retune, deletion or length coercion
- metrics: top1 3/11=27.27%; winner Top3 7/11=63.64%; log loss 1.98971; MRR 0.49545
- concise_result: Second independent 335m day was materially weaker than the first; negative result retained, including incident races under preregistered full-card rules.
- conclusion: 335m historical performance is heterogeneous; do not retune from either day.
- rule/finding_candidate: Genuine prospective 335m evidence now matters more than additional tuning.
- artifact_paths: result path above; PRE artifact `.../KEIRIN_MAEBASHI_20260809_335M_B1A_PRE_FREEZE_R1_R11_v1.json`
- next_action: Score already-frozen 2026-09-12 prospective Maebashi R1-R9 after official outcomes.

## EXP-335M-PROSPECTIVE-MAEBASHI-20260912-R1-R9
- timestamp_jst: 2026-09-12
- hypothesis/question: Can frozen B1a be evaluated prospectively on exact 335m with zero circumference coercion?
- input_dataset_id/path/hash/count: `v3/historical_all_market/research_candidates/KEIRIN_335M_PROSPECTIVE_LANE_BOOTSTRAP_STATUS_20260912_v1.json`; n=9
- method/model_version: frozen `B1a_RECONSTITUTED_v1`
- hidden_outcome_discipline: all R1-R9 frozen before target outcomes; no payout/actual-odds input; no retune
- metrics: pending official outcome scoring
- concise_result: 9/9 forward cases successfully frozen before outcomes.
- conclusion: Evidence class is genuinely prospective; scientific result remains pending until all 9 are scored.
- rule/finding_candidate: none until scoring.
- artifact_paths: path above plus per-race PRE/prediction artifacts under corresponding Maebashi prospective directories.
- next_action: Score all 9 after official outcomes; no deletion or retune.

## CONTINUITY-SYNC-20260912-02
- timestamp_jst: 2026-09-12 20:06 JST
- hypothesis/question: Can the live Keirin lane be resumed from repository state alone after repeated streaming/capacity interruptions?
- input_dataset_id/path/hash/count: active branch `research/keirin-real-evidence-dual-lane-20260901-v1`; synchronized checkpoint commit `6eace27fd46021de256ed0e0afb7f82b5d96b6e3`
- method/model_version: Issue #377 continuity protocol + PR #385 substrate
- hidden_outcome_discipline: synchronization only; prediction semantics unchanged
- metrics: CURRENT_STATE synchronized; RULE_REGISTRY synchronized; latest meaningful experiments indexed here; large data kept by artifact path
- concise_result: Next chat can Fresh Read #377, PR #385, these three continuity files, then the active branch checkpoint and continue without a giant handoff.
- conclusion: Repository-only resume path is now populated with current science, fixed rules, active model binding, blockers and exact next actions.
- rule/finding_candidate: Chat remains an ephemeral terminal; GitHub is canonical continuity state.
- artifact_paths: `research/keirin/continuity/*`; active detailed continuity paths under `v3/historical_all_market/continuity/`
- next_action: Continue Omiya 2026-09-13 prospective 500m PRE freeze and Maebashi 2026-09-12 prospective scoring when authoritative data is available.
