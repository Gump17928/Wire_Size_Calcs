"""NEC 2023 240.6(A) - Standard ampere ratings for fuses and inverse-time
circuit breakers.

VERIFY every value against your bound NEC copy before using for a real design.
"""

STANDARD_OCPD: list[int] = [
    15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125,
    150, 175, 200, 225, 250, 300, 350, 400, 450, 500, 600, 700, 800,
    1000, 1200, 1600, 2000, 2500, 3000, 4000, 5000, 6000,
]


def next_standard(amps: float) -> int:
    """Return the next-higher standard OCPD rating at or above `amps`."""
    if not STANDARD_OCPD:
        raise ValueError(
            "nec_data/ocpd.py STANDARD_OCPD is empty - fill in NEC 240.6(A)."
        )
    for rating in STANDARD_OCPD:
        if rating >= amps:
            return rating
    return STANDARD_OCPD[-1]
