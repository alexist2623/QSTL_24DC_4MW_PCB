# Split mounting plate drawings - Rev B

The drawing layout was revised against the native Enclosure3 DWG/IPN workflow.
Scope: central plate with integral boss, left support, right support and their eight-screw assembly.

## Drawings

- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-CP01.dwg: central plate overall and hole-pattern dimensions.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-CP02.dwg: central plate thread and countersink sections.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-LS01.dwg and RS01.dwg: separate support drawings.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-AS01.dwg: native presentation-linked exploded assembly, eight fastening axes, assembled boss-side view and fastening section C-C.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_Inventor.dwg: combined five-sheet master.
- Manufacturing_DWG/QSTL_Split_Mount_RevB.pdf: print-layout companion.

All six DWGs are native Inventor drawings, with editable model-associated views and dimensions on ISO A3 landscape sheets. Native borders and title blocks are used. The manually typed BOM and assembly-sequence blocks were removed. No general NOTES block or cylinder/device/frame installation drawing is included.

The IPN contains two real presentation tweaks and one associative snapshot. Eight supplemental vector axis trails identify individual screw-to-hole alignment on AS01. The IAM/IPN and source IPT files are included; retain the directory structure when extracting the package. The source part STEP files are also included.

Material: oxygen-free copper. Surface treatment: none.

Device lip reliefs: two 72 mm long grooves beside the boss, 0.5 mm deep with R0.5 end corners. The measured device lip is 3.0398406169 mm thick; groove width is 3.3398406169 mm (lip + 0.3 mm). The groove allowance extends outward to retain the original boss contact faces, device placement and thread axes. CP01 locates the grooves; CP02 section B-B dimensions width and depth.

Internal threaded holes retain native Inventor ISO Metric profile M3x0.5, class 6H, right-hand: ten in the central boss and four in each support. The eight assembly screws are unmodified Inventor 2027 Content Center DIN 7991 M3x10 members, with native M3x0.5-6g external thread features and hexagonal drives. Their 6 mm heads include a 0.2 mm rim; the 6.6 mm x 90-degree countersinks seat the head fronts 0.1 mm below the deck. Nominal engagement is 6.1 mm, with 0.4 mm remaining bore depth. Content Center cosmetic thread cylinders overlap the pilot-bore representation only within the intended threaded engagement; head and clearance-region interference is checked separately.

Validation: all six DWGs reopened in Inventor; five A3 sheets, 46 attached model dimensions without value overrides, linked IPN assembly view, unchanged source CAD hashes during drawing generation, and rendered-page layout inspection. Independent STEP validation checks groove volume, floor height, width, corner radii, retained boss/threads, device alignment and rod contact area.
