"""Link the current saved M1 PCB, native hardware fit, and regenerated CAM."""
from pathlib import Path
import hashlib, json

H=Path(__file__).resolve().parent
R=H.parents[1]; P=R/'QSTL_24DC_4MW_PCB'
out=P/'Mechanical_Assembly/ZIF_M1_Review'
F=P/'fabrication/JLCPCB_HDI_20260925'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))

board=P/'QSTL_24DC_4MW_PCB.PcbDoc'
fit=read(out/'inventor_fit.json'); clear=read(out/'cable_hole_clearance.json')
validation=read(H/'validation.json'); cam=read(F/'CAM_validation.json')
assert all(r['pcb_sha256']==sha(board) for r in (fit,clear,validation,cam))
assert validation['passed'] and cam['passed'] and fit['saved_and_reopened']
member=fit['hardware']
assert member['family']=='KS B 1021 - Metric' and member['is_content_member']
assert member['values']['NND']=='1' and member['values']['PTC']=='0.25'
assert member['values']['KOD']=='2' and member['values']['KOH']=='0.65'
assert sha(Path(member['file'])).upper()==member['sha256']
assert sha(Path(member['source']))==sha(Path(member['file']))
housing=[h for h in fit['interferences'] if 'Molex_502598_5193' in (h['first'],h['second'])]
assert not housing
assert len(fit['interferences'])==2
assert all('FPC_51x0p3_Dimensional_Envelope' in (h['first'],h['second']) for h in fit['interferences'])
assert min(d['connector_distance_mm'] for d in fit['distances'])>.62
assert all(abs(g-.3)<.00001 for g in clear['signed_hole_edge_to_cable_edge_clearance_mm'])
assert cam['through_diameters']['1.2']==2 and cam['blind_holes']==480
report=dict(pcb_sha256=sha(board),native_saved_and_reopened=True,standard_member_unmodified=True,
    hardware_family=member['family'],hardware_size='M1 x 4',thread_pitch_mm=.25,
    head_diameter_mm=2,head_height_mm=.65,washer_count=0,
    hole_geometry=validation['mounts'],hole_center_pitch_mm=17.4,
    cable_hole_plan_clearance=clear,nominal_connector_gap_mm=fit['distances'],
    housing_interferences=housing,permitted_head_cable_intersections=fit['interferences'],
    nominal_radial_hole_play_mm=.1,minimum_housing_gap_less_nominal_radial_play_mm=min(d['connector_distance_mm'] for d in fit['distances'])-.1,
    fit_status='No nominal connector or PCB collision. Only the user-permitted head/cable contact remains.',
    limitations=['Cable width 15.6 mm and reinforced thickness 0.20 mm are a dimensional envelope.',
                 'Cable center height 0.47 mm above the PCB is an unverified placement assumption; bending and clamping are not modeled.',
                 'Full dimensional tolerance analysis and mating support/nut are outside this review. Screw length 4 mm is a review assumption.'],
    electrical_validation=validation,cam_validation_passed=cam['passed'],
    gerber_zip_sha256=sha(F/'QSTL_24DC_6RF_HDI_Gerber_20260925.zip'),
    artifact_sha256={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.suffix.lower() in ('.iam','.ipt','.step','.png','.svg') and 'OldVersions' not in f.parts})
(out/'final_pcb_fit_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(out/'README.md').write_text('''# ZIF M1 round-head mounting review

Current revision, 2026-09-25. `ZIF_M1_Fit.iam` and its matching STEP use two unmodified Autodesk Inventor Content Center **KS B 1021 - Metric M1 x 4** slotted pan/round-head screws. Thread is **M1 x 0.25 - 6g**, head diameter **2.00 mm**, head height **0.65 mm**. No washers or custom screw geometry. `m1_round_member.json` records the installed library member and original file hash.

## PCB geometry

MH7/MH8 use **1.20 mm plated clearance drills**, **1.60 mm lands**, at **(1.05,1.20)** and **(18.45,1.20) mm**. Center pitch is **17.40 mm**. Each hole moved 0.55 mm outward from the superseded M1.6 arrangement. The board remains 19.5 x 67.9 mm. Drill-to-outline margins are 0.45 mm at the sides and 0.60 mm at the end. Mounts join GND directly, with no thermal relief or paste. Original six mounts, routing, masks and components are preserved.

## Cable and native fit

The centered 15.60 mm cable spans X1.95..17.55 mm. Inward hole edges are X1.65 and X17.85 mm: **0.30 mm positive lateral clearance per side**, and 16.20 mm clear width between holes. `ZIF_Cable_Hole_Clearance.png`/`.svg` expose the drilled holes and dimension these gaps. `ZIF_Holes_Cable_Native_Top.png` shows the native Inventor geometry with screws temporarily hidden and the cable transparent. `ZIF_M1_Round_Oblique.png` shows the actual assembled standard hardware.

Saved/reopened Inventor reports **0.627624 mm minimum screw-to-ZIF-housing distance** on each side, no screw/PCB intersection and no housing intersection. Nominal 0.10 mm radial hole/shank play alone does not consume this gap. The only intersections are the allowed screw-head/cable-envelope contact (approximately 0.00140 and 0.00142 mm3). Head-to-cable lateral overlap is nominally 0.10 mm in top projection; screw shanks remain outside the cable envelope.

The cable model uses a 0.20 mm reinforced thickness, from the [Molex 502598-5193 sales drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/502/502598/5025983993_sd.pdf). Its center height of 0.47 mm above the PCB remains an unverified placement assumption. Cable bending/clamping and a full dimensional tolerance stack are not modeled. Screw length 4 mm is a review assumption; mating threaded support/nut is not specified. The 0.30 mm top-projection hole gap does not depend on the assumed cable height.

## Saved-design and fabrication checks

Altium save/reopen: zero unrouted connections and zero violations across 16 checked DRC rules. Independent saved-copper analysis: all 37 nets connected. Original routing, pin mapping, 480 L5-L6 blind microvias, DC ground clearance, masks, QD ground exclusions and original six mounts are preserved.

Updated Gerbers are in `../../fabrication/JLCPCB_HDI_20260925/QSTL_24DC_6RF_HDI_Gerber_20260925.zip`. The package has 96 plated through holes, including the two 1.20 mm mounts, and 480 separate L5-L6 laser holes. `final_pcb_fit_validation.json` links the saved PCB, standard-member hash, native fit and CAM validation. The neighboring M1.6/M2 review folders are superseded historical reviews. No new supplier upload, order or Git push was made.
''',encoding='utf-8')

req=P/'docs/DESIGN_REQUIREMENTS.md';t=req.read_text(encoding='utf-8')
start=t.index('- Latest ZIF size correction');end=t.index('\n\n',start)
t=t[:end]+' Implemented and verified: 0.30 mm cable-to-hole clearance per side, 0.627624 mm nominal screw-to-housing distance, no housing/PCB interference, and only permitted head/cable-envelope contact. Saved/reopened DRC: 16 rules, zero violations; independent continuity: 37 nets. Current native review and matching STEP are in Mechanical_Assembly/ZIF_M1_Review. Cable height remains an unverified placement assumption.'+t[end:]
t=t.replace('- Latest ZIF fastener correction (2026-09-25):','- Superseded M1.6 round-head trial (2026-09-25):').replace('- Implemented ZIF end mounts (2026-09-25):','- Superseded M1.6 socket-head trial (2026-09-25):')
req.write_text(t,encoding='utf-8')

root=R/'README.md';t=root.read_text(encoding='utf-8')
a=t.index('Latest PCB revision,');b=t.index('\n\nOpen ',a)
t=t[:a]+'''Latest PCB revision, 2026-09-25: two **M1** clearance mounts at the ZIF end, with 1.20 mm plated drills, 1.60 mm lands and 17.40 mm center pitch. Centers are (1.05,1.20) and (18.45,1.20) mm. Direct GND, no thermal relief or paste. Board outline, original six mounts, L2/L4 GND clearance, routing, masks, pin assignments and blind-via spans are preserved. Saved/reopened Altium DRC has zero violations across 16 checked rules, zero unconnected lines, and all 37 nets independently connected. See [validation](QSTL_24DC_4MW_PCB/docs/ZIF_M1_mount_validation.json), [current PCB Top](QSTL_24DC_4MW_PCB/docs/PCB_Top_current.png), and [fresh Gerber/drill ZIP](QSTL_24DC_4MW_PCB/fabrication/JLCPCB_HDI_20260925/QSTL_24DC_6RF_HDI_Gerber_20260925.zip). The ZIP has 96 through holes and 480 L5-L6 blind holes. Native OutJob retains its 20260924 working directory; `script/pcb_end_mounts_20260925/package_m1_cam.py` validates and copies the fresh output to the 20260925 delivery. No new supplier upload was made.

The [current Inventor M1 review](QSTL_24DC_4MW_PCB/Mechanical_Assembly/ZIF_M1_Review/README.md) uses supplied **KS B 1021 M1 x 4** slotted round/pan-head screws (pitch 0.25 mm, head diameter 2.00 mm). Nominal housing clearance is 0.627624 mm, and the centered cable has **0.30 mm clearance to each drilled hole**; see the [dimensioned view](QSTL_24DC_4MW_PCB/Mechanical_Assembly/ZIF_M1_Review/ZIF_Cable_Hole_Clearance.png). Only user-permitted head/cable contact remains in the native fit. Cable height and deformation are not fully verified; this is a nominal fit check. M1.6 and M2 review folders are historical.
'''.rstrip()+t[b:]
t=t.replace('docs/ZIF_M1p6_mount_validation.json','docs/ZIF_M1_mount_validation.json')
t=t.replace('All eight SMP positions, six mounting holes','All eight SMP positions, six original mounting holes')
root.write_text(t,encoding='utf-8')

(F/'README.md').write_text('''# Current PCB CAM export — 2026-09-25, M1 revision

`QSTL_24DC_6RF_HDI_Gerber_20260925.zip` contains the current native Altium Gerbers and separate through/blind drills. M1 mounts use 1.20 mm plated drills and 1.60 mm lands at (1.05,1.20) and (18.45,1.20) mm, pitch 17.40 mm, direct GND with no thermal relief or paste. Board size stays 19.5 x 67.9 mm.

Saved/reopened DRC: 16 checked rules, zero violations; zero unrouted connections. Independent saved-copper graph: all 37 nets connected. CAM has 96 through holes, including two 1.20 mm mounts, and 480 blind laser holes restricted to L5-L6. Bottom non-through milling remains 4.3 x 4.3 mm, R0.5, depth 1.2 mm; DC ground clearance remains 0.20 mm.

The native Inventor review uses real KS B 1021 M1 x 4 slotted pan/round-head screws. Nominal housing clearance is 0.627624 mm; cable-to-hole clearance is 0.30 mm per side in top projection. Only the permitted head/cable-envelope contact remains. Cable height and deformation are assumptions; see `../../Mechanical_Assembly/ZIF_M1_Review/README.md`. The previous M1.6 ZIP is archived in `script/pcb_end_mounts_20260925/superseded_m1p6_cam/`. No new supplier upload or order was made.
''',encoding='utf-8')

(H/'README.md').write_text('''# M1 ZIF-end PCB mounts

Current geometry: MH7/MH8 at X1.05/18.45, Y1.20 mm, with 1.20 mm plated drills, 1.60 mm lands and 17.40 mm pitch. Original outline and six mounts persist. All eight mounts use direct GND, no thermal relief and no paste.

`ApplyM1.pas` records the original-PCB mutation, native repour, save/reopen DRC, paste audit and schematic check. `before_m1.PcbDoc` preserves the immediate M1.6 predecessor. These mutation scripts are one-time records; do not rerun blindly. Historical M2/M1.6 mutation and review scripts are superseded.

Current saved-file validation: `verify_m1_saved.py`, together with `../dc_even_zif_20260923/audit_connectivity.py` and `../dc_ground_pour_20260924/preview_ground.py --saved`. It verifies original pads/routes/vias/components, masks, GND/QD conditions, schematic mapping, DRC and independent continuity.

`generate_m1_round_member.ps1` obtains the genuine KS B 1021 M1 x 4 member. `prepare_m1_review.py` exports saved PCB and embedded connector geometry, plus a dimensional cable envelope. `build_m1_review.ps1` creates/reopens the native Inventor assembly, checks interference/minimum distances, and exports STEP and views. Run Inventor COM scripts using Windows PowerShell 5.1. `render_m1_clearance.py` provides the explicit dimensioned top view; `finalize_m1_review.py` links reports and updates documentation. The output is `Mechanical_Assembly/ZIF_M1_Review/`.

After native Altium `HDI_Fabrication.OutJob` export, `package_m1_cam.py` checks fresh output, 96 through holes, 480 L5-L6 blind holes, DC GND Gerber geometry and preserved silkscreen, then builds the current 18-file ZIP. `prepare_m1_deliverables.py` records how the M1-specific scripts were adapted from the preceding review; do not rerun it over finalized files.
''',encoding='utf-8')
sr=H.parent/'README.md';t=sr.read_text(encoding='utf-8').replace('The latest M1.6 ZIF-end mounts','The latest M1 ZIF-end mounts');sr.write_text(t,encoding='utf-8')
print(json.dumps({'hardware':'KS B 1021 M1 x 4','pcb':sha(board),'hole_gap_mm':clear['signed_hole_edge_to_cable_edge_clearance_mm'],'housing_gap_mm':fit['distances'],'drc_violations':validation['DRC']['violations'],'gerber_zip_sha256':report['gerber_zip_sha256']},indent=2))
