# Molex 15015-0451 FPC reconstruction

Created 2026-10-02 for the Molex 502598-5193 carrier connector. Open `FPC_15015_0451.PrjPcb` in Altium Designer. This is a separate cable project; the carrier PCB and schematic are unchanged.

## Scope and nominal dimensions

The editable PCB reproduces the public nominal cable outline and staggered, same-face contact pattern. It is not Molex's proprietary production artwork or a certified replacement cable. All 51 conductors are present, including contacts unused by the carrier.

| Feature | Implemented nominal value |
| --- | --- |
| Part | Molex 15015-0451 / 0150150451 |
| Length | 101.60 mm; marketed as 102 mm |
| Width | 15.60 mm |
| Circuit count / pitch | 51 / 0.30 mm |
| First / last contact centre | 0.30 / 15.30 mm across the width |
| Contact face | Type A; both ends on Top |
| Corner radius | R0.20 mm; native arc outline segments |
| Exposed contact length | 3.00 mm at each end |
| Back stiffener length | 4.00 mm at each end |
| Contact neck / finger width | 0.10 / 0.30 mm |
| Body conductor width | 0.20 mm |
| Contact transition stations | 0.15, 0.25, 1.10, 1.20, 2.00 and 2.10 mm from the end |
| Copper | 18 micrometres, one conductive layer |
| Base PI + adhesive | 45 micrometres |
| Coverlay PI + adhesive | 50 micrometres |
| End stiffener + adhesive | 150 micrometres, on the back |
| Contact thickness requirement | 0.20 +/- 0.03 mm |
| Surface finish specified by source | Hard gold at least 0.0508 micrometres over nickel at least 2.54 micrometres |

The base/copper/coverlay body sums to 0.113 mm. The exposed end sums to 0.213 mm before plating, within the published 0.20 +/- 0.03 mm end requirement. The 1 mm coverlay/stiffener overlap sums to 0.263 mm before plating. These layer sums use the published nominal composite thicknesses; adhesive compression and detailed production tolerances are not known.

## Altium representation

- Top Layer contains the 51 copper nets. Each end array is a native component with 51 numbered pads and copper regions that define the staggered fingers. The small native pad rectangles lie entirely within their corresponding copper regions.
- Top Solder is used as the **coverlay opening artwork**, not a solder-resist application instruction. Two full-width 3 mm end openings expose the mating fingers.
- The stored master/substack is flex, with one copper layer, the PI base and the upper coverlay. No bottom copper, bottom solder mask, holes or vias are present.
- Mechanical 2, named **Back stiffener boundary**, defines the two 4 mm back stiffener extents. Stiffeners are fabrication annotations, not separate native rigid-flex substacks or 3D solids. Their material/thickness is specified in this document and the review section drawing.
- Mechanical 1 contains English fabrication annotations. No printed silkscreen is required. All contact pad paste generation is disabled.
- `contact_mapping.csv` labels matching physical conductors A1-B1 through A51-B51, viewed from the same global mating face. These cable labels do not imply the pin-number orientation of two separately installed connectors; connector orientation must be considered when wiring an assembly.
- The 0.0707 mm clearance rule follows the drawing's opposed 45-degree stagger transitions: 0.10 / sqrt(2) = 0.0707107 mm. Straight body trace clearance is 0.10 mm. This is the geometry of the copied cable, not a generic PCB fabrication capability claim. No DRC rule was disabled to hide a violation.
- Dielectric constant 3.5 is a modelling placeholder, not a released Molex material property. No controlled-impedance claim is made for this cable.

## Source reconciliation

1. [Molex product page](https://www.molex.com/en-us/products/part-detail/150150451): 51 circuits, 0.30 mm pitch, Type A, 102 mm catalog length; compatibility with the 502598 series.
2. [Current Molex family sales drawing, 150150001PSD000 Rev B, 2023-08-08](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/150/15015/150150445_sd.pdf): staggered contact dimensions, width formula, composite layer thicknesses and end-thickness tolerance. Its searchable dimension text was read; direct local PDF download was unavailable during this task.
3. [Legacy original Molex sales drawing, SD-15015-001 Rev B, 2013-01-23, distributor mirror](https://pdf.icgoo.net/productinfo/allpdf/72b4076c-1cfe-31fc-a247-91ae0da5b5bd.pdf): the 150150451 row explicitly gives 101.6 mm length and 15.6 mm width. The local PDF was rendered and visually checked, including the staggered pattern. A copy is retained under the repository helper's `reference/` directory.
4. [Molex family product specification, PS-15015-001 Rev C](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/000/000000/PS-15015-001-001.pdf): electrical/environmental family properties and generic construction requirements.

The sources are not fully consistent: the family product specification has a width formula that adds 0.10 mm, a nominal 0.10 mm conductor width, and a 0.135 mm stiffener value; the sales drawing gives 15.6 mm width, a 0.20 mm body conductor detail, and a 0.150 mm stiffener-plus-adhesive callout. This reconstruction follows the **sales-drawing geometry**. The older drawing has tighter exposure/stiffener tolerances than the current drawing. No unpublished adhesive formulation, copper temper, exact material grade, finished compression, bend lifetime or manufacturing qualification has been inferred. Resolve these differences with the manufacturer before treating the reconstruction as a production-equivalent part.

## Validation and outputs

- `native_validation.txt`: saved-file reopen, one signal layer, zero stored unrouted connections and successful native Altium DRC.
- `Native_DRC.html`: 13 enabled rule checks, zero violations after applying the drawing-derived minimum copper gap.
- `saved_geometry_validation.json`: independent saved-binary geometry checks, including continuity, isolation, pitch, copper layer, stack thicknesses, no vias/drills, and original-carrier hash preservation.
- `FPC_15015_0451_review.png`: review image generated from the saved native copper, with dimensional overview, contact detail and construction section. It is a geometry render, not an Altium screenshot.
- `nominal_geometry.json` and `contact_mapping.csv`: editable nominal specification and physical conductor mapping.

The initial project wrapper contained an invalid optional enum (`ClassGenNCAutoScope=All`). It has been removed from both the saved project and its generator. Native PCB reopen and DRC succeeded; final project-tree registration after this wrapper correction remains unverified because the Altium UI automation repeatedly returned an unresponsive/stale error dialog. The PCB document remains available independently of the project wrapper.

Git delivery of this source cable and the two derivative adapters was requested on 2026-10-03. No Gerber fabrication release, vendor upload or purchase was performed.
