# One-Line Diagram Reference: Adding a Non-Fused Switch Fed From an Existing Panel Breaker

**Scope**: New non-fused disconnect switch tapped off an existing circuit breaker in an existing panelboard. Original electrical drawings are not available. Deliverable is a one-line diagram (standalone or overlay).

---

## 1. Pre-Drawing Data Collection

### 1.1 Existing Panel (Source of the New Circuit)
- [ ] Panel ID / tag (e.g., `PP-1`, `MDP`, `LP-2A`)
- [ ] Location (room, level, column line)
- [ ] Voltage / phases / wires (e.g., 480Y/277V, 3Ø 4W or 208Y/120V, 3Ø 4W)
- [ ] Main bus ampacity
- [ ] Main type: MLO or MCB (if MCB, size and AIC)
- [ ] Panel SCCR / short-circuit rating
- [ ] Manufacturer & catalog series (breaker compatibility)
- [ ] Available fault current at the panel bus (from prior study or utility letter)
- [ ] Existing panel schedule — confirm spare/space availability if new breaker is added, or confirm existing spare breaker to be used
- [ ] Grounded (neutral) system type and whether neutral is required at the load

### 1.2 The Existing Breaker Being Used
- [ ] Breaker position/circuit number
- [ ] Poles (1P / 2P / 3P)
- [ ] Frame size and trip rating (A)
- [ ] Interrupt rating (AIC) — must equal or exceed available fault current
- [ ] Type: thermal-magnetic, electronic trip, adjustable settings
- [ ] Is it an **existing spare** or is a **new breaker** being installed in a spare space?
- [ ] If new: verify breaker is listed for the panel (series rating if applicable)
- [ ] Lock-off / lockout provision if used as the disconnecting means upstream

### 1.3 The New Non-Fused Switch
- [ ] Tag (e.g., `DS-1`, `NFDS-01`)
- [ ] Ampacity (A) — must be ≥ breaker rating unless load-based sizing is justified
- [ ] Voltage rating (must match system)
- [ ] Poles (match breaker poles; switched neutral if required)
- [ ] Horsepower rating (if feeding a motor — NEC 430.109/430.110)
- [ ] Enclosure NEMA rating (1, 3R, 4, 4X, 12, 7/9, etc.) — match environment
- [ ] SCCR / withstand rating — must be ≥ available fault current at switch location
- [ ] Service-entrance rated? (No, in this case — it's a feeder/branch disconnect)
- [ ] Lockable in the OFF position (NEC 110.25)
- [ ] Manufacturer / catalog number (if specified)
- [ ] Mounting: wall, floor, structure — coordinate with working clearances (NEC 110.26)

### 1.4 Conductors & Raceway (Breaker → Switch → Load)
- [ ] Conductor size, material (Cu/Al), insulation (THHN/THWN-2/XHHW-2)
- [ ] Number of current-carrying conductors, neutral, EGC
- [ ] Conduit type (EMT, RMC, PVC, LFMC) and size
- [ ] Estimated one-way length (for voltage drop)
- [ ] EGC size per NEC 250.122 (based on breaker rating)
- [ ] Ampacity verified per NEC 310.16 with derating (ambient, fill)
- [ ] Voltage drop within acceptable limits (NEC 210.19 / 215.2 informational: 3%/5%)
- [ ] Termination temperature rating (60/75°C column) per NEC 110.14(C)

### 1.5 Downstream Load
- [ ] Equipment name, tag, location
- [ ] FLA / HP / kW, voltage, phases
- [ ] Motor: code letter, service factor, controller location (switch may be motor disconnect per 430.102)
- [ ] Continuous vs. non-continuous load (125% factor for continuous)
- [ ] Any nameplate SCCR requirement
- [ ] Is the new switch the **required disconnecting means** per NEC 430.102(B) (within sight of motor) or NEC 422/424 for appliances/heating?

### 1.6 Code & Study Impacts
- [ ] Adopted NEC edition
- [ ] Panel load calc updated — does added load exceed panel/feeder capacity? (NEC 220)
- [ ] Arc-flash study update needed? New labels on panel and switch?
- [ ] Short-circuit study update if system impedance changes materially
- [ ] Working clearances (NEC 110.26) at both panel and new switch
- [ ] Grounding/bonding continuity maintained
- [ ] AHJ permit / plan review requirements

---

## 2. What the One-Line Must Show

### 2.1 Upstream (Existing — Show for Context, Screened if Overlaid)
- [ ] Utility or building service reference (voltage, source)
- [ ] Upstream transformer (kVA, voltages, %Z, connection) if known
- [ ] Main service disconnect / upstream OCPD (size, AIC)
- [ ] Existing panel symbol with: tag, voltage, bus rating, SCCR, MLO/MCB
- [ ] Available fault current callout at the panel bus

### 2.2 The Modification (Full Line Weight, Clouded, Deltas)
- [ ] Existing breaker highlighted: circuit #, poles, trip (A), AIC
  - Note whether it is **existing spare** or **new breaker in existing space**
- [ ] Feeder conductors: size, quantity, material, insulation, conduit, length, EGC size
- [ ] New non-fused switch symbol with:
  - Tag (e.g., `DS-1`)
  - Ampacity / voltage / poles
  - HP rating (if motor load)
  - NEMA enclosure
  - SCCR
  - "NON-FUSED" callout
  - "Lockable in OFF" note
- [ ] Load-side conductors (if different from line side)
- [ ] Downstream equipment symbol with tag, HP/kW/FLA, voltage
- [ ] Grounding/bonding path shown continuous from panel to equipment

### 2.3 Labels, Notes, Blocks
- [ ] Revision cloud + revision triangle (Δ) around all new items
- [ ] Keyed notes tied to the new switch and feeder
- [ ] General notes:
  - Code edition
  - Scope of work statement
  - "Existing shown screened for reference only"
  - "Contractor to field-verify existing conditions prior to installation"
  - Available fault current statement
  - Arc-flash label update note (if applicable)
- [ ] Legend / symbol list (only symbols actually used)
- [ ] Abbreviations
- [ ] Panel schedule reference or updated panel schedule on companion sheet
- [ ] Title block: project, address, sheet #, date, revision, drawn/checked, PE seal area

---

## 3. Overlay Best Practices (No Original CAD Available)

- Import best-available existing document (PDF, scan, photo) as **underlay** — georeferenced/scaled if possible.
- Trace or reference only what is needed to establish context; do not re-draw the entire existing system.
- Screen underlay content to **30–50%** so new work is visually dominant.
- Cloud + delta every new/modified item.
- Add a boilerplate note:
  > *"Existing conditions shown are based on field observation and available documentation. Contractor shall field-verify all existing ratings, conductor sizes, and available fault current prior to installation and notify Engineer of any discrepancies."*
- Do **not** assume ratings you cannot verify — call them out as "FIELD VERIFY" on the drawing.

---

## 4. Tool Selection

| Tool | Recommendation for This Task |
|---|---|
| **AutoCAD (plain)** | **Preferred.** Fast, flexible, easy to overlay a PDF underlay. Use a personal/company one-line symbol library. |
| **AutoCAD Electrical** | Only if the project will grow into multiple sheets with wire numbering / BOM automation. Overkill for one switch. |
| **Revit MEP** | Only if the project already exists in Revit. One-lines in Revit are schematic drafting views — no automatic generation from the model. |

---

## 5. Pre-Issue Checklist

- [ ] All new items clouded and deltas placed
- [ ] Ratings shown for every OCPD, switch, and conductor
- [ ] AIC / SCCR verified against available fault current
- [ ] EGC size confirmed per NEC 250.122
- [ ] Voltage drop calc filed (reference the tool/spreadsheet used)
- [ ] Panel load calc updated and filed
- [ ] Working clearance verified in the field (or noted as field-verify)
- [ ] Arc-flash label update noted (if study is being updated)
- [ ] Legend matches symbols used
- [ ] Title block, revision block, and seal complete
- [ ] Notes reference correct NEC edition
- [ ] Reviewed by second engineer / QC pass
- [ ] Field-verify items clearly flagged

---

## 6. Questions to Confirm With Client / Owner / Field

1. Which existing panel and which specific breaker/space will feed the switch? (Photo of panel interior + nameplate.)
2. What is the documented available fault current at that panel?
3. Is there a current arc-flash study? Will labels need updating?
4. Preferred manufacturer for the disconnect?
5. Will installation be energized or de-energized? (LOTO plan.)
6. Any existing spare capacity concerns on the panel or upstream feeder?
7. Any AHJ or utility notification required for the modification?
8. As-built markup required at project close?

---

## 7. Common Pitfalls to Avoid

- Sizing the switch on load current when NEC requires it be rated for the upstream OCPD (e.g., motor disconnect HP rating vs. ampacity).
- Missing EGC size update when breaker size changes.
- Forgetting SCCR verification at the new switch location.
- Not addressing working clearance at the new switch mounting location.
- Overlooking neutral requirement (or lack thereof) — switched vs. solid.
- Assuming the existing panel AIC without field verification.
- Skipping the arc-flash label update when the study is affected.
