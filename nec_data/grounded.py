"""NEC 2023 Table 250.102(C)(1) - Grounded (neutral) conductor, main bonding
jumper, system bonding jumper, and supply-side bonding jumper minimum size,
keyed by the size of the largest ungrounded (phase) supply conductor.

Above 1100 kcmil Cu / 1750 kcmil Al the table requires >= 12.5% of the phase
conductor CM area; values below reflect that computation.

VERIFY every value against your bound NEC copy before using for a real design.
"""

# GROUNDED_MIN[material][phase_size] -> "<AWG/kcmil>"
GROUNDED_MIN: dict[str, dict[str, str]] = {
    "Cu": {
        "14":   "8",
        "12":   "8",
        "10":   "8",
        "8":    "8",
        "6":    "8",
        "4":    "8",
        "3":    "8",
        "2":    "8",
        "1":    "6",
        "1/0":  "6",
        "2/0":  "4",
        "3/0":  "4",
        "4/0":  "2",
        "250":  "2",
        "300":  "2",
        "350":  "2",
        "400":  "1/0",
        "500":  "1/0",
        "600":  "1/0",
        "700":  "2/0",
        "750":  "2/0",
        "800":  "2/0",
        "900":  "2/0",
        "1000": "2/0",
        # Above 1100 kcmil: 12.5% of phase CM area.
        "1250": "3/0",   # 156.25 kcmil -> 3/0 (167.8 kcmil)
        "1500": "4/0",   # 187.5  kcmil -> 4/0 (211.6 kcmil)
        "1750": "250",   # 218.75 kcmil -> 250
        "2000": "250",   # 250    kcmil -> 250
    },
    "Al": {
        "12":   "6",
        "10":   "6",
        "8":    "6",
        "6":    "6",
        "4":    "6",
        "3":    "6",
        "2":    "6",
        "1":    "6",
        "1/0":  "6",
        "2/0":  "4",
        "3/0":  "4",
        "4/0":  "2",
        "250":  "2",
        "300":  "1/0",
        "350":  "1/0",
        "400":  "1/0",
        "500":  "1/0",
        "600":  "3/0",
        "700":  "3/0",
        "750":  "3/0",
        "800":  "3/0",
        "900":  "3/0",
        "1000": "4/0",
        "1250": "4/0",
        "1500": "4/0",
        "1750": "4/0",
        # Above 1750 kcmil: 12.5% of phase CM area.
        "2000": "250",   # 250 kcmil -> 250
    },
}
