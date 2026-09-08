# MULTIVERSE LIVE — KEIRIN RESEARCH / CANDIDATE LANE
## FULL HANDOFF / RECOVERY / CONTINUOUS EXECUTION PLAN v3

Checkpoint: 2026-09-09 08:02 JST
Canonical repo: `fufufu1116/multiverse-research`
Research branch: `research/keirin-real-evidence-dual-lane-20260901-v1`
Branch head before handoff write: `75c25bd96c1b8eb627222881f51c383d3d8c30dc`
Runtime: OFF

## 0. 再開ルール

このhandoffの CURRENT / NOW / workflow status を最新と決めつけない。
次チャットの最初は必ず Fresh Read:

1. branch HEAD
2. `KEIRIN_CURRENT_RESEARCH_STATE_20260908_v114.json` または後継CURRENT
3. `KEIRIN_RESEARCH_RESUME_INDEX_20260909_v29.json` または後継Resume
4. Resumeが指す delta（checkpointでは v21）
5. NEXTGEN5000 batch workflow states
6. active Keirin automations

Ownerに既知情報を再質問しない。Owner操作不要なら止まらず進める。

## 1. Owner固定方針

- 母数不足なら追加の過去レースPREを集めてよい。
- 必ず PRE-first。
- PREと結果/払戻を別管理。
- prediction / selection / evaluation ruleをfreezeする前にoutcomeを開けない。
- result/payoutからPREを再構築しない。
- 過去レースを「当時の未来」として再生する。
- 的中率だけでなく回収率、drawdown、一発依存、週/月安定性、確率校正で評価する。
- 車券種は固定しない。回収率と安定性で採用。
- 3連単3着流し、決勝、単騎、ガールズ、実力差を仮説として検証。
- Runtime OFF、自動購入なし、Research laneからcanonical mainを変更しない。
- 未証明の利益を「勝利の方程式完成」と呼ばない。

## 2. 進行度

- 実用・研究実装: **100%**
- 大量シミュレーション / 勝ち筋探索: **89%**
- 正式科学検証: **60%**
- 正式30/60 support: **1 rider / 2 PRE rows**
- profitability proven: **NO**

## 3. 今日 2026-09-09 京王閣 — freeze維持

Owner指示: **答え合わせはそのまま。変更禁止。**

Artifacts:
- `KEIRIN_TODAY_PRACTICAL_OPERATION_PROFILE_20260909_v2.json`
- `KEIRIN_PROSPECTIVE_PRE_DECISION_KEIOKAKU_20260909_R1_R9_v2.json`
- `KEIRIN_OWNER_PRACTICAL_CARD_20260909_v2.md`

R1-R7/R9 NO_BET。
R8:
- 23:00
- 3連複 `1=2=3`
- conservative p = `0.342756614995`
- stake 100円
- <3.3x NO_BET
- 3.3–80x BUY_CANDIDATE
- >80x requires independent current PRE odds corroboration
- missing/stale/placeholder/contradictory => NO_BET_UNVERIFIED

京王閣R8購入判定と23:45答え合わせautomationは変更しない。

## 4. DEV2000

Driveから復旧済み。
- A = 1000R burned
- B = 500R burned
- C = 500R protected/unscored

Cは救済チューニング・候補選択に使わない。
ECON_HOLDOUT1000もsealed。

Pointer:
- `KEIRIN_DEV2000_DRIVE_RECOVERY_AND_AB_REPLAY_20260909_v1.json`

## 5. 主な車券研究結果

### 3連複 center candidate
Rule:
top1 agreement / conservative top1 >=.40 / top3 1pt / ticket EV>=10% / odds<=20 / 100円。

Burned:
- A recovery 108.21%
- B recovery 185.45%
- AB 89 bets / hit 13.48% / recovery 136.85%

Development-only。

### 20倍超
Comparable incremental >20x = 27 bets, approximately zero return。
高オッズ自体は禁止ではないが、実地昇格根拠なし。shadow-only。

### 3連単3着流し
代表4点構造:
- AB hit ~27.18%
- recovery ~86.74%

的中率は上がるが現3連複より経済性が弱い。primaryへ昇格しない。

### Girls
A+B 113R:
- Candidate A top1 hit ~69.91%
- non-Girls ~43.11%
- winner in top3 ~95.58%

winner rankingは明確に強いが、simple market profit ruleは未発見。

### Score gap
男子では得点1位-2位差が大きいほど1着的中が改善。
>=5点差でtop1 hit ~57.93%。
一方 exact top3 companion setは散りやすくなる。
Ownerの「頭は分かるが3着は散る」感覚と整合する診断。

## 6. Conditional 3連複 challenger

Posthoc burned A+B candidate:
- non-Girls
- score gap <5
- top1 agreement
- conservative top1 >=.40
- fixed top1 + next3 combinations
- EV>=10%
- odds<=20
- max2 tickets

Results:
- A recovery ~120.32%
- B ~144.15%
- AB 124 bet races / 146 tickets / recovery ~128.97%
- largest single return share ~9.4%
- positive week fraction 0.8

Posthocなのでshadow-only。
Pointer:
- `KEIRIN_CONDITIONAL_SHADOW_CANDIDATE_FREEZE_20260909_v1.json`

## 7. 88,200-rule massive search

Pointer:
- `KEIRIN_DEV2000_AB_MASS_3RENHUKU_GRID_88200_20260909_v1.json`

88,200の3連複rulesをPRE features×ticket policiesで探索。

500R×3:
- all positive min10 = 1011
- min20 = 441
- min30 = 87

250R×6:
- all 6 positive = **0**
- >=5/6 positive = 177

Top100 5/6 candidate failed block:
- Q2 86
- Q1 11
- Q3 3

結論:
大量探索のwinnerをそのまま採用しない。
「勝利の方程式完成」は未達。

## 8. Q2診断

Pointer:
- `KEIRIN_DEV2000_AB_Q2_INSTABILITY_DIAGNOSTIC_20260909_v1.json`

Q2のbasic winner-rankingは崩れていない。
代表rule Q2 = 9 bets / 0 hit。
zero-hit probability:
- conservative model ~21.4%
- normalized market ~38.3%

特定期間regime崩壊の証拠は弱い。date-specific rescue tuning禁止。

## 9. model-market stress

Pointer:
- `KEIRIN_DEV2000_AB_MODEL_MARKET_MIXTURE_STRESS_20260909_v1.json`

50,000 Monte Carlo reps / mixture point。
Economic break-evenは概ね true probabilityにmodel signalが1/3程度寄与する付近。
modelが完全に正しい世界でも250R×6全部profitは低確率。
よって6/6 positivityはsole gateにしない。

Future validation:
sample size + calibration + ROI + drawdown + concentration + weekly/monthly stability + bootstrap。

## 10. NEXTGEN5000 universe

Pointer:
- `KEIRIN_NEXTGEN5000_UNIVERSE_RECOVERY_20260909_v1.json`

Recovered:
- candidate universe 9201R
- 2026-03-01..2026-06-30
- locked first5000 = 5000R
- SHA256 `dd2045cc609c37c08a9e65ba4f80ab121803d0749440a7023394e431a1678781`
- result-independent date/venue/race ascending
- archived 122 daily pagesからexact reproduction PASS

Formal historical5000 admissionは旧governance上blocked。
現在は exploratory development expansion。
正式30/60 supportへ加算しない。

## 11. PRE expansion — 2001..2500

Run `34286882585`: SUCCESS。

Receipt:
- `KEIRIN_NEXTGEN5000_PRE_2001_2500_RECOVERY_RECEIPT_20260909_v1.json`

- requested 500
- usable PRE races **493**
- rejected 7 fail-closed
- PRE rows **3528**
- no outcome/payout/odds/forecast emitted
- no formal support increment

Evaluation freeze:
- `KEIRIN_NEXTGEN5000_BATCH2001_2500_PREOUTCOME_EVAL_FREEZE_20260909_v1.json`

## 12. PRE expansion — 2501..3000

Run `34288111136`: **SUCCESS**。

Receipt:
- `KEIRIN_NEXTGEN5000_PRE_2501_3000_RECOVERY_RECEIPT_20260909_v1.json`

- requested 500
- usable PRE races **494**
- rejected 6 fail-closed
- PRE rows **3497**
- no outcome/payout/odds/forecast emitted

Evaluation freeze:
- `KEIRIN_NEXTGEN5000_BATCH2501_3000_PREOUTCOME_EVAL_FREEZE_20260909_v1.json`

### cumulative beyond DEV2000
- requested = 1000
- usable PRE races = **987**
- fail-closed rejects = 13
- PRE rows = **7025**
- outcome access during PRE = 0

## 13. PRE expansion — 3001..3500

Workflow:
- `.github/workflows/keirin-nextgen5000-pre-batch-3001-3500-v1.yml`

Run:
- `34288642577`

Checkpoint:
- **IN_PROGRESS**
- PRE-only
- no outcome access

次チャットはFresh status確認。Successならreceipt固定し、結果を見る前にevaluation freezeを作る。
必要なら3501..4000へ進む。

## 14. Untouched batch challenger

2001..2500でfreeze済み:
`NON_GIRLS_GAP_LT3_CONF40_TOP3_3RENHUKU_1PT_NO_PRICE_FILTER`

Rule:
- non-Girls
- top PRE score gap <3
- two model lineages agree top1
- conservative top1 >=.40
- one consensus top3 3連複
- race selectionにodds/result/payoutを使わない
- hypothetical flat 100円

Burned reference:
- A1 52 / ROI +7.31%
- A2 46 / +42.39%
- B 55 / +42.0%
- AB 153 / +30.33%

Known six-250 ROI:
`[+50.43%, -26.90%, -22.86%, +97.20%, +80.74%, +4.64%]`

2501..3000にも**同じruleをthreshold変更なしでfreeze済み**。
新batch outcomeを見て救済調整しない。

## 15. Historical virtual-future protocol

Pointer:
- `KEIRIN_HISTORICAL_VIRTUAL_FUTURE_REPLAY_PROTOCOL_20260909_v1.json`

PRE vaultとOutcome escrowを分離。
prediction/selection/evaluation freeze後だけjoin。

## 16. Owner hypotheses

- 決勝: objective race_stageをhistorical expansionで取得し検証。
- 単騎: objective line/solo provenance確立後に検証。人の並び予想をground truth扱いしない。
- ガールズ: ranking superiority supported; economic edge not proven。
- score-gap: head clarity / companion scatter supported diagnostically。

## 17. Active automations

- 京王閣R8購入判定 — enabled, 今日22:40 JST
- 京王閣実用版答え合わせ — enabled, 今日23:45 JST, **変更禁止**
- Keirin 30/60 Gate — enabled hourly, Resume v29+参照
- old Keirin PRE auto progression — disabled

## 18. Next-chat continuous execution

1. Fresh GitHub / Resume v29+ / delta v21+ / automations。
2. Run 34288642577 Fresh status。
3. Successなら3001..3500 receipt固定。
4. outcome前evaluation freeze。
5. 必要なら3501..4000 → 4001..4500 → 4501..5000をPRE-onlyで続行。
6. 各batchのPRE prediction/selectionを先にmaterialize。
7. その後だけOutcome escrowを開けてfrozen rulesをscore。
8. Earlier scored batchから新仮説が出ても、そのbatchでvalidated扱いしない。later untouched batchへfreeze。
9. race_stage / Girls / score-gap / ticket structureを大母数で再評価。
10. objective solo/line provenanceを別に構築。
11. formal 30/60は別prospective laneで継続。
12. DEV2000 C / ECON_HOLDOUT1000はrescue目的で開けない。
13. 今日の京王閣answer-checkはそのまま。

## 19. Prohibitions

- NO DEV2000 C rescue scoring/tuning
- NO ECON_HOLDOUT1000 open
- NO result/payout -> PRE reconstruction
- NO batch outcome before freeze
- NO same-batch posthoc rescue
- NO auto betting
- NO Runtime ON
- NO Research-lane main mutation
- NO profitability claim from burned/search-selected evidence alone

## 20. Resume anchors

- CURRENT: `KEIRIN_CURRENT_RESEARCH_STATE_20260908_v114.json` or later
- Resume: `KEIRIN_RESEARCH_RESUME_INDEX_20260909_v29.json` or later
- Delta: `KEIRIN_V114_POST_CURRENT_ENGINEERING_DELTA_20260909_v21.json` or later

Fresh Read overrides this handoff.

## 21. Fixed progress reporting

Every project-progress reply ends with percentage.

Checkpoint:
- 実用実装 **100%**
- 勝ち筋探索 **89%**
- 正式科学検証 **60%**
