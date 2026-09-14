# ClickUp checker external-test instrumentation contract v0

Status: INTERNAL / RESEARCH_ONLY / NOT DEPLOYED / NO MONETIZATION / RUNTIME OFF
Prepared: 2026-09-14

## Goal
Make the preregistered ClickUp plan-generation falsification measurable without collecting credentials, billing documents, Workspace identifiers, email, name, screenshots or other direct PII.

This document grants no publication or data-collection authority.

## Core measurement principle
Do not infer demand from raw pageviews alone.

The external test needs two separately evidenced denominators:
1. **qualified exposure denominator** — evidence that a person plausibly interested in ClickUp pricing/AI/upgrade decisions was actually exposed to the test proposition;
2. **checker interaction denominator** — anonymous starts and completed diagnostic states.

If qualified exposure cannot be verified, zero interactions remain `DISTRIBUTION_INCONCLUSIVE`, not product rejection.

## Frozen anonymous events
Only these logical events are needed:

### `EXPOSURE_QUALIFIED`
Source-side denominator, not self-reported page traffic.
Required dimensions:
- date bucket;
- source channel;
- source placement/test id;
- estimated/verified unique qualified exposures where platform evidence permits.

No user identity stored.

### `CHECKER_START`
Count once when a session makes the first deliberate diagnostic interaction after page load.
Examples:
- changes Workspace state from default; or
- changes visible Plans/Billing/Upgrade surface from default; or
- presses `判定する` after selecting at least one non-default diagnostic value.

Do not count passive load as start.

### `CHECKER_COMPLETE`
Count once when the checker returns one of the frozen terminal states with sufficient input to produce a meaningful next-evidence recommendation.

Terminal states:
- `NEW_INCLUDED_AI_PLAN_PRICE_OBSERVED`
- `NEW_INCLUDED_AI_PLAN_CONFIRMED_PRICE_UNKNOWN`
- `CLASSIC_ADDON_MODEL_PRICE_OBSERVED`
- `CLASSIC_ADDON_MODEL_CONFIRMED_PRICE_UNKNOWN`
- `CONFLICTING_SURFACES_HUMAN_REVIEW`
- `NEW_PLAN_SET_EXPECTED_SURFACE_NOT_CONFIRMED`
- `UPGRADE_SURFACE_UNKNOWN`
- `INSUFFICIENT_EVIDENCE`

`INSUFFICIENT_EVIDENCE` counts as completion only if the user deliberately provided at least one meaningful diagnostic input; a default untouched page does not count.

### `PUBLIC_PRICE_INSUFFICIENT`
Derived, not directly asked. True if terminal state is one of:
- `NEW_INCLUDED_AI_PLAN_CONFIRMED_PRICE_UNKNOWN`
- `CLASSIC_ADDON_MODEL_CONFIRMED_PRICE_UNKNOWN`
- `CONFLICTING_SURFACES_HUMAN_REVIEW`
- `NEW_PLAN_SET_EXPECTED_SURFACE_NOT_CONFIRMED`
- `UPGRADE_SURFACE_UNKNOWN`
- deliberate-input `INSUFFICIENT_EVIDENCE` with a specific missing-evidence recommendation.

### `QUALIFIED_CONFUSION_CONFIRMATION`
Optional one-tap post-result question:
`この判定は、実際に迷っていた料金・AIプランの判断に役立ちましたか？`
Frozen responses:
- `YES_REAL_DECISION_CONFUSION`
- `NO_GENERAL_CURIOSITY`
- `NO_NOT_HELPFUL`
- `UNSURE`

No free-text field in the first test.

### `OFFICIAL_UI_ALREADY_SUFFICIENT`
Optional one-tap post-result question:
`ClickUp公式の現在の画面だけで、同じ判断は迷わずできましたか？`
Frozen responses:
- `YES_OFFICIAL_UI_SUFFICIENT`
- `NO_CHECKER_ADDED_VALUE`
- `UNSURE`

This directly tests redundancy risk.

## Privacy / data minimization
First external falsification must not ask for or intentionally record:
- name;
- email;
- phone;
- ClickUp account or Workspace ID/name;
- login state;
- billing document;
- card/payment data;
- screenshot/image upload;
- company/customer identity;
- exact invoice amount if it could identify a contract;
- free-text response.

Optional numeric inputs should be generic scenario numbers only. The user can leave them blank.

## Frozen metrics
Given verified qualified exposure `Q`, starts `S`, completions `C`, public-price-insufficient completions `P`, qualified real-confusion yes responses `R`, and official-UI-sufficient yes responses `O`:

- `START_RATE = S / Q`
- `COMPLETION_RATE = C / S`
- `PUBLIC_PRICE_INSUFFICIENT_RATE = P / C`
- `REAL_CONFUSION_CONFIRMATIONS = distinct qualified confirmations R`
- `OFFICIAL_UI_SUFFICIENT_RATE = O / answered_redundancy_question`

Do not calculate a rate when its denominator is zero or unverified.

## Preregistered threshold mapping
After >=100 qualified unique exposures:

Strengthen only if:
- `START_RATE >= 15%`;
- `COMPLETION_RATE >= 60%`;
- >=5 distinct qualified `YES_REAL_DECISION_CONFUSION` confirmations;
- `PUBLIC_PRICE_INSUFFICIENT_RATE >= 20%`;
- redundancy evidence does not show the official UI already solves the problem for most qualified users.

Downrank if, after >=100 qualified exposures:
- start <5%; or
- completion <30%; or
- <3 distinct qualified real-confusion confirmations; or
- >90% of qualified redundancy respondents say current official UI is already sufficient.

Hold/inconclusive when qualified exposure denominator is absent or <100.

## Source attribution
Permitted non-identifying dimensions:
- source channel;
- source post/placement id;
- variant id;
- date bucket.

Do not use cross-site fingerprinting, invasive tracking, scraped identities, DMs, paid retargeting or lookalike-audience uploads in the first test.

## Monetization firewall
Instrumentation must remain functional with:
- no affiliate links;
- no ads;
- no payment;
- no email capture;
- no seller/service offer.

This makes usefulness falsification independent of monetization incentives.

## Deployment preconditions
Before any external deployment:
1. Fresh Read main / #394 / #404 / #430.
2. Explicitly confirm the separate external-test authority envelope.
3. Recheck current ClickUp official sources and checker assumptions.
4. Verify no PII/free-text fields were introduced.
5. Verify source-side qualified exposure evidence can be measured without prohibited outreach/spend.
6. Preserve an exact publication receipt and downstream visibility proof.

`INSTRUMENTATION=INTERNAL_READY`
`PII_COLLECTION=OFF`
`FREE_TEXT=OFF`
`MONETIZATION=OFF`
`EXTERNAL_COLLECTION=NOT_AUTHORIZED_HERE`
`#430=RESEARCH_ONLY`
`RUNTIME=OFF`
