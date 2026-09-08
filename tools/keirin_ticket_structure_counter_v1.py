#!/usr/bin/env python3
"""Pure ticket-structure combination counter for keirin research.

No odds, predictions, results, payouts, betting, or external data access.
"""

from math import comb

def trifecta_box_count(n: int) -> int:
    if n < 3:
        return 0
    return n * (n - 1) * (n - 2)

def trio_box_count(n: int) -> int:
    if n < 3:
        return 0
    return comb(n, 3)

def exacta_box_count(n: int) -> int:
    if n < 2:
        return 0
    return n * (n - 1)

def quinella_box_count(n: int) -> int:
    if n < 2:
        return 0
    return comb(n, 2)

def trifecta_fixed_first_second_group_all_count(
    field_size: int,
    second_group_size: int,
) -> int:
    """Count A-[second group]-ALL, assuming A is not in second group.

    For each second-place choice, the third place can be anyone except
    the fixed first and chosen second: field_size - 2 choices.
    """
    if field_size < 3:
        return 0
    if second_group_size < 1 or second_group_size > field_size - 1:
        raise ValueError("invalid second_group_size")
    return second_group_size * (field_size - 2)

def _self_test():
    assert trifecta_box_count(3) == 6
    assert trifecta_box_count(4) == 24
    assert trifecta_box_count(5) == 60
    assert quinella_box_count(3) == 3
    assert exacta_box_count(3) == 6
    assert trifecta_fixed_first_second_group_all_count(7, 3) == 15
    assert trifecta_fixed_first_second_group_all_count(9, 3) == 21
    print("PASS")

if __name__ == "__main__":
    _self_test()
