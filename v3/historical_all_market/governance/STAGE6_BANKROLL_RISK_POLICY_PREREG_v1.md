# Multiverse Hybrid v3.0 — Stage 6 Bankroll / Risk Policy Prereg v1

Status: PREREGISTERED BEFORE RESULT / PAYOUT / SETTLEMENT ACCESS
Track: All-Market Historical Economic Track
Date: 2026-08-19 JST

## 1. Purpose

Stage 6 freezes a finite family of stake-allocation / bankroll-risk policies over the Stage-5 race-level portfolio templates.

No policy is promoted as profitable before Settlement.

## 2. Common monetary conventions

- starting bankroll for historical bankroll-path simulation: `100000 JPY`
- minimum stake unit: `100 JPY`
- stakes are integer multiples of 100 JPY
- a ticket whose computed stake rounds below 100 JPY is not bought
- races are settled chronologically before the next race stake is determined
- no borrowing and no negative bankroll
- if available bankroll is below the required minimum stake, the affected ticket is NO-BET

## 3. Conservative probability and price for risk sizing

For every selected ticket:

- `p = min(candidate_a_ticket_probability, b1a_ticket_probability)`
- normal markets use the frozen closing decimal odds
- wide uses the already-frozen `closing_odds_low` only

No diagnostic high-wide price may size a stake.

## 4. Frozen stake-policy family

### `FLAT100`
Stake exactly 100 JPY on every Stage-5 selected elementary ticket, subject only to available bankroll.

### `RACE2PCT_EQUAL`
At each race, risk at most 2% of bankroll available immediately before the race.

1. Convert 2% race budget to whole 100-JPY units by floor.
2. If the unit budget is smaller than the number of selected tickets, keep only the highest Stage-4-ranked tickets up to the available unit count.
3. Split the available units as evenly as possible over retained tickets.
4. Any remainder units are assigned one-by-one in Stage-4 rank order.

### `FK10_R2`
Per-ticket full Kelly fraction for decimal odds `o` and conservative probability `p`:

`kelly = max(0, (o*p - 1) / (o - 1))`.

Use 10% fractional Kelly:

`raw_fraction = 0.10 * kelly`.

Caps:

- maximum per ticket = 0.25% of pre-race bankroll
- maximum sum over the race = 2.00% of pre-race bankroll

If uncapped ticket fractions exceed the race cap, scale all positive fractions proportionally to the race cap. Convert each resulting stake down to the nearest 100 JPY. Zero-unit tickets are omitted.

### `FK25_R3`
Same Kelly formula, using 25% fractional Kelly.

Caps:

- maximum per ticket = 0.50% of pre-race bankroll
- maximum sum over the race = 3.00% of pre-race bankroll

If the race cap is exceeded, scale proportionally. Round each ticket stake down to the nearest 100 JPY. Zero-unit tickets are omitted.

## 5. No outcome-conditioned discretionary changes

The following are prohibited after Settlement opens unless a new separately governed research line is created:

- changing Kelly fraction because of observed ROI
- changing per-ticket / per-race caps because of observed drawdown
- changing starting bankroll to improve a historical result
- adding stop-loss / take-profit rules after seeing the path
- changing the 100-JPY rounding rule

## 6. Frozen full configuration space

Stage 6 crosses:

- 7 Stage-3 profiles
- 4 Stage-4 agreement gates
- 7 Stage-5 portfolio templates
- 4 Stage-6 stake policies

Total frozen economic configurations = `7 * 4 * 7 * 4 = 784`.

This is a finite preregistered search space. No configuration has yet seen realized Settlement.

## 7. Scientific state

- RESULT access = false
- PAYOUT access = false
- Settlement access = false
- realized ROI = not computed
- scientific trial count = 0
- `ECON_HOLDOUT1000 = SEALED`

Stage 6 completion alone does not authorize Settlement. Opening Settlement is a material outcome-sensitive governance boundary.

END OF STAGE 6 PREREG v1
