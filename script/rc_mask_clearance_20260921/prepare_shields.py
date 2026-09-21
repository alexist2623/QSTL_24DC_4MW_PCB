"""Rebuild shielding around saved relocated components using hole-edge offsets."""
from pathlib import Path
import sys,json,math,shutil,importlib.util,collections
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB';OLD=H.parent/'shield_rc_ring_20260921';DENSE=H.parent/'shield_spacing_20260921'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,sha,UNIT
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions,trackkey,arckey
source=P/(B+'.PcbDoc');spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=source;n=m.read_native()
assert len(n['vias'])==60
wanted=json.loads((H/'planned_native.json').read_text())
assert collections.Counter(map(trackkey,n['tracks']))==collections.Counter(map(trackkey,wanted['tracks']))
assert collections.Counter(map(arckey,n['arcs']))==collections.Counter(map(arckey,wanted['arcs']))
for p in n['pads']:
    a=next(a for a in wanted['pads'] if a['component']==p['component'] and a['number']==p['number'] and (p['component'] is not None or math.dist((a['x'],a['y']),(p['x'],p['y']))<.001))
    assert math.dist((p['x'],p['y']),(a['x'],a['y']))<6*UNIT,(p,a)
(H/'after_move_native.json').write_text(json.dumps(n,indent=2))
prefix=(DENSE/'prepare.py').read_text().split('WIDTH=.11;')[1].split('# Ring increments use')[0]
prefix='WIDTH=.11;'+prefix
prefix=prefix.replace('OFFSET=.51','OFFSET=.435').replace("(OLD/'plan.json')","(H/'plan.json')")
prefix=prefix.replace("rf_copper_edge_gap_mm=Point(x,y).distance(center)-WIDTH/2-LAND/2","rf_copper_edge_gap_mm=Point(x,y).distance(center)-WIDTH/2-LAND/2,rf_hole_edge_gap_mm=Point(x,y).distance(center)-WIDTH/2-HOLE/2")
exec(compile(prefix,'shield_geometry_base','exec'))
body=(OLD/'prepare.py').read_text().split('from shapely.geometry import mapping')[1].split("req=P/'docs/DESIGN_REQUIREMENTS.md'")[0]
body='from shapely.geometry import mapping'+body
body=body.replace("p['size_x']/2+.33+LAND/2","p['size_x']/2+.33+HOLE/2").replace('buffer(.33+LAND/2','buffer(.33+HOLE/2')
exec(compile(body,'shield_component_rings','exec'))
# Generate a native script from the validated shield-only template.
template=(DENSE/'prepare.py').read_text().split("pas='''",1)[1].split("'''",1)[0]
helper=(H/'ApplyMove.pas').read_text();findnet=helper[helper.index('Function FindNet'):helper.index('Procedure SaveCurrent')]
template=template.replace('Procedure ApplyShieldSpacing;',findnet+'\nProcedure ApplyShieldSpacing;')
template=template.replace('N:=0;GN:=Nil;','N:=0;GN:=FindNet(B,\'GND\');')
for k,v in {'LOGPATH':str(H/'shield_native.txt'),'PCBDOC':str(source),'OLDCOUNT':'0','NEWCOUNT':str(len(vias)),'ADDALL':'\n'.join(f"AddShield(B,GN,{round(v['x']/UNIT)},{round(v['y']/UNIT)});" for v in vias)}.items():template=template.replace(k,v)
(H/'ApplyShields.pas').write_text(template,encoding='utf-8')
for name in ('audit_connectivity.py','verify_final.py','AuditPaste.pas','ReopenAudit.pas','read_drc.py','fabrication_notes.py','publish_outputs.py','verify_fabrication.py'):
    s=(OLD/name).read_text().replace('shield_rc_ring_20260921',H.name).replace('Shield_RC_Ring_DRC.html','RC_Mask_Clearance_DRC.html').replace('shield_rc_ring_reopen_check.txt','rc_mask_clearance_reopen_check.txt').replace('Shield_RC_Ring_validation.json','RC_Mask_Clearance_validation.json')
    s=s.replace('(22,147,37,473)',f'(22,147,37,{60+len(vias)})').replace('len(shield)==413',f'len(shield)=={len(vias)}').replace('len(holes)==413',f'len(holes)=={len(vias)}').replace('413 GND shields',f'{len(vias)} GND shields').replace('413 saved L5-L6 vias',f'{len(vias)} saved L5-L6 vias')
    if name=='verify_final.py':
        s=s.replace("check(properties(s['Components6/Data'])==properties(old['Components6/Data']),'Component placement metadata changed')", "\nfor a,b in zip(properties(s['Components6/Data']),properties(old['Components6/Data'])):\n    name=a['SOURCEDESIGNATOR']\n    for key in a:\n        if name in plan['component_y_moves_mm'] and key in ('X','Y'):continue\n        check(a[key]==b.get(key),'Component metadata changed '+name+' '+key)\n")
        s=s.replace("edgegap>=.33-6*UNIT","edgegap>=.255-6*UNIT").replace("'RF fence edge gap'","'RF fence land-edge gap (hole-edge equivalent 0.33 mm)'")
        s=s.replace("shield_edge_gap_min_mm=edgegap","shield_land_edge_gap_min_mm=edgegap,shield_hole_edge_gap_min_mm=edgegap+.075")
    if name=='publish_outputs.py':s=s.replace('(0,25,19.5,52)','(0,25,19.5,54)').replace('(.5,37,19,49.8)','(.5,37,19,53.5)')
    if name=='fabrication_notes.py':s=s.replace('0.33 mm RF-copper-edge to via-land-edge gap','0.33 mm RF-copper-edge to laser-hole-edge gap').replace('Equal-angle 14-position grids surround each active SMP centre; only two symmetric RF-exit positions are omitted, leaving 12 vias and approximately 0.425 mm centre chords','Equal-angle 13-position grids surround each active SMP centre; two symmetric RF-exit positions are omitted, leaving 11 vias with approximately 0.421 mm centre chords')
    (H/name).write_text(s,encoding='utf-8')
print('Native placement and routes match. Prepared',len(vias),'shields.')
