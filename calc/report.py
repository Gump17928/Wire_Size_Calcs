"""Show-your-work reporting layer.

Every calc stage is turned into typed rows on a `Trace` (see calc/trace.py):
input / lookup / calc rows carry a variable name and go into the trace's
symbol table; `calc` rows evaluate their equation from earlier names, so the
equation, the substituted numbers and the result cannot drift apart.

Section builders therefore have to be called in dependency order (load,
ambient, CCC, phase, fill, voltage drop), and a later section reads values
such as I_RLA, V_nom, F_amb, F_ccc and N_sets from the trace instead of
taking them as arguments.  The sizing decisions themselves still come from
the calc layer, which stays pure.
"""

from __future__ import annotations

from math import sqrt

from calc.fill import FillResult
from calc.sizing import PhaseResult
from calc.trace import HEADER_MARK, CalcStep, Trace
from nec_data import ambient_derate, ccc_derate
from nec_data.conductor_dims import COND_AREA_IN2
from nec_data.conduit_dims import CONDUIT
from nec_data.dc_resistance import R_DC
from nec_data.impedance import R_AC, X_AC
from nec_data.ocpd import next_standard

__all__ = ["HEADER_MARK", "CalcStep", "Trace"]


# ---------------------------------------------------------------------------
# Section builders.  Each returns any downstream values the caller needs so
# the same trace ordering matches the calc order in wiresize.py / review.
# ---------------------------------------------------------------------------

def report_load(t: Trace, rla: float, continuous: bool, voltage: float,
                config_key: str, cfg_notes: str) -> tuple[float, int]:
    t.header("LOAD")
    t.add("LOAD", "Configuration", config_key, source=cfg_notes)
    t.input("LOAD", "V_nom", voltage, "V", label="Nominal voltage")
    t.input("LOAD", "I_RLA", rla, "A", label="Running current", fmt=".2f")
    t.lookup("LOAD", "k_cont", 1.25 if continuous else 1.0, label="Continuous factor", fmt=".2f",
             equation="k_cont = 1.25 if continuous else 1.00",
             substituted=f"continuous = {continuous}",
             nec_ref="NEC 210.19(A)(1) / 215.2(A)(1)")
    design_i = t.calc("LOAD", "I_design", "I_RLA * k_cont", "A", label="Design current",
                      nec_ref="NEC 210.19(A)(1) / 215.2(A)(1)")
    ocpd = next_standard(design_i)
    t.lookup("LOAD", "OCPD", ocpd, "A", label="OCPD rating",
             equation="OCPD = next_std(I_design)",
             substituted=f"OCPD = next_std({t.shown['I_design']}) = {ocpd}",
             nec_ref="NEC 240.6(A)",
             source="lowest standard OCPD >= I_design")
    return design_i, ocpd


def report_ambient(t: Trace, term_temp: int, ambient_c: float) -> None:
    table = ambient_derate.AMBIENT[term_temp]
    lo = hi = 0
    fa = 1.0
    for (rlo, rhi), f in table.items():
        if rlo <= ambient_c < rhi:
            lo, hi, fa = rlo, rhi, f
            break
    else:
        raise ValueError(f"Ambient {ambient_c} C outside any tabulated range.")
    t.lookup("AMPACITY", "F_amb", fa, label="Ambient factor", fmt=".2f",
             equation="F_amb from Table 310.15(B)(1)(1)",
             substituted=f"ambient {ambient_c:g} C in [{lo},{hi}) C -> F_amb = {fa:.2f}",
             nec_ref="NEC Table 310.15(B)(1)(1)",
             source=f"column: {term_temp} C insulation rating")


def report_ccc(t: Trace, ccc_count: int, label_suffix: str = "") -> None:
    f = ccc_derate.factor_for(ccc_count)
    t.lookup("AMPACITY", "F_ccc", f, label=f"CCC factor{label_suffix}", fmt=".2f",
             equation="F_ccc from Table 310.15(C)(1)",
             substituted=f"CCC = {ccc_count} -> F_ccc = {f:.2f}",
             nec_ref="NEC Table 310.15(C)(1)",
             source=f"current-carrying conductor count = {ccc_count}")


def report_ccc_context(t: Trace, job: dict, cfg: dict, phase_sets: int,
                       neutral_is_ccc: bool) -> int:
    """Report the CCC count derivation and return the count used for sizing.

    When a `raceways:` block is present the count is the worst-case (max)
    per raceway; otherwise it is phase count * sets + optional neutral.
    """
    naive = cfg["phases"] * phase_sets + (phase_sets if (cfg["neutral"] and neutral_is_ccc) else 0)
    t.lookup("AMPACITY", "CCC_naive", naive, label="CCC count (single-raceway assumption)",
             equation="CCC_naive = phases * N_sets + (N_sets if neutral_is_ccc else 0)",
             substituted=f"CCC_naive = {cfg['phases']} * {phase_sets} + "
                         f"{phase_sets if (cfg['neutral'] and neutral_is_ccc) else 0}",
             nec_ref="NEC 310.15(E) (neutral counting)",
             source=f"phases={cfg['phases']}, sets={phase_sets}, "
                    f"neutral_is_ccc={neutral_is_ccc}")

    racks = job.get("raceways") or (job.get("as_built") or {}).get("raceways")
    if not racks:
        return naive

    per_rw = []
    worst = 0
    for i, r in enumerate(racks, 1):
        c = int(r.get("phase", 0))
        if neutral_is_ccc:
            c += int(r.get("neutral", 0))
        per_rw.append(f"rw#{i}={c}")
        worst = max(worst, c)
    worst = max(worst, 1)
    t.add("AMPACITY", "CCC count per raceway", ", ".join(per_rw), "",
          equation="CCC_rw = phase_rw + (neutral_rw if neutral_is_ccc else 0)",
          substituted=f"per-raceway CCCs = {per_rw}",
          nec_ref="NEC 310.15(C)(1)",
          source="each raceway derated independently")
    t.lookup("AMPACITY", "CCC", worst, label="CCC count (used for sizing)",
             equation="CCC = max over raceways of CCC_rw",
             substituted=f"CCC = max({', '.join(str(x) for x in [int(r.get('phase',0)) + (int(r.get('neutral',0)) if neutral_is_ccc else 0) for r in racks])}) = {worst}",
             nec_ref="NEC 310.15(C)(1)",
             source="worst raceway drives ampacity")
    return worst


def report_phase(t: Trace, pr: PhaseResult, design_i: float,
                 material: str, term_temp: int, ambient_c: float,
                 label_suffix: str = "") -> None:
    """Needs I_design, F_amb and F_ccc already in the trace."""
    t.header(f"AMPACITY {label_suffix}".strip())
    t.add("AMPACITY", "Selected size", pr.size, "AWG/kcmil",
          equation="smallest size where derated ampacity >= I_design",
          substituted=f"{pr.sets} set(s) x {pr.size} {material}",
          nec_ref="NEC 310.16 + 310.14 + 310.10(G)",
          source=f"insulation column: {term_temp} C, material: {material}")
    t.lookup("AMPACITY", "N_sets", pr.sets, label="Parallel sets",
             equation="N_sets from sizing", nec_ref="NEC 310.10(G)")
    t.lookup("AMPACITY", "I_base", pr.ampacity_base, "A", label="Base ampacity", fmt=".1f",
             equation="I_base = Table 310.16 lookup",
             substituted=f"I_base = 310.16[{material}][{pr.size}][{term_temp}C] = {pr.ampacity_base:.1f}",
             nec_ref="NEC Table 310.16",
             source=f"{material}, {pr.size}, {term_temp} C column, ambient 30 C reference")
    t.calc("AMPACITY", "I_amp_per", "I_base * F_amb * F_ccc", "A", label="Derated ampacity per conductor",
           nec_ref="NEC 310.15")
    total = t.calc("AMPACITY", "I_amp_total", "I_amp_per * N_sets", "A", label="Ampacity total",
                   nec_ref="NEC 310.10(G)")
    t.add("AMPACITY", "Ampacity check", f"{total:.2f} >= {design_i:.2f}", "A",
          equation="I_amp_total >= I_design",
          substituted=f"{total:.2f} A >= {design_i:.2f} A",
          nec_ref="NEC 310.14",
          status="PASS" if total >= design_i else "FAIL", kind="check")


def report_neutral(t: Trace, phase_size: str, neutral_size: str,
                   material: str) -> None:
    t.header("NEUTRAL / GROUNDED CONDUCTOR")
    t.add("NEUTRAL", "Neutral size", neutral_size, "AWG/kcmil",
          equation="lookup Table 250.102(C)(1) by phase size",
          substituted=f"250.102(C)(1)[{material}][phase={phase_size}] = {neutral_size}",
          nec_ref="NEC Table 250.102(C)(1)",
          source=f"phase conductor = {phase_size} {material}")


def report_egc(t: Trace, egc_size: str, material: str, ocpd: int) -> None:
    t.header("EQUIPMENT GROUNDING CONDUCTOR")
    t.add("EGC", "EGC size", egc_size, "AWG/kcmil",
          equation="lookup Table 250.122 by OCPD rating",
          substituted=f"250.122[{material}][OCPD>={ocpd}] = {egc_size}",
          nec_ref="NEC Table 250.122",
          source=f"OCPD = {ocpd} A, {material}")


def report_fill(t: Trace, raceway_idx: int,
                conductors: list[tuple[str, str, int]],
                fr: FillResult, conduit_type: str, insulation: str,
                suffix: str = "") -> None:
    """`suffix` is appended to every variable name so several raceways can share one trace (e.g. '_rw2')."""
    s = suffix
    trade = fr.trade_size
    n_cond = sum(c for _, _, c in conductors)
    if n_cond == 1:
        limit_pct, note = 53, "1 conductor -> 53%"
    elif n_cond == 2:
        limit_pct, note = 31, "2 conductors -> 31%"
    else:
        limit_pct, note = 40, "> 2 conductors -> 40%"
    a_int = CONDUIT[conduit_type][trade]["area_100"]

    t.header(f"CONDUIT FILL - raceway #{raceway_idx}: {trade}\" {conduit_type}")
    role_summary = ", ".join(f"{r}:{c}" for r, _s, c in conductors)
    t.add("FILL", "Contents", role_summary, "",
          source=f"insulation: {insulation}")
    for role, size, count in conductors:
        t.lookup("FILL", f"A_each_{role}{s}", COND_AREA_IN2[insulation][size], "in^2",
                 label=f"{role} {size} area per conductor", fmt=".4f",
                 equation=f"A_each_{role} = Table 5 lookup",
                 nec_ref="NEC Ch 9 Table 5", source=f"{insulation}, {size}")
        t.lookup("FILL", f"n_{role}{s}", count, label=f"{role} conductor count",
                 equation=f"n_{role} from raceway contents")
        t.calc("FILL", f"A_{role}{s}", f"A_each_{role}{s} * n_{role}{s}", "in^2",
               label=f"{role} {size} total area", fmt=".4f", nec_ref="NEC Ch 9 Table 5")
    a_cond = t.calc("FILL", f"A_cond{s}", " + ".join(f"A_{role}{s}" for role, _z, _n in conductors), "in^2",
                    label="Total conductor area", fmt=".4f", nec_ref="NEC Ch 9, Notes to Tables")
    t.lookup("FILL", f"A_int{s}", a_int, "in^2", label="Raceway internal area", fmt=".3f",
             equation="A_int = Table 4 lookup (100% column)",
             substituted=f"A_int = Table4[{conduit_type}][{trade}] = {a_int:.3f}",
             nec_ref="NEC Ch 9 Table 4",
             source=f"{conduit_type} trade size {trade}\"")
    t.lookup("FILL", f"f_limit_pct{s}", limit_pct, "%", label="NEC fill limit",
             equation="f_limit_pct from Ch 9 Table 1",
             substituted=note,
             nec_ref="NEC Ch 9 Table 1",
             source=f"total conductor count = {n_cond}")
    a_allow = t.calc("FILL", f"A_allow{s}", f"A_int{s} * f_limit_pct{s} / 100", "in^2",
                     label="Allowed conductor area", fmt=".4f", nec_ref="NEC Ch 9 Table 1")
    t.calc("FILL", f"f_raceway_pct{s}", f"100 * A_cond{s} / A_int{s}", "%",
           label="Fill of raceway", source="informational (fraction of physical raceway used)")
    t.calc("FILL", f"f_allowed_pct{s}", f"100 * A_cond{s} / A_allow{s}", "%",
           label="Fill of allowed", source="informational (fraction of NEC limit used)")
    t.add("FILL", "Fill check", f"{a_cond:.4f} <= {a_allow:.4f}", "in^2",
          equation=f"pass if A_cond{s} <= A_allow{s}",
          substituted=f"{a_cond:.4f} <= {a_allow:.4f} ?",
          nec_ref="NEC Ch 9 Table 1",
          status="PASS" if a_cond <= a_allow else "FAIL", kind="check")


def report_vdrop(t: Trace, cfg: dict, length_ft: float, size: str, material: str,
                 raceway_magnetic: str, pf: float, limit_pct: float | None) -> tuple[float, float]:
    """Needs I_RLA, V_nom and N_sets already in the trace.

    R and X are per 1000 ft, so the length is entered in units of 1000 ft (L_kft).  That keeps the equations
    free of a stray `/ 1000` and makes the units work out to volts when Mathcad evaluates them.
    """
    t.header("VOLTAGE DROP")
    kind = cfg["kind"]
    k = cfg["vdrop_factor"]

    t.input("VDROP", "L_kft", length_ft / 1000.0, "1000ft", label="Circuit length in units of 1000 ft",
            source=f"circuit length = {length_ft:g} ft")

    if kind == "ac":
        three_phase = abs(k - sqrt(3)) < 1e-3
        t.lookup("VDROP", "k", k, label="Formula factor", fmt=".4f",
                 equation="k = sqrt(3)" if three_phase else f"k = {k:g}",
                 substituted=f"config kind = {kind}",
                 nec_ref="Ch 9 Table 9 (formula)",
                 source="sqrt(3) for 3-phase; 2 for 1-phase")
        r_per_1k = R_AC[material][raceway_magnetic][size]
        x_per_1k = X_AC[raceway_magnetic][size]
        t.lookup("VDROP", "R", r_per_1k, "ohm/1000ft", label="R per 1000 ft", fmt=".4f",
                 equation="R = Table 9 lookup",
                 substituted=f"R = Ch9Tbl9[{material}][{raceway_magnetic}][{size}] = {r_per_1k:.4f}",
                 nec_ref="NEC Ch 9 Table 9",
                 source=f"{material} in {raceway_magnetic} raceway, size {size}")
        t.lookup("VDROP", "X", x_per_1k, "ohm/1000ft", label="X per 1000 ft", fmt=".4f",
                 equation="X = Table 9 lookup",
                 substituted=f"X = Ch9Tbl9[XL][{raceway_magnetic}][{size}] = {x_per_1k:.4f}",
                 nec_ref="NEC Ch 9 Table 9",
                 source=f"{raceway_magnetic} raceway, size {size}")
        t.calc("VDROP", "R_eff", "R / N_sets", "ohm/1000ft", label="R effective (parallel sets)",
               fmt=".4f", nec_ref="NEC 310.10(G)")
        t.calc("VDROP", "X_eff", "X / N_sets", "ohm/1000ft", label="X effective (parallel sets)",
               fmt=".4f", nec_ref="NEC 310.10(G)")
        t.input("VDROP", "pf", pf, label="Power factor", fmt=".2f")
        t.calc("VDROP", "theta", "acos(pf)", "rad", label="Load angle", fmt=".4f")
        t.calc("VDROP", "cos_th", "cos(theta)", label="cos(theta)", fmt=".4f")
        t.calc("VDROP", "sin_th", "sin(theta)", label="sin(theta)", fmt=".4f")
        vd = t.calc("VDROP", "Vd", "k * I_RLA * (R_eff * cos_th + X_eff * sin_th) * L_kft", "V",
                    label="Voltage drop", fmt=".3f", nec_ref="NEC Ch 9 Table 9 (formula)")
    else:
        r_per_1k = R_DC[material]["stranded"][size]
        t.lookup("VDROP", "R", r_per_1k, "ohm/1000ft", label="R per 1000 ft (DC)", fmt=".4f",
                 equation="R = Table 8 lookup",
                 substituted=f"R = Ch9Tbl8[{material}][stranded][{size}] = {r_per_1k:.4f}",
                 nec_ref="NEC Ch 9 Table 8",
                 source=f"{material} stranded, size {size}")
        t.calc("VDROP", "R_eff", "R / N_sets", "ohm/1000ft", label="R effective (parallel sets)",
               fmt=".4f", nec_ref="NEC 310.10(G)")
        vd = t.calc("VDROP", "Vd", "2 * I_RLA * R_eff * L_kft", "V", label="Voltage drop", fmt=".3f",
                    nec_ref="NEC Ch 9 Table 8 (formula)")

    t.calc("VDROP", "Vd_pct", "100 * Vd / V_nom", "%", label="Voltage drop percent",
           nec_ref="NEC 210.19 IN (informational)",
           source=("no advisory limit set" if limit_pct is None
                   else f"advisory limit = {limit_pct} %"),
           status=lambda pct: "" if limit_pct is None else ("PASS" if pct <= limit_pct else "WARN"))
    return vd, t.symbols["Vd_pct"]


def report_comparison(t: Trace, checks: list) -> None:
    """Append a comparison table to the trace (used by review mode)."""
    t.header("COMPARISON (as-built vs. NEC + recommendation)")
    for c in checks:
        t.add("COMPARE", c.label, f"as-built = {c.as_built}", "",
              substituted=c.detail,
              nec_ref=c.nec_ref,
              source=f"recommended = {c.recommended}",
              status=c.status, kind="check")
