"""Link the saved CAD review to the final PCB and document fit limitations."""
from pathlib import Path
import json,sys,math,struct,zlib,hashlib
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
H=Path(__file__).resolve().parent; R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,pads_stream,binary_records,UNIT,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route
out=P/'Mechanical_Assembly/ZIF_M1p6_Review'
inputs=json.loads((out/'model_inputs.json').read_text())
fit=json.loads((out/'inventor_fit.json').read_text(encoding='utf-8-sig'))
pcb=P/'QSTL_24DC_4MW_PCB.PcbDoc';s=snapshot(pcb)
ps=pads_stream(s['Pads6/Data']);ns=properties(s['Nets6/Data']);cs=properties(s['Components6/Data'])
ci=next(i for i,c in enumerate(cs) if c['SOURCEDESIGNATOR']=='J1')
for row in binary_records(s['ComponentBodies6/Data'],12):
    raw=row['body']
    if struct.unpack_from('<H',raw,7)[0]!=ci:continue
    a=raw.index(b'V7_LAYER=');n=struct.unpack_from('<I',raw,a-4)[0]&0xffffff
    body=dict(x.split('=',1) for x in raw[a:a+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
    assert body==inputs['body']
    mi=next(i for i,m in enumerate(properties(s['Models/Data'])) if m['ID']==body['MODELID'])
    assert zlib.decompress(s[f'Models/{mi}'])==(out/'J1_embedded.step').read_bytes()
    break
else:raise AssertionError('Missing connector body')
for m in inputs['mounts']:
    pad=next(p for p in ps if p['component']==65535 and p['number']==m['name'])
    assert [pad['coords'][i]*UNIT for i in (0,1,8)]==[m['x'],m['y'],m['drill']]
assert sha(Path(fit['hardware']['file'])).upper()==fit['hardware']['sha256']
top=[]
for p in ps:
    if p['layer'] not in (1,74) or (p['net']!=65535 and ns[p['net']]['NAME']=='GND'):continue
    x,y,sx,sy=[v*UNIT for v in p['coords'][:4]]
    geom=translate(rotate(box(-sx/2,-sy/2,sx/2,sy/2),p['rotation'],origin=(0,0)),x,y)
    if p['layer']==74:geom=Point(x,y).buffer(max(sx,sy)/2,quad_segs=256)
    top.append(((cs[p['component']]['SOURCEDESIGNATOR'] if p['component']!=65535 else 'MOUNT')+'-'+p['number'],geom))
ts,ars,vs=read_route(s,ns)
for t in ts:
    if t['layer']==1 and t['net']!='GND':top.append(('track '+t['net'],LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2)))
for v in vs:
    if v['net']!='GND':top.append(('via '+v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=256)))
clear=[]
for m in inputs['mounts']:
    head=Point(m['x'],m['y']).buffer(1.5,quad_segs=512)
    gap,label=min((head.distance(g),label) for label,g in top)
    clear.append(dict(mount=m['name'],head_to_non_GND_copper_mm=gap,nearest=label))
    assert gap>0
nominal=min(d['connector_distance_mm'] for d in fit['distances'])
play=(1.8-1.6)/2
report=dict(final_pcb_sha256=sha(pcb),cad_source_pcb_sha256=fit['pcb_sha256'],
    connector_body_and_placement_match=True,embedded_connector_model_bytes_match=True,
    both_mount_locations_and_drills_match=True,standard_screw_bytes_unchanged=True,
    final_change_after_CAD_export='Top silkscreen pin-1 marker moved; physical fit geometry verified unchanged.',
    nominal_connector_gap_mm=nominal,nominal_radial_shank_play_mm=play,
    gap_after_possible_shank_shift_mm=nominal-play,
    tolerance_safe_fit_confirmed=False,
    fit_status='Nominal centered screw clears housing; radial hole play exceeds clearance and can cause contact. No tolerance-safe fit claim.',
    head_to_non_GND_copper=clear,
    cable_height_status='0.47 mm center above PCB is a placement assumption; detailed section verification and flex deformation are not modeled.',
    cable_width_mm=15.6,cable_reinforced_thickness_mm=.2,
    screw_length_status='M1.6 x 4 used for clearance review; mating threaded support/nut and required engagement are not specified.',
    artifacts={f.name:sha(f) for f in out.iterdir() if f.suffix.lower() in ('.iam','.ipt','.step','.png')})
(out/'final_pcb_fit_validation.json').write_text(json.dumps(report,indent=2))
text=f'''# ZIF M1.6 mounting review

The original PCB now has two M1.6 clearance mounts: plated drill 1.8 mm, copper land 2.2 mm, centers (1.60, 1.20) and (17.90, 1.20) mm. Pitch is 16.30 mm. The 19.5 x 67.9 mm outline is unchanged. Minimum nominal drill-to-edge web is 0.30 mm at the end and 0.70 mm at the sides. Mounts connect directly to GND, without thermal relief or paste.

`ZIF_M1p6_Fit.iam` contains the saved PCB end, the actual J1 embedded Molex 502598-5193 model, a dimensional FPC envelope, and two unmodified Inventor Content Center ISO 4762 M1.6 x 4 screws, M1.6 x 0.35 - 6g. Head diameter is 3.0 mm and head height is 1.6 mm. No washers. Screw length is a review assumption; the mating support/nut was not specified.

Native Inventor interference analysis finds no screw/housing or screw/PCB intersection at centered nominal placement. Minimum screw/housing distance is {nominal:.6f} mm. However, 1.8 mm holes around 1.6 mm shanks allow 0.10 mm nominal radial shift, greater than that gap. Housing contact is possible with screw displacement, even before manufacturing tolerances. This is not a tolerance-safe fit approval.

The two screw heads intersect the undeformed cable envelope, which the user explicitly permits as cable pressure. Cable width is 15.6 mm and reinforced thickness is 0.20 mm; its center at 0.47 mm above the PCB is an unverified placement assumption. This is not a detailed production cable or a flex/clamping simulation. No screw-head footprint overlaps non-GND Top copper; see `final_pcb_fit_validation.json` for measured conservative plan-view distances.

The connector and hardware are native imported/supplied CAD. The PCB end is simplified to substrate and relevant holes. Pictures are native Inventor view exports. `inventor_fit.json` records saved/reopened assembly checks; `final_pcb_fit_validation.json` verifies that its physical inputs still match the final PCB after the silkscreen-only marker correction.

The final PCB passes 16 native DRC rules, has zero stored unrouted connections, and passes independent connectivity for all 37 nets. Fresh Gerber/through-drill/blind-drill files are in `../../fabrication/JLCPCB_HDI_20260925/`. There are 96 through holes, including the two 1.8 mm mounts, and 480 L5-L6-only laser blind holes.
'''
(out/'README.md').write_text(text,encoding='utf-8')
req=P/'docs/DESIGN_REQUIREMENTS.md'
text=req.read_text().replace('actual supplied M2 screw hardware','actual supplied M1.6 screw hardware')
marker='- Implemented ZIF end mounts (2026-09-25):'
if marker not in text:
    text=text.replace('## Mechanical geometry and placement\n','## Mechanical geometry and placement\n\n'+marker+' MH7/MH8 at (1.60,1.20) and (17.90,1.20) mm, pitch 16.30 mm, plated drill 1.80 mm and land 2.20 mm. Direct GND, no thermal relief or paste, unchanged board outline. Fit review uses unmodified Content Center ISO 4762 M1.6 x 4, pitch 0.35 mm, no washer. Nominal housing gap is only 0.025 mm, less than 0.10 mm radial shank play; housing contact remains possible and tolerance-safe assembly is not confirmed. Cable-head contact is permitted; cable is a dimensional envelope. See Mechanical_Assembly/ZIF_M1p6_Review/README.md.\n')
req.write_text(text,encoding='utf-8')
# Correct the script comment to distinguish an unverified placement assumption
# from the manufacturer-confirmed cable width/thickness recommendation.
f=H/'prepare_review.py';t=f.read_text().replace('# The manufacturer section gives a nominal 0.47 mm cable reference above seating plane.','# Cable center height 0.47 mm above the PCB is an unverified placement assumption.')
f.write_text(t,encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='artifacts'},indent=2))
