"""Show-your-work trace: typed rows, a symbol table, and the CSV / terminal writers.

Every row is one of these kinds (the `kind` CSV column):

    input   a number supplied by the user (no equation)
    calc    computed by `Trace.calc` from earlier named values; the equation shown is the equation that ran
    lookup  a number taken from a code table or rule (the equation column says where it came from)
    text    shown only (sizes, descriptions, comparisons)
    check   a PASS / FAIL / WARN test

Named rows (input, lookup, calc) are stored in the trace's symbol table, so a later `calc` can refer to them by
name.  Rows must therefore be emitted in dependency order, which is also the order a worksheet reads top to bottom.

The CSV is read by MathCAD_Template (tool/csv_import.py), which turns `calc` rows whose equation is plain
arithmetic into live Mathcad formulas.  Write equations with `* / + - ^` and brackets, and put percentages in
variables ending `_pct` with an explicit `/ 100` in the equation, so the equation and the value always agree.
"""

from __future__ import annotations

import ast
import csv
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from math import acos, cos, sin, sqrt
from pathlib import Path

HEADER_MARK = "__HEADER__"
KINDS = ("input", "calc", "lookup", "text", "check")
COLUMNS = ["section", "label", "name", "kind", "value", "unit", "equation",
           "substituted", "nec_ref", "source", "status"]

_FUNCTIONS = {"sqrt": sqrt, "cos": cos, "sin": sin, "acos": acos, "min": min, "max": max}
_OPERATORS = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a**b,
}
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def evaluate(expression: str, symbols: dict[str, float]) -> float:
    """Value of a plain-arithmetic expression (`^` is a power) using only numbers, `symbols` and `_FUNCTIONS`."""
    try:
        tree = ast.parse(expression.replace("^", "**").strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"cannot read expression {expression!r}") from exc
    return _evaluate_node(tree.body, symbols, expression)


def _evaluate_node(node: ast.AST, symbols: dict[str, float], source: str) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in symbols:
            raise KeyError(f"{node.id!r} in {source!r} is not defined yet - emit the row that defines it first")
        return symbols[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate_node(node.left, symbols, source),
                                         _evaluate_node(node.right, symbols, source))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _evaluate_node(node.operand, symbols, source)
        return -value if isinstance(node.op, ast.USub) else value
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS
            and not node.keywords):
        return _FUNCTIONS[node.func.id](*(_evaluate_node(a, symbols, source) for a in node.args))
    raise ValueError(f"unsupported syntax in {source!r}")


@dataclass
class CalcStep:
    section: str
    label: str
    value: str
    unit: str
    equation: str
    substituted: str
    nec_ref: str
    source: str
    status: str = ""
    name: str = ""
    kind: str = "text"


@dataclass
class Trace:
    job_name: str
    mode: str
    steps: list[CalcStep] = field(default_factory=list)
    symbols: dict[str, float] = field(default_factory=dict)  # name -> exact value, for later `calc` rows
    shown: dict[str, str] = field(default_factory=dict)      # name -> value as printed, for `substituted`

    def header(self, title: str) -> None:
        self.steps.append(CalcStep(HEADER_MARK, title, "", "", "", "", "", ""))

    # -- rows ---------------------------------------------------------------
    def add(self, section: str, label: str, value: str, unit: str = "",
            equation: str = "", substituted: str = "",
            nec_ref: str = "", source: str = "", status: str = "",
            kind: str = "text") -> None:
        """A row that is shown but not part of the symbol table (text and check rows)."""
        if kind not in ("text", "check"):
            raise ValueError(f"add() is for text and check rows, not {kind!r}")
        self.steps.append(CalcStep(section, label, value, unit, equation, substituted,
                                   nec_ref, source, status, kind=kind))

    def input(self, section: str, name: str, value: float, unit: str = "", *, label: str, fmt: str = "g",
              nec_ref: str = "", source: str = "") -> float:
        """A number supplied by the user."""
        return self._named(section, name, "input", value, unit, label, fmt, "", "", nec_ref, source, "")

    def lookup(self, section: str, name: str, value: float, unit: str = "", *, label: str, equation: str,
               substituted: str = "", fmt: str = "g", nec_ref: str = "", source: str = "") -> float:
        """A number taken from a table or rule.  `equation` says where it came from and must be non-empty, so the
        MathCAD importer keeps it as a fixed value instead of offering it as an input."""
        if not equation:
            raise ValueError(f"lookup {name!r} needs an equation text saying where the value comes from")
        return self._named(section, name, "lookup", value, unit, label, fmt, equation, substituted,
                           nec_ref, source, "")

    def calc(self, section: str, name: str, expression: str, unit: str = "", *, label: str, fmt: str = ".2f",
             nec_ref: str = "", source: str = "", status: str | Callable[[float], str] = "") -> float:
        """`name = expression`, evaluated from the symbol table.  The equation and the values filled into it are
        written from the same expression, so the shown work always matches the result.  `status` may be a
        function of the result (for PASS / WARN limits)."""
        value = evaluate(expression, self.symbols)
        shown = format(value, fmt)
        filled = _IDENTIFIER.sub(lambda m: self.shown.get(m.group(), m.group()), expression.replace("^", " ^ "))
        substituted = f"{name} = {re.sub(r' +', ' ', filled)} = {shown}"
        return self._named(section, name, "calc", value, unit, label, fmt, f"{name} = {expression}", substituted,
                           nec_ref, source, status(value) if callable(status) else status)

    def _named(self, section: str, name: str, kind: str, value: float, unit: str, label: str, fmt: str,
               equation: str, substituted: str, nec_ref: str, source: str, status: str) -> float:
        if not _IDENTIFIER.fullmatch(name):
            raise ValueError(f"{name!r} is not a valid variable name")
        if name in self.symbols:
            raise ValueError(f"{name!r} is already defined in this trace")
        self.symbols[name] = value
        self.shown[name] = format(value, fmt)
        self.steps.append(CalcStep(section, label, self.shown[name], unit, equation, substituted,
                                   nec_ref, source, status, name=name, kind=kind))
        return value

    # -- output -------------------------------------------------------------
    def render_terminal(self) -> str:
        out: list[str] = []
        title = f"=== {self.job_name}  [mode: {self.mode}] "
        out.append(title.ljust(80, "="))
        for s in self.steps:
            if s.section == HEADER_MARK:
                out.append("")
                out.append(f"-- {s.label} ".ljust(80, "-"))
                continue
            label = f"{s.label} ({s.name})" if s.name else s.label
            head = f"  {label:<44} = {s.value} {s.unit}".rstrip()
            tail_parts = []
            if s.nec_ref:
                tail_parts.append(f"[{s.nec_ref}]")
            if s.status:
                tail_parts.append(f"-> {s.status}")
            if tail_parts:
                head = f"{head:<76}  {'  '.join(tail_parts)}"
            out.append(head)
            if s.equation:
                out.append(f"      eqn:  {s.equation}")
            if s.substituted and s.substituted != s.equation:
                out.append(f"      sub:  {s.substituted}")
            if s.source:
                out.append(f"      src:  {s.source}")
        out.append("=" * 80)
        return "\n".join(out)

    def write_csv(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="ascii", errors="replace") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            for s in self.steps:
                if s.section == HEADER_MARK:
                    continue
                w.writerow({c: getattr(s, c) for c in COLUMNS})
        return path
