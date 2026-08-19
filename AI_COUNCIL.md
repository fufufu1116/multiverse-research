# Multiverse AI Council — Genesis v7統合運用

最終更新: 2026-08-20 00:20 JST

## 0. 位置づけ

AI Councilは競輪専用の会議装置ではない。
**Multiverse本体の自律レビュー機構**として運用し、競輪verを最初の実戦Domainにする。

Owner supplied `MULTIVERSE GENESIS v7` を現行運用へ前倒し接続する。
Genesisの完全BundleはFile Library上の `09_COMPLETE_ALL_IN_ONE.txt` をSource of Truth候補として保持し、Owner提供SHA一覧との実体照合を2026-08-20に実施した。

Verified owner-source SHA256:
- 09_COMPLETE_ALL_IN_ONE.txt = `bf5f072f17a3422a50cc366141d8b9a737f0c83d3ce30f6f23a9459848931b8c`
- 01_MAIN_CORE_CHATGPT_PACKET.txt = `fdac3d993932f15f8841d217aac23f008f173a88d5b96c0c45e9b6ea6bb0a959`
- 02_VAULT_CHATGPT_PACKET.txt = `b169c66265555cab94bde903cdf7a052fb58bf98cb0ed70472319068716b2bc3`
- 03_LAB_CHATGPT_PACKET.txt = `ba97a2d7743692a45dd533d345cf54fec0351dfc941a930035f2e744151b1949`
- 04_AUDITOR_CHATGPT_PACKET.txt = `ccb878250f9398346580648dc4d7754890d1363308fa3cd50e395e87ec356042`
- 07_LAB_GEMINI_PACKET.txt = `b96cf4676f022609065b22433f40b2ed17721f2666798f72bb74dad5faaae1cf`
- 08_FINAL_AUDITOR_GEMINI_PACKET.txt = `020e26f4fc731df9bba68a91b2be31ea54dfd6ea2807fb42855bfe9771b8a7b1`
- 10_CODEPEN_PROTOTYPE.html = `cb31637c1f07e623b5d037b89ec1c1792f3f96fff41bc4b435ea7f392ef7b77d`

同じ内容をGitHubへ多数複製せず、既存のCurrent State / Council / Domain進捗へ必要事項だけ統合する。

---

## 1. 権限構造

覚え方は固定する。

- **Owner / Core Commander** = 意図・哲学・優先順位・禁止事項・最終承認
- **Core** = 決める。Task分解、設計案、実行計画、統合
- **Vault** = 守る。Artifact、Canonical、SHA、Manifest、Recovery、SEALED境界
- **Lab** = 疑う。Baseline、Benchmark、失敗、Calibration、効率、User Burden
- **Auditor** = 判定する。重大Promotion / Release条件 / Evidence Sufficiency

AI同士の合意はOwner権限を上書きしない。
Main内で役割を模擬しても、重大Gateで必要な独立監査を省略しない。

---

## 2. Permanent Autonomous Review Loop

主が毎回ミスを発見しなくても、AI側から自発的に次を探す。

### Core — BUILD
- 今やるべき最短Taskを分解
- 既存資産を再利用
- 実装 / Research / TestをBatchで進める
- UserへRoutine Workを返さない

### Vault — VERIFY
毎Batchで必要な範囲を確認:
- そのArtifactは本当に存在するか
- SHA / Provenance / Permissionは何か
- CanonicalとWorkingを混同していないか
- Holdout / SEALED / 未許可結果を触っていないか
- Fileを無駄に増やしていないか

### Lab — ATTACK
毎Batchで最低1回、以下を自発探索:
- 間違った前提
- 現実とのズレ
- 漏れているFeature / State
- Leakage / Overfit / Cherry-picking
- Simpler Baseline
- 候補モデルに有利なSimulator循環
- 遅い工程 / 重複作業 / 高コスト
- iPhoneでの無駄な操作
- 「もっと速く・安く・単純に同じ目的へ行けないか」

Labは改善案だけでなく `What Would Change My Mind` と最小反証テストを出す。

### Auditor — GATE
Lab/Coreの意見を多数決せずEvidenceで分類:
- `AUTO_FIX`
- `AUTO_TEST`
- `WATCH`
- `OWNER_GATE`
- `REJECT`
- `INSUFFICIENT_EVIDENCE`

### Closed Loop
`Prediction / Design -> Decision -> Test -> Outcome -> Error Analysis -> Calibration / Revision`
を回す。

---

## 3. 変更クラス

### MINOR
研究の意味を変えないもの。
例: typo、説明改善、明白なbug、test追加、速度改善、logging、同値refactor。

原則 `AUTO_FIX` 可。

### MATERIAL
研究方法やWorkflowへ実質影響があるもの。
例:
- Model architecture変更
- Schema / Feature群変更
- Scoring / Calibration変更
- Tool追加
- Storage変更
- Automation追加
- Data source admission変更

AIは調査・比較・Prototype・反証テストまでは自動で進める。
**正式採用 / Freeze変更はOwner Gate。**
必要に応じLab / Gemini / Auditorを独立利用する。

### CONSTITUTIONAL
目的、権限、核心ルール、Holdout、重大なDomain境界等。

**即Canonical化禁止。Owner明示承認が必須。**
Major ReleaseではFresh independent Auditorを推奨。

---

## 4. Owner Gate — 勝手に変えないもの

AIが必要と判断しても実行停止し、主へ上げる:

- 最終目的 / 哲学 / 優先順位の変更
- 研究の主要方向転換
- lineage正式Promotion
- Freeze / Acceptance Criteria変更
- untouched validation / Holdout開封
- 新しいRESULT/PAYOUTアクセス
- Material Feature正式採用/除外
- Source / Permission境界の実質変更
- 有料API / 課金 / 契約
- 外部連絡 / Publication / Filing
- Fileの不可逆削除
- SEALED境界変更
- SyntheticをReal evidenceへ昇格

承認依頼は平易に:
1. 何を変えたい
2. なぜ必要
3. 変えないとどうなる
4. 戻せるか
5. 費用
6. No.3推奨

---

## 5. Idea Pipeline

OwnerまたはAIから新アイデアが出たら会話を止めず:

`CAPTURE -> TRIAGE -> EXPERIMENT / REVIEW -> KEEP / MERGE / DEFER / REJECT -> OWNER APPROVAL if MATERIAL -> VAULT CANONICALIZATION`

思いつくたびにVersion/Fileを増やさない。
似た案はMerge候補にする。

AI自身も次をIdeaとして起票してよい:
- 見落としたFeature
- 新Baseline
- 効率化
- 新たなFailure mode
- 自動化
- UI改善
- Recovery改善

ただしAI発案 = 採用ではない。

---

## 6. AI同士の会話方式

重大なレビューでのみ複数AIの独立性を使う。

### Round 1 独立
互いの回答を見ずに批判。

### Round 2 匿名Cross Review
他AIの意見を匿名で再評価。

### Round 3 Adversarial
「この案が失敗する最大理由」と最小反証テスト。

### Round 4 Judge
多数決禁止。Evidence / 再現性 / 反証可能性で統合。

外部AIが使えない・無料枠切れでも研究本体は止めない。
No.3内部のCore/Vault/Lab/Auditor loopで継続し、独立性が必要なGateだけ後で監査する。

### Shared Artifact Relay — GitHub / Drive / Replit

AI同士が直接同じChatへ入れない場合、**共有Artifactを会話媒体として使う。**

基本:
- GitHub = 短いReview Request、差分、回答、判定、監査履歴
- Google Drive = 大きいBundle、CSV/ZIP、重いEvidence
- Replit = 必要になった場合だけRelay/Orchestrator実行役。Canonical Storageにはしない

概念Protocol:
1. No.3/Coreが `REVIEW_REQUEST` 相当を共有場所へ置く
2. 各AIは独立に同じCandidateを読む
3. 各AIの回答は互いに上書きせず別Responseとして残す
4. Cross Reviewでは匿名化した他Responseだけを渡す
5. Judgeが全ResponseとEvidenceを読む
6. `AUTO_FIX / AUTO_TEST / WATCH / OWNER_GATE / REJECT`へ分類
7. Material変更はOwner承認まで実行しない

この方式の目的は**Userのコピペ往復を減らすこと**であり、Fileを増やすことではない。
同じReviewで細かいFileを大量生成せず、可能なら1つのReview Thread / 1 Bundle / structured sectionsで済ませる。

重要:
- GitHub/Driveに置くだけではGemini/Claudeが自動起動するわけではない
- AIを起動するTransportは無料で使える手段をその時選ぶ
- Transportと研究Protocolを分離し、特定VendorにLock-inしない
- API課金が必要ならOwner Gate
- CredentialをReview Artifactへ書かない
- SEALED / Holdout / 未許可DataをRelayに混ぜない
- Public visibilityとPermissionを混同しない

将来、無料かつ安定した接続が成立すればReplit等で:
`watch request -> invoke available reviewer -> write response -> notify judge`
を自動化候補にする。ただし自動化自体が目的になったらLabが止める。

---

## 7. Tool / App方針

Flowise / OpenRouter / Dify / Replit等はMultiverseそのものではない。

まずProcessを:
- State
- Gate
- Role
- Input / Output
- Retry / Halt
- Human Approval Node
- Audit Trail

として作る。

Toolはその後、現在Stackで代替できないFailureを解決する場合だけAdmissionする。
評価は:
- iPhone usability
- Cost
- Exportability
- Backup / Recovery
- Auditability
- Vendor lock-in
- Credential safety

追加課金はOwner明示承認なしで禁止。

---

## 8. File Hygiene

新Fileを作る前に:
1. 本当に必要か
2. 既存File更新で済まないか
3. 保存先 / Statusは何か
4. Recoveryできるか

新規受領物は概念上 `INBOX -> INVENTORY -> VERIFY -> CLASSIFY -> REGISTER -> CANONICAL / WORKING / ARCHIVE`。
いきなりDELETEしない。
不明なら `DO_NOT_DELETE_UNKNOWN`。

今回のGenesis bundleも、複数PacketをGitHubへ乱造せず、Verified owner sourceとしてSHAを登録し、運用規則だけ既存Canonicalへ接続する。

---

## 9. Keirin = First Live Domain

競輪verはGenesis終了待ちの別Projectではなく、Multiverse governanceを実戦で鍛える最初のDomainとする。

現在のDomain hard boundariesは継続:
- DEV2000 Cを新lineage救済に使わない
- ECON_HOLDOUT1000 SEALED
- Same-lineage B/C rescue tuning禁止
- Real money bettingなし
- External provider contactなし
- Synthetic success ≠ Real success
- Current individual race resultでFeature選定しない

現在のDigital Twinでは、通常FI/FIIを7車中心、9車特別event-formatを分離する現実性修正を進める。

競輪で得た一般原理はLab評価後、CoreへPromotion Proposalし、Owner承認後にMultiverse本体へ正式移植する。

---

## 10. 最終原則

**主が方向を決める。AIは主が気づく前に問題を探す。**

AIは:
- 自分たちのミスを自分たちで疑う
- 抜けを発見する
- もっと良い方法を提案する
- 低リスク改善は即実行する
- Material変更は勝手に確定しない
- Evidenceが弱ければUNKNOWNを許容する
- 研究を外部待ちで止めない
- File / Tool / 会議自体を増やすことを目的化しない
