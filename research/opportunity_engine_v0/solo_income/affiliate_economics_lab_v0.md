# Affiliate Economics Lab v0 — internal research only

Status: RESEARCH_ONLY / NO APPLICATION / NO AFFILIATE LINKS / NO PUBLICATION / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Compare monetization density and program friction for Owner-operated media without assuming traffic, approval, conversion, or revenue. The objective is to decide which monetization layer deserves priority *after* a lawful audience test exists.

## Current official program surfaces

### Make — high-fit automation SaaS
Current official terms checked:
- 35% commission on paid subscriptions for 12 months.
- payout request requires at least USD100 commission and at least 3 unique paying referred users.
- Wise payout.
- no application/account action performed here.
Sources:
- https://www.make.com/en/affiliate
- https://help.make.com/affiliate-program

Synthetic density example only:
- if a referred user paid USD12/month for a full 12 months with no changes/refunds, gross subscription value would be USD144 and 35% would be USD50.40.
- this is arithmetic, NOT a revenue forecast and NOT a statement that every referral stays 12 months or that this exact price/commission treatment will apply at payout time.

### n8n Cloud — high-fit automation SaaS
Current official terms checked:
- 30% commission on n8n Cloud referrals for 12 months.
- application/approval required.
- monthly PayPal payout; EUR100 minimum balance.
- affiliate links may not be used in paid advertising.
Sources:
- https://n8n.io/affiliates/
- https://n8n.io/pricing/

Synthetic density example only:
- Starter is currently EUR20/month billed annually, i.e. EUR240 annual plan value before other factors.
- 30% of EUR240 = EUR72 if the full eligible amount qualified.
- arithmetic only; no approval/conversion/retention is assumed.

### Pipedrive — strong recurring affiliate economics
Current official affiliate page / support checked:
- base Rising Affiliate: 20% revenue share for first 12 months of each new paying customer.
- Growth Affiliate: 30% first 12 months after sustaining 2–5 sales/month for at least 6 months.
- Power Affiliate: custom commission after 6+ sales/month for at least 6 months.
- no minimum sales requirement to join Rising tier; 90-day cookie.
- PartnerStack payout can be withdrawn after more than USD5; commission is locked on a delayed schedule after customer transaction.
Sources:
- https://www.pipedrive.com/ja/affiliate-partnership
- https://support.pipedrive.com/ja/article/how-can-i-become-a-pipedrive-affiliate-or-partner

Official Pipedrive example itself says a first-year customer revenue of USD200 would yield USD40 at the 20% base rate. This is a vendor-provided illustration, not our forecast.

### HubSpot — strong recurring rate, broader CRM scope
Current official affiliate page checked:
- Starter affiliate tier: 30% recurring commission up to one year on sales.
- application reviewed by HubSpot; current page says review/contact in roughly 2–3 business days.
- software reviewers, content creators, online educators and business-solution media are target applicants; being a HubSpot customer is not required.
Source:
- https://www.hubspot.com/partners/affiliates
- https://legal.hubspot.com/jp/affiliate-program-agreement

Exact payable commission still depends on current Affiliate Tool/program terms and approved account state. Do not model a guaranteed unit amount before approval.

### monday.com — attractive headline, insufficient exact starting-rate visibility
Current official affiliate page says:
- tier model can pay **up to 100% of first-year sales** for referred customers.
- payouts monthly via PayPal or Stripe.
Source:
- https://monday.com/lang/ja/affiliate-program

Fail-closed interpretation:
- `UP_TO_100_PERCENT` is not the same as a guaranteed starting commission.
- public page retrieved here does not expose enough exact base-tier economics to rank it above programs with explicit starting rates.
- treat as `ATTRACTIVE_BUT_RATE_CONDITIONAL` until exact approved-tier terms are observed.

### ClickUp — free-workspace referral, different funnel economics
Current official page checked:
- up to USD25 for each new free Workspace referral.
- 30-day cookie.
- existing ClickUp users, self-referrals and certain last-touch paid-marketing cases do not qualify.
- some countries are not commissionable; referrals are verified.
Source:
- https://clickup.com/partners/affiliates

Interpretation:
- this pays at a different funnel stage than paid-subscription revenue-share programs.
- potentially lower friction than paid conversion, but `up to USD25` and geo/verification/last-touch conditions prevent treating USD25 as guaranteed.

### Zapier — media monetization fit is weaker/less direct
Current official partner page checked:
- no generic open consumer-style affiliate surface is presented as the core route.
- Solution Partner/referral programs exist for eligible partners; Creator sponsored-content path targets serious influencers and the page cites a 50K+ subscriber threshold for sponsored-content application.
- referral reward amounts are governed through partner portal/terms rather than a simple public base affiliate rate.
Sources:
- https://zapier.com/l/partners
- https://zapier.com/legal/partner-referral-program-terms

Interpretation:
- do not build the first owned-media monetization thesis around Zapier affiliate revenue.
- Zapier remains relevant as comparison/search content but monetization should not be assumed.

## General product-affiliate benchmarks in Japan

### Amazon.co.jp Associates
Current standard rate schedule checked:
- category-dependent; examples include 10%, 8%, 5%, 4.5%, 4%, 3%, 2%, 0.5%, and 0% categories.
- common PC/camera/home-electronics category examples are currently 2%; books/stationery/toys/kitchen/interior examples 3%; clothing/food examples 8%.
- Amazon can change the schedule under program terms.
Source:
- https://affiliate.amazon.co.jp/help/node/topic/GRXPHT8U84RAYDXZ

Simple density illustration:
- JPY10,000 eligible sale at 2% -> JPY200;
- JPY10,000 eligible sale at 8% -> JPY800.
This does not include returns, disallowed transactions or category reclassification.

### Rakuten Affiliate
Current guideline checked:
- Rakuten Market/shop commission: generally 2%–4% by product genre.
- attribution rule shown: click -> add to cart within 24h -> complete purchase within 89 days.
Source:
- https://affiliate.rakuten.co.jp/guideline/rule/

Simple density illustration:
- JPY10,000 eligible sale -> JPY200–400 before any program-specific adjustments.

## Ad revenue benchmark — AdSense
Current Google official help checked:
- AdSense has no usage fee to publishers.
- content AdSense publisher share is 80% after the buy-side advertising platform fee; when Google Ads buys through Google’s buy-side, Google gives an example that this works out to about 68% of advertiser spend.
- actual earnings cannot be predicted precisely; they depend on traffic, content, user geography and ad setup.
Sources:
- https://support.google.com/adsense/answer/32850?hl=ja
- https://support.google.com/adsense/answer/180195?hl=ja
- https://support.google.com/adsense/answer/9902?hl=ja

Interpretation:
- AdSense is a useful secondary monetization layer once traffic exists.
- it is not a first-business proof because revenue density is unknown until actual qualified traffic exists.

## Japan disclosure boundary
Current Consumer Affairs Agency Q&A says affiliate-site disclosure must be clear to ordinary consumers. Merely placing a phrase somewhere on the site is not enough if size/color/context make the commercial nature unclear; local disclosure near a potentially misleading paid/expert-style statement can also be necessary.
Official:
- https://www.caa.go.jp/policies/policy/representation/fair_labeling/faq/stealth_marketing/

Future commercial pages must therefore have a clearly visible disclosure such as `このサイトはアフィリエイト広告を利用しています` / equivalent, while still complying with each program's own terms. This is a design requirement, not a current publication action.

## Current monetization ranking for the owned-media wedge

### A — PRIMARY: B2B SaaS recurring affiliate
Best current fit:
- Make
- n8n
- Pipedrive
- HubSpot

Why:
- high commission density relative to low-ticket product affiliate sales;
- recurring/revenue-share mechanics can monetize fewer high-intent decisions;
- aligns directly with a decision-safe pricing/calculator media asset.

Risks:
- application rejection;
- program changes;
- long sales cycle / lower paid conversion;
- vendor dependence;
- payout thresholds/lock periods;
- the media must remain trustworthy even when the highest-paying vendor is not the best fit.

### B — SUPPORTING: ClickUp / monday.com
- ClickUp can reward qualified free-Workspace acquisition but uses different funnel economics and conditions.
- monday.com's public headline is attractive, but exact base-tier rate is insufficiently explicit in the retrieved public page.

### C — TRAFFIC MONETIZER: AdSense
Use only after traffic exists. It should monetize informational visits that do not convert to an affiliate program; never distort page UX to chase ads before utility is proven.

### D — ADJACENT ONLY: Amazon/Rakuten
Useful where a page naturally involves physical books/equipment/accessories, but current percentage commissions are generally lower-density than B2B SaaS recurring referrals. Do not force irrelevant product links into SaaS decision pages.

## Synthetic sensitivity formula
For paid SaaS affiliate pages:
`AFFILIATE_REVENUE = QUALIFIED_VISITS * OUTBOUND_CTR * PAID_CONVERSION * ELIGIBLE_COMMISSION_PER_CUSTOMER`

Every term except the commission formula is currently `UNPROVEN` for our media asset.
Do not fill missing terms with industry averages and call the result expected revenue.

Example purely to show sensitivity, NOT forecast:
- 1,000 qualified visits
- 10% outbound CTR
- 3% eligible paid conversion
- USD50 eligible commission/customer
=> 3 paying referrals -> USD150.
Changing paid conversion from 3% to 1% changes the same model to USD50. Therefore actual traffic + conversion evidence dominates revenue prediction.

## Strategic conclusion
The current first-priority business architecture is:
`DECISION-SAFE TOOL / CALCULATOR -> OWNED SEARCH CONTENT -> B2B SAAS AFFILIATE -> ADS AS SECONDARY FILL`

Not:
`AI BLOG VOLUME -> GENERIC PRODUCT LINKS`.

This architecture keeps Owner independence, creates reusable owned data/tools, has high automation headroom, and preserves an auditable separation between editorial recommendation and monetization.

No affiliate program application, account creation, tracking-link generation, ad-network application, public publication or monetization action was performed.
