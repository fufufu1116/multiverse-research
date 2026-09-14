# Automation Cost Lab v0 — internal research artifact

Status: RESEARCH_ONLY / NOT PUBLISHED / NO AFFILIATE LINKS / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Test whether an Owner-operated SaaS comparison asset can create value by normalizing billing units, plan state, and change dates instead of publishing generic recommendation lists.

## First wedge
`MAKE_VS_N8N_COST_NORMALIZER`

Why this wedge:
- Make and n8n charge on materially different usage units.
- Make's current billing unit is credits; most non-AI modules use 1 credit per action, while some AI/advanced functions can consume variable credits.
- n8n Cloud pricing is based on workflow executions regardless of workflow step count.
- Japanese search results currently include fresh pages but also stale/incorrect plan facts, especially around Make's old `operations` terminology/prices.
- Both vendors have affiliate programs, but monetization registration remains outside this artifact and blocked by #430.

## Official facts frozen for synthetic calculator

### Make
Official pricing page checked 2026-09-14:
- Free: up to 1,000 credits/month.
- Core: current retrieved pricing view shows $12/month at 10,000 credits/month.
- Pro: $21/month at 10,000 credits/month.
- Teams: $38/month at 10,000 credits/month.
- Billing page exposes monthly/annual cadence controls; exact decision output must preserve cadence.
- Most ordinary module actions: 1 action ~= 1 credit.
- Some AI / advanced features have dynamic credit use; do not treat all AI actions as 1 credit.
Official sources:
- https://www.make.com/en/pricing
- https://help.make.com/credits

Affiliate facts checked 2026-09-14:
- 35% commission on referred paid subscriptions for 12 months.
- Payout requires >= $100 commission AND >= 3 unique paying referred users for each payout request.
- Payouts use Wise.
- Registration/action is NOT authorized here.
Official sources:
- https://www.make.com/en/affiliate
- https://help.make.com/affiliate-program

### n8n Cloud
Official pricing page checked 2026-09-14:
- Pricing is based on monthly workflow executions regardless of workflow complexity.
- Starter: EUR 20/month billed annually; 2.5K executions; unlimited steps.
- Pro: EUR 50/month billed annually; 10K executions; unlimited steps.
- Community Edition exists as a separate self-hosted option; do not compare Cloud sticker price to self-hosted as if operating cost were zero.
Official source:
- https://n8n.io/pricing/

Affiliate facts checked 2026-09-14:
- 30% commission on n8n Cloud referrals for 12 months.
- Application/approval required.
- PayPal payout, monthly, minimum balance EUR 100.
- Paid advertising using affiliate links is prohibited.
Official source:
- https://n8n.io/affiliates/

## Deterministic non-AI calculator model
Inputs:
- `runs_per_month`
- `chargeable_steps_per_run`
- `billing_cadence`
- `needs_self_hosting`
- `contains_dynamic_ai_credit_features`

Derived values:
- `make_estimated_credits = runs_per_month * chargeable_steps_per_run` only when dynamic-AI flag is false and all steps follow the ordinary 1-credit assumption.
- `n8n_estimated_executions = runs_per_month` regardless of step count for ordinary full workflow executions.

Fail-closed rules:
- If Make dynamic-AI flag is true -> numeric Make estimate becomes `REQUIRES_USAGE_MODEL`, not a false precise total.
- If self-hosting is required -> n8n Community/Business hosting cost must be separately modeled; Cloud price alone is not decision-safe.
- Currency is never silently converted without a checked FX timestamp.
- Monthly vs annual cadence is never merged into one price.

## Synthetic examples
### Case A — 1,000 runs/month, 4 ordinary steps/run
- Make estimate: 4,000 credits/month. Fits inside 10K-credit Core capacity; exact payable price still depends on cadence/current checkout conditions.
- n8n estimate: 1,000 executions/month. Fits inside Starter 2.5K execution capacity.
- Decision: both fit base capacity; sticker-price comparison alone is insufficient because currencies/cadence/features differ.

### Case B — 2,000 runs/month, 6 ordinary steps/run
- Make estimate: 12,000 credits/month. Exceeds 10K base bucket, so current 10K Core headline is not enough.
- n8n estimate: 2,000 executions/month. Fits inside Starter 2.5K execution capacity.
- Decision: step-count billing materially changes the result; this is exactly the kind of normalization a generic monthly-price table misses.

### Case C — 1,000 runs/month, 4 steps/run with Make dynamic AI feature
- Make: `REQUIRES_USAGE_MODEL`; do not claim 4,000 total credits because AI token/feature use can add dynamic credit consumption.
- n8n: workflow execution count remains 1,000 for plan-capacity purposes, but third-party model/API costs and n8n AI-assistant credits must be modeled separately and must not be conflated.

## First 3 internal page specs
1. `Make料金・クレジット計算` — user enters runs and chargeable steps; calculator shows capacity bucket + assumptions + checked date.
2. `Make vs n8n 同一ワークフロー料金比較` — normalize credits vs executions; no winner unless user inputs workflow shape.
3. `ClickUp AI料金・旧/新プラン判定` — use plan-generation/migration-state schema already proven in #404; designed as a separate plan-drift page, not mixed into automation execution math.

## Promotion / kill criteria for this media wedge
Advance only if a future lawful zero-cost external test shows at least one of:
- repeated search/visit behavior around exact cost-condition queries;
- users interact with calculator/decision-normalization rather than generic feature list;
- affiliate-eligible vendors remain available with economics sufficient to justify maintenance;
- update/change events create reusable traffic/content rather than one-off article churn.

Kill/down-rank if:
- value collapses to generic AI-generated comparison content;
- vendor official pages answer the decision cleanly enough that normalization adds little;
- search acquisition is dominated by incumbents without a credible long-tail/calculator entry point;
- affiliate programs close/reject the channel broadly or economics are too small relative to maintenance;
- #430 or other legal/tax constraints prevent lawful monetization when the research phase ends.

No registration, affiliate application, public site deployment, monetized publication, payment collection, inventory purchase, ads, or spend performed by this artifact.
