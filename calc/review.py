"""Review mode: compare an as-built installation against NEC minimums
and the design recommendation.

Each check emits a CheckResult so the CLI can render a table and set an
exit code.  FAIL means an NEC violation; WARN means within-code but
outside the designer-supplied advisory (e.g. voltage drop above target).
"""

from dataclasses import dataclass, field
from math import acos, cos, sin

from calc.configurations import CONFIGS
from calc.fill import check_conduit, check_by_raceway
from calc.load import design_current
from calc.sizing import (
    PhaseResult,
    check_phase,
    recommend_phase,
    size_egc,
    size_grounded,
)
from calc.vdrop import vdrop_ac, vdrop_dc
from nec_data import sizes
from nec_data.ocpd import next_standard


@dataclass
class CheckResult:
    label: str
    status: str            # PASS | FAIL | WARN
    recommended: str
    as_built: str
    detail: str
    nec_ref: str


@dataclass
class ReviewReport:
    checks: list[CheckResult] = field(default_factory=list)
    recommendation: dict = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return any(c.status == "FAIL" for c in self.checks)


def _ccc_count(cfg: dict, neutral_is_ccc: bool) -> int:
    n = cfg["phases"]
    if cfg["neutral"] and neutral_is_ccc:
        n += 1
    return n


def _vdrop(job: dict, cfg: dict, size: str, sets: int) -> tuple[float, float]:
    load_i = job["rla_amps"]
    if cfg["kind"] == "ac":
        vd = vdrop_ac(
            current_amps=load_i,
            length_ft=job["length_ft"],
            size=size,
            sets=sets,
            material=job["material"],
            raceway_magnetic=job.get("raceway_magnetic", "magnetic"),
            factor=cfg["vdrop_factor"],
            pf=float(job.get("power_factor", 0.9)),
        )
    else:
        vd = vdrop_dc(
            current_amps=load_i,
            length_ft=job["length_ft"],
            size=size,
            sets=sets,
            material=job["material"],
        )
    return vd, 100 * vd / job["voltage"]


def review(job: dict) -> ReviewReport:
    cfg = CONFIGS[job["configuration"]]
    ab = job.get("as_built") or {}
    if not ab:
        raise ValueError("review mode requires an 'as_built' block in the job file.")

    design_i = design_current(job["rla_amps"], job.get("continuous", True))
    ocpd = next_standard(design_i)
    neutral_is_ccc = bool(ab.get("neutral_is_ccc", job.get("neutral_is_ccc", False)))
    ccc = _ccc_count(cfg, neutral_is_ccc)

    rec_phase = recommend_phase(
        design_i=design_i,
        material=job["material"],
        termination_temp_c=int(job["conductor_temp_c"]),
        ambient_c=float(job["ambient_c"]),
        ccc_count=ccc,
    )
    rec_egc = size_egc(design_i, job["material"])
    rec_neutral = size_grounded(rec_phase.size, job["material"]) if cfg["neutral"] else None

    ab_phase_size = ab.get("phase_size", rec_phase.size)
    ab_phase_sets = int(ab.get("phase_sets", rec_phase.sets))
    ab_neutral = ab.get("neutral_size", rec_neutral)
    ab_egc = ab.get("egc_size", rec_egc)
    ab_conduit_type = ab.get("conduit_type", job["conduit_type"])
    ab_trade_size = ab.get("conduit_trade_size")
    ab_conduit_count = int(ab.get("conduit_count", 1))
    ab_insulation = ab.get("insulation", job["insulation"])

    checks: list[CheckResult] = []

    ab_phase = check_phase(
        size=ab_phase_size,
        sets=ab_phase_sets,
        design_i=design_i,
        material=job["material"],
        termination_temp_c=int(job["conductor_temp_c"]),
        ambient_c=float(job["ambient_c"]),
        ccc_count=ccc,
    )
    checks.append(CheckResult(
        label="Phase ampacity",
        status="PASS" if ab_phase.ampacity_derated >= design_i else "FAIL",
        recommended=f"{rec_phase.ampacity_derated:.0f} A",
        as_built=f"{ab_phase.ampacity_derated:.0f} A",
        detail=f"design current {design_i:.0f} A",
        nec_ref="310.16 + 310.15",
    ))
    checks.append(CheckResult(
        label="Phase size",
        status="PASS" if sizes.ge(ab_phase_size, rec_phase.size) else "FAIL",
        recommended=f"({rec_phase.sets}) x {rec_phase.size}",
        as_built=f"({ab_phase_sets}) x {ab_phase_size}",
        detail="as-built smaller than recommendation" if not sizes.ge(ab_phase_size, rec_phase.size) else "",
        nec_ref="310.16",
    ))
    if ab_phase_sets > 1:
        ok = sizes.ge(ab_phase_size, sizes.MIN_PARALLEL_SIZE)
        checks.append(CheckResult(
            label="Parallel min size",
            status="PASS" if ok else "FAIL",
            recommended=f">= {sizes.MIN_PARALLEL_SIZE}",
            as_built=ab_phase_size,
            detail="paralleled conductors must be 1/0 AWG or larger",
            nec_ref="310.10(G)(1)",
        ))

    if cfg["neutral"]:
        ok = sizes.ge(ab_neutral, rec_neutral)
        checks.append(CheckResult(
            label="Neutral / grounded",
            status="PASS" if ok else "FAIL",
            recommended=rec_neutral,
            as_built=ab_neutral,
            detail="min per phase size" if not ok else "",
            nec_ref="250.102(C)(1)",
        ))

    if cfg["egc"]:
        ok = sizes.ge(ab_egc, rec_egc)
        checks.append(CheckResult(
            label="EGC",
            status="PASS" if ok else "FAIL",
            recommended=rec_egc,
            as_built=ab_egc,
            detail=f"per {ocpd} A OCPD",
            nec_ref="250.122",
        ))

    conductors = [("phase", ab_phase_size, cfg["phases"])]
    if ab_neutral:
        conductors.append(("neutral", ab_neutral, 1))
    if cfg["egc"]:
        conductors.append(("egc", ab_egc, 1))

    ab_raceways = ab.get("raceways") or job.get("raceways")
    if ab_raceways and ab_trade_size:
        role_sizes = {"phase": ab_phase_size,
                      "neutral": ab_neutral or "",
                      "egc": ab_egc}
        fills = check_by_raceway(ab_raceways, role_sizes,
                                 ab_conduit_type, ab_trade_size, ab_insulation)
        for rack, fill in zip(ab_raceways, fills):
            status = "PASS" if fill.total_area_in2 <= fill.allowed_area_in2 else "FAIL"
            roles = ", ".join(f"{k}:{v}" for k, v in rack.items())
            checks.append(CheckResult(
                label="Conduit fill",
                status=status,
                recommended="<= 100% allowed",
                as_built=f"{fill.fill_pct:.1f}% of allowed",
                detail=f"{fill.total_area_in2:.3f} in^2 vs {fill.allowed_area_in2:.3f} in^2 "
                       f"({ab_trade_size} {ab_conduit_type}: {roles})",
                nec_ref="Ch 9 Table 1 Notes",
            ))
    elif ab_trade_size:
        if ab_conduit_count > 1 and ab_phase_sets == ab_conduit_count:
            per_conduit = conductors
        else:
            per_conduit = [(r, s, c * ab_phase_sets if r == "phase" else c)
                           for (r, s, c) in conductors]
        fill = check_conduit(per_conduit, ab_conduit_type, ab_trade_size, ab_insulation)
        status = "PASS" if fill.total_area_in2 <= fill.allowed_area_in2 else "FAIL"
        checks.append(CheckResult(
            label="Conduit fill",
            status=status,
            recommended="<= 100% allowed",
            as_built=f"{fill.fill_pct:.1f}% of allowed",
            detail=f"{fill.total_area_in2:.3f} in^2 vs {fill.allowed_area_in2:.3f} in^2 "
                   f"({ab_conduit_count}x {ab_trade_size} {ab_conduit_type})",
            nec_ref="Ch 9 Table 1 Notes",
        ))

    vd, vd_pct = _vdrop(job, cfg, ab_phase_size, ab_phase_sets)
    limit = job.get("max_vdrop_pct")
    if limit is None:
        vd_status = "PASS"
        vd_detail = "no advisory limit set"
    elif vd_pct <= limit:
        vd_status = "PASS"
        vd_detail = f"under {limit}% advisory"
    else:
        vd_status = "WARN"
        vd_detail = f"exceeds {limit}% advisory (NEC informational only)"
    _, rec_vd_pct = _vdrop(job, cfg, rec_phase.size, rec_phase.sets)
    checks.append(CheckResult(
        label="Voltage drop",
        status=vd_status,
        recommended=f"{rec_vd_pct:.2f}%",
        as_built=f"{vd_pct:.2f}%  ({vd:.2f} V)",
        detail=vd_detail,
        nec_ref="Ch 9 Table 9 / 210.19 IN",
    ))

    return ReviewReport(
        checks=checks,
        recommendation={
            "phase": rec_phase,
            "neutral": rec_neutral,
            "egc": rec_egc,
            "ocpd": ocpd,
            "design_i": design_i,
        },
    )
