# ClickUp Plan Generation Lab v0 — internal research artifact

Status: RESEARCH_ONLY / NOT PUBLISHED / NO AFFILIATE LINKS / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Prevent a public comparison page from falsely saying “ClickUp AI costs $9/$28” when the exact Workspace may instead be offered ClickUp's newer AI-included plan generation.

This is a same-vendor plan-generation / migration-state test case for the broader `AUTOMATION_COST_PLAN_DRIFT_MEDIA` route.

## Fresh official facts

### Current public add-on surface
ClickUp's public Brain pricing currently shows:
- Brain AI: $9 / user / month.
- Everything AI: $28 / user / month.
- AI Super Credits: $10 per 10,000 credits.
- Brain AI includes 1,500 AI Super Credits per user/month.
- Everything AI includes broader unlimited AI functionality and larger agent usage.

Official:
- https://clickup.com/brain/pricing
- https://clickup.com/pricing

### New plan-generation surface
ClickUp Help currently states:
- some Workspaces see a new set of plans with more ClickUp AI;
- new plans are currently available to a limited number of Workspaces, with broader rollout planned;
- an existing customer's current plan and price stay the same and the Workspace is not automatically moved;
- what changes is which plans are offered when upgrading;
- the new plan set includes AI rather than selling it only as separate add-ons;
- new-plan AI allowances are pooled per Workspace based on per-user allocation.

Current new-plan AI allowances in the official Help page:
- Core: trial + 1,000 credits/user/month pooled.
- Business: Brain + 1,500 credits/user/month pooled.
- Business Plus: 2,000 credits/user/month pooled plus specified unlimited features.
- Enterprise: 2,500 credits/user/month pooled plus specified unlimited features.
- Max: 5,000 Super Agent credits/user/month plus many unlimited AI features.

Which Workspaces see the new plans, per current Help:
- Workspaces created after launch;
- all Free Forever Workspaces;
- a small number of paid Workspaces.

Official:
- https://help.clickup.com/hc/en-us/articles/42972527662359-New-plans-and-pricing-options
- https://help.clickup.com/hc/en-us/articles/6303244318999-Pricing-per-user-role-and-plan
- https://help.clickup.com/hc/en-us/articles/10129535087383-Intro-to-pricing

### Existing add-on usage rules
ClickUp Help currently says, for the add-on model:
- all plans get trial access to select Brain AI features;
- paid plans can purchase AI add-ons after trial;
- paid plans with no AI add-on receive a one-time 1,000 AI Super Credits/user trial;
- Brain add-on: 1,500 Super Credits/user/month;
- Everything AI: 5,000 Super Credits/user/month.

Official:
- https://help.clickup.com/hc/en-us/articles/20686299081879-ClickUp-Brain-AI-feature-availability-and-limits
- https://help.clickup.com/hc/en-us/articles/40085008147863-Which-features-are-included-with-the-Brain-AI-add-ons

## Canonical state machine v0

### Inputs
- `workspace_age = NEW_AFTER_NEW_PLAN_LAUNCH | EXISTING | UNKNOWN`
- `current_plan = FREE_FOREVER | PAID_CLASSIC_NAME | NEW_PLAN_NAME | UNKNOWN`
- `observed_upgrade_plan_names = []`
- `observed_ai_addon_purchase_surface = YES | NO | UNKNOWN`
- `workspace_specific_price_observed = YES | NO`
- `public_pricing_checked_at`

### Output states
1. `NEW_INCLUDED_AI_PLAN_CONFIRMED`
   - exact Workspace upgrade/billing surface visibly offers new names such as Core / Business Plus / Max and AI-included allowances.
   - use the exact Workspace-specific displayed price/terms only; public generic price is supporting context.

2. `CLASSIC_ADDON_MODEL_CONFIRMED`
   - exact Workspace remains on classic/legacy paid-plan generation and the Workspace-specific billing/upgrade surface visibly offers Brain AI / Everything AI as add-ons.
   - public $9/$28 may be cited only if the Workspace-specific surface agrees at checked time.

3. `NEW_PLAN_SET_EXPECTED_NOT_PRICE_CONFIRMED`
   - Free Forever or a Workspace created after the new-plan launch, where official policy says new plans are offered, but the exact Workspace-specific upgrade price/surface has not been observed.
   - do not publish a definitive payable price.

4. `UPGRADE_SURFACE_UNKNOWN`
   - existing paid Workspace and no exact upgrade/billing surface observed.
   - public add-on pages and public new-plan Help conflict at the decision boundary; answer must be “check exact Workspace billing/upgrade screen”.

5. `CONFLICTING_PUBLIC_VS_WORKSPACE`
   - Workspace-specific evidence disagrees with current public pricing/help.
   - preserve both facts, timestamp both, and require vendor/support confirmation before a purchase recommendation.

6. `INSUFFICIENT_EVIDENCE`
   - key inputs missing or ambiguous.
   - never guess plan generation from plan name alone if the exact billing/upgrade surface is unavailable.

## Decision-safe rule
A public page may say:
- “ClickUp publicly advertises Brain AI at $9/user/month and Everything AI at $28/user/month as of the checked date.”

It may NOT say:
- “Your ClickUp AI price is $9/$28”

unless the exact Workspace state confirms the add-on model and Workspace-specific billing surface.

For newer-plan Workspaces, AI may be bundled into the plan generation; for existing paid Workspaces, the current plan/price stays unchanged until an upgrade is selected. Therefore `plan_generation_or_migration_state` is a required material field.

## Content utility hypothesis
A useful page is not “ClickUp pricing explained.” It is:
- “Which ClickUp pricing generation applies to my Workspace?”
- “Do I still buy Brain AI as an add-on, or is AI included in my upgrade plan?”
- “Why the public $9/$28 AI price may not be the price shown to my Workspace.”

This creates an update-sensitive owned-data asset and can reuse the same state machine whenever ClickUp changes rollout scope, names, prices, credits, or migration rules.

## Kill / advance
Advance only if a future lawful external test shows people arrive with a Workspace-specific pricing/upgrade ambiguity and interact with the checker or return on updates.
Kill/down-rank if ClickUp converges to one universally visible plan generation and the state machine becomes unnecessary, or if public Help resolves the exact buyer question without added normalization value.

No account login, Workspace inspection, affiliate application, public deployment, payment collection, or monetization performed.
