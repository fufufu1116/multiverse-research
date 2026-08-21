# Multiverse 競輪ver — いまここ

最終更新: 2026-08-21 09:43 JST

この1枚は **主向けの現在地表示**。
NOW / CURRENT / LATEST の技術確認は必ず GitHub Fresh Read を優先する。

## 現在の結論

**競輪科学は、Synthetic（合成）限定で再開許可済みです。**

Foundation v1 は正式受理・固定済み。
その後の別Gateとして、PR #32 exact head
`5ddca980391c0a3692454cdad540825c155852e7`
について:

- Lab（検証室） exact-head PASS
- Auditor（監査室） PASS
- Owner Gate（主承認） PASS

が揃いました。

ただし、これは競輪研究全体の自由な再開ではありません。
**許可範囲はSyntheticだけ**です。

---

## 今回許可された範囲

1. source-independent synthetic regression checks
   - 外部・現実データを使わない回帰・不変条件検査
2. Digital Twin W0-W4 synthetic stress / failure diagnostics
   - 合成世界W0〜W4での壊れ方・耐性検査
3. C0/C1/N1 comparison only inside those synthetic worlds
   - C0/C1/N1比較は、その合成世界の中だけ

この範囲から得られる証拠は引き続き
**SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY**
（合成データによる工学・反証検査のみ）です。

現実世界で勝てる、利益が出る、ROIがある、という証拠にはなりません。

---

## 引き続き禁止・未許可

- real/live input collection（現実・ライブ入力収集）
- economics / bankroll evaluation（経済評価）
- real-world / untouched validation（現実・未使用検証）
- PR #15隔離指標の閲覧・再開選択への利用
- RESULT/PAYOUT（結果・払戻）
- ECON_HOLDOUT1000 の開封・採点
- DEV2000 C の新系統救済
- 同一系統 B/C 救済チューニング
- model promotion（モデル昇格）
- 外部業者・外部提供者への連絡
- automated bulk collection（自動大量収集）
- access-control / rate-limit / CAPTCHA / WAF bypass
- 現実のお金を使う賭け
- Synthetic結果をReal edge / ROI証拠として扱うこと

scientific segment C scoring count は **0のまま**です。

---

## 最後に正当に完了した科学チェックポイント

PR #14

Labが確認した科学head:
`e70bda39a5d3ce585af4e028b35106b859871bd9`

PR #15 は引き続き
`QUARANTINED_NOT_ADMITTED（隔離・採用禁止）`
です。

---

## 次にやること

最初の実行直前に、必ずFresh Readして:

- canonical main
- `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json`
- `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
- `governance/KEIRIN_LIMITED_SYNTHETIC_EXECUTION_AUTHORIZATION_RECEIPT_20260821_v1.json`

の一致を確認します。

一致していれば、上記3種類のSynthetic限定scopeから最小Batchを開始します。

少しでもRelevant drift（重要なずれ）があれば fail-closed（止める）です。

---

## 自動化について

研究判断を勝手に広げる自動化はまだしません。

ただし進行がボトルネックになる場合は、
Fresh Read、SHA確認、Review Request受け渡し、証拠整理、CIなど
**科学意味を変えないAI同士のルーチン連携**から先に自動化候補へ回します。

---

## 主がやること

**今はなし。**

このSynthetic限定Owner Gateは今回のscope専用で、他の再開・Holdout・現実データ・経済評価等には流用しません。

詳細ルール: `AI_COUNCIL.md`
科学的Current State: `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
Foundation / vNext Current State: `multiverse_vnext/VNEXT_CURRENT_STATE_v0.json`
