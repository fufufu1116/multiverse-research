# Solo Media Content Test Pack v0 — internal only

Status: RESEARCH_ONLY / NOT PUBLISHED / NO MONETIZATION / RUNTIME OFF
Checked: 2026-09-14

## Goal
Prepare a small, non-generic first cluster that can later test three things at once when external testing is lawful and separately authorized:
1. exact decision/problem search intent;
2. calculator/checker interaction rather than passive generic reading;
3. whether affiliate-eligible commercial intent can coexist with decision-safe evidence.

Do not publish this pack under #430 RESEARCH_ONLY.

---

## Page 1 — Make料金・クレジット計算

### Search/job intent
User already uses or is evaluating Make and wants to know whether the advertised credit bucket will cover a concrete workflow.

### Working title
`Makeの料金・クレジット計算｜月間実行回数×ステップ数で目安を出す`

### Meta description draft
`Makeのcreditsを、月間ワークフロー実行回数と通常ステップ数から概算。AI機能など単純計算できない条件は「要追加確認」と分け、料金表だけでは分からない使用量を整理します。`

### Above-the-fold promise
`あなたのワークフローは月に何credits使う？`

### Primary tool
- runs/month
- ordinary chargeable steps/run
- dynamic AI yes/no
- output: estimated credits + capacity bucket + assumption state

### Mandatory integrity blocks
- checked date
- monthly vs yearly cadence warning
- dynamic AI credit warning
- official source links
- `estimate != invoice`

### FAQ candidates
- Makeの1 operationは今も1 creditですか？
- Router/filterはcreditを使いますか？
- AIを使うとcredit計算はどう変わりますか？
- 10,000 creditsで何回実行できますか？
- 月払いと年払いで何が変わりますか？

### Update triggers
- pricing bucket change
- `credit` definition change
- module billing exception change
- AI dynamic-credit rule change
- annual/monthly price change

---

## Page 2 — Make vs n8n 同一ワークフロー料金比較

### Search/job intent
User is not asking “which tool is best” in the abstract. They want to know how the same workflow shape maps to Make credits vs n8n executions.

### Working title
`Make vs n8n料金比較｜同じ自動化をcreditsとexecutionsで正規化`

### Meta description draft
`Makeはcredits、n8n Cloudはworkflow executions。単純な月額比較をせず、同じ実行回数・ステップ数を両方の課金単位へ変換して、どの料金枠に収まるかを比較します。`

### Above-the-fold promise
`月額ではなく「同じ仕事をさせた時」で比較する`

### Primary tool
Inputs:
- runs/month
- ordinary steps/run
- dynamic Make AI yes/no
- self-hosting candidate yes/no

Outputs:
- Make estimated credits / state
- n8n Cloud executions / state
- `BOTH_FIT | MAKE_BUCKET_EXCEEDED | N8N_BUCKET_EXCEEDED | REQUIRES_USAGE_MODEL | SELF_HOST_COST_NOT_MODELED`

### Mandatory non-comparison traps
- USD vs EUR not silently converted without FX timestamp
- annual vs monthly not merged
- n8n self-hosting not called “free” without infrastructure/admin cost
- external model/API cost not conflated with SaaS plan charge
- no generic winner badge

### FAQ candidates
- Makeとn8nはどちらが安い？
- n8nはステップが多いと料金が増えますか？
- Makeは1ステップごとにcreditを使いますか？
- n8n Community Editionは本当に無料ですか？
- AIワークフローの費用はどう比較しますか？

### Update triggers
- Make credit rules/prices
- n8n execution buckets/prices
- n8n self-host/community licensing changes
- affiliate program economics/eligibility changes

---

## Page 3 — ClickUp AI料金世代チェッカー

### Search/job intent
User sees $9/$28 public AI add-on pricing but may see different AI-included upgrade plans in their exact Workspace.

### Working title
`ClickUp AI料金が違う？旧プラン・新プランをWorkspace別に判定`

### Meta description draft
`ClickUpの公開AI価格$9/$28と、AI内包の新プラン表示が食い違う理由を整理。Workspaceの現在プランとUpgrade画面から、どの料金世代が適用されるかを判定します。`

### Above-the-fold promise
`「公開価格」と「あなたのWorkspaceの価格」が違う理由を判定`

### Primary checker states
- `NEW_INCLUDED_AI_PLAN_CONFIRMED`
- `CLASSIC_ADDON_MODEL_CONFIRMED`
- `NEW_PLAN_SET_EXPECTED_NOT_PRICE_CONFIRMED`
- `UPGRADE_SURFACE_UNKNOWN`
- `CONFLICTING_PUBLIC_VS_WORKSPACE`
- `INSUFFICIENT_EVIDENCE`

### Mandatory integrity blocks
- exact Workspace screen overrides generic assumption for the user's purchase decision
- existing paid customers are not automatically migrated according to current Help
- rollout is partial and pricing/packaging can change
- public Brain AI $9 and Everything AI $28 are public current context, not automatically the user's payable price
- checked date + source context

### FAQ candidates
- ClickUp Brain AIは$9ですか？
- Everything AIは$28ですか？
- Core / Business Plus / Maxとは何ですか？
- 既存のBusinessから自動で新プランに変わりますか？
- AI Super Creditsは何に使いますか？

### Update triggers
- rollout scope change
- old add-on model removal
- new plan prices or names
- AI credit allowance changes
- automatic migration policy changes

---

## Cluster-level internal QA
Before any future publication candidate is allowed to leave research-only status:
- every material number has an official URL + checked date;
- billing cadence/currency/unit visible near the number;
- uncertainty is shown, never hidden to improve conversion;
- page contains an interactive or deterministic decision aid, not just AI-generated prose;
- no affiliate link is added until #430 READY + separate Owner revenue gate + actual affiliate approval;
- affiliate disclosure is planned before any future commercial link appears;
- update triggers have an owner-free monitoring path, with human review for conflict/migration-state changes.

## Future external-test metrics, not yet authorized
If/when lawful and authorized:
- qualified organic visits by exact intent page;
- calculator/checker start rate;
- result completion rate;
- return visits after a material vendor change;
- outbound commercial-click rate only after lawful affiliate/monetization gate;
- revenue per qualified visit only after real monetization is allowed.

Pageviews alone do not prove product value. Affiliate click/revenue does not override decision-integrity requirements.
