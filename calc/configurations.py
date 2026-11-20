"""System configurations supported by the sizing calc.

For each configuration we record:
    phases            : number of phase (ungrounded) conductors
    neutral           : does the run include a neutral?
    egc               : does the run include an EGC (yes for premises wiring)?
    vdrop_factor      : constant used in the standard voltage-drop formula
                        Vdrop = factor * I * (R*cos + X*sin) * L / 1000
    kind              : "ac" | "dc"  (selects Table 9 vs Table 8)

vdrop_factor values (standard formulas):
    single_phase_2w   : 2          (out and back)
    three_phase       : sqrt(3)
    dc                : 2
"""

from math import sqrt

CONFIGS: dict[str, dict] = {
    "3ph_wye_4w": {
        "phases": 3, "neutral": True,  "egc": True,
        "vdrop_factor": sqrt(3), "kind": "ac",
        "notes": "3-phase 4-wire wye (A,B,C,N + EGC).  Neutral is a CCC "
                 "only if it carries harmonic / unbalanced current per 310.15(E).",
    },
    "3ph_wye_3w": {
        "phases": 3, "neutral": False, "egc": True,
        "vdrop_factor": sqrt(3), "kind": "ac",
        "notes": "3-phase 3-wire wye, no neutral run.",
    },
    "3ph_delta_3w": {
        "phases": 3, "neutral": False, "egc": True,
        "vdrop_factor": sqrt(3), "kind": "ac",
        "notes": "3-phase 3-wire delta (A,B,C + EGC).",
    },
    "3ph_hi_leg_delta_4w": {
        "phases": 3, "neutral": True,  "egc": True,
        "vdrop_factor": sqrt(3), "kind": "ac",
        "notes": "High-leg (red-leg) delta, 4-wire.  B-phase to neutral is "
                 "~208 V; do not use B-phase for L-N loads.",
    },
    "1ph_3w": {
        "phases": 2, "neutral": True,  "egc": True,
        "vdrop_factor": 2.0, "kind": "ac",
        "notes": "Split-phase 120/240 (L1,L2,N + EGC).",
    },
    "1ph_2w": {
        "phases": 1, "neutral": True,  "egc": True,
        "vdrop_factor": 2.0, "kind": "ac",
        "notes": "Single-phase 2-wire (L,N + EGC).",
    },
    "dc_2w": {
        "phases": 1, "neutral": True,  "egc": True,
        "vdrop_factor": 2.0, "kind": "dc",
        "notes": "DC 2-wire (+,- + EGC).  Uses Table 8, not Table 9.",
    },
}
