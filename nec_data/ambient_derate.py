"""NEC 2023 Table 310.15(B)(1)(1) - Ambient temperature correction factors
for ambients other than 30 deg C (base for Table 310.16).

Ranges use inclusive-low, exclusive-high (lo <= T < hi).  A very low `lo`
represents the "10 deg C or less" row.

VERIFY every value against your bound NEC copy before using for a real design.
"""

# AMBIENT[insulation_temp_c][(lo, hi)] -> factor
AMBIENT: dict[int, dict[tuple[int, int], float]] = {
    60: {
        (-99, 11): 1.29,
        (11, 16):  1.22,
        (16, 21):  1.15,
        (21, 26):  1.08,
        (26, 31):  1.00,
        (31, 36):  0.91,
        (36, 41):  0.82,
        (41, 46):  0.71,
        (46, 51):  0.58,
        (51, 56):  0.41,
    },
    75: {
        (-99, 11): 1.20,
        (11, 16):  1.15,
        (16, 21):  1.11,
        (21, 26):  1.05,
        (26, 31):  1.00,
        (31, 36):  0.94,
        (36, 41):  0.88,
        (41, 46):  0.82,
        (46, 51):  0.75,
        (51, 56):  0.67,
        (56, 61):  0.58,
        (61, 66):  0.47,
        (66, 71):  0.33,
    },
    90: {
        (-99, 11): 1.15,
        (11, 16):  1.12,
        (16, 21):  1.08,
        (21, 26):  1.04,
        (26, 31):  1.00,
        (31, 36):  0.96,
        (36, 41):  0.91,
        (41, 46):  0.87,
        (46, 51):  0.82,
        (51, 56):  0.76,
        (56, 61):  0.71,
        (61, 66):  0.65,
        (66, 71):  0.58,
        (71, 76):  0.50,
        (76, 81):  0.41,
        (81, 86):  0.29,
    },
}
