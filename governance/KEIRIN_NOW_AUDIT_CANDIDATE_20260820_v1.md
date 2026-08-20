# Multiverse 競輪ver — 監査中の「いまここ」候補

Status: `DRAFT / NONCANONICAL / FOUNDATION_AUDIT`

この1枚は、古い `KEIRIN_NOW.md` をいきなり上書きせず、**今の実際の状況を主向けに分かりやすく同期するための候補版**。
正式採用までは正本ではない。

## いま何をしてる？

**競輪の新しい科学実験はいったん停止。Multiverseの土台をゼロベース監査中。**

理由は研究がダメだったからではない。
研究の進み方に対して、

- Current State（現在地の記録）
- Review status（検証依頼・結果・受理の区別）
- Pause / Safe Mode（停止指示を自動実行まで止める仕組み）

の運用が追いついていないことが分かったため。

## 競輪研究はどこまで終わってる？

最新の強いCheckpoint（確認地点＝壊さず再開できる節目）は **PR #14**。

- 7車のライン構造は `4-3` を含む全15分割を耐久試験
- R0/R1/R2という3種類の仮想PRE世界を使用
- バンク、風、見える得点と隠れ能力の相関などを広く変化
- 合計 **388,800評価**
- CI（自動テスト）: PASS
- Lab（検証室）: PASS

ただし、これは **Synthetic engineering（仮想世界の耐久試験）** のPASS。
現実で勝てる証拠ではない。

Auditor（最終監査室）はPR #14ではまだ実行記録を確認できていない。
Untouched Validation（まだ見ていない本番検証）も開いていない。

## PR #15は？

PR #14の次に、約100万評価のContinuous Assumption Surface（連続仮定空間＝仮想世界の条件を細かく連続的に変える試験）を準備していた。

主の停止指示後、停止前に既に予約されていたGitHub Actions（自動実行）が1回だけ完了してしまった。

この結果は現在:

`QUARANTINED_NOT_ADMITTED`

つまり**隔離済み。結果の数字を見て研究判断に使わない**。

PR #15の自動実行は現在manual-only（手動のみ）へ変更済み。
勝手に次の科学実験は走らない。

## 今見つかったMultiverse側の問題

### 1. 状態表示が古かった

既存 `CURRENT_STATE_KEIRIN.json` と `KEIRIN_NOW.md` は00:29 JST付近の状態のまま。
実際の研究はPR #14/#15まで進んでいた。

→ 再開時に古い地点へ戻る危険がある。

### 2. 「停止」が全部の自動実行へ直結していなかった

設計上はSafe Mode（安全停止）がある。
でもPR #15のGitHub Actionsには自動的に伝わっていなかった。

→ 設計はあるが配線不足。

### 3. PRが開いているだけでは状態が分からない

たとえば:

- Lab PASS済み
- 採取終了済み
- 期限切れ
- Review依頼だけ出して結果なし
- Pause中

が全部「OPEN PR」に見える。

→ `Lifecycle Registry（案件状態一覧）` を新しく作って、これを区別し始めた。

## Multiverseを作り直すの？

**作り直さない。**

North Star Architecture（全体設計図）、Recovery Capsule（復旧パッケージ）、Zero-History Bootstrap（過去Chatなし復旧）などは強い。

新しい巨大システムを足すのではなく、既存の仕組みに不足している配線だけ直す。

## 競輪を再開する最低条件

次の5個だけ直す。

1. Pause（停止）が自動実行にも効く
2. Current State（現在地）が最新
3. Review/PRの状態一覧がある
4. 新Chatでも1回で正しい再開地点が分かる
5. 主が1画面で「正常/停止/待ち/主の作業」を分かる

フルL3/L4/L5化や新しい有料サービスは不要。

## 重要な保護状態

変わっていない。

- `ECON_HOLDOUT1000` = SEALED
- DEV2000 Cを新lineage救済に使わない
- same-lineage B/C rescue tuning禁止
- RESULT/PAYOUTは開かない
- Untouched Validationは閉じたまま
- Model promotion（モデル昇格）禁止
- 現実のお金は使わない
- 外部業者へ連絡しない

## 主が今やること

**なし。**

No.3側で監査・状態同期・忘れ物整理・停止制御を進める。
主へ返すのは、本当にOwner Gate（主本人の判断が必要な重大判断）が出た時だけ。
