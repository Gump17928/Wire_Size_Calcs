"""Tests for the typed trace and for the CSV the report builders write.

Run from the Wire_Size_Calcs folder:   python -m unittest discover -s tests
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import wiresize  # noqa: E402
from calc.configurations import CONFIGS  # noqa: E402
from calc.load import design_current  # noqa: E402
from calc.trace import COLUMNS, KINDS, Trace, evaluate  # noqa: E402
from calc.vdrop import vdrop_ac, vdrop_dc  # noqa: E402

DESIGN_JOB = {
    "rla_amps": 180, "length_ft": 250, "voltage": 480, "configuration": "3ph_wye_4w", "continuous": True,
    "ambient_c": 30, "conductor_temp_c": 75, "material": "Cu", "insulation": "THWN-2", "conduit_type": "EMT",
    "raceway_magnetic": "magnetic", "power_factor": 0.9, "max_vdrop_pct": 3.0,
}
PARALLEL_JOB = {**DESIGN_JOB, "rla_amps": 500}
DC_JOB = {**DESIGN_JOB, "configuration": "dc_2w", "voltage": 125}
REVIEW_JOB = {
    **DESIGN_JOB, "rla_amps": 140, "length_ft": 285, "conduit_type": "PVC-40",
    "raceways": [{"phase": 3, "egc": 1}, {"neutral": 1, "egc": 1}],
    "as_built": {"phase_size": "2/0", "phase_sets": 1, "egc_size": "6",
                 "conduit_type": "PVC-40", "conduit_trade_size": "2-1/2"},
}


def design_trace(job: dict) -> Trace:
    t = Trace("test", "design")
    wiresize._build_design_trace(t, job)
    return t


def as_built_trace(job: dict) -> Trace:
    t = Trace("test", "review")
    wiresize._build_asbuilt_trace(t, job)
    return t


def read_csv(t: Trace) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        path = t.write_csv(Path(tmp) / "out.csv")
        with path.open(newline="", encoding="ascii") as f:
            return list(csv.DictReader(f))


class EvaluatorTest(unittest.TestCase):
    def test_arithmetic_functions_and_power(self):
        self.assertAlmostEqual(evaluate("2 * (a + 1) ^ 2 + sqrt(9)", {"a": 2}), 21.0)

    def test_unknown_name_says_what_to_emit_first(self):
        with self.assertRaisesRegex(KeyError, "not defined yet"):
            evaluate("a * b", {"a": 1})

    def test_rejects_anything_but_arithmetic(self):
        for bad in ("__import__('os')", "a.real", "open('x')", "[1]"):
            with self.assertRaises(ValueError, msg=bad):
                evaluate(bad, {"a": 1})


class TraceRowsTest(unittest.TestCase):
    def setUp(self):
        self.t = Trace("job", "design")
        self.t.input("S", "I", 180, "A", label="Current", fmt=".2f")
        self.t.lookup("S", "k", 1.25, label="Factor", equation="k from table", fmt=".2f")

    def test_calc_writes_equation_substitution_and_result_from_one_expression(self):
        self.t.calc("S", "Id", "I * k", "A", label="Design current")
        row = self.t.steps[-1]
        self.assertEqual((row.name, row.kind, row.value), ("Id", "calc", "225.00"))
        self.assertEqual(row.equation, "Id = I * k")
        self.assertEqual(row.substituted, "Id = 180.00 * 1.25 = 225.00")

    def test_status_can_depend_on_the_result(self):
        self.t.calc("S", "Id", "I * k", label="x", status=lambda v: "PASS" if v < 300 else "FAIL")
        self.assertEqual(self.t.steps[-1].status, "PASS")

    def test_duplicate_and_invalid_names_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "already defined"):
            self.t.input("S", "I", 1, label="again")
        with self.assertRaisesRegex(ValueError, "valid variable name"):
            self.t.input("S", "1x", 1, label="bad")

    def test_lookup_needs_an_equation_so_it_is_not_mistaken_for_an_input(self):
        with self.assertRaises(ValueError):
            self.t.lookup("S", "z", 1, label="z", equation="")


class PipelineCsvTest(unittest.TestCase):
    """Properties that must hold for every job type, so a later change to a report builder cannot break the
    contract with the MathCAD importer."""

    def traces(self):
        return {
            "design": design_trace(DESIGN_JOB),
            "parallel": design_trace(PARALLEL_JOB),
            "dc": design_trace(DC_JOB),
            "review design": design_trace(REVIEW_JOB),
            "review as-built": as_built_trace(REVIEW_JOB),
        }

    def test_csv_has_the_documented_columns_and_kinds(self):
        for name, t in self.traces().items():
            with self.subTest(name):
                rows = read_csv(t)
                self.assertEqual(list(rows[0]), COLUMNS)
                self.assertTrue({r["kind"] for r in rows} <= set(KINDS))

    def test_names_are_unique_and_rows_follow_their_kind(self):
        for name, t in self.traces().items():
            with self.subTest(name):
                rows = read_csv(t)
                names = [r["name"] for r in rows if r["name"]]
                self.assertEqual(len(names), len(set(names)))
                for r in rows:
                    if r["kind"] == "input":
                        self.assertEqual(r["equation"], "", r["name"])
                    if r["kind"] in ("calc", "lookup"):
                        self.assertTrue(r["name"] and r["equation"], r["label"])

    def test_every_calc_row_reproduces_its_printed_value_from_the_printed_inputs(self):
        # The same check the MathCAD importer applies (1 %), using the rounded numbers a reader sees.
        for name, t in self.traces().items():
            with self.subTest(name):
                values: dict[str, float] = {}
                for r in read_csv(t):
                    if not r["name"]:
                        continue
                    number = float(r["value"])
                    if r["kind"] == "calc":
                        rhs = r["equation"].split("=", 1)[1]
                        self.assertAlmostEqual(evaluate(rhs, values), number,
                                               delta=0.01 * max(abs(number), 1e-12), msg=r["name"])
                    values[r["name"]] = number

    def test_results_match_the_calc_layer(self):
        t = design_trace(DESIGN_JOB)
        cfg = CONFIGS["3ph_wye_4w"]
        self.assertAlmostEqual(t.symbols["I_design"], design_current(180, True))
        self.assertAlmostEqual(
            t.symbols["Vd"],
            vdrop_ac(180, 250, "4/0", 1, "Cu", "magnetic", cfg["vdrop_factor"], 0.9))

    def test_parallel_sets_divide_impedance_and_multiply_ampacity(self):
        t = design_trace(PARALLEL_JOB)
        sets = t.symbols["N_sets"]
        self.assertGreater(sets, 1)
        self.assertAlmostEqual(t.symbols["R_eff"], t.symbols["R"] / sets)
        self.assertAlmostEqual(t.symbols["I_amp_total"], t.symbols["I_amp_per"] * sets)

    def test_dc_voltage_drop_matches_the_calc_layer(self):
        t = design_trace(DC_JOB)
        size = next(s.value for s in t.steps if s.label == "Selected size")
        self.assertAlmostEqual(t.symbols["Vd"], vdrop_dc(180, 250, size, int(t.symbols["N_sets"]), "Cu"))

    def test_several_raceways_get_separate_variable_names(self):
        t = as_built_trace(REVIEW_JOB)
        for name in ("A_cond_rw1", "A_cond_rw2", "A_allow_rw1", "A_allow_rw2"):
            self.assertIn(name, t.symbols)
        self.assertNotIn("A_cond", t.symbols)

    def test_a_single_raceway_keeps_plain_names(self):
        self.assertIn("A_cond", design_trace(DESIGN_JOB).symbols)


if __name__ == "__main__":
    unittest.main()
