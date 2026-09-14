# ClickUp search-intent proxy v0 — no volume claim

Status: RESEARCH_ONLY / QUALITATIVE ONLY / NOT PUBLISHED / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Use zero/low-cost autocomplete + current SERP structure to decide how the ClickUp plan-generation checker should be framed if a later external test is authorized. This is **not** search-volume measurement and does not add demand points to the 80/100 solo-media readiness cap.

## Google-autocomplete proxy
Seed expansion in Japan/Japanese for:
- `ClickUp AI 料金`
- `ClickUp Brain 料金`
- `ClickUp プラン 変更`
- `ClickUp Everything AI 料金`

Repeated ClickUp-specific suggestions included:
- `clickup 料金`
- `clickup費用`
- `clickup 値段`
- `clickup 価格`
- `clickup 有料`
- `clickup 課金`
- `clickup プラン`
- `clickup 無料 制限`
- `clickup unlimited vs business`
- `clickup ai`
- `clickup ai model`

Interpretation:
- broad pricing/plan intent is visibly present in autocomplete;
- the exact internal phrase `plan generation` is not how Japanese users naturally express the problem;
- exact AI-price seeds are noisy and frequently collapse back to broad ClickUp pricing queries.

Therefore do not title a future test around internal terminology like `料金世代`. Use the user's visible symptom first, e.g.:

`ClickUpのAI料金が違う？あなたのWorkspaceが旧/新どちらの料金体系か判定`

Then explain `料金世代` inside the result, not as the acquisition keyword.

## Current SERP observations
Current search surfaces prominently expose:
- official ClickUp Brain pricing with public Brain AI `$9/user/month` and Everything AI `$28/user/month`;
- official ClickUp Help `New plans and pricing options`, stating some Workspaces see new AI-included plans;
- official general pricing and upgrade help;
- Japanese third-party pricing pages that repeat classic/public plan and AI-add-on prices.

One current Japanese third-party result dated 2026-04 presents Brain AI `$9/user/month` and Everything AI `$28/user/month` as add-ons, while current ClickUp Help now simultaneously documents limited rollout of a different AI-included plan generation. This is exactly the type of freshness/migration-state gap the checker is designed to handle.

Sources checked:
- https://clickup.com/brain/pricing
- https://help.clickup.com/hc/en-us/articles/42972527662359-New-plans-and-pricing-options
- https://help.clickup.com/hc/en-us/articles/6303244318999-Pricing-per-user-role-and-plan
- https://help.clickup.com/hc/en-us/articles/6303314345623-Upgrade-your-plan
- https://help.clickup.com/hc/en-us/articles/10129535087383-Intro-to-pricing
- https://clickup.com/pricing
- https://clickup.dxable.com/faq/
- https://saasmap.jp/tools/clickup

## Acquisition implication
Future external falsification should not rely on ranking for an obscure diagnostic phrase. It should meet broader intent:

Primary acquisition framing:
`ClickUp 料金 / ClickUp AI 料金 / ClickUp 費用`

Differentiating first-screen question:
`公式の$9/$28と、あなたのWorkspaceに出ている料金が違いませんか？`

Tool promise:
`公開価格をそのまま当てはめず、今見えているPlans/Billing画面から旧/新の料金体系を判定。断定できない場合は次に確認する場所を返します。`

## Falsification implication
Because the exact niche phrase is not a strong autocomplete signal, the future test must measure whether broad pricing-intent users actually start the checker. The preregistered `START_RATE >=15%` strengthening threshold is therefore meaningful and should not be relaxed after seeing results.

If broad-pricing visitors ignore the checker despite qualified exposure, the differentiated wedge is weak even if generic ClickUp pricing demand exists.

## Limits
- autocomplete presence != monthly volume;
- SERP existence != traffic opportunity;
- third-party stale-looking content != proven user pain;
- no keyword-volume/CPC/difficulty numbers were available from the current quota state;
- no publication/search indexing has occurred.

`BROAD_PRICING_INTENT_PROXY=PRESENT`
`EXACT_PLAN_GENERATION_QUERY=NOT_ESTABLISHED`
`SEO_FRAME=SYMPTOM_FIRST_NOT_INTERNAL_TERM`
`SEARCH_VOLUME=UNMEASURED`
`REAL_WORLD_DEMAND=UNPROVEN`
`NO_PUBLICATION`
`RUNTIME=OFF`
