# Multiverse 競輪ver — いまここ

最終更新: 2026-08-20 00:17 JST

この1枚が **主向けの進捗表**。
内部の専門用語・SHA・監査証拠は必要な時だけ展開する。

## 最終ゴール

現実の競輪について、発走前情報だけから

1. 着順確率
2. 各券種確率
3. 市場価格との比較
4. 仮想資金でBUY/NO-BETと資金配分
5. 未知の現実レースで再現するか

まで到達する。

---

## 大きな変更 — 競輪verとMultiverse本体を今から接続

競輪verが終わるまでMultiverse Genesisを寝かせる案はやめた。

今回Ownerがアップロードした `MULTIVERSE GENESIS v7` を、**今の競輪研究の運用OSとして前倒し接続**した。

つまり競輪はただの予想研究ではなく、Multiverse本体の最初の実戦Domainになる。

役割は簡単に:
- **主** = 方向と最終承認
- **Core** = 進める
- **Vault** = 証拠・正本・保護状態を守る
- **Lab** = ミス・抜け・もっと良い方法を探す
- **Auditor** = 重大変更を止める/通す

AIは主から指摘されるまで待たず、自分たちで改善点を探す。
ただし研究方向を勝手には変えない。

---

## Genesis資料の確認状態

Owner提供の主要Packetを実体SHAで照合済み。
付属SHA一覧と一致した。

特に完全Bundle:
`09_COMPLETE_ALL_IN_ONE.txt`
SHA256:
`bf5f072f17a3422a50cc366141d8b9a737f0c83d3ce30f6f23a9459848931b8c`

Main/Core、Vault、Lab、Auditor、Gemini監査Packet、CodePen Prototypeも一致確認済み。

ファイルを増やさないため、同じBundleをGitHubへ大量複製せず、必要な規則だけ既存の `AI_COUNCIL.md` とCurrent Stateへ統合する。

---

## いま何をしてる？

**Digital Twinを現実に近づけながら、Core/Vault/Lab/Auditorの自律改善ループを同時運用している。**

外部AI会議や無料枠を待たず、No.3内部で常に:

`作る -> 証拠確認 -> 穴を探す -> 判定 -> 直す`

を回す。

重大な変更だけ主へ上げる。

---

## AIが勝手にやってよいこと

- 明らかなbug修正
- test追加
- 数学チェック
- 速度/軽量化
- 重複処理削除
- 説明改善
- Fileを増やさない整理
- 現実とのズレ発見
- 新しい反証テスト
- 改善案作成
- 既存方針内のSynthetic stress test

## 主の許可が必要なこと

- 研究目的/大方向変更
- Model/lineage正式Promotion
- Freeze変更
- 評価基準変更
- Holdout/untouchedを開ける
- 新しいRESULT/PAYOUTを見る
- Material Feature正式採用/除外
- Data境界の意味を変える
- 外部連絡
- 課金/有料API/契約
- Fileの不可逆削除
- Synthetic結果を現実の証拠にする

---

## 今日すぐ分かったこと

Digital Twinに現実性バグを1件発見済み。

通常FI/FIIは基本7車なのに、Simulatorが通常世界で7/9車をランダム生成していた。

現在は:
- 通常FI/FII = 7車
- 9車 = 特別event-formatとして明示した時だけ

へ修正する方向で進めている。

これは新しい自律レビュー機構の `AUTO_FIX` 対象。
研究の意味を変えず、現実制度に合わせるだけなのでNo.3側で進める。

---

## 現在できているもの

- 仮想選手 / レース / ライン生成
- S系 / A1-A2系 / A3系を無造作に混ぜない構造
- PREで見える能力と、本当の当日能力を分離
- 5種類の仮想世界
  - 個人能力中心
  - ライン効果
  - 2・3着のライン依存
  - ライン崩壊/当日ブレ
  - 大波乱/高不確実性
- 仮想オッズ生成
- 全券種確率を一つの着順分布から作る土台
- 自律AI Council / Owner Gate
- 追加課金禁止・研究停止禁止

---

## 次にやること

1. 通常7車 / 特別9車をCode上で完全分離
2. 公開PREから現実のライン形状・脚質・B/H/S等の根本統計を確認
3. Digital Twinの作り物パラメータを「現実から確認済み / 仮定」に分ける
4. 旧方式・ライン入り方式・新方式を同条件比較
5. Labが毎Batchで新しい見落とし/効率化を探す
6. Materialな改善案だけOwner Gateへまとめて上げる
7. 仮想で壊した後、現実PREへ戻って検証

---

## 研究を止めない

- 2〜3日待機は禁止
- Gemini/Claude/Flowise無料枠待ちで停止しない
- データ待ちでも実装・Synthetic・公開情報確認を並行
- 1件でもズレを見つけたら即修正候補へ
- 課金が本当に避けられない時だけ事前相談

---

## 主がやること

**今はなし。**

主は方向・優先順位・重大承認に集中。
コード収集、大量転記、大量スクショ、routine整理はNo.3側。

---

## 重要な保護状態

- DEV2000 C: 新lineage救済に使わない
- ECON_HOLDOUT1000: SEALED
- same-lineage B/C rescue tuning: 禁止
- 現実のお金: 使わない
- 外部業者への連絡: しない
- Synthetic好成績: 現実で勝てる証拠ではない
- 追加課金: 主の明示OKなしではしない

詳細ルール: `AI_COUNCIL.md`
科学的Current State: `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json`
