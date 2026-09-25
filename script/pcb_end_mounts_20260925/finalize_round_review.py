"""Publish the standard round-head review and retire socket-head conclusions."""
from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';out=P/'Mechanical_Assembly/ZIF_M1p6_Review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
fit=json.loads((out/'inventor_fit_round.json').read_text(encoding='utf-8-sig'))
member=fit['hardware'];clear=json.loads((out/'cable_hole_clearance.json').read_text())
board=P/'QSTL_24DC_4MW_PCB.PcbDoc'
assert fit['pcb_sha256']==clear['pcb_sha256']==sha(board)
assert member['family']=='ISO 7045 H' and member['is_content_member']
assert sha(Path(member['file'])).upper()==member['sha256']
assert member['values']['NND']=='1.6' and member['values']['PTC']=='0.35'
assert fit['placement_preserved'] and fit['saved_and_reopened']
housing=[r for r in fit['interferences'] if r['first']=='Molex_502598_5193' or r['second']=='Molex_502598_5193']
assert len(housing)==2
shutil.copy2(out/'inventor_fit_round.json',out/'inventor_fit.json')
prior=json.loads((H/'superseded_socket_head/final_pcb_fit_validation.json').read_text())
report={k:v for k,v in prior.items() if k not in ('artifacts','head_to_non_GND_copper','nominal_connector_gap_mm','gap_after_possible_shank_shift_mm','fit_status','final_change_after_CAD_export')}
report.update(hardware_family='ISO 7045 H',hardware_member='M1.6 x 4 - H',thread_pitch_mm=.35,
    head_diameter_mm=3.2,head_height_mm=1.3,nominal_connector_gap_mm=0,
    fit_status='Both round screw heads intersect the ZIF housing at the existing saved hole positions.',
    housing_interferences=housing,cable_hole_plan_clearance=clear,
    unchanged_pcb_and_gerber=True,tolerance_safe_fit_confirmed=False,
    artifacts={f.name:sha(f) for f in out.iterdir() if f.suffix.lower() in ('.iam','.ipt','.step','.png','.svg')})
report['cad_source_pcb_sha256']=fit['pcb_sha256']
(out/'final_pcb_fit_validation.json').write_text(json.dumps(report,indent=2))
(out/'README.md').write_text('''# ZIF M1.6 round-head mounting review

Latest correction, 2026-09-25: the current `ZIF_M1p6_Fit.iam` and matching STEP use two unmodified Autodesk Inventor Content Center **ISO 7045 H M1.6 x 4** cross-recessed pan/round-head screws. Thread is M1.6 x 0.35 - 6g; supplied head diameter 3.2 mm and height 1.3 mm. No washers or custom screw geometry. Prior ISO 4762 conclusions and source assembly are archived under `script/pcb_end_mounts_20260925/superseded_socket_head/`.

The PCB remains unchanged: 1.8 mm plated drills at (1.60,1.20) and (17.90,1.20) mm, pitch 16.30 mm; lands 2.20 mm, direct GND, no thermal relief or paste. Current Gerbers remain valid representations of this unchanged PCB geometry.

## Cable-to-hole dimensions

The centered 51-contact cable envelope is 15.60 mm wide (X1.95 to X17.55 mm). The space between the inward hole edges is 14.50 mm. Signed lateral clearance is therefore **-0.55 mm per side**, i.e. the cable and drilled holes overlap by 0.55 mm on each side in top projection. This is not a positive clearance. The cable is above the PCB, so a top-projection overlap is not itself a 3D collision with the hole void.

`ZIF_Cable_Hole_Clearance.png` / `.svg` show a dimensioned plan and enlarged edge detail with screw heads omitted. `ZIF_Holes_Cable_Native_Top.png` is a native Inventor top view with screws temporarily hidden and the cable temporarily transparent. `ZIF_M1p6_Round_Oblique.png` shows the actual assembled round-head hardware.

## Native interference result

The saved/reopened Inventor assembly has two screw-head/cable-envelope intersections (allowed as cable pressure by the user) **and two screw-head/ZIF-housing intersections** (about 0.00952 mm3 each). The current positions therefore do not provide an interference-free fit with the requested round-head screws. No hole relocation was made in this correction; the collision is reported rather than hidden by changing the hardware or geometry.

The cable is a dimensional envelope, 0.20 mm reinforced thickness. Center height 0.47 mm above PCB is an unverified placement assumption, and flex/deformation is not modeled. Screw length 4 mm is a review assumption; mating threaded support/nut was not specified. `inventor_fit.json` and `inventor_fit_round.json` are the current native results; `final_pcb_fit_validation.json` links them to the unchanged PCB and actual Content Center member hash.
''',encoding='utf-8')
req=P/'docs/DESIGN_REQUIREMENTS.md';t=req.read_text()
needle='- Latest ZIF fastener correction (2026-09-25):'
start=t.index(needle);end=t.index('\n\n',start)
t=t[:end]+' Implemented with Content Center ISO 7045 H M1.6 x 4 (0.35 mm pitch, 3.2 mm head diameter, 1.3 mm head height). Saved/reopened Inventor finds head-to-housing intersection on both sides. The 15.6 mm cable overlaps each 1.8 mm hole by 0.55 mm in top projection; inside-hole clear width is 14.5 mm. Current positions are unchanged and not interference-free.'+t[end:]
req.write_text(t,encoding='utf-8')
readme=R/'README.md';t=readme.read_text();a=t.index('The [Inventor M1.6 fit review]');b=t.index('\n\n',a)
t=t[:a]+'The [Inventor M1.6 fit review](QSTL_24DC_4MW_PCB/Mechanical_Assembly/ZIF_M1p6_Review/README.md) now uses actual Content Center ISO 7045 H M1.6 x 4 round/pan-head screws, superseding the cylindrical ISO 4762 heads. At the unchanged hole positions both heads intersect the ZIF housing. The 15.6 mm cable overlaps each hole by 0.55 mm in Top projection; see the [dimensioned detail](QSTL_24DC_4MW_PCB/Mechanical_Assembly/ZIF_M1p6_Review/ZIF_Cable_Hole_Clearance.png). This arrangement is not interference-free.'+t[b:]
readme.write_text(t,encoding='utf-8')
fab=P/'fabrication/JLCPCB_HDI_20260925/README.md';t=fab.read_text(encoding='utf-8');a=t.index('This is an electrically checked export')
t=t[:a]+'This is an electrically checked export, not a mechanical fit approval. The latest Inventor review uses the requested Content Center ISO 7045 H M1.6 round/pan-head screws and finds head/housing intersection on both sides at the unchanged hole positions. Cable-to-hole overlap in Top projection is 0.55 mm per side. See `../../Mechanical_Assembly/ZIF_M1p6_Review/README.md`. No new supplier upload or order has been made.\n'
fab.write_text(t,encoding='utf-8')
readme=H/'README.md';t=readme.read_text();t+='''

## Round-head correction

`generate_round_member.ps1` obtains the real ISO 7045 H M1.6 x 4 member. `update_round_review.ps1` replaces only the two screw occurrences, verifies unchanged transforms, saves/reopens, checks interference and exports updated STEP/views. `render_cable_hole_clearance.py` dimensions the 0.55 mm cable/hole overlap in XY. `finalize_round_review.py` publishes current reports and supersedes the socket-head conclusions above. The latest configuration has two actual head/housing intersections; do not call it interference-free. Historical `build_review.ps1` / `finalize_review.py` reproduce the superseded socket-head review and must not be rerun as the current pipeline.
''';readme.write_text(t,encoding='utf-8')
print(json.dumps({'pcb_unchanged':True,'standard_round_head':member['family'],'housing_collisions':len(housing),'plan_clearance_mm':clear['signed_hole_edge_to_cable_edge_clearance_mm']},indent=2))
