# KEIRIN_CURRENT_STATE v1

Updated: 2026-09-12 20:06 JST
Authority: continuity pointer only; Fresh GitHub read required on resume.
Runtime: OFF
Automatic betting: OFF
Scientific validation progress: **85%**

## Objective
競輪研究をチャット容量に依存せず継続し、結果漏洩なし・再調整なし・走路長を正確に分離した証拠で、科学検証100%へ最短で進める。

## Canonical research pointer
- Repo: `fufufu1116/multiverse-research`
- Active research branch: `research/keirin-real-evidence-dual-lane-20260901-v1`
- Active branch checkpoint commit: `6eace27fd46021de256ed0e0afb7f82b5d96b6e3`
- Detailed canonical state: `v3/historical_all_market/continuity/KEIRIN_CURRENT_STATE.json`
- Detailed rule registry: `v3/historical_all_market/continuity/KEIRIN_RULE_REGISTRY_v1.json`
- Detailed experiment ledger: `v3/historical_all_market/continuity/KEIRIN_EXPERIMENT_LEDGER_v1.jsonl`
- Exact circumference inventory: `v3/historical_all_market/research_candidates/KEIRIN_EXACT_CIRCUMFERENCE_LANE_INVENTORY_20260912_v1.json`
- Continuity protocol: Issue #377 / Candidate PR #385

## Frozen model / current model boundary
- Winner model: `B1a_RECONSTITUTED_v1`
- Frozen predictor blob: `62ae4ebc17cda47dca1fffae190fa44caae58ca3`
- Temperature: `1.15`
- Retune: **forbidden** inside confirmatory/prospective sets.
- Current circumference challenger is supported only for exact `333.3m` and `400m` lanes.
- `335m` and `500m` are exact separate lanes and remain B1a-only until same-length challenger validation exists. Do not coerce 335→333.3 or 500→400.

## Latest scientific state
- **335m prospective / Maebashi 2026-09-12:** R1-R9 **9/9 frozen before outcomes**. Artifact: `v3/historical_all_market/research_candidates/KEIRIN_335M_PROSPECTIVE_LANE_BOOTSTRAP_STATUS_20260912_v1.json`. Scoring pending; all 9 must be retained.
- **335m retrospective / Maebashi 2026-08-15:** 4/9 top1, 7/9 winner Top3, log loss 1.44593. Artifact: `.../retrospective_335m_maebashi_20260815_full_day/KEIRIN_MAEBASHI_20260815_335M_B1A_RETROSPECTIVE_FULL_DAY_R1_R9_v1.json`.
- **335m independent replication / Maebashi 2026-08-09:** 3/11 top1, 7/11 winner Top3, log loss 1.98971. Pre-freeze commit `7f31322035e964355358fe3a0077153c754dd72d`; result artifact: `.../retrospective_335m_maebashi_20260809_full_day/KEIRIN_MAEBASHI_20260809_335M_B1A_RETROSPECTIVE_FULL_DAY_R1_R11_v1.json`. This was weaker replication; retain as negative evidence and **do not retune**.
- **500m pooled retrospective robustness:** 48 races / 4 full days / 3 venues; 22/48 top1 (45.83%), 37/48 winner Top3 (77.08%), weighted log loss 1.57024. A/S top1 difference did not persist (45.0% vs 46.43%); discard subgroup-retune story. Artifact: `v3/historical_all_market/research_candidates/KEIRIN_500M_FOUR_DAY_THREE_VENUE_ROBUSTNESS_AUDIT_20260912_v1.json`.
- **500m prospective / Omiya 2026-09-13:** final PRE freeze still pending at this checkpoint. Must freeze trustworthy R1-R12 card and B1a predictions before outcomes; live odds are not required; do not apply the 333/400 circumference challenger.

## Exact next executable actions
1. Fresh Read authoritative Omiya 2026-09-13 final racecard; once trustworthy, freeze exact-500m R1-R12 PRE inputs + frozen B1a predictions before outcomes.
2. After official Maebashi 2026-09-12 outcomes are available, score all already-frozen R1-R9 without deletion or retune and append to ledger.
3. Continue same-length 335m/500m evidence accumulation; only build a length-specific challenger after sufficient same-length evidence.
4. After each major batch, update CURRENT_STATE and append EXPERIMENT_LEDGER; do not stream large tables into chat.

## Resume procedure
1. Fresh Read Issue #377 and PR #385.
2. Fresh Read this file, `KEIRIN_RULE_REGISTRY.md`, and `KEIRIN_EXPERIMENT_LEDGER.md`.
3. Fresh Read the active research branch HEAD and the detailed canonical state/ledger paths above before treating any SHA/count/status as CURRENT.
4. Continue all Owner-free work without waiting; stop only at a genuine Owner boundary.

## Owner action
None required now.
