"""Conductor sizing: apply derates, walk the size ladder, add parallel sets
when the single-conductor size exceeds the parallel threshold.

References:
    NEC 310.14 / 310.16          Ampacity selection
    NEC 310.15(B)(1)             Ambient correction
    NEC 310.15(C)(1)             CCC adjustment
    NEC 310.10(G)(1)             Parallel conductor rules (min 1/0)
    NEC 110.14(C)                Termination temperature limits
"""

from dataclasses import dataclass

from nec_data import ampacity, ambient_derate, ccc_derate, sizes
from nec_data.ocpd import next_standard
from nec_data.egc import EGC
from nec_data.grounded import GROUNDED_MIN


@dataclass
class PhaseResult:
    size: str
    sets: int
    ampacity_base: float
    ampacity_derated: float
    temp_col_used: int


def _ambient_factor(insulation_temp_c: int, ambient_c: float) -> float:
    table = ambient_derate.AMBIENT.get(insulation_temp_c)
    if not table:
        raise KeyError(
            f"ambient_derate.AMBIENT[{insulation_temp_c}] is empty - "
            "fill in NEC Table 310.15(B)(1)(1)."
        )
    for (lo, hi), factor in table.items():
        if lo <= ambient_c < hi:
            return factor
    raise ValueError(f"Ambient {ambient_c} C outside any tabulated range.")


def _lookup_ampacity(material: str, size: str, temp_col: int) -> float:
    row = ampacity.AMPACITY.get(material, {}).get(size)
    if not row:
        raise KeyError(
            f"ampacity.AMPACITY[{material!r}][{size!r}] is empty - "
            "fill in NEC Table 310.16."
        )
    if temp_col not in row:
        raise KeyError(
            f"ampacity.AMPACITY[{material!r}][{size!r}] missing {temp_col} C column."
        )
    return row[temp_col]


def recommend_phase(
    design_i: float,
    material: str,
    termination_temp_c: int,
    ambient_c: float,
    ccc_count: int,
    allow_parallel: bool = True,
) -> PhaseResult:
    """Pick the smallest conductor (and number of parallel sets) whose
    derated ampacity meets or exceeds `design_i`.
    """
    amb = _ambient_factor(termination_temp_c, ambient_c)
    ccc = ccc_derate.factor_for(ccc_count)
    parallel_at = sizes.index(sizes.PARALLEL_THRESHOLD)

    for size in sizes.SIZES:
        base = _lookup_ampacity(material, size, termination_temp_c)
        derated = base * amb * ccc
        if derated >= design_i:
            if sizes.index(size) > parallel_at and allow_parallel:
                break
            return PhaseResult(size, 1, base, derated, termination_temp_c)

    if not allow_parallel:
        raise ValueError("No single conductor size meets the load.")

    for sets in range(2, 11):
        per_set = design_i / sets
        for size in sizes.at_or_above(sizes.MIN_PARALLEL_SIZE):
            base = _lookup_ampacity(material, size, termination_temp_c)
            derated = base * amb * ccc
            if derated >= per_set:
                return PhaseResult(size, sets, base, derated, termination_temp_c)

    raise ValueError("Could not size phase conductor even with 10 parallel sets.")


size_phase = recommend_phase  # backward-compat alias


def check_phase(
    size: str,
    sets: int,
    design_i: float,
    material: str,
    termination_temp_c: int,
    ambient_c: float,
    ccc_count: int,
) -> PhaseResult:
    """Compute derated ampacity of an as-built phase conductor."""
    amb = _ambient_factor(termination_temp_c, ambient_c)
    ccc = ccc_derate.factor_for(ccc_count)
    base = _lookup_ampacity(material, size, termination_temp_c)
    derated = base * amb * ccc * sets
    return PhaseResult(size, sets, base, derated, termination_temp_c)


def size_egc(design_i: float, material: str) -> str:
    ocpd = next_standard(design_i)
    table = EGC.get(material, {})
    if not table:
        raise KeyError(
            f"egc.EGC[{material!r}] is empty - fill in NEC Table 250.122."
        )
    for rating in sorted(table):
        if rating >= ocpd:
            return table[rating]
    return table[max(table)]


def size_grounded(phase_size: str, material: str) -> str:
    table = GROUNDED_MIN.get(material, {})
    if not table:
        raise KeyError(
            f"grounded.GROUNDED_MIN[{material!r}] is empty - "
            "fill in NEC Table 250.102(C)(1)."
        )
    if phase_size not in table:
        raise KeyError(
            f"grounded.GROUNDED_MIN[{material!r}][{phase_size!r}] missing."
        )
    return table[phase_size]
