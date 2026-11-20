"""Load-current adjustments (continuous load, spare capacity, motor rules).

Right now this only implements the 125% continuous factor per NEC 210.19 /
215.2.  Add motor 430.22 / HVAC 440 rules here when needed.
"""


def design_current(rla_amps: float, continuous: bool) -> float:
    """Return the current used for conductor and OCPD sizing."""
    return rla_amps * (1.25 if continuous else 1.0)
