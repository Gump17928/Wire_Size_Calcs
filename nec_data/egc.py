"""NEC 2023 Table 250.122 - Minimum size equipment grounding conductor for
grounding raceway and equipment, keyed by OCPD rating.

VERIFY every value against your bound NEC copy before using for a real design.
"""

# EGC[material][ocpd_amps] -> "<AWG/kcmil>"
EGC: dict[str, dict[int, str]] = {
    "Cu": {
        15:   "14",
        20:   "12",
        60:   "10",
        100:  "8",
        200:  "6",
        300:  "4",
        400:  "3",
        500:  "2",
        600:  "1",
        800:  "1/0",
        1000: "2/0",
        1200: "3/0",
        1600: "4/0",
        2000: "250",
        2500: "350",
        3000: "400",
        4000: "500",
        5000: "700",
        6000: "800",
    },
    "Al": {
        15:   "12",
        20:   "10",
        60:   "8",
        100:  "6",
        200:  "4",
        300:  "2",
        400:  "1",
        500:  "1/0",
        600:  "2/0",
        800:  "3/0",
        1000: "4/0",
        1200: "250",
        1600: "350",
        2000: "400",
        2500: "600",
        3000: "600",
        4000: "800",
        5000: "1250",
        6000: "1250",
    },
}
