"""NEC 2023 Table 310.15(C)(1) - Adjustment factors for more than three
current-carrying conductors in a raceway or cable.

Keys are the upper bound of each row.  factor_for(ccc) picks the row whose
upper bound is >= ccc.

VERIFY every value against your bound NEC copy before using for a real design.
"""

# CCC_ADJUST[upper_bound_ccc] -> factor
CCC_ADJUST: dict[int, float] = {
    6:   0.80,   # 4-6
    9:   0.70,   # 7-9
    20:  0.50,   # 10-20
    30:  0.45,   # 21-30
    40:  0.40,   # 31-40
    999: 0.35,   # 41 and above
}


def factor_for(ccc: int) -> float:
    """Return the adjustment factor for a given number of CCCs.

    Raises KeyError with a clear message if the table is empty.
    """
    if not CCC_ADJUST:
        raise KeyError(
            "nec_data/ccc_derate.py CCC_ADJUST is empty - fill in NEC Table 310.15(C)(1)."
        )
    if ccc <= 3:
        return 1.0
    keys = sorted(CCC_ADJUST)
    for k in keys:
        if ccc <= k:
            return CCC_ADJUST[k]
    return CCC_ADJUST[keys[-1]]
