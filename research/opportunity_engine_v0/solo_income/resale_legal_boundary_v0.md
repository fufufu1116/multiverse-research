# Resale / せどり Legal Boundary v0 — internal research only

Status: RESEARCH_ONLY / NO PURCHASE / NO LISTING / NO SALE / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Prevent the 百人将 solo-income scan from treating recurring used-goods sourcing as a frictionless cash route. This note is a generic research boundary, not legal advice or an Owner-specific eligibility determination.

## Current official baseline

### What Japanese police guidance calls `古物`
Kanagawa Prefectural Police currently explains that, under the Secondhand Articles Business Act, `古物` includes:
- an item that has been used once;
- an unused item that has been traded for the purpose of use;
- either of those after some repair/maintenance.

The 13 categories include clothing, watches/jewelry, vehicles, bicycles, cameras, office equipment, machinery/tools, miscellaneous goods, books, and vouchers, among others.

Official:
- https://www.police.pref.kanagawa.jp/tetsuzuki/eigyokankei/kobutsu/mesd0019.html

### Recurring secondhand business is permission-bound
The same current Kanagawa guidance says a person newly operating a secondhand-goods business needs Public Safety Commission permission.
Current application fee: JPY 19,000.
Guidance says typical issuance period is about 40 days.

This means a recurring “buy used goods -> resell for profit” plan must not be scored as zero-setup or immediate-first-cash before the exact legal/business form is confirmed.

### Sourcing from flea-market / auction sellers creates identity-verification obligations
Tokyo Metropolitan Police currently states that when a licensed secondhand dealer buys goods, the counterparty's address/name/occupation/age must be verified, including purchases through online auctions/flea-market apps and purchases from another secondhand dealer.
For non-face-to-face sourcing, legally specified verification methods are required; a simple copy of an ID is not necessarily sufficient.

Current Tokyo guidance also states that for online/flea-market purchases of certain goods, identity-verification obligations can apply regardless of lower transaction value for specified categories; do not assume “small ticket = no compliance burden.”

Official:
- https://www.keishicho.metro.tokyo.lg.jp/tetsuzuki/kobutsu/kaisetsu/kobutsu_shinsei.html
- https://www.keishicho.metro.tokyo.lg.jp/tetsuzuki/kobutsu/kaisetsu/hitaimen.html

### Internet sales have public display / URL obligations
Tokyo/Kanagawa police guidance currently requires Internet-trading secondhand dealers to disclose permit-related information, and URL/business-model filings can apply. Tokyo guidance also notes that internet sales can fall under mail-order rules with additional business information disclosure.

Official:
- https://www.keishicho.metro.tokyo.lg.jp/tetsuzuki/kobutsu/kaisetsu/kobutsu_shinsei.html
- https://www.police.pref.kanagawa.jp/tetsuzuki/eigyokankei/kobutsu/mesd0045.html

## Research routing consequence
Split the resale route into four distinct research classes and never merge their economics:

1. `PERSONAL_PROPERTY_LIQUIDATION`
   - disposing of items already owned for personal use;
   - useful as a cash-floor concept, but not automatically a repeatable business model;
   - exact legal/tax treatment must be checked before any real sale if material.

2. `RETAIL_NEW_GOODS_ARBITRAGE`
   - buy from ordinary retailer/manufacturer channel and resell;
   - exact secondhand-law treatment depends on transaction history/product state and must not be guessed from the word “new”; separate legal check needed before execution;
   - inventory, return, account/ToS and price-drop risk still apply.

3. `RECURRING_USED_GOODS_SOURCING`
   - buy used/new-old-stock-like goods from consumers/flea markets/recyclers and resell;
   - permission/compliance burden is material; score lower on time-to-first-profit until ready.

4. `NO_INVENTORY_PRICE_INTELLIGENCE`
   - research price spreads, completed-sale ranges, seasonality, fees, shipping and failure rates without buying anything;
   - this is the only route authorized in the current research-only phase and is the correct next step for category discovery.

## Category filter before any price-spread research
Exclude or strongly down-rank:
- counterfeit-prone luxury goods;
- regulated weapons/chemicals/medication/alcohol/nicotine;
- stolen-goods risk categories without strong provenance;
- high return/hidden-defect electronics unless the margin clearly covers inspection/return loss;
- bulky goods where shipping destroys spread;
- categories where model/condition cannot be normalized reliably.

Prefer research candidates with:
- exact model/JAN/ISBN/part-number identity;
- low counterfeit risk;
- public sold-price evidence, not only active asking prices;
- small/light shipping;
- bounded condition grading;
- repeatable sourcing evidence;
- gross spread large enough to survive platform fee + shipping + return/markdown reserve.

## Required unit-economics formula
`NET_EXPECTED = SELL_PRICE - BUY_COST - PLATFORM_FEE - SHIPPING - PACKAGING - EXPECTED_RETURN_LOSS - MARKDOWN_RESERVE - PAYMENT/PAYOUT_COST`

Also record:
- capital-lock days;
- sell-through rate proxy;
- number of repeatable sourcing observations;
- platform dependency;
- legal/compliance setup state;
- account/ToS risk.

A positive gross spread is not a valid opportunity if it requires unmodeled permit/identity/display obligations or depends on one non-repeatable listing.

No permit application, seller onboarding, inventory purchase, listing, payment, or revenue action was taken.
