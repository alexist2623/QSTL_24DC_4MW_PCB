"""Publish the completed pour/CAM status without modifying design geometry."""
from pathlib import Path
import json

H=Path(__file__).resolve().parent
R=H.parents[1]
P=R/'QSTL_24DC_4MW_PCB'
v=json.loads((H/'validation.json').read_text())
c=json.loads((P/'fabrication/JLCPCB_HDI_20260924/CAM_validation.json').read_text())
assert v['passed'] and c['passed'] and v['pcb_sha256']==c['pcb_sha256']
(H/'README.md').write_text(f'''# DC-layer ground pour and CAM refresh

Completed on 2026-09-24 in the original Altium project. The user confirmed GND pour around existing L2/L4 DC traces. Actual saved-copper images were delivered before CAM generation.

## Saved design

`ApplyGroundPour.pas` initially added `L2_DC_GND` and `L4_DC_GND` through Altium's native PCB API. The user's subsequent widening request was implemented by `WidenGround.pas`: a dedicated 0.20 mm `DC_GND_GAP_0P2` rule applies to GND on L2/L4, and the general 0.15 mm clearance rule excludes that scope. Both polygons were rebuilt and the original PCB was saved, reopened and independently validated.

- L2 grounded copper: {v['ground']['2']['ground_area_mm2']:.6f} mm2; L4: {v['ground']['4']['ground_area_mm2']:.6f} mm2. One connected region per added layer; no floating islands.
- Nominal DC clearance: 0.20 mm; minimum saved signal-copper gap: {v['ground']['2']['minimum_signal_clearance_mm']:.9f} mm (within the native 2.54 nm coordinate grid). Trace-only minimum is approximately 0.199999 mm. Trace-to-trace minima remain 0.224998 mm on L2 and 0.274998 mm on L4.
- QD GND exclusion retained on every non-Top layer; Top GND retained.
- Existing tracks, arcs, pads, vias, components, net identities and masks preserved. L1/L3/L5/L6 ground geometry is unchanged. The dedicated DC clearance rule is the only new rule; existing clearance priorities were renumbered and the general rule scope was narrowed accordingly. Native save also materialized zero-valued Manhattan-length statistics and closed the unused polygon terminal vertices onto vertex zero.
- All six mechanical GND annuli connect directly to the new pours without thermal relief.
- All 37 copper nets connected; zero stored connection lines and zero native DRC violations across {v['DRC']['checked_rules']} checked rules after save/reopen, including the new 0.20 mm DC pour rule.
- Native schematic compilation: zero violations; physical assignments match. J1 uses even contacts 2..48; 50 and odd contacts remain NC.
- Existing 480 L5-L6 shield microvias and 48 signal through vias preserved; no added DC transitions.
- Native paste audit checked 147 pads; mask/paste geometry unchanged.

Source SHA-256: `{v['source_sha256']}`.

Pre-widening (0.15 mm pour) SHA-256: `{v['clearance_change_source_sha256']}`. Backup: `before_clearance_0p20.PcbDoc`.

Saved PCB SHA-256: `{v['pcb_sha256']}`.

`verify_saved.py` records checks in `validation.json` and `../../QSTL_24DC_4MW_PCB/docs/DC_GND_pour_validation.json`. `preview_ground.py --saved` renders actual native copper to `../../QSTL_24DC_4MW_PCB/docs/DC_GND_pour.png`. Its default mode and `DC_GND_pour_preview.png` are historical proposals, not final results. Mutation scripts are one-time records and must not be rerun against a later board.

## Manufacturing outputs

`prepare_outjob.py` transfers the original project's saved Gerber/NC-drill settings into `HDI_Fabrication.OutJob`. The OutJob belongs to the original project and selects its PCB. Altium regenerated both outputs into `fabrication/JLCPCB_HDI_20260924/Native_CAM` after the 0.20 mm change. Export did not change the PCB.

`package_cam.py` checks timestamps, source hashes, 12 Gerbers, actual GND pours against native geometry, all 94 plated through holes, all 480 laser holes, coordinates/diameters, L5-L6 layer pair, outline and separate Bottom blind-pocket contour. Gerber GND boundaries match native copper within the 0.0002 mm comparison tolerance.

Delivery: `fabrication/JLCPCB_HDI_20260924/QSTL_24DC_6RF_HDI_Gerber_20260924.zip`. Includes requested stack, 50-ohm geometry and Bottom 4.3 x 4.3 x 1.2 mm pocket documentation. Paste/stencil outputs are excluded. `CAM_validation.json` and `Native_DRC.html` accompany the ZIP.

Earlier startup/login and standalone-dialog problems were resolved; the native OutJob completed CAM generation. No supplier upload, new quote, order or Git push was performed for this refresh.
''',encoding='utf-8')
a=H.parent/'dwg_gerber_refresh_20260924/README.md'
t=a.read_text(encoding='utf-8').split('## Pending work and blockers')[0].split('## PCB pour and manufacturing outputs completed')[0]
t=t.replace('Current PCB SHA-256 is e252bd2d1eb66c667f9d9521f6877922dba3e0579a901d9490fa90835c539c07.', 'The pre-pour PCB SHA-256 was e252bd2d1eb66c667f9d9521f6877922dba3e0579a901d9490fa90835c539c07.')
t+=f'''## PCB pour and manufacturing outputs completed

The user confirmed GND fill around L2/L4 DC traces and then requested widening its signal clearance to 0.20 mm. Application, saved-copper images and CAM packaging are recorded in `../dc_ground_pour_20260924/README.md`. Images were delivered before new CAM generation.

After startup recovery and user login, `AuditAll.pas` ran against the saved/reopened original PCB. Fresh `reopen_check.txt`, `native_paste_audit.txt`, `schematic_compile.txt` and `fabrication/JLCPCB_HDI_20260924/Native_DRC.html` confirm zero connection lines, zero DRC violations across {v['DRC']['checked_rules']} checked rules, preserved paste and matching schematic assignments. The independent graph verifies all 37 copper nets.

Current PCB SHA-256: `{v['pcb_sha256']}`.

`HDI_Fabrication.OutJob` generated fresh Gerber and separate laser/through drills. The validated delivery is `fabrication/JLCPCB_HDI_20260924/QSTL_24DC_6RF_HDI_Gerber_20260924.zip`. Earlier CAM packages remain historical. No supplier upload or Git push was performed.
'''
a.write_text(t,encoding='utf-8')
root_note='''Latest fabrication revision, 2026-09-24: L2/L4 include GND pours around existing DC traces, widened to nominal 0.20 mm clearance with a dedicated native rule. QD exclusions, routes, masks and via spans are preserved. Fresh save/reopen checks report zero unconnected lines and zero violations across 16 checked Altium DRC rules. See the [saved-copper image](QSTL_24DC_4MW_PCB/docs/DC_GND_pour.png), [validation](QSTL_24DC_4MW_PCB/docs/DC_GND_pour_validation.json), and [fresh Gerber/drill package](QSTL_24DC_4MW_PCB/fabrication/JLCPCB_HDI_20260924/QSTL_24DC_6RF_HDI_Gerber_20260924.zip). The original project includes `HDI_Fabrication.OutJob` for repeatable native output. This revision has not been uploaded for a new supplier quote.
'''
script_note='''The latest 2026-09-24 native L2/L4 GND pour, save/reopen verification, saved-copper rendering and fresh CAM packaging are in [dc_ground_pour_20260924/](dc_ground_pour_20260924/README.md). Native audits and completed Rev E DWG refresh are in [dwg_gerber_refresh_20260924/](dwg_gerber_refresh_20260924/README.md). The current Gerber ZIP is under `fabrication/JLCPCB_HDI_20260924/`; earlier CAM/quote records are historical.
'''
for file,note in ((R/'README.md',root_note),(R/'script/README.md',script_note)):
    t=file.read_text(encoding='utf-8')
    if file==R/'README.md':
        t='\n\n'.join(p for p in t.split('\n\n') if not p.startswith('Latest fabrication revision,'))
    if note not in t:
        head,body=t.split('\n',1)
        file.write_text(head+'\n\n'+note+body,encoding='utf-8')
print('Completed status and current artifact links published.')
