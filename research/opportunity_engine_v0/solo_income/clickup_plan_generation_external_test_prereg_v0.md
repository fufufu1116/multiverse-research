# ClickUp plan-generation checker — external falsification prereg v0

Status: INTERNAL / RESEARCH_ONLY / NOT PUBLISHED / NO MONETIZATION / RUNTIME OFF
Prepared: 2026-09-14

## Purpose
Pre-register the smallest future zero-spend market test that can falsify or strengthen the `CLICKUP_PLAN_GENERATION_CHECKER` wedge without turning a public pricing page into a business launch or assuming affiliate demand.

This document grants no publication authority. Any external publication/distribution must still satisfy current Control / lane gate requirements. #430 remains RESEARCH_ONLY for revenue-producing activity.

## Frozen problem hypothesis
A meaningful subset of ClickUp users cannot safely infer their payable AI/upgrade economics from public pricing pages alone because ClickUp is simultaneously operating more than one plan-generation surface:

1. public Brain AI / Everything AI pricing exists;
2. ClickUp Help says a limited rollout of newer AI-included plans is in progress;
3. existing paid Workspaces are not automatically migrated;
4. only upgrade options change for affected existing Workspaces;
5. all Free Forever Workspaces, Workspaces created after launch, and a small subset of paid Workspaces are offered the new plans.

Therefore the decision job is not merely `what is ClickUp's public price?` but `which pricing generation does my exact Workspace currently expose, and what evidence is still missing before I act?`.

## Current official-source evidence frozen for this prereg
Checked 2026-09-14:

- ClickUp Help — New plans and pricing options:
  - limited rollout;
  - current plan and price stay the same;
  - no automatic migration;
  - new plans include AI rather than separate AI add-ons;
  - eligibility includes new Workspaces, all Free Forever Workspaces, and a small number of paid Workspaces.
  - https://help.clickup.com/hc/en-us/articles/42972527662359-New-plans-and-pricing-options
- ClickUp Brain pricing:
  - public Brain AI $9/user/month and Everything AI $28/user/month context.
  - https://clickup.com/brain/pricing
- ClickUp pricing / AI add-on help:
  - public AI surfaces and Workspace-level add-on mechanics remain relevant to classic-generation users.
  - https://clickup.com/pricing
  - https://help.clickup.com/hc/en-us/articles/6303101719831-Purchase-or-cancel-ClickUp-add-ons
  - https://help.clickup.com/hc/en-us/articles/20686299081879-ClickUp-Brain-AI-feature-availability-and-limits

## Qualitative pain evidence — supportive, not prevalence proof
Current community examples show users asking about:
- a newly offered Business plan with AI bundled versus older Business / Business Plus choices;
- whether AI must be purchased for every Workspace member;
- why advertised public AI prices differ from prices shown inside a Workspace;
- whether Everything AI promotional pricing will persist and who must be licensed.

These examples support a confusion/decision-risk hypothesis but do NOT establish search volume, market size, conversion, willingness-to-pay or representativeness.

## Frozen test asset
Internal candidate:
`research/opportunity_engine_v0/solo_income/clickup_plan_generation_checker_v1.html`

The checker must remain deterministic and must not ask for ClickUp credentials, Workspace IDs, email, name, payment data, screenshots, billing documents or other PII in the first external falsification.

## Test proposition
Primary proposition:
`公開価格ではなく、あなたのWorkspaceに今見えている料金世代を判定する`

Secondary promise:
`断定できない時は、何を追加確認すべきかを返す`

Do not promise:
- the lowest possible price;
- vendor negotiation outcomes;
- billing correctness;
- refund eligibility;
- tax/FX-inclusive invoice totals;
- guaranteed savings.

## Frozen test design
When separately authorized for external zero-spend testing:

### Page
One page only. No generic ClickUp review article is required for the first test.

### Required inputs
- Workspace state: Free Forever / existing paid / recently created / unknown;
- visible Plans/Billing/Upgrade surface: classic AI add-on / new AI-included plans / both / unknown;
- whether Workspace-specific price is actually visible;
- optional billing cadence;
- optional billable member count and exact visible per-member AI add-on price, used only for classic-generation simple exposure arithmetic.

### Outputs
Exactly one state:
- `NEW_INCLUDED_AI_PLAN_PRICE_OBSERVED`
- `NEW_INCLUDED_AI_PLAN_CONFIRMED_PRICE_UNKNOWN`
- `CLASSIC_ADDON_MODEL_PRICE_OBSERVED`
- `CLASSIC_ADDON_MODEL_CONFIRMED_PRICE_UNKNOWN`
- `CONFLICTING_SURFACES_HUMAN_REVIEW`
- `NEW_PLAN_SET_EXPECTED_SURFACE_NOT_CONFIRMED`
- `UPGRADE_SURFACE_UNKNOWN`
- `INSUFFICIENT_EVIDENCE`

Every output must include:
- what is safe to conclude;
- what evidence is still missing;
- checked date;
- official source links;
- explicit statement that public pricing does not prove a specific Workspace invoice.

## Frozen falsification thresholds
Do NOT score raw impressions as product proof.

After at least **100 qualified unique exposures** to users plausibly evaluating ClickUp pricing/AI/upgrade decisions:

### Strengthen
Require all of:
1. checker start rate >= 15%;
2. checker completion rate >= 60% of starts;
3. >= 5 distinct qualified confirmations that the multi-generation / Workspace-specific distinction resolved a real decision confusion;
4. at least 20% of completed sessions end in a state where generic public pricing alone was insufficient (`*_PRICE_UNKNOWN`, `CONFLICTING_*`, `UPGRADE_SURFACE_UNKNOWN`, or `INSUFFICIENT_EVIDENCE` with a clear next evidence step);
5. no material evidence that ClickUp's own current help/upgrade UX makes the checker redundant for most qualified users.

### Hold / inconclusive
- <100 qualified exposures;
- denominator cannot be verified;
- traffic is broad/non-ClickUp;
- analytics transport is missing;
- user intent cannot be separated from general curiosity.

### Downrank
After >=100 qualified exposures, any of:
- checker start < 5%;
- completion < 30% of starts;
- <3 distinct qualified confirmations of actual decision confusion;
- >90% of qualified users can resolve the issue directly from one obvious official surface with no generation ambiguity;
- users primarily want negotiation/refund/support escalation rather than plan-generation diagnosis.

### Kill this exact wedge
- ClickUp completes rollout and removes the material classic/new generation split;
- public and Workspace pricing become deterministically identical for the relevant decision path;
- ClickUp launches an official self-service generation/price diagnostic that fully covers the same job;
- maintaining correctness requires account credential access or billing-document collection that materially violates the low-friction/privacy advantage.

## Monetization separation
First external falsification must contain:
- no affiliate links;
- no ads;
- no paid upgrade CTA;
- no payment collection;
- no revenue account creation;
- no seller/service offer.

Only after independent usefulness / qualified-intent evidence exists, and only after #430 reaches the appropriate READY state plus any separate Owner revenue gate, may monetization be evaluated.

Potential later monetization architecture remains research-only:
`decision-safe checker -> owned updateable evidence asset -> affiliate where editorially appropriate -> ads only as secondary fill`.

## Integrity constraints
- Never rank a vendor higher because its affiliate payout is larger.
- Public $9/$28 figures are context, not a user's guaranteed payable price.
- User-entered price arithmetic must visibly exclude tax, FX, negotiated discounts, proration, empty-seat effects, contract terms and refunds unless each factor is separately evidenced.
- A conflicting Workspace screen forces human/vendor review; it must never be silently normalized to the public page.

## Current readiness conclusion
The ClickUp wedge is internally build-complete enough for a future external falsification candidate, but not externally validated.

`INTERNAL_TOOL=V1_BUILT`
`EXTERNAL_TEST=PREREGISTERED_NOT_AUTHORIZED_HERE`
`REAL_WORLD_DEMAND=UNPROVEN`
`WTP=UNPROVEN`
`AFFILIATE=NOT_APPLIED`
`MONETIZATION=OFF`
`#430=RESEARCH_ONLY`
`NO_NEW_SPEND`
`NO_RANK_PROMOTION`
`RUNTIME=OFF`
