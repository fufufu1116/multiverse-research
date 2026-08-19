# Multiverse Keirin — Synthetic Market / Odds Boundary v1

Status: OPERATIONAL RESEARCH BOUNDARY — NOT A SCIENTIFIC FREEZE
Date: 2026-08-19 JST

## Owner authorization

If real decision-time odds are unavailable or incomplete, No.3 may create an original synthetic market/odds process for pipeline engineering, stress testing and virtual-bankroll experiments.

The project remains personal, noncommercial and simulation-only. No real-money wagering is in scope.

## Allowed uses

Synthetic odds may be used for:
- testing ticket-price/EV plumbing;
- validating BUY/NO-BET code paths;
- testing virtual FLAT/Kelly/portfolio mechanics;
- stress testing tail behavior, odds drift, market noise and liquidity scenarios;
- verifying cross-market interfaces and probability-object contracts;
- evaluating whether an algorithm is numerically stable under realistic-shaped price ranges.

## Prohibited scientific claims

Synthetic odds MUST NOT be used as evidence that:
- a real market inefficiency exists;
- a model beats the real keirin market;
- real-world ROI is positive;
- a BUY threshold is economically valid in the real market;
- a market-residual model adds real incremental information;
- a simulated bankroll path predicts actual betting performance.

Any report using synthetic odds must label the economic outputs as `SYNTHETIC_MARKET_SIMULATION_ONLY`.

## Design philosophy

The first synthetic market is a **stylized pari-mutuel-like emulator**, not a claim to reproduce exact historical keirin odds.

The emulator may include:
- a normalized ticket-demand/quote shape;
- configurable market sharpness/bias exponent;
- deterministic seeded multiplicative noise;
- configurable payout-return factor / friction;
- optional odds caps/floors for engineering scenarios;
- multiple scenario profiles (sharp, noisy, tail-heavy, stress).

Parameters are scenario inputs unless later calibrated against a legally held real odds sample. Uncalibrated parameters must never be described as empirically estimated keirin-market parameters.

## Wide semantics

Wide event probabilities overlap and have total event mass 3 under the Probability Object Contract. The synthetic market generator therefore must not treat the Wide event-probability vector itself as a normalized exclusive outcome distribution.

For synthetic quote generation only, a separate unit-mass `quote_shape` may be constructed from Wide event probabilities. This quote shape is a market-pricing engineering object, not an event-probability distribution.

## Real odds replacement rule

If a valid real decision-time odds source later becomes available:
- synthetic and real price objects must carry different explicit types;
- real-market evaluation must not silently mix synthetic prices;
- any economic promotion claim requires the real-price path unless the research question is explicitly synthetic-only.

## Anti-overfit rule

Do not tune synthetic-market parameters to make a candidate model profitable.

Primary synthetic profiles must be preregistered or fixed before comparing candidate policies. Sensitivity analysis may vary profiles, but candidate selection must not cherry-pick the most favorable synthetic market.

## Current role

Synthetic odds are a fallback and engineering accelerator. They remove an I/O blocker; they do not replace real-market evidence.

END
