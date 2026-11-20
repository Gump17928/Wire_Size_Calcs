# Wire Size Calcs

Sizing / conduit-fill / voltage-drop helper aligned to **NEC (NFPA 70) 2023**.
Two modes:

- **`design`** — you give a load, it recommends conductor, neutral, EGC, conduit, and reports voltage drop.
- **`review`** — you give a load *plus* what is actually installed, it checks the install against NEC and against its own recommendation, and exits non-zero if anything fails.

All NEC lookup tables ship with placeholder values transcribed from NEC 2023 — **verify each cell against your bound copy before using for a real design**. Each module names the exact NEC table it maps to in a header comment.

## Layout

```
nec_data/                One module per NEC table (data only, no logic)
  ampacity.py                Table 310.16 (0-2000V, 3 CCC in raceway)
  ampacity_mv.py             Table 311.60(C) (MV, in raceway)
  conductor_dims.py          Chapter 9, Table 5 (insulated conductor areas)
  conduit_dims.py            Chapter 9, Table 4 (raceway fill area by trade)
  egc.py                     Table 250.122 (equipment grounding conductor)
  grounded.py                Table 250.102(C)(1) (grounded / neutral min size)
  impedance.py               Chapter 9, Table 9 (AC R and X per 1000 ft)
  dc_resistance.py           Chapter 9, Table 8 (DC resistance per 1000 ft)
  ambient_derate.py          Table 310.15(B)(1)(1) (ambient correction)
  ccc_derate.py              Table 310.15(C)(1) (adjustment for >3 CCCs)
  ocpd.py                    240.6(A) standard OCPD ratings
  sizes.py                   Ordered AWG/kcmil size ladder + comparators
calc/
  configurations.py          Delta / wye / split-phase / DC system definitions
  load.py                    RLA -> design current (125% continuous, etc.)
  sizing.py                  Recommend conductor size; check as-built ampacity
  vdrop.py                   Voltage drop using Table 9 (AC) or Table 8 (DC)
  fill.py                    Conduit fill per Chapter 9 (Tables 4 & 5)
  review.py                  Review-mode orchestrator (as-built vs NEC)
  report.py                  Section builders (LOAD, AMPACITY, FILL, VDROP, ...) that emit trace rows
  trace.py                   Typed trace: named variables, equation evaluator, terminal + CSV writers
wiresize.py                CLI entry point
jobs/
  example.yaml               Design-mode template
  review_example.yaml        Review-mode template
tests/
  test_trace.py              Trace rows, and the CSV contract with MathCAD_Template
```

## Usage

```powershell
python wiresize.py jobs\example.yaml           # design mode
python wiresize.py jobs\review_example.yaml    # review mode (exit 1 on FAIL)
python -m unittest discover -s tests           # run the tests
```

Mode is chosen by the `mode:` key in the job file; default is `design`.

## Job file inputs

### Common keys (both modes)b

| Key | Type | Purpose |
|---|---|---|
| `mode` | `design` \| `review` | Which pipeline to run. Default `design`. |
| `rla_amps` | number | Running load amps. |
| `length_ft` | number | One-way run length, feet. |
| `voltage` | number | System nominal voltage. L-L for 3-phase. |
| `configuration` | key | System type; see list below. |
| `continuous` | bool | Apply the 125% factor per NEC 210.19 / 215.2. Default `true`. |
| `ambient_c` | number | Raceway ambient temperature, °C. |
| `conductor_temp_c` | `60` \| `75` \| `90` | Termination rating per NEC 110.14(C). |
| `material` | `Cu` \| `Al` | Conductor material. |
| `insulation` | string | Must exist as a key in nec_data/conductor_dims.py (e.g. `THWN-2`, `XHHW-2`). |
| `conduit_type` | string | Must exist in nec_data/conduit_dims.py (e.g. `EMT`, `RMC`, `PVC-40`, `PVC-80`). |
| `raceway_magnetic` | `magnetic` \| `nonmagnetic` | Steel = magnetic; PVC/Al = nonmagnetic. Affects Table 9 reactance. |
| `power_factor` | number | AC voltage-drop only. Default `0.9`. |
| `max_vdrop_pct` | number | Advisory limit (NEC informational). Above this the report says `OVER LIMIT` (design) or `WARN` (review). |
| `neutral_is_ccc` | bool | Count the neutral as a current-carrying conductor per NEC 310.15(E). Default `false`. |
| `output_csv` | bool | If `false`, skip writing the per-step CSV. Default `true`. |
| `output_dir` | string | Directory for the CSV output. Default `"output"`. Created if it does not exist. |

### Optional: explicit raceway layout

Add a top-level `raceways:` list to say exactly what goes in each pipe. If omitted, everything shares one raceway (or one per parallel set when `one_set_per_conduit: true`). In review mode, `raceways:` may also live inside the `as_built:` block and overrides `conduit_count` for the fill check. Each list item is one raceway; supported roles are `phase`, `neutral`, `egc`.

```yaml
# Default: one big raceway
raceways:
  - {phase: 3, neutral: 1, egc: 1}

# One phase per conduit + a separate neutral pipe (4 raceways total)
raceways:
  - {phase: 1, egc: 1}
  - {phase: 1, egc: 1}
  - {phase: 1, egc: 1}
  - {neutral: 1, egc: 1}
```

**Warning:** Separating phases into individual **ferromagnetic** raceways (steel EMT/RMC) is prohibited for AC by NEC 300.3(B) / 300.20 because of induced currents in the raceway. Use nonmagnetic conduit (PVC, aluminum) if you route this way. The tool does not enforce this; it only reports fill.

### Worked example: three CCCs + one EGC in one conduit

A very common feeder / branch layout is **three current-carrying conductors and one equipment grounding conductor sharing a single raceway** (3-phase 3-wire delta or 3-wire wye, no neutral). The tool handles this natively — pick the matching configuration key and either let the default single-raceway layout stand or state it explicitly.

**Design mode** — let the tool size everything:

```yaml
mode: design
configuration: 3ph_delta_3w    # or 3ph_wye_3w — both have 3 CCCs, no neutral
rla_amps: 150
length_ft: 100
voltage: 480
continuous: true
ambient_c: 30
conductor_temp_c: 75
material: Cu
insulation: THWN-2
conduit_type: EMT
raceway_magnetic: magnetic
power_factor: 0.9
max_vdrop_pct: 3.0

# Optional but explicit; identical to the default for a no-neutral config:
raceways:
  - {phase: 3, egc: 1}
```

The `CCC count` row of the trace will read `3`, so the `F_ccc` derate is `1.00` (NEC Table 310.15(C)(1) only applies to more than 3 CCCs).

**Review mode** — check an as-built install of **(3) 2/0 phase + (1) #10 EGC** in one conduit:

```yaml
mode: review
configuration: 3ph_delta_3w
rla_amps: 150
length_ft: 100
voltage: 480
continuous: true
ambient_c: 30
conductor_temp_c: 75
material: Cu
insulation: THWN-2
conduit_type: EMT
raceway_magnetic: magnetic
power_factor: 0.9
max_vdrop_pct: 3.0

raceways:
  - {phase: 3, egc: 1}

as_built:
  phase_size: "2/0"          # quote — YAML would otherwise read 2/0 as a float divide
  phase_sets: 1
  egc_size: "10"
  conduit_trade_size: "1-1/4"
  conduit_count: 1
```

For a 150 A continuous load the tool reports 4 FAILs against this install: 2/0 Cu ampacity (175 A) is below the 187.5 A design current, phase is one size smaller than the recommended 3/0, #10 EGC is short of the #6 required by NEC Table 250.122 at a 200 A OCPD, and the conductors overrun the Table 1 fill limit of a 1-1/4" EMT (115% of allowed). Voltage drop passes at 0.61%. Bumping the conduit to at least 1-1/2" EMT resolves the fill FAIL; sizing the phase to 3/0 Cu and the EGC to #6 Cu clears the rest.

### Configuration keys

Defined in [calc/configurations.py](calc/configurations.py):

| Key | Description |
|---|---|
| `3ph_wye_4w` | 3-phase 4-wire wye (A, B, C, N + EGC) |
| `3ph_wye_3w` | 3-phase 3-wire wye, no neutral |
| `3ph_delta_3w` | 3-phase 3-wire delta |
| `3ph_hi_leg_delta_4w` | High-leg (red-leg) delta, 4-wire |
| `1ph_3w` | Split-phase 120/240 |
| `1ph_2w` | Single-phase 2-wire |
| `dc_2w` | DC 2-wire (uses Table 8) |

### Design-mode keys

| Key | Purpose |
|---|---|
| `one_set_per_conduit` | If `true` and the recommendation ends up paralleled, each parallel set gets its own raceway (a designer choice — NEC allows either). Default `false`. |

### Review-mode keys

| Key | Purpose |
|---|---|
| `as_built` | Block describing what is actually installed. Every field is optional — anything you omit falls back to the design recommendation, so partial reviews work (e.g. only check conduit fill). |

`as_built` sub-keys:

| Key | Purpose |
|---|---|
| `phase_size` | Installed phase conductor size (e.g. `"3/0"`, `"250"`). Quote it so YAML doesn't misparse. |
| `phase_sets` | Number of parallel sets actually installed. |
| `neutral_size` | Installed neutral / grounded conductor size. |
| `egc_size` | Installed equipment grounding conductor size. |
| `conduit_type` | Installed raceway type. Overrides the top-level `conduit_type` for the fill check. |
| `conduit_trade_size` | Installed trade size (e.g. `"2"`, `"1-1/4"`). Required to run the fill check; omit to skip it. |
| `conduit_count` | Number of raceways. If `phase_sets > 1` and `conduit_count == phase_sets`, the fill check assumes one set per raceway. Otherwise all conductors are treated as sharing a single raceway. |
| `insulation` | Installed insulation type. Overrides the top-level `insulation` for the fill check. |
| `neutral_is_ccc` | Override of the top-level flag for the CCC count in the review. |

## Outputs

Every run does two things:

1. Prints a **step-by-step "show your work" trace** to the terminal, ASCII-only, one section per calc stage (LOAD, AMPACITY, NEUTRAL, EGC, CONDUIT FILL, VOLTAGE DROP). Each step lists the value, unit, equation, substituted numbers, NEC citation, and (where meaningful) a source line explaining the lookup. The trace is always emitted at maximum verbosity — there is no `verbose` toggle.
2. Writes the same steps to `<output_dir>/<job basename>.csv` (default `output/<name>.csv`). Review mode writes two files, `<name>.design.csv` (the recommendation) and `<name>.review.csv` (as-built plus comparison). Set `output_csv: false` in the job to skip the CSV.

The CSV is meant to be imported by `MathCAD_Template` (copy it to a discipline's `calcs\` folder). Every quantity that an equation uses has its own named row, so the importer can turn the calculation rows into live Mathcad formulas.

CSV columns:

| Column | Meaning |
|---|---|
| `section` | Which stage the step belongs to (`LOAD`, `AMPACITY`, `NEUTRAL`, `EGC`, `FILL`, `VDROP`, `COMPARE`). |
| `label` | Description of the quantity. The variable name is not repeated here; the terminal shows it in brackets after the label. |
| `name` | Variable name (`I_design`, `A_cond`, `Vd`, ...). Empty for rows that are only shown. When a design has several raceways their fill variables get a suffix (`A_cond_rw1`, `A_cond_rw2`). |
| `kind` | `input` (supplied by the job), `calc` (computed from earlier names), `lookup` (taken from a table or rule), `text` (shown only) or `check` (a PASS / FAIL test). |
| `value` | Numeric or textual result. Numeric when the row has a `name`. |
| `unit` | Units (`A`, `V`, `in^2`, `ohm/1000ft`, `%`, `rad`, ...). Empty for dimensionless / textual results. |
| `equation` | For `calc` rows, the exact expression that was evaluated (e.g. `I_design = I_RLA * k_cont`). For `lookup` rows, where the value came from. Empty for `input` rows. |
| `substituted` | The equation with actual numbers substituted (e.g. `I_design = 180.00 * 1.25 = 225.00`). |
| `nec_ref` | NEC section or table cited. |
| `source` | Extra provenance — table lookup arguments, column used, etc. |
| `status` | `PASS` / `FAIL` / `WARN` on the steps that carry a check; empty otherwise. |

Conventions that keep the CSV importable:

- Rows must appear in dependency order; a `calc` row can only use names defined above it.
- Percentages are stored as plain percent numbers in variables ending `_pct`, and the equation divides by 100 where it needs a fraction (`A_allow = A_int * f_limit_pct / 100`).
- Voltage drop uses the circuit length in units of 1000 ft (`L_kft`), because R and X are per 1000 ft; this keeps the equation free of `/ 1000` and gives volts when Mathcad evaluates the units.

### Adding a new calculation

Emit rows from a section builder in `calc/report.py` instead of formatting strings by hand:

```python
t.input("LOAD", "I_RLA", rla, "A", label="Running current", fmt=".2f")
t.lookup("LOAD", "k_cont", 1.25, label="Continuous factor", equation="k_cont = 1.25 if continuous else 1.00")
t.calc("LOAD", "I_design", "I_RLA * k_cont", "A", label="Design current")   # value, equation and substitution all come from the expression
```

`calc` supports `+ - * / ^`, brackets and `sqrt`, `cos`, `sin`, `acos`, `min`, `max`. A `lookup` must always have an equation text (where the value came from), otherwise the MathCAD importer would offer it as an input.

### Design mode

Sections emitted, in order: `LOAD`, `AMPACITY - phase sizing`, `AMPACITY`, `NEUTRAL / GROUNDED CONDUCTOR` (if the configuration has one), `EQUIPMENT GROUNDING CONDUCTOR` (if applicable), one `CONDUIT FILL - raceway #N` block per raceway, and `VOLTAGE DROP`. The voltage-drop step carries the `PASS` / `FAIL` status vs. `max_vdrop_pct` if set.

### Review mode

The trace is emitted in three parts:

1. **`DESIGN RECOMMENDATION`** — full design trace, labelled `(recommended)` where relevant.
2. **`AS-BUILT ANALYSIS`** — same pipeline recomputed using the values from the `as_built:` block (falling back to the recommendation for any missing field), labelled `(as-built)`. Ampacity, fill, and voltage-drop checks are stamped `PASS` / `FAIL` inline.
3. **`COMPARISON (as-built vs. NEC + recommendation)`** — one row per NEC check, listing the as-built value, the recommendation, and the status.

After the trace, a summary line is printed:

```
Overall: FAIL  (3 failures, 0 warnings)
```

Checks performed:

| Check | NEC | Fails when |
|---|---|---|
| Phase ampacity | 310.16 + 310.15 | derated as-built ampacity < design current |
| Phase size vs recommendation | 310.16 | as-built size smaller than recommendation on the size ladder |
| Parallel min size (only if `phase_sets > 1`) | 310.10(G)(1) | as-built smaller than 1/0 AWG |
| Neutral / grounded | 250.102(C)(1) | as-built smaller than required minimum |
| EGC | 250.122 | as-built smaller than required minimum for OCPD |
| Conduit fill | Ch 9 Table 1 Notes | total conductor area exceeds applicable 53 / 31 / 40 % column |
| Voltage drop | 210.19 IN (advisory) | above `max_vdrop_pct` -> `WARN` (never `FAIL`) |

Process exit code:
- `0` if there are no `FAIL`s (warnings allowed).
- `1` if any `FAIL`.

This makes the tool suitable for a batch reviewer, git hook, or CI job.

## Filling in / correcting the tables

Open any file in `nec_data/`. The header comment names the NEC table. Add or correct rows in the dict; keep the key format shown so the calc layer finds them. Nothing in `calc/` needs to change when you populate or update tables.
