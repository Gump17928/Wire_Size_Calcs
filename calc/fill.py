"""Conduit fill per NEC Chapter 9.

Rules (Chapter 9, Note to Tables):
    1 conductor  -> 53% max fill
    2 conductors -> 31% max fill
    3+           -> 40% max fill

Given the phase / neutral / EGC sizes and counts, sum insulated conductor
areas (Chapter 9 Table 5) and walk conduit trade sizes (Table 4) until the
appropriate fill area is met.
"""

from dataclasses import dataclass

from nec_data.conductor_dims import COND_AREA_IN2
from nec_data.conduit_dims import CONDUIT


@dataclass
class FillResult:
    trade_size: str
    total_area_in2: float
    allowed_area_in2: float
    fill_pct: float


def _area(insulation: str, size: str) -> float:
    row = COND_AREA_IN2.get(insulation, {})
    if size not in row:
        raise KeyError(
            f"conductor_dims.COND_AREA_IN2[{insulation!r}][{size!r}] missing - "
            "fill in NEC Chapter 9 Table 5."
        )
    return row[size]


def size_conduit(
    conductors: list[tuple[str, str, int]],
    conduit_type: str,
    insulation: str,
) -> FillResult:
    """conductors: list of (role, size, count) tuples, e.g.
        [("phase","4/0",3), ("neutral","4/0",1), ("egc","4",1)]
    """
    total_count = sum(c for _, _, c in conductors)
    total_area = sum(_area(insulation, s) * c for _, s, c in conductors)

    if total_count == 1:
        col = "area_53"
    elif total_count == 2:
        col = "area_31"
    else:
        col = "area_40"

    trades = CONDUIT.get(conduit_type, {})
    if not trades:
        raise KeyError(
            f"conduit_dims.CONDUIT[{conduit_type!r}] is empty - "
            "fill in NEC Chapter 9 Table 4."
        )

    def _num(sz: str) -> float:
        if "-" in sz:
            w, f = sz.split("-")
            return int(w) + eval(f)  # e.g. "1-1/4"
        if "/" in sz:
            return eval(sz)
        return float(sz)

    for size in sorted(trades, key=_num):
        allowed = trades[size][col]
        if allowed >= total_area:
            return FillResult(size, total_area, allowed, 100 * total_area / allowed)

    raise ValueError(
        f"No {conduit_type} trade size in Table 4 can fit {total_area:.3f} in^2."
    )


def check_conduit(
    conductors: list[tuple[str, str, int]],
    conduit_type: str,
    trade_size: str,
    insulation: str,
) -> FillResult:
    """Compute the fill for an as-built conduit choice (no search)."""
    total_count = sum(c for _, _, c in conductors)
    total_area = sum(_area(insulation, s) * c for _, s, c in conductors)

    if total_count == 1:
        col = "area_53"
    elif total_count == 2:
        col = "area_31"
    else:
        col = "area_40"

    trades = CONDUIT.get(conduit_type, {})
    if trade_size not in trades:
        raise KeyError(
            f"conduit_dims.CONDUIT[{conduit_type!r}][{trade_size!r}] missing - "
            "fill in NEC Chapter 9 Table 4."
        )
    allowed = trades[trade_size][col]
    return FillResult(trade_size, total_area, allowed, 100 * total_area / allowed)


def _raceway_conductors(
    rack: dict, role_sizes: dict[str, str]
) -> list[tuple[str, str, int]]:
    return [(role, role_sizes[role], int(count))
            for role, count in rack.items() if int(count) > 0]


def size_by_raceway(
    raceways: list[dict],
    role_sizes: dict[str, str],
    conduit_type: str,
    insulation: str,
) -> list[FillResult]:
    """Pick the smallest trade size that fits each raceway spec."""
    return [size_conduit(_raceway_conductors(r, role_sizes), conduit_type, insulation)
            for r in raceways]


def check_by_raceway(
    raceways: list[dict],
    role_sizes: dict[str, str],
    conduit_type: str,
    trade_size: str,
    insulation: str,
) -> list[FillResult]:
    return [check_conduit(_raceway_conductors(r, role_sizes),
                          conduit_type, trade_size, insulation)
            for r in raceways]
