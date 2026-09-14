# Resale Price Intelligence Probe v0 — no-inventory research

Status: RESEARCH_ONLY / NO PURCHASE / NO LISTING / NO SALE / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Test whether obvious public retail-to-marketplace spreads survive seller fees before spending any money. This is not a live-buy signal: public indexed prices can lag, inventory can disappear, and condition/edition differences matter.

## Fee baseline
Current Yahoo! official surfaces checked 2026-09-14:
- Yahoo!フリマ normal seller fee: 5% of sale price.
- Yahoo!オークション normal closing fee: 10% of winning price.
- current Yahoo!フリマ promotion can reduce fees for certain new sellers after meeting stated conditions, but unit economics must not rely on temporary campaign treatment.
Official:
- https://paypayfleamarket.yahoo.co.jp/topics/20231215/0000/
- https://support.yahoo-net.jp/PccAuctions/s/article/H000005313

## Probe A — CASIO ClassWiz `fx-JP900` / `fx-JP900CW`

### Public source side
Current indexed Surugaya result for `fx-JP900CW-N`:
- used sale: JPY 3,330;
- current communication/order fee shown for orders under JPY 5,000: JPY 240;
- indexed effective acquisition before any other incidental cost: about JPY 3,570.
The page also exposes a buyback reference of JPY 2,200, showing a meaningful retailer spread already exists inside the reuse chain.
Source:
- https://www.suruga-ya.jp/search?brand=&category=8130402&search_word=
- https://www.suruga-ya.jp/product/detail/749002142

### Public sold-history side
Yahoo! closed-search for `fx-JP900` family shows 68 completed items in the prior 180-day window with average JPY 4,001, but the result set mixes older `fx-JP900` and newer `fx-JP900CW` generations/conditions, so the average is not decision-safe for an exact model.
Examples visible in the result set for newer `fx-JP900CW(-N)` include completed prices around JPY 3,590, 4,500, 4,900, 5,000, 5,100, 5,260, 5,600 and 6,095 depending on condition/channel.
Source:
- https://auctions.yahoo.co.jp/closedsearch/closedsearch/%E9%96%A2%E6%95%B0%E9%9B%BB%E5%8D%93%20fx-jp900/0

### Falsification arithmetic
If acquired around JPY 3,570 and sold on Yahoo!フリマ:
- at JPY 3,590 -> after 5% fee = JPY 3,410.5 **before shipping**, already below acquisition;
- at JPY 4,900 -> after 5% fee = JPY 4,655; only JPY 1,085 remains before shipping, packaging, return/defect reserve and capital lock;
- at JPY 6,095 -> after 5% fee = JPY 5,790.25; spread is better, but this is an upper-condition outcome and cannot be assumed as repeatable.

Conclusion:
`RETAIL_SOURCE_TO_MARKETPLACE_ARBITRAGE = NOT ROBUSTLY PROVEN`.
Exact generation/condition classification dominates the spread. Do not treat the family average as a buy signal.

## Probe B — KING JIM `SR-MK1` label printer

### Public source side
Indexed current/recent reuse-store prices include:
- HardOff A/B-like listings around JPY 8,800;
- Second Street historical sold-out examples around JPY 6,490 (used B) and JPY 8,690 (used A).
Sources:
- https://netmall.hardoff.co.jp/product/5510366/
- https://www.2ndstreet.jp/goods/detail/goodsId/2320386099473/shopsId/30704
- https://www.2ndstreet.jp/goods/detail/goodsId/2331038910992/shopsId/30953

### Public sold-history side
Yahoo! closed-search for `SR-MK1` shows 57 completed items over the indexed 180-day window with average JPY 7,555 and range JPY 3,643–11,280. Visible examples vary materially with condition, unused status, AC adapter/tape bundle and channel.
Source:
- https://auctions.yahoo.co.jp/closedsearch/closedsearch/pro%2Bsr-mk1/0

### Falsification arithmetic
Even using the low historical source example JPY 6,490:
- average JPY 7,555 sale on Yahoo!フリマ -> after 5% fee = JPY 7,177.25;
- only JPY 687.25 remains before shipping, packaging, return/defect reserve and capital lock.

At a current HardOff-like JPY 8,800 source price, the indexed average resale price is already below acquisition before fees.

Conclusion:
`OBVIOUS_REUSE_RETAIL_TO_FLEA_ARBITRAGE = FAIL_ON_MARGIN` for this probe.

## Cross-probe lesson
The easy public-source arbitrage is largely competed away. A viable resale route, if any, probably needs at least one harder edge:
- bundle splitting / accessory-specific model knowledge;
- local/offline mispricing not already indexed online;
- repair/test/cleaning that creates verifiable condition uplift;
- seasonality with disciplined inventory turns;
- a sourcing channel structurally below public retail;
- or a data/intelligence layer that is more valuable than holding inventory.

But each harder edge increases Owner hours, compliance burden or defect risk. Therefore `retail store price -> public marketplace price` is down-ranked as the default solo-income path.

## Next research gate
Before any category survives desk research, require at least:
- 20 exact-model completed sales, not family-mixed search results;
- median and lower-quartile sold price, not only average/high examples;
- at least 5 repeatable source observations below the modeled break-even buy price;
- explicit fee/shipping/return reserve;
- legal/permit state resolved separately;
- expected net margin high enough to justify testing after all friction.

No product was bought, reserved, listed, messaged about, or sold.
