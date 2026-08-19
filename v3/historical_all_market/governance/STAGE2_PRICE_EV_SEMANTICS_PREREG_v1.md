# Multiverse Hybrid v3.0 — Stage 2 Price / EV Semantics Preregistration v1

Status: PREREGISTERED BEFORE STAGE2 EV CATALOG EXECUTION
Scope: All-Market Historical Economic Track, DEV2000 development data only

## Inputs

- Stage-0 PRICE catalog SHA-256:
  `2ca98097f74e5282fdc9c91629083f39bef4dafb94a1fc4f7e510acadefc407b`
- Stage-1 PL ticket-probability catalog SHA-256:
  `6348d9af2a535578cf454afca52ea2c944cb6c50cab87f6e6ffa75149880b526`
- Probability sources:
  - `candidate_a`
  - `b1a_reconstituted_v1`

## Scientific firewall

Stage 2 may read only:
- ticket probabilities;
- closing odds / price ranges;
- race_id / market / ticket identity;
- market availability and active-car metadata required for joins.

Stage 2 MUST NOT read or derive:
- RESULT / finishing order;
- PAYOUT / refund / Settlement;
- hit/miss;
- realized return / realized ROI;
- bankroll outcome;
- ECON_HOLDOUT1000.

Settlement remains prohibited.

## Elementary-ticket join

Join key is exact:
`(race_id, market, ticket_key)`.

Every Stage-1 probability ticket must have exactly one corresponding Stage-0 price quote for its sold market. Any missing/extra/duplicate ticket is Fail-Closed.

No fuzzy matching or ticket-key fallback is allowed.

## Point-odds markets

Applies to:
- 3連単 (`3rentan`)
- 3連複 (`3renhuku`)
- 2車単 (`2shatan`)
- 2車複 (`2shahuku`)
- 2枠単 (`2wakutan`)
- 2枠複 (`2wakuhuku`)

For model event probability `p` and closing decimal odds `o`:

`raw_ev = p * o - 1`

`raw_implied_probability = 1 / o`

Within each race × market, define market-shape probability:

`market_shape_q(ticket) = (1/o_ticket) / sum_all_tickets(1/o)`

Define model-shape probability:

`model_shape_p(ticket) = p_ticket / sum_all_tickets(p_ticket)`

For these mutually exclusive complete markets, model probability sum is expected to be 1.

Market-relative diagnostics:

`shape_edge_delta = model_shape_p - market_shape_q`

`shape_edge_ratio = model_shape_p / market_shape_q`

`market_implied_sum = sum_all_tickets(1/o)` is retained as a market-level price diagnostic; it is not interpreted as a literal bookmaker overround without additional pari-mutuel semantics.

## Wide market

Historical Wide prices are intervals `[low, high]`.

Primary conservative price rule is frozen as:

`primary_odds = low`

Primary EV:

`raw_ev_primary = p * low - 1`

Upper diagnostic only:

`raw_ev_high_diagnostic = p * high - 1`

The high value MUST NOT replace the primary low value for Stage-2 candidate ranking or later preregistration unless a new pre-outcome rule explicitly supersedes this one before Settlement.

Wide market shape diagnostics use two explicitly separate quote surfaces:

Primary low-odds surface:

`q_low_raw = 1 / low`

`market_shape_q_primary = q_low_raw / sum(q_low_raw)`

High-odds diagnostic surface:

`q_high_raw = 1 / high`

`market_shape_q_high_diagnostic = q_high_raw / sum(q_high_raw)`

Wide elementary ticket event probabilities overlap. For an n-car race with top-3 Wide semantics, the Stage-1 invariant is:

`sum_all_wide_ticket_probabilities = 3`

Therefore Wide model-shape probability is:

`model_shape_p = p / 3`

for market-relative shape comparisons only.

Raw EV always uses the actual Wide event probability `p`, never `p/3`.

## Stage-2 outputs

Per elementary ticket, retain:
- race_id;
- probability_source;
- market;
- ticket_key;
- model_event_probability;
- closing odds or Wide low/high interval;
- primary raw EV;
- Wide high-EV diagnostic where applicable;
- raw implied probability;
- normalized market-shape probability;
- normalized model-shape probability;
- shape edge delta;
- shape edge ratio;
- market-level implied-sum diagnostic.

## Prohibited in this preregistered Stage 2

Stage 2 v1 MUST NOT:
- choose an EV threshold;
- choose a shape-edge threshold;
- choose Top-K;
- choose one market over another based on realized returns;
- create BOX / wheel / formation / portfolio rules;
- allocate bankroll;
- calculate realized ROI;
- inspect winning tickets or refunds;
- promote Candidate A or B1a based on outcomes.

Descriptive distributions of model probabilities, odds, raw EV, and market-relative diagnostics are allowed because they use no outcomes.

## Trial accounting

Stage-2 price/probability engineering and descriptive catalog creation consume scientific trial count `0` because no outcome or Settlement data is accessed and no realized-return candidate is scored.

`ECON_HOLDOUT1000 = SEALED`.

END
