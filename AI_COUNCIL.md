# Multiverse AI Council — iPhone-first setup

目的: ChatGPT系 / Claude系 / Gemini系の3体に、同じ研究案を独立監査させ、互いの反論も読ませ、最後にJudgeが論点を整理する。

## 使うもの

- Flowise Cloud: 会議の進行役。iPhoneのSafariから使う。ローカルPCやNode/Dockerは使わない。
- OpenRouter: 3社系モデルを1本のAPIキーでFlowiseへ接続する。

## 会議の基本構造

### Round 1 — 独立監査

3体は互いの回答を見ない。

- Auditor A: 統計・機械学習・検証設計
- Auditor B: 競輪構造・現実再現性
- Auditor C: 反証・リーク・過学習・シミュレータ偏り

共通命令:
- 褒めることを目的にしない。
- 現実の競輪と違う可能性を優先して探す。
- 「仮想世界で成功した = 現実で通用する」とは認めない。
- 不明な点は推測せず UNKNOWN とする。
- 重大度を P0 / P1 / P2 で分類する。

### Round 2 — 匿名クロスレビュー

3体へ、他2体の回答を AI-X / AI-Y と匿名化して渡す。

各AIは:
- 同意する点
- 間違っている点
- 自分の初回回答で修正すべき点
- まだ誰も気づいていない最大の欠陥

を返す。

### Round 3 — 敵対審査

各AIに1問だけ強制する。

「この研究/シミュレータが現実の競輪予測に移植できない最大の理由を1つ選び、それを反証するために必要な最小テストを示せ。」

### Round 4 — Judge

Judgeは多数決を禁止。
根拠の強さ、検証可能性、再現性だけで統合する。

出力:
1. 合意できたこと
2. 未解決の対立
3. P0 blocker
4. 今すぐ直すべきこと
5. 今は直さなくてよいこと
6. 現実データへ進んでよい条件
7. 最終 verdict: GO / REVISE / STOP

## Flowise側の実装方針

Agentflow V2を使う。

- Start
- Auditor A
- Auditor B
- Auditor C
- Cross Review A
- Cross Review B
- Cross Review C
- Adversarial Check A/B/C
- Judge
- End

最初はSupervisorに自由裁量を持たせすぎず、順序を固定する。
理由: 研究監査では「誰に何を聞いたか」が毎回同じ方が再現性が高い。

3体の独立性を守るため、Round 1では他AIの出力をstateへ保存しても各Auditorの入力には渡さない。
Round 2から匿名化して渡す。

## モデル選択

OpenRouterのその時点のモデル一覧から、原則:
- OpenAI系の強い推論モデル 1体
- Anthropic Claude系の強い推論モデル 1体
- Google Gemini系の強い推論モデル 1体

を選ぶ。

固定の古いモデル名を長期ルールにはしない。モデル更新時はCouncil versionを変えて記録する。
Judgeは3体のうち誰かと同じモデルでもよいが、可能なら別インスタンス/別promptにする。

## コスト暴走防止

- 1会議の最大往復回数を固定
- Agent loopを無制限にしない
- OpenRouter APIキーに利用上限を設定
- 最初は短いDigital Twin監査で動作確認

## 主の操作を最小化する

初回だけ:
1. Flowise Cloudへ登録
2. OpenRouterへ登録
3. OpenRouter APIキーを1個作る
4. FlowiseのCredentialへ貼る

以後はNo.3が用意する1つの監査文章をFlowiseへ貼って実行するだけを目標にする。

## 秘密情報

OpenRouter APIキーをChatGPT/GitHub/研究ファイルへ貼らない。
FlowiseのCredential欄だけへ保存する。
GitHubに残すのはモデル名・Council version・監査結果で、APIキーは残さない。

## 最初のCouncil対象

`v3/historical_all_market/governance/KEIRIN_DIGITAL_TWIN_MULTIWORLD_DESIGN_v1.md`

監査目的:
- 現在の仮想競輪が現実の何を再現できているか
- 何が作り物すぎるか
- 現実予測へ移るために最低限どこを実データで校正すべきか
- Simulatorが候補モデルに有利な世界を作っていないか

## 絶対ルール

AI Councilの合意も「真実」ではない。
Councilは設計レビュー装置。
最終的な現実適合性は、PRE-onlyの現実データで検証する。
