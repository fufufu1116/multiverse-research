from synthetic_market_odds_v1 import (
    DEFAULT_PROFILES,
    event_probabilities_to_quote_shape,
    generate_synthetic_decimal_odds,
    synthetic_market_receipt,
)


def main() -> None:
    exclusive = {("A",): 0.50, ("B",): 0.30, ("C",): 0.20}
    wide_like = {("A", "B"): 0.90, ("A", "C"): 0.80, ("B", "C"): 0.70, ("A", "D"): 0.60}

    assert abs(sum(event_probabilities_to_quote_shape(exclusive).values()) - 1.0) < 1e-12
    assert abs(sum(wide_like.values()) - 3.0) < 1e-12
    assert abs(sum(event_probabilities_to_quote_shape(wide_like).values()) - 1.0) < 1e-12

    profile = DEFAULT_PROFILES["NOISY"]
    odds_1 = generate_synthetic_decimal_odds(exclusive, profile=profile, seed=20260819)
    odds_2 = generate_synthetic_decimal_odds(exclusive, profile=profile, seed=20260819)
    assert odds_1 == odds_2
    assert all(value >= 1.0 for value in odds_1.values())

    wide_odds = generate_synthetic_decimal_odds(wide_like, profile=profile, seed=20260820)
    assert all(value >= 1.0 for value in wide_odds.values())

    receipt = synthetic_market_receipt(
        market_name="synthetic_test",
        profile=profile,
        seed=20260819,
        odds=odds_1,
    )
    assert receipt["price_object_type"] == "SYNTHETIC_MARKET_SIMULATION_ONLY"
    assert receipt["scientific_claim_boundary"] == "NOT_REAL_MARKET_EVIDENCE"

    print("PASS_SYNTHETIC_MARKET_ODDS_V1")


if __name__ == "__main__":
    main()
