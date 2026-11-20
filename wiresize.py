"""CLI entry point: python wiresize.py <job.yaml>

Every run prints a full step-by-step analysis and writes a matching CSV
to <output_dir>/<job basename>.csv (default output_dir: output/).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from calc.configurations import CONFIGS
from calc.fill import size_by_raceway, size_conduit, check_by_raceway, check_conduit
from calc.load import design_current
from calc.report import (
    Trace,
    report_ambient,
    report_ccc,
    report_ccc_context,
    report_comparison,
    report_egc,
    report_fill,
    report_load,
    report_neutral,
    report_phase,
    report_vdrop,
)
from calc.review import review
from calc.sizing import (
    check_phase,
    recommend_phase,
    size_egc,
    size_grounded,
)
from nec_data.ocpd import next_standard


def _load_job(path: Path) -> dict:
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.exit("PyYAML is required for YAML jobs.  pip install pyyaml")
        return yaml.safe_load(text)
    return json.loads(text)


def _out_csv_path(job: dict, job_path: Path, suffix: str = "") -> Path | None:
    if job.get("output_csv") is False:
        return None
    out_dir = Path(job.get("output_dir", "output"))
    stem = f"{job_path.stem}.{suffix}" if suffix else job_path.stem
    return out_dir / f"{stem}.csv"


def _pick_raceways_for_design(job: dict, phase, conductors):
    """Return (raceway_specs_or_None, list_of_conductor_lists, fill_results).

    Mirrors the old behaviour: explicit raceways: block wins, then
    one_set_per_conduit, else everything shares a single raceway.
    """
    ct, ins = job["conduit_type"], job["insulation"]
    racks = job.get("raceways")
    if racks:
        role_sizes = {"phase": phase.size,
                      "neutral": conductors[1][1] if len(conductors) > 1 and conductors[1][0] == "neutral" else "",
                      "egc": conductors[-1][1] if conductors[-1][0] == "egc" else ""}
        fills = size_by_raceway(racks, role_sizes, ct, ins)
        cond_lists = [
            [(role, role_sizes[role], int(cnt))
             for role, cnt in r.items() if int(cnt) > 0]
            for r in racks
        ]
        return racks, cond_lists, fills
    if job.get("one_set_per_conduit") and phase.sets > 1:
        fill = size_conduit(conductors, ct, ins)
        return None, [conductors] * phase.sets, [fill] * phase.sets
    multi = [(r, s, c * phase.sets if r == "phase" else c)
             for (r, s, c) in conductors]
    fill = size_conduit(multi, ct, ins)
    return None, [multi], [fill]


def _raceway_suffix(index: int, count: int) -> str:
    """Variable-name suffix that keeps the fill variables of several raceways apart in one trace."""
    return f"_rw{index}" if count > 1 else ""


def _build_design_trace(t: Trace, job: dict, label_suffix: str = "") -> dict:
    """Emit the full design pipeline into `t` and return chosen sizes."""
    cfg = CONFIGS[job["configuration"]]
    design_i, ocpd = report_load(
        t, job["rla_amps"], job.get("continuous", True),
        job["voltage"], job["configuration"], cfg["notes"],
    )

    t.header(f"AMPACITY - phase sizing {label_suffix}".strip())
    term_temp = int(job["conductor_temp_c"])
    report_ambient(t, term_temp, float(job["ambient_c"]))
    neutral_is_ccc = bool(job.get("neutral_is_ccc", False))
    ccc = report_ccc_context(t, job, cfg, phase_sets=1,
                             neutral_is_ccc=neutral_is_ccc)
    report_ccc(t, ccc)

    phase = recommend_phase(
        design_i=design_i,
        material=job["material"],
        termination_temp_c=term_temp,
        ambient_c=float(job["ambient_c"]),
        ccc_count=ccc,
    )
    report_phase(t, phase, design_i, job["material"], term_temp,
                 float(job["ambient_c"]), label_suffix=label_suffix)

    egc = size_egc(design_i, job["material"])
    neutral = size_grounded(phase.size, job["material"]) if cfg["neutral"] else None
    if neutral:
        report_neutral(t, phase.size, neutral, job["material"])
    if cfg["egc"]:
        report_egc(t, egc, job["material"], ocpd)

    conductors = [("phase", phase.size, cfg["phases"])]
    if neutral:
        conductors.append(("neutral", neutral, 1))
    if cfg["egc"]:
        conductors.append(("egc", egc, 1))

    racks, cond_lists, fills = _pick_raceways_for_design(job, phase, conductors)
    for i, (cl, f) in enumerate(zip(cond_lists, fills), 1):
        report_fill(t, i, cl, f, job["conduit_type"], job["insulation"],
                    suffix=_raceway_suffix(i, len(cond_lists)))

    report_vdrop(
        t, cfg, job["length_ft"], phase.size, job["material"],
        job.get("raceway_magnetic", "magnetic"),
        float(job.get("power_factor", 0.9)),
        job.get("max_vdrop_pct"),
    )
    return {"phase": phase, "neutral": neutral, "egc": egc,
            "design_i": design_i, "ocpd": ocpd}


def _build_asbuilt_trace(t: Trace, job: dict) -> None:
    """Emit an as-built analysis mirroring the design trace."""
    cfg = CONFIGS[job["configuration"]]
    ab = job.get("as_built") or {}

    t.header("AS-BUILT ANALYSIS")

    design_i, ocpd = report_load(
        t, job["rla_amps"], job.get("continuous", True),
        job["voltage"], job["configuration"], cfg["notes"],
    )

    # We still need a design recommendation to fill in gaps for size defaults.
    neutral_is_ccc = bool(ab.get("neutral_is_ccc",
                                 job.get("neutral_is_ccc", False)))
    term_temp = int(job["conductor_temp_c"])

    report_ambient(t, term_temp, float(job["ambient_c"]))
    ccc = report_ccc_context(t, job, cfg,
                             phase_sets=int(ab.get("phase_sets", 1)),
                             neutral_is_ccc=neutral_is_ccc)
    report_ccc(t, ccc)

    # Need a phase size to describe as-built; fall back to design if missing.
    rec_phase = recommend_phase(
        design_i=design_i, material=job["material"],
        termination_temp_c=term_temp,
        ambient_c=float(job["ambient_c"]), ccc_count=ccc,
    )
    rec_neutral = size_grounded(rec_phase.size, job["material"]) if cfg["neutral"] else None
    rec_egc = size_egc(design_i, job["material"])

    ab_phase_size = ab.get("phase_size", rec_phase.size)
    ab_phase_sets = int(ab.get("phase_sets", rec_phase.sets))
    ab_neutral = ab.get("neutral_size", rec_neutral)
    ab_egc = ab.get("egc_size", rec_egc)
    ab_ct = ab.get("conduit_type", job["conduit_type"])
    ab_trade = ab.get("conduit_trade_size")
    ab_ins = ab.get("insulation", job["insulation"])

    ab_phase = check_phase(
        size=ab_phase_size, sets=ab_phase_sets,
        design_i=design_i, material=job["material"],
        termination_temp_c=term_temp,
        ambient_c=float(job["ambient_c"]), ccc_count=ccc,
    )
    report_phase(t, ab_phase, design_i, job["material"], term_temp,
                 float(job["ambient_c"]), label_suffix="(as-built)")

    if cfg["neutral"]:
        report_neutral(t, ab_phase_size, ab_neutral, job["material"])
    if cfg["egc"]:
        report_egc(t, ab_egc, job["material"], ocpd)

    conductors = [("phase", ab_phase_size, cfg["phases"])]
    if ab_neutral:
        conductors.append(("neutral", ab_neutral, 1))
    if cfg["egc"]:
        conductors.append(("egc", ab_egc, 1))

    ab_racks = ab.get("raceways") or job.get("raceways")
    if ab_racks and ab_trade:
        role_sizes = {"phase": ab_phase_size,
                      "neutral": ab_neutral or "",
                      "egc": ab_egc}
        fills = check_by_raceway(ab_racks, role_sizes, ab_ct, ab_trade, ab_ins)
        for i, (rack, f) in enumerate(zip(ab_racks, fills), 1):
            cl = [(role, role_sizes[role], int(cnt))
                  for role, cnt in rack.items() if int(cnt) > 0]
            report_fill(t, i, cl, f, ab_ct, ab_ins,
                        suffix=_raceway_suffix(i, len(ab_racks)))
    elif ab_trade:
        cnt = int(ab.get("conduit_count", 1))
        if cnt > 1 and ab_phase_sets == cnt:
            per = conductors
            n_pipes = cnt
        else:
            per = [(r, s, c * ab_phase_sets if r == "phase" else c)
                   for (r, s, c) in conductors]
            n_pipes = 1
        fill = check_conduit(per, ab_ct, ab_trade, ab_ins)
        for i in range(n_pipes):
            report_fill(t, i + 1, per, fill, ab_ct, ab_ins,
                        suffix=_raceway_suffix(i + 1, n_pipes))

    report_vdrop(
        t, cfg, job["length_ft"], ab_phase_size, job["material"],
        job.get("raceway_magnetic", "magnetic"),
        float(job.get("power_factor", 0.9)),
        job.get("max_vdrop_pct"),
    )


def _emit(t: Trace, job: dict, job_path: Path, suffix: str = "") -> None:
    print(t.render_terminal())
    out = _out_csv_path(job, job_path, suffix)
    if out:
        t.write_csv(out)
        print(f"\nCSV written: {out}")


def run_design(job: dict, job_path: Path) -> int:
    t = Trace(job_name=job_path.name, mode="design")
    _build_design_trace(t, job)
    _emit(t, job, job_path)
    return 0


def run_review(job: dict, job_path: Path) -> int:
    t_design = Trace(job_name=job_path.name, mode="design (recommendation)")
    t_design.header("DESIGN RECOMMENDATION (what NEC would prescribe)")
    _build_design_trace(t_design, job, label_suffix="(recommended)")

    t_review = Trace(job_name=job_path.name, mode="review (as-built)")
    _build_asbuilt_trace(t_review, job)
    report = review(job)
    report_comparison(t_review, report.checks)

    _emit(t_design, job, job_path, suffix="design")
    _emit(t_review, job, job_path, suffix="review")

    fails = sum(1 for c in report.checks if c.status == "FAIL")
    warns = sum(1 for c in report.checks if c.status == "WARN")
    verdict = "FAIL" if fails else ("WARN" if warns else "PASS")
    print(f"\nOverall: {verdict}  ({fails} failures, {warns} warnings)")
    return 1 if fails else 0


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python wiresize.py <job.yaml|job.json>")
    path = Path(sys.argv[1])
    job = _load_job(path)
    mode = (job.get("mode") or "design").lower()
    if mode == "review":
        sys.exit(run_review(job, path))
    sys.exit(run_design(job, path))


if __name__ == "__main__":
    main()
