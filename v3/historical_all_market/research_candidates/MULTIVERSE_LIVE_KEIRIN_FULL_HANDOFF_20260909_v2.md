# MULTIVERSE LIVE — KEIRIN RESEARCH / CANDIDATE LANE
## FULL HANDOFF / RECOVERY / CONTINUOUS EXECUTION PLAN v2

Checkpoint: 2026-09-09 07:57 JST
Role: KEIRIN Research / Candidate Lane
Canonical repo: `fufufu1116/multiverse-research`
Research branch: `research/keirin-real-evidence-dual-lane-20260901-v1`
Branch head before this handoff write: `6dfb531b1206dd2bc219ec77dc47aa21b3ade1c5`
Runtime: OFF

---

## 0. 最重要 — 次チャットの再開方法

このhandoffに書かれている CURRENT / NOW / LATEST / SHA / workflow状態を、そのまま最新と決めつけない。

再開時の第一行動は必ず Fresh Read:

1. research branch HEAD
2. `KEIRIN_CURRENT_RESEARCH_STATE_20260908_v114.json` または後継CURRENT
3. `KEIRIN_RESEARCH_RESUME_INDEX_20260909_v28.json` または後継Resume
4. Resumeが指す post-current delta
5. NEXTGEN5000 PRE batch workflow状態
6. active Keirin automations

Ownerに既知情報を再質問しない。
Owner操作が不要な研究・実装・検証は止まらず進める。

---

## 1. Owner固定方針

- 必要なら過去レース母数を追加収集してよい。
- ただし必ず **PRE-first**。
- 発走前に知れた情報と、結果・払戻を分離する。
- 予測・買い目・評価ルールをfreezeする前に結果を見ない。
- 結果や払戻から欠損PREを再構築しない。
- 過去レースは「当時の未来」として仮想再生する。
- 的中率だけでなく回収率、最大資金減少、一発依存、週/月安定性を評価する。
- 車券種へのこだわりはない。回収率と安定性で勝つ市場を採用する。
- 3連単の3着流し仮説は検証するが、現時点の主戦場は3連複。
- ガールズ、決勝、単騎、実力差などの条件別に買い方を変える可能性を研究する。
- Runtime OFF / 自動購入なし / Research laneからcanonical mainを勝手に変更しない。
- 利益が証明される前に「勝てる」「完成」と断言しない。

---

## 2. 進行度

- 実用・研究実装: **100%**
- 大量シミュレーション / 勝ち筋探索: **88%**
- 正式科学検証: **60%**
- 正式30/60 support: **1 rider / 2 PRE rows**
- 長期収益性証明: **未達**

実装100%と科学検証100%を混同しない。

---

## 3. 今日 2026-09-09 京王閣 — 完全freeze

今日の答え合わせはOwner指示により **変更禁止**。

Active practical artifacts:
- `KEIRIN_TODAY_PRACTICAL_OPERATION_PROFILE_20260909_v2.json`
- `KEIRIN_PROSPECTIVE_PRE_DECISION_KEIOKAKU_20260909_R1_R9_v2.json`
- `KEIRIN_OWNER_PRACTICAL_CARD_20260909_v2.md`

R1-R7/R9: NO_BET
R8:
- 発走 23:00
- 3連複 `1=2=3`
- conservative ticket probability = `0.342756614995`
- stake = 100円
- 3.3倍未満: NO_BET
- valid odds 3.3〜80倍: BUY_CANDIDATE 100円
- >80倍: 別のcurrent PRE odds sourceで照合できた場合のみ候補
- 欠損 / stale / placeholder / contradictory odds: NO_BET_UNVERIFIED

京王閣の購入判定・23:45答え合わせautomationは触らない。

---

## 4. DEV2000復旧済み

約2000レースの元データは失われていなかった。Google Driveから復旧し、主要監査hash一致。

Partition:
- A = 1000R burned development
- B = 500R burned development
- C = 500R protected / unscored

Cは救済チューニングや候補選択に使わない。
ECON_HOLDOUT1000もsealed。

Critical artifact:
- `KEIRIN_DEV2000_DRIVE_RECOVERY_AND_AB_REPLAY_20260909_v1.json`

---

## 5. 現在の車券研究

### 5.1 3連複 primary development center

Rule:
- model top1 agreement
- conservative top1 >= 0.40
- consensus top3 3連複 1点
- conservative ticket EV >=10%
- odds <=20x
- flat 100円

Burned A+B:
- A 56 bets / recovery 108.21%
- B 33 bets / recovery 185.45%
- AB 89 bets / hit 13.48% / recovery 136.85%

これはdevelopment候補であり、future profit provenではない。

### 5.2 20倍超

比較可能な追加27件:
- hit/return approximately 0
- incremental ROI approximately -100%

よって20倍超は数学上禁止ではないが、現在の実地昇格根拠はない。
future longshot shadow laneとして検証する。

### 5.3 3連単「1着固定・2着絞り・3着流し」

Owner仮説を専用simulatorで検証済み。
代表4点型 AB:
- hit rate ~27.18%
- recovery ~86.74%

当たりやすくなるが回収率で現3連複に負ける。
現時点ではprimaryへ昇格しない。

### 5.4 Girls

A+B 113R:
- Candidate A top1 hit ~69.91%
- non-Girls ~43.11%
- winner in model top3 ~95.58%

「ガールズは個人実力の信号が強い」仮説はかなり支持。
ただし単純な車券ルールではA/B両方安定プラスが未発見。
当てやすい != 儲けやすい。

### 5.5 score-gap

男子non-Girlsでは、PRE競走得点1位と2位の差が大きいほどwinner top1 hitが改善。
>=5点差で top1 hit ~57.93%。

一方、高confidence exact top3 set hitはgap拡大で低下。
解釈:
**頭は分かりやすくなるが、相手/3着が散る条件がある。**

---

## 6. 新conditional 3連複 challenger

Burned A+Bでposthoc発見した候補:

- non-Girls
- top PRE score gap <5
- model top1 agreement
- conservative top1 >=0.40
- fixed top1 + next3 ridersから3連複候補
- each EV >=10%
- each odds <=20
- max2 tickets
- flat 100円 each

Results:
- A recovery ~120.32%
- B recovery ~144.15%
- AB 124 bet races / 146 tickets / recovery ~128.97%
- largest single return share ~9.4%
- positive week fraction 0.8

ただしA+Bを見た後に発見したため **shadow-only**。
artifact:
- `KEIRIN_CONDITIONAL_SHADOW_CANDIDATE_FREEZE_20260909_v1.json`

---

## 7. 88,200ルール大量探索

artifact:
- `KEIRIN_DEV2000_AB_MASS_3RENHUKU_GRID_88200_20260909_v1.json`

3連複でPRE-only features / ticket policyを組み合わせ、**88,200 rules**を探索。

500R×3区間:
- min10 bets/split & all positive = 1011 rules
- min20 = 441
- min30 = 87

より厳しい250R×6区間:
- all 6 positive = **0**
- >=5/6 positive = 177

Top100 5/6候補の失敗block:
- Q2 = 86
- Q1 = 11
- Q3 = 3
- Q4/Q5/Q6 = 0

結論:
**現時点で「勝利の方程式完成」とは言わない。**
大量探索後のwinnerをそのまま採用しない。

---

## 8. Q2診断

artifact:
- `KEIRIN_DEV2000_AB_Q2_INSTABILITY_DIAGNOSTIC_20260909_v1.json`

Q2は基本のwinner-ranking精度自体は崩れていない。
代表ruleではQ2:
- 9 bets
- 0 hit
- model expected hits ~1.397
- zero-hit probability under conservative model ~21.4%
- market-normalized world ~38.3%

つまり特定日付regime崩壊の証拠としては弱い。
Q2/date-specific rescue filterを追加しない。

---

## 9. model vs market stress

artifact:
- `KEIRIN_DEV2000_AB_MODEL_MARKET_MIXTURE_STRESS_20260909_v1.json`

Monte Carlo 50,000 reps / mixture point。

Selected-ticket true probabilityを
market-normalized probability と conservative model probability のmixとして検証。

Break-even model contribution approx:
- center ~0.328
- conditional max2 ~0.325
- broad candidate ~0.332

重要:
model probabilityが完全に正しい仮想世界でも、250R×6 blockすべてprofitになる確率は低い。
よって6/6 positiveだけを唯一のpass gateにしない。

Future verdictは:
- sample size
- calibration
- ROI
- drawdown
- hit/profit concentration
- week/month stability
- block bootstrap
を合わせる。

---

## 10. NEXTGEN5000 — 母数拡張

過去に作った5000R母集団をDriveから復旧。

Critical artifact:
- `KEIRIN_NEXTGEN5000_UNIVERSE_RECOVERY_20260909_v1.json`

Candidate universe:
- 9201 races
- date window 2026-03-01..2026-06-30

Locked universe:
- 5000 races
- exact SHA256:
  `dd2045cc609c37c08a9e65ba4f80ab121803d0749440a7023394e431a1678781`
- result-independent date/venue/race ascending selection
- archived 122 daily pagesからexact reproduction PASS

旧formal governanceではretrospective NEW_HISTORICAL5000はformal admission blocked。
理由はpoint-in-time PRE/source provenance。
したがって今のNEXTGEN5000は **exploratory development expansion**。
正式30/60 supportへ勝手に加算しない。

---

## 11. NEXTGEN5000 PRE batch 2001–2500

tool:
- `tools/keirin_nextgen5000_pre_bulk_recovery_v1.py`

workflow:
- `.github/workflows/keirin-nextgen5000-pre-batch-2001-2500-v1.yml`

run:
- GitHub Actions run `34286882585`
- conclusion: SUCCESS

receipt:
- `KEIRIN_NEXTGEN5000_PRE_2001_2500_RECOVERY_RECEIPT_20260909_v1.json`

Results:
- requested 500
- **493 successful PRE races**
- **3528 PRE rows**
- 7 rejected fail-closed for active-car continuity
- no result emitted
- no payout emitted
- no odds emitted
- no forecast/comment emitted
- raw mixed HTML not persisted
- formal support increment = 0

この493RはDEV2000外の母数追加として利用可能。

---

## 12. NEXTGEN5000 batch 2501–3000

workflow:
- `.github/workflows/keirin-nextgen5000-pre-batch-2501-3000-v1.yml`

GitHub Actions run:
- `34288111136`

Checkpoint 07:57 JST:
- **IN_PROGRESS**
- outcome access during PRE = false

再開時はFresh statusを確認。
成功したら同じ形式でreceiptを固定し、必要なら3001–3500へ継続してよい。
Ownerは追加historical PRE collectionを許可済み。

---

## 13. batch 2001–2500 result access前freeze

artifact:
- `KEIRIN_NEXTGEN5000_BATCH2001_2500_PREOUTCOME_EVAL_FREEZE_20260909_v1.json`

Price-independent challenger:
`NON_GIRLS_GAP_LT3_CONF40_TOP3_3RENHUKU_1PT_NO_PRICE_FILTER`

Rule:
- non-Girls
- top PRE score gap <3.0
- two model lineages agree top1
- conservative top1 >=0.40
- one top3 3連複 ticket
- race selectionにodds/result/payoutを使わない
- flat hypothetical 100円

Burned reference:
- A1 52 selected / ROI +7.31%
- A2 46 / +42.39%
- B 55 / +42.0%
- AB 153 / +30.33%

Known six-250 block ROI:
`[+50.43%, -26.90%, -22.86%, +97.20%, +80.74%, +4.64%]`

負けblockも含んだままfreeze済み。
新500の結果を見て救済調整してはいけない。

---

## 14. Historical virtual-future protocol

artifact:
- `KEIRIN_HISTORICAL_VIRTUAL_FUTURE_REPLAY_PROTOCOL_20260909_v1.json`

PRE vault:
- historical racecard PRE
- rider/car
- competition score at race
- class/style
- venue/bank
- race stage if objectively sourced
- Girls flag
- objective line/solo only if provenance is defensible
- point-in-time recent form
- PRE odds only for price-gate research

Outcome escrow:
- finish order
- payout/settlement
- result status

必ずprediction/selection freeze後にjoin。

---

## 15. Owner仮説の現在地

### 決勝
「全員強く拮抗するので荒れやすい」仮説。
現在のDEV2000 structured PREにはrace_stage明示が足りず、直接の大標本検証は未完。
NEXTGEN historical PRE拡張ではobjective race_stageを取得して検証する。

### 単騎
「単騎が食い込んで展開を荒らす」仮説。
客観的line/solo provenanceが必要。
人の予想並びを客観事実として無条件採用しない。

### ガールズ
winner rankingの強さはburned A/Bで支持。
経済edgeは未証明。

---

## 16. Active automations

- 京王閣R8購入判定 — enabled; 今日22:40 JST
- 京王閣実用版答え合わせ — enabled; 今日23:45 JST; **変更禁止**
- Keirin 30/60 Gate — enabled hourly; Resume v28+を参照
- 旧 Keirin PRE 自動進行 — disabled

---

## 17. 次チャットでOwner操作なしに進める順番

1. Fresh GitHub / Resume / Delta / automations read.
2. Run 34288111136 status確認。
3. 2501–3000成功ならreceipt固定。
4. 必要に応じて3001–3500, 3501–4000...とPRE-only母数を増やす。
5. 各batchで結果を見る前にprediction / evaluation freezeを作る。
6. PRE側predictionをmaterializeした後だけoutcome escrowを開けてscore。
7. 2001–2500のfrozen challengerを後出し変更なしで検証。
8. 新発見は別candidateとしてfreezeし、同じデータで「validated」と呼ばない。
9. race_stage/Girls/score-gap/ticket structureを母数増加後に再評価。
10. solo/lineはobjective provenanceが確立してから入れる。
11. formal 30/60 prospectively valid PREは別laneで継続。
12. DEV2000 C / ECON_HOLDOUT1000は救済目的で開けない。
13. 今日の京王閣answer-checkはそのまま。

---

## 18. Absolute prohibitions

- NO DEV2000 C rescue tuning/scoring
- NO ECON_HOLDOUT1000 open
- NO result/payout -> PRE reconstruction
- NO outcome access before prediction/evaluation freeze
- NO posthoc rescue on the same new batch
- NO automatic betting
- NO Runtime enable
- NO Research-lane canonical main mutation
- NO profitability claim from burned/search-selected data alone

---

## 19. Resume anchors

Use:
- CURRENT: `KEIRIN_CURRENT_RESEARCH_STATE_20260908_v114.json` or later successor
- Resume: `KEIRIN_RESEARCH_RESUME_INDEX_20260909_v28.json` or later successor
- Delta: `KEIRIN_V114_POST_CURRENT_ENGINEERING_DELTA_20260909_v20.json` or later successor

Fresh Read always overrides this handoff.

---

## 20. Progress line — fixed reporting convention

Every project-progress reply should end with a concise percentage so Owner can see movement.

Checkpoint:
- 実用実装: **100%**
- 大量シミュレーション / 勝ち筋探索: **88%**
- 正式科学検証: **60%**

100% scientific completion requires real untouched/prospective replication, not just more code or more searched rules.
