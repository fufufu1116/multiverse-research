# Make affiliate commission-window conflict — resolution attempt v0

Status: RESEARCH_ONLY / NO AFFILIATE APPLICATION / NO LINK / NO REVENUE MODEL AUTHORITY / RUNTIME OFF
Checked: 2026-09-14

## Question
Can current public Make sources establish whether affiliate commission continues for 12 months or 24 months?

## Current official evidence
### Make affiliate landing page
Current page contains all of the following simultaneously:
- headline: 35% commission on referrals for 12 months;
- How it works: earn 35% commission for 12 months;
- FAQ `For how long will I receive my commission?`: 35% of payments for the next 12 months, starting when the user registers with the affiliate link;
- FAQ `What's the difference between the affiliate and the partner program?`: says a successful affiliate referral receives affiliate commission for 24 months.

Source:
https://www.make.com/en/affiliate

### Make Help Center — Affiliate program
Current Help Center states:
- 35% commission for 12 months;
- the 12-month period begins on affiliate-link registration, not first payment;
- explicit example: user registers Nov 1 2025, starts paying Dec 1 2025, commission is earned on payments through Nov 1 2026;
- payout minimum $100 plus three unique paying users;
- commission is from subscription payments, not extra operations.

Source:
https://help.make.com/affiliate-program

### Make Solution Partner page
Current Solution Partner page's affiliate-vs-partner comparison says affiliates earn commissions on successful sales for 24 months.

Source:
https://www.make.com/en/solution-partners

### General Terms & Conditions page
Current generic Terms & Conditions page links the Master Services Agreement, privacy/data documents and website terms, but the public page retrieved in this check does not state the affiliate commission duration.

Source:
https://www.make.com/en/terms-and-conditions

## Historical/context evidence — not current authority
A 2025 Make Community answer from a Make staff account described the then-program as 20% for 24 months. An older Make blog guide also described a 24-month structure with different percentages. These are evidence that 24 months may be stale lineage rather than proof of the current 2026 program.

Do not use these community/blog items to override current program Help.

## Fail-closed interpretation
The public current corpus does **not** support asserting a single exact total commission duration beyond dispute.

However, the apparent contradiction is asymmetric:
- every current program-specific source inspected supports commission during at least the first 12 months;
- the disputed question is whether commission continues for months 13–24.

Therefore use two separate planning fields:

`PUBLICLY_SUPPORTED_CORE_WINDOW = 12 months`

`MONTHS_13_TO_24_EXTENSION = UNRESOLVED`

Meaning:
- a conservative internal sensitivity model may cap referral economics at 12 months without relying on the disputed extension;
- do **not** call 12 months a contractual guarantee;
- do **not** count months 13–24 in expected revenue;
- do **not** advertise or publish a definitive program duration while the conflict persists;
- before any real affiliate application/revenue decision, inspect the exact terms presented to the approved account and/or obtain vendor confirmation if material.

## Effect on ranking
This conflict does not remove Make from the owned-media affiliate candidate set because 12-month recurring economics are independently supported by the current Help and multiple current landing-page statements. It does reduce confidence in long-horizon revenue modeling and strengthens the need for source-drift monitoring.

No real traffic, conversion, approval, retention, payout or revenue is inferred.

`MAKE_AFFILIATE_RATE_PUBLIC_CONTEXT=35_PERCENT`
`PUBLICLY_SUPPORTED_CORE_WINDOW=12_MONTHS`
`MONTHS_13_TO_24_EXTENSION=UNRESOLVED`
`CONSERVATIVE_MODEL_CAP=12_MONTHS_ONLY`
`CONTRACTUAL_GUARANTEE=NOT_CLAIMED`
`AFFILIATE_APPLICATION=OFF`
`MONETIZATION=OFF`
`#430=RESEARCH_ONLY`
`RUNTIME=OFF`
