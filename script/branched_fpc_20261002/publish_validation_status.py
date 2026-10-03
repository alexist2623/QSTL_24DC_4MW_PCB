"""Publish evidence-backed documentation without changing Altium design files."""
from pathlib import Path
import hashlib
import json
import re

H = Path(__file__).resolve().parent
R = H.parents[1]
OUT = R / 'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for name in ('ZIF_to_2xZIF', 'ZIF_to_DSUB25'):
    folder = OUT / name
    geometry = json.loads((folder / 'geometry_validation.json').read_text())
    audit = (folder / 'native_validation.txt').read_text()
    drc = (folder / 'Native_DRC.html').read_text(errors='replace')
    pcb = folder / (name + '.PcbDoc')
    assert sha(pcb) == geometry['pcb_sha256'], 'Saved PCB changed after geometry audit'
    assert ('COLD_OPENED_SAVED_DOCUMENT=' in audit or 'SAVED_AND_REOPENED=' in audit) and 'COMPLETE' in audit
    assert 'REBUILT_CONNECTION_COUNT=0' in audit and 'DRC_RETURNED_TRUE' in audit
    assert 'PAD_PASTE_ENABLED=0' in audit
    status = {
        'native_generation': 'Altium PCB API, saved by Altium',
        'native_reopen_verified': True,
        'native_drc_verified': True,
        'native_drc_violation_count': 0,
        'native_rebuilt_connection_count': 0,
        'requires_native_rebuild': False,
        'native_compile_verified': False,
        'native_compile_limitation': 'Branch compile reported missing footprint models before library recovery. Component-specific libraries and explicit schematic links have now been added; native reload and recompile are pending because Altium window activation times out. Independent schematic correspondence is verified.',
        'independent_check_count': len(geometry['checks']),
        'pcb_sha256': sha(pcb),
        'schematic_sha256': sha(folder / (name + '.SchDoc')),
        'native_drc_report_sha256': sha(folder / 'Native_DRC.html'),
        'native_audit_sha256': sha(folder / 'native_validation.txt'),
        'review_source': 'Actual saved native copper, rendered by the independent validator',
        'mask_paste': {
            'pad_paste_enabled_count': 0,
            'explicit_paste_geometry_count': 0,
            'via_apertures': 'Closed by manual negative Top and Bottom mask overrides',
            'generic_via_cache_flags': 'Preserved in raw audit; not used as actual CAM aperture evidence',
        },
        'fabrication_released': False,
    }
    (folder / 'native_status.json').write_text(json.dumps(status, indent=2) + '\n')

(OUT / 'README.md').write_text('''# FPC adapter designs

Updated 2026-10-02. Open each `.PrjPcb` to load its PCB and schematic. These are additional designs; the original carrier, straight cable and read-only references are preserved.

| Design | Wiring and geometry | Saved validation |
| --- | --- | --- |
| ZIF_to_2xZIF | All 51 contacts branch C.n = A.n = B.n; output tips separated by **70 mm** | Native reopen and DRC: 0 violations; rebuilt connections: 0; 532 independent checks |
| ZIF_to_DSUB25 | Anton's NorComp Micro-D mapping; 25 signals on even ZIF contacts | Native reopen and DRC: 0 violations; rebuilt connections: 0; 87 independent checks |

Both PCBs were rebuilt through Altium's native API and saved normally. The final saved files were reopened in a fresh Altium process for DRC and connection rebuilding. `Native_DRC.html`, `native_validation.txt`, `geometry_validation.json` and `native_status.json` provide the evidence for each board. The review PNGs show actual saved copper with dimensions; they are not Altium screenshots.

The branch's first native schematic compile reported three missing footprint models. Component-specific local `.PcbLib` files were recovered from actual saved PCB pad/region geometry, and explicit model links plus project membership were added. `footprint_recovery.json` records source hashes and coordinate round-trip checks. Native library reload and schematic recompile remain unverified because Altium window activation times out. Independent saved schematic wire/pin correspondence is verified. Restart Altium and run the prepared read-only `CompileOnly.PrjScr` with both final projects open to finish this check; do not run the obsolete offline PCB writers against these final files. Existing `native_compile.txt` reports predate library recovery and are not final compile passes.

The branch's 420 mm overall length and 10 mm strip-to-strip clear gap remain provisional interpretations of the sketch. The DSUB adapter's 40 mm length, 31 mm base and 1.6 mm finished connector-area backing are design assumptions. The original straight 101.6 mm cable was not shortened; the new branch's A-to-B tip separation is 70 mm.

These files are not released for fabrication. The inherited 0.0707105 mm contact gap, small DSUB PTH annulus, fine branch drilling and finished flex/stiffener stack require supplier acceptance. Native DRC confirms the stored design rules, not universal supplier capability.

Git delivery to the existing repository was requested on 2026-10-03. No supplier upload, fabrication release or order was performed.
''')

(OUT / 'ZIF_to_2xZIF/README.md').write_text('''# ZIF to two ZIF ends

Open `ZIF_to_2xZIF.PrjPcb`; it references the native PCB and schematic.

## Wiring and geometry

Every numbered contact branches to both outputs: **C.n = A.n = B.n for n = 1..51**. C is the long common end with Bottom contacts; A and B are the upper and lower right outputs with Top contacts. Contact numbers increase left to right in the review's common Top XY projection. A physical Bottom view is mirrored.

| Item | Saved value |
| --- | --- |
| A-to-B tip separation | **70 mm**, A at Y=420, B at Y=350 mm |
| Overall length | 420 mm, provisional reading of 390 + 30 |
| Strip width / clear lateral gap | 15.60 / 10.00 mm; gap interpretation provisional |
| Contact count / pitch | 51 / 0.30 mm at every end |
| Straight section above junction | 20.00 mm |
| Exposed contacts / back stiffeners | 3.00 / 4.00 mm |
| Finished mating thickness target | 0.20 +/- 0.03 mm |
| Branch via land / drill | 0.30 / 0.10 mm; 51 plated Top-to-Bottom vias |
| Copper | 18 um Top and Bottom |
| PI core plus adhesive | Nominal 45 um |
| Coverlay plus adhesive | Nominal 25 um per face |
| Nominal body stack | 0.131 mm |

The staggered fingers retain the Molex 15015-0451 reconstruction. A continuous Top bus joins A to B; a rounded Bottom bus from C reaches the diagonal crossover vias. Body tracks are 0.20 mm and junction tracks are 0.10 mm. The junction is a static no-bend area. The outline's in-plane curve is not an out-of-plane folding-radius specification.

Top/Bottom Solder layers represent coverlay openings: Top at A and B, Bottom at C. Mechanical 2 shows back-stiffener boundaries opposite the exposed fingers; these are fabrication boundaries, not native 3D stiffener solids. Final backing thickness must achieve the required finished mating thickness.

## Saved validation

- Altium native save and fresh-process reopen succeeded. Native DRC has zero violations; rebuilt connection count is zero.
- 532 independent saved-file checks passed, including 70 mm tip spacing, 51 physically continuous three-contact nets, inter-net isolation, drill spacing, outline and coverlay geometry.
- Minimum saved copper gap: 0.0707105367 mm at the inherited fingers. Via annulus: 0.10 mm. Minimum drill-to-other-net copper distance: approximately 0.200 mm.
- All 153 saved PCB assignments match the independently recovered schematic wire/label graph.
- Native pad paste is disabled. No explicit paste geometry exists. Every via has a negative manual mask expansion that closes its opening on both faces. Generic inherited via cache flags in the raw audit are not actual CAM-aperture indicators.
- Original carrier PCB/schematic and straight-cable hashes remain unchanged.
- The first native schematic compile found three missing footprint models. Component-specific local footprint files have now been recovered from saved geometry and explicitly linked in the schematic/project. Native library loading and recompile remain pending because Altium window activation times out. This limitation does not waive those checks.

See `Native_DRC.html`, `native_validation.txt`, `geometry_validation.json` and `native_status.json`. The PNG is a dimensional rendering of actual saved copper, not an Altium screenshot.

Fabricator review is still required: the 0.10/0.30 mm hole/land pair is at JLCPCB's published two-layer-flex extreme capability, and the original finger gap is below its regular line/space capability. Stack, backing and coverlay registration remain subject to supplier acceptance. [JLCPCB flex capabilities](https://jlcpcb.com/capabilities/flex-pcb-capabilities)

Git delivery was requested on 2026-10-03. No fabrication release, supplier upload or order was performed. Helpers are under `script/branched_fpc_20261002/`.
''')

(OUT / 'ZIF_to_DSUB25/README.md').write_text('''# ZIF contact tail to Micro-D adapter

Open `ZIF_to_DSUB25.PrjPcb`; it references the native PCB, schematic and recovered local footprint libraries. Native PCB save/reopen and DRC pass. Native library loading and schematic compilation remain unverified because Altium window activation times out.

## Electrical mapping

- J1: NorComp 381-025-112L565, 25-pin right-angle male Micro-D.
- A: 51-contact integral FPC fingers based on the Molex 15015-0451 reconstruction.
- DSUB 1..13 connect to A2, A6, A10, ..., A50.
- DSUB 14..25 connect to A4, A8, A12, ..., A48.
- Odd A contacts are NC. Both boardlocks are isolated mechanical pads.

This matches Anton's saved adapter map, including A50. The carrier's separate unused-pin-50 requirement is unaffected. Source hashes are recorded in `design_plan.json`; `contact_mapping.csv` lists the 25 signal pairs. Independent PCB/schematic correspondence covers all 78 pins/pads, including the 26 NC contacts and two boardlocks.

## Geometry and stack

| Item | Saved value |
| --- | --- |
| Overall length / connector base | 40 / 31 mm, provisional |
| Mating width / pitch / contacts | 15.60 mm / 0.30 mm / 51 |
| Contact opening / back stiffener | 3 / 4 mm |
| Finished mating thickness target | 0.20 +/- 0.03 mm |
| Signal lands / drills | 0.9652 / 0.7112 mm, Anton footprint |
| Boardlock drills / pitch | 2.69 / 24.51 mm |
| Boardlock row to edge | 5.0 mm, within manufacturer's 5.70 mm maximum |
| Copper | 18 um Top and Bottom |
| PI core plus adhesive | Nominal 45 um |
| Coverlay plus adhesive | Nominal 25 um per face |
| Nominal body stack | 0.131 mm |
| Finished DSUB mounting thickness | Provisional 1.6 mm with bonded backing |

Boardlock geometry follows the [NorComp drawing](https://www.norcomp.net/rohspdfs/Micro-D/381-025-112L565.pdf). The inherited 0.7112 mm signal drill is retained; the drawing specifies 0.70 mm. Mechanical 2 backing boundaries are fabrication geometry, not 3D stiffener solids. Dielectric constant 3.5 is a placeholder; no controlled impedance is claimed.

Twelve 0.40/0.20 mm land/drill vias lie at Y=23 mm, away from exposed fingers. DSUB signal holes use one rectangular coverlay opening per row on each face, expanded 0.10 mm from the row envelope, eliminating narrow coverlay webs. Boardlock openings remain separate. The native maximum-hole rule remains enabled at 2.70 mm to accommodate the 2.69 mm boardlocks.

## Saved validation

- Native Altium save and fresh-process reopen succeeded. Native DRC: zero violations. Rebuilt connection count: zero.
- 87 independent checks passed, including physical cross-layer connectivity, signal isolation, source pin mapping, outline containment and mask/paste geometry.
- Minimum saved copper gap: 0.0707105367 mm at inherited staggered contacts.
- All contact and through-hole pad paste is disabled. No explicit paste geometry exists. Manual negative via-mask overrides close apertures on both faces; raw generic via cache flags are not CAM-aperture evidence.
- Native schematic compilation remains pending; independent saved schematic correspondence passes.

See `Native_DRC.html`, `native_validation.txt`, `geometry_validation.json` and `native_status.json`. The PNG shows actual saved copper rather than an Altium screenshot.

This is not a fabrication release. The inherited fine finger gap and 0.127 mm signal-pad annulus need supplier acceptance; the latter is below JLCPCB's published flex PTH-annulus limit. The backing and final mating thickness also need fabrication review. [JLCPCB flex capabilities](https://jlcpcb.com/capabilities/flex-pcb-capabilities)

Git delivery to the existing repository was requested on 2026-10-03. No supplier upload, fabrication release or order was performed.
''')
print('Published current native PCB evidence; schematic compilation remains pending.')
