"""Voltage drop.

AC: Vdrop = k * I * (R*cos + X*sin) * L / 1000       (Chapter 9, Table 9)
DC: Vdrop = 2 * I * R * L / 1000                     (Chapter 9, Table 8)

k = configuration vdrop_factor (sqrt(3) for 3-phase, 2 for 1-phase / DC).
R, X are per 1000 ft.  Parallel sets divide R and X by the number of sets.
"""

from math import cos, sin, acos

from nec_data.impedance import R_AC, X_AC
from nec_data.dc_resistance import R_DC


def _lookup_ac(material: str, magnetic: str, size: str) -> tuple[float, float]:
    r_row = R_AC.get(material, {}).get(magnetic, {})
    x_row = X_AC.get(magnetic, {})
    if size not in r_row or size not in x_row:
        raise KeyError(
            f"impedance.py missing size {size!r} for {material}/{magnetic} - "
            "fill in NEC Chapter 9 Table 9."
        )
    return r_row[size], x_row[size]


def _lookup_dc(material: str, size: str, stranding: str = "stranded") -> float:
    row = R_DC.get(material, {}).get(stranding, {})
    if size not in row:
        raise KeyError(
            f"dc_resistance.py missing size {size!r} for {material}/{stranding} - "
            "fill in NEC Chapter 9 Table 8."
        )
    return row[size]


def vdrop_ac(
    current_amps: float,
    length_ft: float,
    size: str,
    sets: int,
    material: str,
    raceway_magnetic: str,
    factor: float,
    pf: float = 0.9,
) -> float:
    r, x = _lookup_ac(material, raceway_magnetic, size)
    r /= sets
    x /= sets
    theta = acos(pf)
    return factor * current_amps * (r * cos(theta) + x * sin(theta)) * length_ft / 1000.0


def vdrop_dc(
    current_amps: float,
    length_ft: float,
    size: str,
    sets: int,
    material: str,
) -> float:
    r = _lookup_dc(material, size) / sets
    return 2.0 * current_amps * r * length_ft / 1000.0
