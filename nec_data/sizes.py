"""Ordered conductor size ladder used to walk 'next size up' decisions.
Small-to-large; parallel-only sizes (below 1/0) are excluded from the
parallel search per NEC 310.10(G)(1).
"""

# Standard AWG/kcmil labels smallest -> largest.
SIZES: list[str] = [
    "14", "12", "10", "8", "6", "4", "3", "2", "1",
    "1/0", "2/0", "3/0", "4/0",
    "250", "300", "350", "400", "500", "600", "700", "750",
    "800", "900", "1000", "1250", "1500", "1750", "2000",
]

# Minimum size that may be paralleled per NEC 310.10(G)(1).
MIN_PARALLEL_SIZE: str = "1/0"

# Cutoff above which the designer typically switches to parallel sets.
# (This is the value the user set as the "> 250 kcmil" threshold.)
PARALLEL_THRESHOLD: str = "250"


def index(size: str) -> int:
    return SIZES.index(size)


def at_or_above(size: str) -> list[str]:
    return SIZES[index(size):]


def ge(a: str, b: str) -> bool:
    """True if size `a` is at least as large as size `b` (by ladder index)."""
    return index(a) >= index(b)


def gt(a: str, b: str) -> bool:
    return index(a) > index(b)
