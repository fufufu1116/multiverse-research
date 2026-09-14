# Automation Affiliate Content Cluster v1 — narrowed after competitive falsification

Status: RESEARCH_ONLY / INTERNAL / NOT PUBLISHED / NO AFFILIATE LINKS / NO APPLICATION / NO REVENUE / RUNTIME OFF
Checked: 2026-09-14

## Decision
The previous concept `generic Make vs n8n comparison + simple usage calculator` is **not whitespace**.

Fresh current SERP/competitor evidence shows:
- multiple 2026 Japanese comparison articles already explain credits vs executions;
- AutomationLabGuide already operates a Make-vs-n8n pricing calculator with runs/month, Make operations/run, scheduled trigger checks, n8n executions/run and affiliate monetization;
- AI Cost Kit already models tasks/credits/executions together with AI/API calls, retries, hosting, monitoring and support labor.

Therefore the surviving first-party wedge must not be “we also have a calculator.”

Narrowed working wedge:

`OFFICIAL-SOURCE CONDITION ENGINE -> WORKLOAD-SHAPE COST MODEL -> PLAN/MIGRATION STATE -> MATERIAL CHANGE DIFF -> DECISION BOUNDARY`

Owner-facing shorthand: **自動化コスト診断 + 変更監視**.

## Why this can still be different
The defensible layer is not arithmetic. It is maintaining decision validity when vendor billing rules, plan generations, migration states, AI packaging, billing cadence or eligibility conditions change.

A useful page should answer:
1. What is the user's actual workload shape?
2. Which billing unit applies to each part of that workload?
3. Which plan generation / billing cadence / currency / region / AI-credit model applies now?
4. Which facts are confirmed, conflicting, not found, or require vendor confirmation?
5. Has a material vendor change invalidated the previous decision?

This is the reusable asset already supported by the existing materiality-diff and plan-generation work.

## Fresh competitive evidence
### AutomationLabGuide
Observed current page: `Make vs n8n Pricing Calculator: Credits vs Executions`.
It already includes:
- business-process runs/month;
- Make standard operations/run;
- Make scheduled trigger checks/month;
- n8n executions/business-process run;
- simple/15-minute-polling/complex presets;
- Make affiliate link;
- official-source checked date;
- warnings for AI, retries, sub-workflows and special modules.

Conclusion: scheduled polling and basic workload normalization are **already covered by a live competitor**.

### AI Cost Kit
Observed current comparison/cost pages already normalize:
- platform subscriptions;
- AI/API calls;
- retries;
- hosting;
- monitoring;
- support labor;
- cost per completed business run.

Conclusion: adding an “AI cost” input or a generic retry buffer alone is **not enough differentiation**.

## Surviving differentiation requirements
A future public candidate must contain at least one hard-to-copy managed-data layer, not merely more form fields.

Required layers:

### A. Official fact provenance
Every material fact carries:
- official source URL;
- checked date;
- source context;
- normalized value/unit;
- billing basis;
- currency/tax basis;
- effective date if known.

### B. Plan-generation / migration state
Separate field:
`PLAN_GENERATION_OR_MIGRATION_STATE`

Do not infer a user's payable plan from a generic public pricing page when workspace/account generation can differ.

### C. Evidence state
Allowed material states:
- `CONFIRMED`
- `CONFLICTING`
- `NOT_FOUND`
- `REQUIRES_VENDOR_CONFIRMATION`

Do not silently resolve contradictions to make a cleaner recommendation.

### D. Materiality diff
Changes classified at least as:
- PRICE
- BILLING_BASIS
- MINIMUM_SEATS_OR_BUCKET
- BILLABLE_ACTOR
- CURRENCY_OR_TAX
- ELIGIBILITY_OR_REGION
- FEATURE_INCLUDED_OR_REMOVED
- AI_PACKAGING_OR_CREDIT_MODEL
- PLAN_GENERATION_OR_MIGRATION
- DEPRECATION_OR_EFFECTIVE_DATE
- TERM_COMMITMENT_RENEWAL_REFUND

Migration drift or evidence degradation forces human review.

### E. Decision boundary
Output is not “Tool X wins.”
Output should be conditional, for example:
- `CURRENT_DECISION_STILL_SUPPORTED`
- `DECISION_CHANGED_BY_USAGE_SHAPE`
- `DECISION_INVALIDATED_BY_PLAN_DRIFT`
- `REQUIRES_VENDOR_CONFIRMATION`
- `INSUFFICIENT_EVIDENCE`

## Workload-shape schema v1
The next calculator/checker prototype should accept or derive:
- completed business runs/month;
- ordinary Make chargeable module actions/run;
- bundles/items processed per run where iteration multiplies actions;
- branch/path firing rates where material;
- polling/scheduled checks/month where applicable;
- retry/redelivery assumption;
- Make dynamic-AI/advanced-credit flag;
- n8n workflow executions/run;
- n8n AI-credit/external-model flag;
- self-host candidate yes/no;
- monthly vs annual billing;
- currency + tax treatment;
- checked date;
- plan-generation/migration state.

The current deterministic `automation_cost_normalizer_v1.py` intentionally models only the subset that can be stated safely and leaves unresolved AI/API/self-host/currency/tax conditions explicit.

## Monetization fit after lawful audience validation
Current official program surfaces remain attractive but are **not proof of audience or conversion**:

### Make
- official affiliate surface: 35% commission for 12 months;
- current detailed Help: payout eligibility requires at least USD100 commission and at least 3 unique paying referred users;
- Wise payout;
- commission from subscription payments, not extra credits/operations.

Important integrity note: the current Make marketing FAQ also contains a contradictory 24-month sentence in a partner-comparison answer while the main page and detailed Help state 12 months. Preserve this as an evidence conflict; do not quietly present 24 months as current payable entitlement.

### n8n
- official affiliate surface: 30% commission on n8n Cloud referrals for 12 months;
- application/approval required.

Editorial rule:
Affiliate rate never changes the factual recommendation. The page must remain useful if all affiliate links are removed.

## First future external-test cluster — prepared, not authorized
### Page 1 — `Make vs n8n 実コスト診断`
Primary job:
“自分のワークフロー形状で、どの課金単位がどれだけ発生し、何がまだ不明か知りたい。”

Differentiators required before publication:
- explicit workload-shape model;
- checked official-source snapshot;
- dynamic-AI unknown preservation;
- plan/cadence/currency conditions;
- decision boundary rather than generic winner;
- future change-diff hook.

### Page 2 — `Make credits 発生源チェック`
Not a generic plan table.
Focus on which scenario properties multiply or invalidate a naive credit estimate and which parts require current vendor confirmation.

### Page 3 — `n8n Cloud execution + AI credit 境界`
Separate workflow execution allowance from AI-credit allowance and external AI/API spend. Do not call self-hosting “free” without infra/admin boundary.

### Page 4 — `ClickUp AI料金世代チェッカー`
Keep as adjacent proof that plan-generation drift is a real, reusable problem beyond Make/n8n.

## Future advance criteria
Do not increase solo-media reconnaissance above 80/100 merely for more internal code/content.

Advance only after a lawful, separately authorized external test produces material evidence such as:
- qualified visits from exact problem/decision intent;
- meaningful calculator/checker start and completion;
- users encountering a condition/conflict that a generic comparison page would miss;
- repeat/return usage after a material vendor change;
- qualitative evidence that checked-date/change-diff/plan-state is valued, not just the arithmetic.

Commercial advancement additionally requires #430 READY + separate Owner revenue gate + actual program approval where applicable.

## Kill / downrank criteria
Downrank this wedge if future evidence shows any of the following:
- users only want a simple static price table/basic calculator already provided by incumbents;
- official-source condition maintenance costs exceed plausible traffic/affiliate value;
- vendor changes cannot be detected/normalized reliably enough to keep pages trustworthy;
- most decision value collapses to generic AI answers with no managed-data advantage;
- external search/interaction evidence remains negligible after a valid distribution test.

## Current verdict
`GENERIC_COMPARISON=COMMODITIZED`
`SIMPLE_PRICING_CALCULATOR=COMPETED`
`FULL_AI_COST_CALCULATOR=ALSO_COMPETED`
`CONDITION_AWARE_OFFICIAL_DIFF=SURVIVING_RESEARCH_WEDGE`
`SOLO_MEDIA_READINESS=80_HOLD_FOR_REAL_WORLD_EVIDENCE`
`SEARCH_VOLUME=NOT_MEASURED`
`NO_PUBLICATION`
`NO_AFFILIATE_APPLICATION`
`NO_AFFILIATE_LINKS`
`NO_REVENUE`
`NO_NEW_SPEND`
`RUNTIME: OFF`

## Evidence references checked for this narrowing
Official:
- https://www.make.com/en/affiliate
- https://help.make.com/affiliate-program
- https://n8n.io/affiliates/

Competitive falsification:
- https://automationlabguide.com/guides/make-vs-n8n-pricing
- https://aicostkit.com/zapier-vs-make-vs-n8n-ai-workflow-cost/

These competitor pages are used to falsify whitespace, not as authority for vendor billing rules.
